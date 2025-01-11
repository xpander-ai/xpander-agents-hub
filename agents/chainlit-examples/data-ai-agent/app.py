import json
import os
import chainlit as cl
from typing import Union, List, Dict, Any
from openai import AsyncOpenAI

from xpander_sdk import XpanderClient, ToolCallType, LLMProvider
from youtube_transcript_api import YouTubeTranscriptApi

import csv
import xml.etree.ElementTree as ET
from io import StringIO
import pathlib
import tiktoken
import openai
import time

# ------------------------------
# 0) Constants & Globals
# ------------------------------
PRIMARY_EMBED_MODEL = "text-embedding-3-large"
FALLBACK_EMBED_MODEL = "text-embedding-ada-002"
TOKEN_THRESHOLD = 4000

EMBED_CACHE_FILE = "embedding_cache.json"
VECTOR_DB_FILE = "vector_db.json"
KNOWLEDGE_REPO_DIR = "knowledge_repo"

MSG_LARGE = (
    "The result was too large and has been stored in the vector DB. "
    "Use 'search-long-response' to retrieve relevant chunks."
)

# We'll store embeddings & vector DB in memory:
EMBED_CACHE: Dict[str, List[float]] = {}
VECTOR_DB: List[Dict[str, Any]] = []

# ------------------------------
# 0.1) Embedding & VectorDB Persistence
# ------------------------------
def load_embedding_cache() -> Dict[str, List[float]]:
    if os.path.exists(EMBED_CACHE_FILE):
        try:
            with open(EMBED_CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return {k: v for k, v in data.items() if isinstance(v, list)}
        except:
            pass
    return {}

def save_embedding_cache(cache_data: Dict[str, List[float]]):
    try:
        with open(EMBED_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache_data, f)
    except Exception as e:
        print(f"[WARN] Could not save embedding cache: {e}")

def load_vector_db():
    if os.path.exists(VECTOR_DB_FILE):
        try:
            with open(VECTOR_DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
        except:
            pass
    return []

def save_vector_db(vdb: List[Dict[str, Any]]):
    try:
        with open(VECTOR_DB_FILE, "w", encoding="utf-8") as f:
            json.dump(vdb, f, indent=2)
    except Exception as e:
        print(f"[WARN] Could not save vector DB: {e}")

# ------------------------------
# 1) Setup OpenAI + xpander
# ------------------------------
api_key = os.environ.get("OPENAI_API_KEY")
client = AsyncOpenAI(api_key=api_key)

xpanderAPIKey = os.environ.get("XPANDER_API_KEY", "")
xpanderAgentID = os.environ.get("XPANDER_AGENT_ID", "")

xpander_client = XpanderClient(api_key=xpanderAPIKey)
xpander_agent = xpander_client.agents.get(agent_id=xpanderAgentID)

openai.api_key = api_key

def count_tokens(text: str, model_name: str = "gpt-4o") -> int:
    try:
        enc = tiktoken.encoding_for_model(model_name)
    except:
        enc = tiktoken.encoding_for_model("gpt-3.5-turbo")
    return len(enc.encode(text))

# ------------------------------
# 2) RAG: Embedding + Vector Search
# ------------------------------
def embed_text(text: str, max_retries=3) -> List[float]:
    if text in EMBED_CACHE:
        return EMBED_CACHE[text]

    candidate_models = [PRIMARY_EMBED_MODEL, FALLBACK_EMBED_MODEL]
    for model_name in candidate_models:
        for attempt in range(max_retries):
            try:
                resp = openai.embeddings.create(input=text, model=model_name)
                embedding = resp.data[0].embedding
                EMBED_CACHE[text] = embedding
                save_embedding_cache(EMBED_CACHE)
                return embedding
            except Exception as e:
                print(f"[ERROR] embed_text: model={model_name}, attempt={attempt+1}, error={e}")
                if attempt == max_retries - 1:
                    break
                time.sleep(2)
    print("[WARN] All embedding attempts failed. Returning empty list.")
    EMBED_CACHE[text] = []
    save_embedding_cache(EMBED_CACHE)
    return []

def add_text_to_vector_db(response_text: str, source: str):
    """
    Splits 'response_text' into ~500-token chunks, embed each chunk,
    and appends to VECTOR_DB. Then persist to disk.
    """
    chunk_size = 500
    enc = tiktoken.encoding_for_model("gpt-4o")
    tokens = enc.encode(response_text)

    new_entries = []
    for i in range(0, len(tokens), chunk_size):
        chunk = tokens[i : i + chunk_size]
        text_chunk = enc.decode(chunk)
        embedding = embed_text(text_chunk)
        entry_id = f"{source}-{i}"
        new_entries.append({
            "id": entry_id,
            "source": source,
            "text": text_chunk,
            "embedding": embedding
        })

    VECTOR_DB.extend(new_entries)
    save_vector_db(VECTOR_DB)

def vector_search(query: str, top_k: int = 3) -> List[str]:
    if not VECTOR_DB:
        return ["No vector data available."]
    query_emb = embed_text(query)
    if not query_emb:
        return ["Error creating query embedding."]

    import numpy as np
    def cos_sim(a, b):
        a_np = np.array(a)
        b_np = np.array(b)
        denom = (np.linalg.norm(a_np) * np.linalg.norm(b_np))
        if denom == 0:
            return 0.0
        return float(np.dot(a_np, b_np) / denom)

    scored = []
    for entry in VECTOR_DB:
        emb = entry["embedding"]
        if not emb:
            continue
        score = cos_sim(query_emb, emb)
        scored.append((score, entry["text"], entry["source"]))

    scored.sort(key=lambda x: x[0], reverse=True)
    top_results = scored[:top_k]

    final_responses = []
    for score, text_chunk, source in top_results:
        snippet = f"[From {source} | Score={score:.4f}] {text_chunk}"
        final_responses.append(snippet)

    return final_responses

# ------------------------------
# 3) File Helpers
# ------------------------------
def is_within_current_directory(file_path: str) -> bool:
    base_dir = pathlib.Path.cwd().resolve()
    target_path = (base_dir / file_path).resolve()
    return str(target_path).startswith(str(base_dir))

def read_file_content(file_path: str) -> str:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except:
        return ""

def read_file(file_path: str, output_format: str = "string") -> dict:
    """
    Always ensure we look in knowledge_repo unless user path already includes it.
    """
    if not file_path.startswith(KNOWLEDGE_REPO_DIR):
        file_path = os.path.join(KNOWLEDGE_REPO_DIR, file_path)

    if not is_within_current_directory(file_path):
        return {"error": "Access outside the current directory is not allowed."}
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            file_content = f.read()

        if len(file_content) > 10000:
            partial_content = file_content[:1000]
            return {
                "info": (
                    "File is very large; returning first 1000 characters only. "
                    "Use vector search if you need more detail."
                ),
                "content": partial_content
            }

        if output_format == "json":
            try:
                return {"content": json.loads(file_content)}
            except json.JSONDecodeError as e:
                return {"error": f"Failed to parse JSON: {str(e)}"}
        elif output_format == "csv":
            rows = list(csv.reader(StringIO(file_content)))
            return {"content": rows}
        elif output_format == "xml":
            try:
                tree = ET.ElementTree(ET.fromstring(file_content))
                root = tree.getroot()
                return {"content": ET.tostring(root, encoding="unicode")}
            except ET.ParseError as e:
                return {"error": f"Failed to parse XML: {str(e)}"}
        else:
            return {"content": file_content}

    except FileNotFoundError:
        return {"error": f"File not found: {file_path}"}
    except Exception as e:
        return {"error": str(e)}

def write_file(file_path: str, content: Union[str, dict, list], file_type: str) -> dict:
    """
    Forces writing to knowledge_repo folder unless path already includes it.
    """
    if not file_path.startswith(KNOWLEDGE_REPO_DIR):
        file_path = os.path.join(KNOWLEDGE_REPO_DIR, file_path)

    if not is_within_current_directory(file_path):
        return {"error": "Access outside the current directory is not allowed."}
    try:
        # Replace placeholder with real transcript if found in session
        from chainlit import user_session
        MSG_PLACEHOLDER = "The transcript content will be fetched and written here."
        if isinstance(content, str):
            if content.strip().startswith(MSG_LARGE) or content.strip() == MSG_PLACEHOLDER:
                cached_outputs = user_session.get("cached_outputs") or {}
                if "transcript_text" in cached_outputs:
                    content = cached_outputs["transcript_text"]

        # Actually write the file
        if file_type.lower() == "json":
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(content, f, indent=2)
        elif file_type.lower() == "xml":
            root = ET.Element("root")
            ET.SubElement(root, "content").text = str(content)
            tree = ET.ElementTree(root)
            tree.write(file_path, encoding="unicode", xml_declaration=True)
        elif file_type.lower() == "csv":
            if isinstance(content, str):
                content = list(csv.reader(StringIO(content)))
            with open(file_path, "w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerows(content)
        else:
            with open(file_path, "w", encoding="utf-8") as f:
                if isinstance(content, str):
                    f.write(content)
                else:
                    f.write(str(content))

        return {"success": f"File written to {file_path}."}
    except Exception as e:
        return {"error": str(e)}

# ------------------------------
# 4) Tools
# ------------------------------
def fetch_youtube_transcript(video_url: str) -> dict:
    try:
        if "youtube.com/watch?v=" in video_url:
            video_id = video_url.split("v=")[-1].split("&")[0]
        elif "youtu.be/" in video_url:
            video_id = video_url.split("/")[-1]
        else:
            return {"error": "Invalid YouTube URL pattern."}

        transcript_entries = YouTubeTranscriptApi.get_transcript(video_id)
        transcript_text = " ".join([e["text"] for e in transcript_entries])
        return {"transcript": transcript_text}
    except Exception as e:
        return {"error": str(e)}

def search_long_response(query: str, top_k: int = 3) -> dict:
    results = vector_search(query, top_k=top_k)
    return {"chunks": results}

local_tools = [
    {
        "type": "function",
        "function": {
            "name": "fetch-youtube-transcript",
            "description": "Fetches the transcript for a given YouTube URL.",
            "parameters": {
                "type": "object",
                "properties": {
                    "video_url": {
                        "type": "string",
                        "description": "A valid YouTube video URL."
                    }
                },
                "required": ["video_url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write-file",
            "description": "Writes content to a local file. Always stored in the knowledge_repo folder unless you explicitly prefix the path with 'knowledge_repo/'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filePath": {
                        "type": "string",
                        "description": "Filename or path. Will be forced into the knowledge_repo folder unless it already has that prefix."
                    },
                    "fileContent": {
                        "type": "string",
                        "description": "The content to write."
                    },
                    "fileType": {
                        "type": "string",
                        "description": "File type (json, xml, csv, txt)."
                    }
                },
                "required": ["filePath","fileContent","fileType"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read-file",
            "description": "Reads a local file from knowledge_repo unless path already includes it. Returns a partial if the file is huge.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filePath": {
                        "type": "string",
                        "description": "Path to the file. Usually just the filename is enough."
                    },
                    "outputFormat": {
                        "type": "string",
                        "description": "Desired format: 'string','json','csv','xml'."
                    }
                },
                "required": ["filePath"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search-long-response",
            "description": "Query large responses stored in vector DB for relevant chunks.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query."
                    },
                    "top_k": {
                        "type": "number",
                        "description": "Number of chunks to retrieve."
                    }
                },
                "required": ["query"]
            }
        }
    }
]

xpander_agent.add_local_tools(local_tools)
remote_tools = xpander_agent.get_tools()
tools = remote_tools

# ------------------------------
# 5) Initialization
# ------------------------------
def init_jarvis_knowledge():
    global EMBED_CACHE, VECTOR_DB
    EMBED_CACHE = load_embedding_cache()
    loaded_db = load_vector_db()

    VECTOR_DB.clear()
    VECTOR_DB.extend(loaded_db)

    # Make sure knowledge_repo folder exists
    repo_path = pathlib.Path(KNOWLEDGE_REPO_DIR)
    if not repo_path.exists():
        repo_path.mkdir(parents=True, exist_ok=True)

    print(f"[INIT] Loaded {len(VECTOR_DB)} entries from {VECTOR_DB_FILE}. "
          f"Embedding cache size: {len(EMBED_CACHE)}.")

# ------------------------------
# 6) Chainlit Setup
# ------------------------------
MAX_ITER = 5
cl.instrument_openai()

@cl.on_chat_start
def start_chat():
    init_jarvis_knowledge()

    cl.user_session.set("cached_outputs", {})
    cl.user_session.set("message_history", [
        {
            "role": "system",
            "content": (
                "You are an advanced AI assistant with xpander's tools + local tools. "
                "You have a persistent memory of local files & transcripts in your vector DB. "
                "Whenever asked a question, you can optionally do a 'search-long-response' to find relevant info. "
                "If a user provides a new YouTube link or file, embed it into your memory for future use. "
            ),
        }
    ])

@cl.step(type="tool")
async def xpander_tool(llm_response, message_history):
    tool_calls = XpanderClient.extract_tool_calls(llm_response=llm_response.model_dump())
    cached_outputs = cl.user_session.get("cached_outputs")

    for i, tool_call in enumerate(tool_calls):
        current_step = cl.context.current_step
        current_step.name = tool_call.name
        current_step.input = tool_call.payload

        if tool_call.type == ToolCallType.LOCAL:
            fn_args = llm_response.choices[0].message.tool_calls[i].function.arguments
            local_params = json.loads(fn_args)
            current_step.input = local_params

            result = {}
            if tool_call.name == "fetch-youtube-transcript":
                # If we already have transcript_text in the session, 
                # you could skip re-fetching or just re-fetch if desired
                if "transcript_text" in cached_outputs:
                    result = {"info": "Transcript in session; stored in vector DB."}
                else:
                    resp = fetch_youtube_transcript(local_params["video_url"])
                    if "transcript" in resp:
                        text = resp["transcript"]
                        tokens_used = count_tokens(text, "gpt-4o")
                        if tokens_used > TOKEN_THRESHOLD:
                            add_text_to_vector_db(text, local_params["video_url"])
                            cached_outputs["transcript_text"] = text
                            result = {"info": MSG_LARGE}
                        else:
                            cached_outputs["transcript_text"] = text
                            result = {"transcript": text}
                    else:
                        result = resp

            elif tool_call.name == "write-file":
                w_result = write_file(
                    file_path=local_params["filePath"],
                    content=local_params["fileContent"],
                    file_type=local_params["fileType"],
                )
                result.update(w_result)

                # If success, embed the new file
                if "success" in w_result:
                    # path might be forcibly in knowledge_repo now
                    final_path = w_result["success"].split("File written to ")[-1].rstrip(".")
                    file_text = read_file_content(final_path)
                    # Use the file's name as the source
                    add_text_to_vector_db(file_text, os.path.basename(final_path))

            elif tool_call.name == "read-file":
                output_format = local_params.get("outputFormat", "string")
                result = read_file(local_params["filePath"], output_format=output_format)

            elif tool_call.name == "search-long-response":
                query_str = local_params["query"]
                top_k = local_params.get("top_k", 3)
                result = search_long_response(query_str, top_k)

            else:
                result = {"error": f"Unknown local tool: {tool_call.name}"}

            # Possibly store big results
            if isinstance(result, dict):
                text_json = json.dumps(result, ensure_ascii=False)
                tok_count = count_tokens(text_json, "gpt-4o")
                if tok_count > TOKEN_THRESHOLD:
                    add_text_to_vector_db(text_json, tool_call.name)
                    result = {"info": MSG_LARGE}

            current_step.output = result
            current_step.language = "json"
            message_history.append({
                "role": "function",
                "name": tool_call.name,
                "content": json.dumps(result),
            })
        else:
            # xpander remote
            function_response = xpander_agent.run_tool(tool_call)
            text_repr = json.dumps(function_response.result, ensure_ascii=False)
            tok_count = count_tokens(text_repr, "gpt-4o")
            if tok_count > TOKEN_THRESHOLD:
                add_text_to_vector_db(text_repr, tool_call.name)
                short_msg = {
                    "info": f"Output from xpander tool '{tool_call.name}' was large. Stored in DB."
                }
                current_step.output = short_msg
                current_step.language = "json"
                message_history.append({
                    "role": "function",
                    "name": function_response.function_name,
                    "content": json.dumps(short_msg),
                    "tool_call_id": function_response.tool_call_id
                })
            else:
                current_step.output = function_response.result
                current_step.language = "json"
                message_history.append({
                    "role": "function",
                    "name": function_response.function_name,
                    "content": json.dumps(function_response.result),
                    "tool_call_id": function_response.tool_call_id
                })

    cl.user_session.set("cached_outputs", cached_outputs)

async def call_gpt4(message_history):
    settings = {
        "model": "gpt-4o",
        "tools": tools,
        "tool_choice": "auto",
    }
    response = await client.chat.completions.create(messages=message_history, **settings)
    message = response.choices[0].message

    # If there are tool calls in the final message, handle them
    if message.tool_calls:
        await xpander_tool(response, message_history)

    return message

@cl.set_starters
async def set_starters():
    return [
        cl.Starter(
            label="Fetch Nvidia Keynote",
            message=(
                "1) fetch-youtube-transcript -> large. store in vector DB.\n"
                "2) write-file to nvidia.txt\n"
                "3) search-long-response about foundation models\n"
                "4) read-file nvidia.txt"
            )
        )
    ]

@cl.on_message
async def run_conversation(msg: cl.Message):
    history = cl.user_session.get("message_history")
    history.append({"name": "user", "role": "user", "content": msg.content})

    cur_iter = 0
    while cur_iter < MAX_ITER:
        resp = await call_gpt4(history)

        # If GPT didn't return any function calls, we have a final or partial answer
        if not resp.tool_calls:
            # If there's text content, send it to the user
            if resp.content:
                await cl.Message(content=resp.content, author="AI Agent").send()
                break
            # If there's no content at all, break anyway
            await cl.Message(content="No more content from GPT.", author="AI Agent").send()
            break

        cur_iter += 1

    if cur_iter >= MAX_ITER:
        # Force final summary
        history.append({
            "role": "user",
            "content": "Please provide a final answer without any tool calls."
        })
        final_resp = await client.chat.completions.create(messages=history, model="gpt-4o")
        if final_resp.choices and final_resp.choices[0].message.content:
            await cl.Message(
                content=final_resp.choices[0].message.content,
                author="AI Agent"
            ).send()
        else:
            await cl.Message(
                content="No final content returned. Conversation ended.",
                author="AI Agent"
            ).send()

if __name__ == "__main__":
    from chainlit.cli import run_chainlit
    run_chainlit(__file__)