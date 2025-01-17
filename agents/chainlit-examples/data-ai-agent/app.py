import os
import json
import time
import chainlit as cl
from typing import Union, List, Dict, Any
import openai
from openai import AsyncOpenAI
import tiktoken
import numpy as np
from io import StringIO
import csv
import xml.etree.ElementTree as ET

from xpander_sdk import XpanderClient, ToolCallType
from youtube_transcript_api import YouTubeTranscriptApi

# ----------------------------------------------------------------
# 0) Constants & Globals
# ----------------------------------------------------------------
KNOWLEDGE_REPO_DIR = "knowledge_repo"
EMBED_CACHE_FILE = os.path.join(KNOWLEDGE_REPO_DIR, "embedding_cache.json")
VECTOR_DB_FILE = os.path.join(KNOWLEDGE_REPO_DIR, "vector_db.json")

PRIMARY_EMBED_MODEL = "text-embedding-3-large"
FALLBACK_EMBED_MODEL = "text-embedding-ada-002"
TOKEN_THRESHOLD = 30000

EMBED_CACHE: Dict[str, List[float]] = {}
VECTOR_DB: List[Dict[str, Any]] = []

MAX_ITER = 5  # maximum GPT calls if it keeps calling tools

api_key = os.environ.get("OPENAI_API_KEY")
openai.api_key = api_key
client = AsyncOpenAI(api_key=api_key)

xpanderAPIKey = os.environ.get("XPANDER_API_KEY", "")
xpanderAgentID = os.environ.get("XPANDER_AGENT_ID", "")
xpander_client = XpanderClient(api_key=xpanderAPIKey)
xpander_agent = xpander_client.agents.get(agent_id=xpanderAgentID)

# ----------------------------------------------------------------
# 1) Persistence
# ----------------------------------------------------------------
def load_json(path: str, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[WARN] Failed loading {path}: {e}")
        return default

def save_json(path: str, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"[WARN] Failed saving {path}: {e}")

def init_vector_db():
    """Load or init knowledge_repo. Then read EMBED_CACHE & VECTOR_DB."""
    global EMBED_CACHE, VECTOR_DB
    os.makedirs(KNOWLEDGE_REPO_DIR, exist_ok=True)
    EMBED_CACHE = load_json(EMBED_CACHE_FILE, {})
    VECTOR_DB = load_json(VECTOR_DB_FILE, [])
    print(f"[INIT] EMBED_CACHE size: {len(EMBED_CACHE)} | VECTOR_DB entries: {len(VECTOR_DB)}")

def save_vector_db():
    """Save EMBED_CACHE & VECTOR_DB to disk."""
    save_json(EMBED_CACHE_FILE, EMBED_CACHE)
    save_json(VECTOR_DB_FILE, VECTOR_DB)

# ----------------------------------------------------------------
# 2) Embedding + Vector DB
# ----------------------------------------------------------------
def embed_text(text: str) -> List[float]:
    """Return an embedding for `text`, caching results."""
    if text in EMBED_CACHE:
        return EMBED_CACHE[text]

    for model_name in [PRIMARY_EMBED_MODEL, FALLBACK_EMBED_MODEL]:
        try:
            print(f"[EMBED] Attempting model={model_name}...")
            resp = openai.embeddings.create(input=text, model=model_name)
            e = resp.data[0].embedding
            EMBED_CACHE[text] = e
            save_vector_db()
            print("[EMBED] Success. Cached.")
            return e
        except Exception as e:
            print(f"[EMBED] Failed with {model_name}: {e}")
            time.sleep(1)

    EMBED_CACHE[text] = []
    save_vector_db()
    print("[EMBED] All attempts failed. Returning empty embedding.")
    return []

def add_text_to_vector_db(text: str, source: str):
    """
    Split `text` into ~500-token chunks, embed each, store in `VECTOR_DB`.
    """
    print(f"[VDB] Storing text from source='{source}', length={len(text)}.")
    chunk_size = 500
    try:
        enc = tiktoken.encoding_for_model("gpt-4o")
    except:
        enc = tiktoken.encoding_for_model("gpt-3.5-turbo")

    tokens = enc.encode(text)
    for i in range(0, len(tokens), chunk_size):
        chunk = enc.decode(tokens[i : i+chunk_size])
        embedding = embed_text(chunk)
        entry_id = f"{source}_chunk_{i//chunk_size}"
        VECTOR_DB.append({
            "id": entry_id,
            "meta": {"source": source},
            "text": chunk,
            "embedding": embedding
        })
        print(f"[VDB] Saved chunk={entry_id}, chunk_length={len(chunk)}")

    save_vector_db()
    print(f"[VDB] Done storing. DB now has {len(VECTOR_DB)} entries.")

def vector_search(query: str, top_k: int = 3) -> List[str]:
    """Return top_k matching chunks from DB as short strings."""
    if not VECTOR_DB:
        print("[VDB] DB empty.")
        return []
    q_emb = embed_text(query)
    if not q_emb:
        print("[VDB] empty embedding for query.")
        return []

    import numpy as np
    def cos_sim(a, b):
        denom = (np.linalg.norm(a) * np.linalg.norm(b))
        return float(np.dot(a, b) / denom) if denom else 0.0

    scored = []
    for entry in VECTOR_DB:
        emb = entry.get("embedding", [])
        if emb:
            s = cos_sim(q_emb, emb)
            scored.append((s, entry["text"], entry["id"]))

    scored.sort(key=lambda x: x[0], reverse=True)
    hits = scored[:top_k]
    if hits:
        print("[VDB] top hits:")
        for i,(score,chunk,cid) in enumerate(hits):
            snippet = chunk[:60] + "..." if len(chunk)>60 else chunk
            print(f" {i+1}) ID={cid}, Score={score:.4f}, chunk={snippet}")
    return [f"[{r[2]}] {r[1]}" for r in hits]

def search_long_response(query: str, top_k: int = 3) -> dict:
    """
    Agentic RAG function to retrieve partial from DB.
    """
    chunks = vector_search(query, top_k)
    return {
        "chunks": chunks,
        "info": "Partial RAG data. Re-run if needed."
    }

# ----------------------------------------------------------------
# 3) Tools
# ----------------------------------------------------------------
def fetch_youtube_transcript(video_url: str) -> dict:
    print(f"[TOOL] fetch_youtube_transcript => {video_url}")
    try:
        if "watch?v=" in video_url:
            vid = video_url.split("v=")[-1].split("&")[0]
        elif "youtu.be/" in video_url:
            vid = video_url.split("/")[-1]
        else:
            return {"error": "Invalid URL pattern."}

        data = YouTubeTranscriptApi.get_transcript(vid)
        text = " ".join(e["text"] for e in data)
        return {"transcript": text}
    except Exception as e:
        return {"error": str(e)}

def read_file(path: str, fmt="string") -> dict:
    print(f"[TOOL] read_file => {path}, fmt={fmt}")
    if not os.path.exists(path):
        path = os.path.join(KNOWLEDGE_REPO_DIR, path)
    if not os.path.exists(path):
        return {"error": "File not found."}
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
    except:
        return {"error": "Couldn't read file."}

    if len(content)>10000:
        snippet = content[:1000]
        return {
            "info":"File large. Partial only. Use vector search for more detail.",
            "content":snippet
        }

    if fmt=="json":
        try:
            return {"content":json.loads(content)}
        except:
            return {"error":"Invalid JSON."}
    elif fmt=="csv":
        return {"content":list(csv.reader(StringIO(content)))}
    elif fmt=="xml":
        try:
            root=ET.fromstring(content)
            return {"content":ET.tostring(root, encoding="unicode")}
        except:
            return {"error":"Invalid XML."}
    else:
        return {"content":content}

def write_file(path: str, fileContent: str, fileType: str) -> dict:
    print(f"[TOOL] write_file => {path}, fileType={fileType}")
    if not path.startswith(KNOWLEDGE_REPO_DIR):
        path=os.path.join(KNOWLEDGE_REPO_DIR,path)
    try:
        if fileType.lower()=="json":
            with open(path,"w",encoding="utf-8") as f:
                json.dump(json.loads(fileContent),f,indent=2)
        elif fileType.lower()=="xml":
            root=ET.Element("root")
            ET.SubElement(root,"content").text=fileContent
            ET.ElementTree(root).write(path,encoding="unicode",xml_declaration=True)
        elif fileType.lower()=="csv":
            r=list(csv.reader(StringIO(fileContent)))
            with open(path,"w",newline="",encoding="utf-8") as f:
                csv.writer(f).writerows(r)
        else:
            with open(path,"w",encoding="utf-8") as f:
                f.write(fileContent)

        add_text_to_vector_db(fileContent, os.path.basename(path))
        return {"success":f"Wrote file: {path}"}
    except Exception as e:
        return {"error":str(e)}

local_tools=[
    {
        "type":"function",
        "function":{
            "name":"fetch-youtube-transcript",
            "description":"Fetch a YouTube transcript.",
            "parameters":{
                "type":"object",
                "properties":{
                    "video_url":{"type":"string"}
                },
                "required":["video_url"]
            }
        }
    },
    {
        "type":"function",
        "function":{
            "name":"search-long-response",
            "description":"Agentic RAG partial data from DB.",
            "parameters":{
                "type":"object",
                "properties":{
                    "query":{"type":"string"},
                    "top_k":{"type":"number"}
                },
                "required":["query"]
            }
        }
    },
    {
        "type":"function",
        "function":{
            "name":"read-file",
            "description":"Reads local file. Partial if huge.",
            "parameters":{
                "type":"object",
                "properties":{
                    "path":{"type":"string"},
                    "fmt":{"type":"string"}
                },
                "required":["path"]
            }
        }
    },
    {
        "type":"function",
        "function":{
            "name":"write-file",
            "description":"Writes local file & stores in DB.",
            "parameters":{
                "type":"object",
                "properties":{
                    "path":{"type":"string"},
                    "fileContent":{"type":"string"},
                    "fileType":{"type":"string"}
                },
                "required":["path","fileContent","fileType"]
            }
        }
    }
]

xpander_agent.add_local_tools(local_tools)
tools = xpander_agent.get_tools()
# Assuming both methods return lists of dictionaries
tools_from_get_tools = xpander_agent.get_tools()
tools_from_retrieve_graph_tools = xpander_agent.retrieve_all_graph_tools()


# Assuming both methods return lists of dictionaries
tools_from_get_tools = xpander_agent.get_tools()
tools_from_retrieve_graph_tools = xpander_agent.retrieve_all_graph_tools()

# Combine both arrays
combined_tools = tools_from_get_tools + tools_from_retrieve_graph_tools

# Use a list to keep unique dictionaries
distinct_tools = []
seen = set()

for tool in combined_tools:
    # Serialize the dictionary to a JSON string to make it hashable
    tool_serialized = json.dumps(tool, sort_keys=True)
    if tool_serialized not in seen:
        seen.add(tool_serialized)
        distinct_tools.append(tool)
# ----------------------------------------------------------------
# 4) Multi-pass Chainlit setup
# ----------------------------------------------------------------
import math
cl.instrument_openai()

@cl.on_chat_start
def start_chat():
    init_vector_db()
    cl.user_session.set("cached_outputs", {})
    cl.user_session.set("message_history", [
        {
            "role":"system",
            "content":(
                "You are an advanced AI with Agentic RAG. "
                "For each user query, do an immediate vector search for context. "
                "If you need more data, call xpander/local tools. "
                "After each tool call, we re-run GPT so it can incorporate the new data. "
                "We store user queries, transcripts, final answers in the local DB. "
                "Stop if you have provided a final answer."
            )
        }
    ])
    print("[CHAINLIT] on_chat_start complete.")

def auto_rag_prepend(user_text: str, top_k: int = 3) -> str:
    """Do a quick vector search on user_text, prepend best chunks as context."""
    print(f"[AUTO-RAG] Searching for user_text[:60]={user_text[:60]}")
    hits=vector_search(user_text, top_k=top_k)
    if not hits:
        print("[AUTO-RAG] No relevant hits. Returning user text alone.")
        return user_text
    ctx="\n".join([f"- {h}" for h in hits])
    return f"Auto-RAG Context:\n{ctx}\n\nUser Query: {user_text}"

async def call_gpt4(msg_history):
    """Helper to avoid confusion. Just calls GPT once with streaming."""
    settings = {
        "model": "gpt-4o",
        "tools": distinct_tools,
        "tool_choice": "auto",
        "stream": True  # Enable streaming
    }
    
    # Create a message placeholder for streaming
    message = cl.Message(content="", author="AI Agent")
    await message.send()
    
    collected_chunks = []
    current_tool_calls = []
    current_content = ""
    
    async for chunk in await client.chat.completions.create(messages=msg_history, **settings):
        if not chunk.choices:
            continue
            
        delta = chunk.choices[0].delta
        
        # Handle tool calls
        if delta.tool_calls:
            for tool_call in delta.tool_calls:
                if len(current_tool_calls) <= tool_call.index:
                    current_tool_calls.append({
                        "id": tool_call.id,
                        "function": {"name": "", "arguments": ""},
                        "type": "function"
                    })
                
                if tool_call.function.name:
                    current_tool_calls[tool_call.index]["function"]["name"] = tool_call.function.name
                if tool_call.function.arguments:
                    current_tool_calls[tool_call.index]["function"]["arguments"] += tool_call.function.arguments
        
        # Handle content streaming
        if delta.content:
            current_content += delta.content
            await message.stream_token(delta.content)
            
        collected_chunks.append(chunk)
    
    # Construct the final message from collected chunks
    full_response = {
        "content": current_content,
        "tool_calls": current_tool_calls if current_tool_calls else None
    }
    
    # Update the message with final content
    if current_content:
        await message.update()
    
    # Create a response object that matches OpenAI's format and includes model_dump
    class SyntheticMessage:
        def __init__(self, content, tool_calls):
            self.content = content
            self.tool_calls = tool_calls
            
        def model_dump(self):
            return {
                "content": self.content,
                "tool_calls": self.tool_calls,
                "role": "assistant"
            }
            
    class SyntheticResponse:
        def __init__(self, message):
            self.choices = [type('Choice', (), {'message': message})]
            
        def model_dump(self):
            return {
                "choices": [{
                    "message": self.choices[0].message.model_dump()
                }]
            }
            
    final_message = SyntheticMessage(full_response["content"], full_response["tool_calls"])
    return final_message, SyntheticResponse(final_message)

@cl.step(type="tool")
async def xpander_tool(llm_response, message_history):
    """
    Intercepts GPT's tool calls, runs them, appends results to the conversation.
    """
    tool_calls=XpanderClient.extract_tool_calls(llm_response=llm_response.model_dump())
    cached_outputs=cl.user_session.get("cached_outputs")

    for i,tc in enumerate(tool_calls):
        current_step=cl.context.current_step
        current_step.name=tc.name
        current_step.input=tc.payload

        fn_args=llm_response.choices[0].message.tool_calls[i]['function']['arguments']
        local_params=json.loads(fn_args)
        result={}

        if tc.type==ToolCallType.LOCAL:
            current_step.input=local_params
            if tc.name=="fetch-youtube-transcript":
                r=fetch_youtube_transcript(local_params["video_url"])
                if "transcript" in r:
                    text=r["transcript"]
                    tok=len(tiktoken.encoding_for_model("gpt-4o").encode(text))
                    add_text_to_vector_db(text, local_params["video_url"])
                    if tok>TOKEN_THRESHOLD:
                        cached_outputs["transcript_text"]=text
                        result={"info":"Transcript chunked into DB."}
                    else:
                        cached_outputs["transcript_text"]=text
                        result={"transcript":text}
                else:
                    result=r
            elif tc.name=="write-file":
                w=write_file(
                    local_params["path"],
                    local_params["fileContent"],
                    local_params["fileType"]
                )
                result.update(w)
            elif tc.name=="read-file":
                r=read_file(
                    local_params["path"],
                    fmt=local_params.get("fmt","string")
                )
                result=r
            elif tc.name=="search-long-response":
                r=search_long_response(
                    local_params["query"],
                    local_params.get("top_k",3)
                )
                result=r
            else:
                result={"error":f"Unknown local tool: {tc.name}"}

            # Possibly store big result
            text_json=json.dumps(result,ensure_ascii=False)
            tok=len(tiktoken.encoding_for_model("gpt-4o").encode(text_json))
            if tok>TOKEN_THRESHOLD:
                add_text_to_vector_db(text_json,tc.name)
                result={"info":"Tool result huge => chunked in DB."}

            current_step.output=result
            current_step.language="json"
            message_history.append({
                "role":"function",
                "name":tc.name,
                "content":json.dumps(result)
            })
        else:
            # xpander remote
            function_response=xpander_agent.run_tool(tc)
            text_repr=json.dumps(function_response.result,ensure_ascii=False)
            tok=len(tiktoken.encoding_for_model("gpt-4o").encode(text_repr))
            if tok>TOKEN_THRESHOLD:
                add_text_to_vector_db(text_repr,tc.name)
                short_msg={"info":f"Output from xpander tool '{tc.name}' was large => stored in DB."}
                current_step.output=short_msg
                current_step.language="json"
                message_history.append({
                    "role":"function",
                    "name":function_response.function_name,
                    "content":json.dumps(short_msg),
                    "tool_call_id":function_response.tool_call_id
                })
            else:
                current_step.output=function_response.result
                current_step.language="json"
                message_history.append({
                    "role":"function",
                    "name":function_response.function_name,
                    "content":json.dumps(function_response.result),
                    "tool_call_id":function_response.tool_call_id
                })

    cl.user_session.set("cached_outputs",cached_outputs)

@cl.on_message
async def multi_pass_rag(msg: cl.Message):
    """
    Multi-pass approach with streaming:
      1) Store user query => user_query
      2) auto-rag prepend
      3) for i < MAX_ITER:
         - call GPT with streaming
         - if GPT calls tools => xpander_tool
         - if GPT has final .content => done
      4) store final answer => assistant_answer
    """
    # 1) store user query
    add_text_to_vector_db(msg.content, "user_query")

    # 2) auto-rag
    user_txt_with_ctx = auto_rag_prepend(msg.content)
    message_history = cl.user_session.get("message_history")
    message_history.append({"role": "user", "content": user_txt_with_ctx})

    cur_iter = 0
    final_ans = None

    while cur_iter < MAX_ITER:
        gpt_msg, raw_llm_resp = await call_gpt4(message_history)
        message_history.append({"role": "assistant", "content": gpt_msg.content if gpt_msg.content else ""})

        if gpt_msg.tool_calls:
            # Tools => xpander_tool
            await xpander_tool(raw_llm_resp, message_history)

        if gpt_msg.content:
            final_ans = gpt_msg.content
            break

        cur_iter += 1

    if cur_iter >= MAX_ITER and not final_ans:
        no_ans = "No final answer after multiple passes."
        await cl.Message(content=no_ans, author="AI Agent").send()

    if final_ans:
        # store final in DB
        add_text_to_vector_db(final_ans, "assistant_answer")

if __name__=="__main__":
    from chainlit.cli import run_chainlit
    run_chainlit(__file__)