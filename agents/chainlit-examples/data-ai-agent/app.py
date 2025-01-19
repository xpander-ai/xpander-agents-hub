import os
import json
import time
import chainlit as cl
from openai import AsyncOpenAI
import tiktoken

from src.config.settings import (
    OPENAI_API_KEY,
    XPANDER_API_KEY,
    XPANDER_AGENT_ID,
    FRIENDLI_TOKEN,
    TOKEN_THRESHOLD,
    MAX_ITER
)
from src.database.vector_store import vector_store
from src.tools.local_tools import (
    fetch_youtube_transcript,
    read_file,
    write_file,
    memory_search,
    list_memories,
    get_memory_stats,
    delete_memory,
    delete_source,
    clean_duplicates,
    clear_all_memories,
    read_query_logs,
    get_query_stats,
    local_tools
)
from src.utils.query_logger import query_logger

from xpander_sdk import XpanderClient, ToolCallType

# Initialize clients
openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
friendli_client = AsyncOpenAI(api_key=FRIENDLI_TOKEN, base_url="https://api.friendli.ai/serverless/v1")
xpander_client = XpanderClient(api_key=XPANDER_API_KEY)
xpander_agent = xpander_client.agents.get(agent_id=XPANDER_AGENT_ID)

# Add tools to agent
xpander_agent.add_local_tools(local_tools)
tools = xpander_agent.get_tools()

# Combine tools from both sources
tools_from_get_tools = xpander_agent.get_tools()
tools_from_retrieve_graph_tools = xpander_agent.retrieve_all_graph_tools()

# Combine and deduplicate tools
combined_tools = tools_from_get_tools + tools_from_retrieve_graph_tools
distinct_tools = []
seen = set()

for tool in combined_tools:
    # Skip tools starting with Pg
    if tool['function']['name'].startswith('Pg'):
        print(f"Skipping tool: {tool['function']['name']}")
        continue
    tool_serialized = json.dumps(tool, sort_keys=True)
    if tool_serialized not in seen:
        seen.add(tool_serialized)
        distinct_tools.append(tool)

# ----------------------------------------------------------------
# Chainlit setup
# ----------------------------------------------------------------
cl.instrument_openai()

@cl.on_chat_start
def start_chat():
    """Initialize chat session with improved system prompt."""
    cl.user_session.set("cached_outputs", {})
    cl.user_session.set("message_history", [
        {
            "role": "system",
            "content": (
                "You are an advanced AI with sophisticated memory and tool capabilities. Follow these guidelines:\n\n"
                "1. TOOL USAGE:\n"
                "   - When a user requests an action (summarize, fetch, search, etc.), ALWAYS use the appropriate tool\n"
                "   - Even if context is provided, you must still use tools to perform the requested action\n"
                "   - Context is supplementary information only, not a replacement for tool calls\n\n"
                "2. CONTEXT HANDLING:\n"
                "   - Context from memory is provided to help inform your actions\n"
                "   - Use context to understand what's already available\n"
                "   - But still make appropriate tool calls based on the user's request\n\n"
                "3. RESPONSE QUALITY:\n"
                "   - Provide accurate, well-reasoned answers\n"
                "   - Use tools for actions, don't just summarize context\n"
                "   - Acknowledge uncertainty when appropriate\n\n"
                "4. SPECIFIC ACTIONS:\n"
                "   - For YouTube videos: Use fetch-youtube-transcript even if transcript exists in context\n"
                "   - For summaries: Use appropriate summarization tools\n"
                "   - For searches: Use memory-search tool\n\n"
                "Remember: Context helps inform your actions but does not replace the need to use appropriate tools."
            )
        }
    ])
    print("[CHAINLIT] Chat session initialized with enhanced system prompt.")

async def auto_rag_prepend(user_text: str, top_k: int = 3) -> str:
    """Enhanced RAG with better context handling and query processing."""
    print(f"[AUTO-RAG] Processing query: {user_text[:60]}")
    
    # Clean and preprocess the query
    query = user_text.strip()
    if not query:
        return user_text
        
    # If it's a YouTube URL, try to find existing transcript first
    if "youtube.com/watch?v=" in query or "youtu.be/" in query:
        video_id = query.split("v=")[-1].split("&")[0]
        source_id = f"youtube_transcript_{video_id}"
        
        try:
            # Search specifically for this transcript
            hits = vector_store.search(query=source_id, top_k=1)
            
            if hits:
                print(f"[AUTO-RAG] Found existing transcript for video {video_id}")
                content = hits[0]
                return (
                    "Note: While this video's transcript exists in memory, you should still use the fetch-youtube-transcript "
                    "tool to ensure you're working with the most up-to-date version.\n\n"
                    f"Previous transcript for reference:\n{content}\n\n"
                    f"User query: {user_text}"
                )
        except Exception as e:
            print(f"[AUTO-RAG] Error searching for transcript: {e}")
            
    # Regular search for other queries or if no transcript found
    try:
        hits = vector_store.search(query=query, top_k=top_k)
        
        if not hits:
            print("[AUTO-RAG] No relevant hits found in initial search.")
            return user_text
            
        # Process and format the context
        contexts = []
        for hit in hits:
            if isinstance(hit, str):
                # Skip assistant answers
                if hit.startswith('[assistant_answer]'):
                    continue
                contexts.append(hit.strip())
        
        if not contexts:
            return user_text
            
        # Combine contexts and original query
        context_str = "\n\n".join(contexts)
        return (
            "Note: The following context is for reference only. You should still use appropriate tools to handle the user's request.\n\n"
            f"Context from memory:\n{context_str}\n\n"
            f"User query: {user_text}"
        )
            
    except Exception as e:
        print(f"[AUTO-RAG] Search failed: {e}")
        return user_text

async def call_gpt4(msg_history):
    """Helper to avoid confusion. Just calls GPT once with streaming."""
    settings = {
        "model": "gpt-4",
        "tools": distinct_tools,
        "tool_choice": "auto",
        "stream": True
    }
    friendli_settings = {
        "model": "meta-llama-3.1-8b-instruct",
        "tools": distinct_tools,
        "temperature": 0.0,
        "tool_choice": "auto",
        "stream": True
    }
    
    collected_chunks = []
    current_tool_calls = []
    current_content = ""
    
    start_time = time.time()
    
    completion = await openai_client.chat.completions.create(messages=msg_history, **settings)
    # completion = await friendli_client.chat.completions.create(messages=msg_history, **friendli_settings)
    
    async for chunk in completion:
        if not chunk.choices:
            continue
            
        delta = chunk.choices[0].delta
        
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
        
        if delta.content:
            current_content += delta.content
            
        collected_chunks.append(chunk)
    
    full_response = {
        "content": current_content,
        "tool_calls": current_tool_calls if current_tool_calls else None
    }
    
    # Log query details
    latency = time.time() - start_time
    query_text = msg_history[-1]["content"] if msg_history else ""
    response_text = current_content if current_content else json.dumps(current_tool_calls)
    
    query_logger.log_query(
        query=query_text,
        response=response_text,
        latency=latency,
        metadata={
            "model": "gpt-4",
            "has_tool_calls": bool(current_tool_calls),
            "num_tool_calls": len(current_tool_calls) if current_tool_calls else 0
        }
    )
    
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
    """Intercepts GPT's tool calls, runs them, appends results to the conversation."""
    tool_calls = XpanderClient.extract_tool_calls(llm_response=llm_response.model_dump())
    cached_outputs = cl.user_session.get("cached_outputs")

    for i, tc in enumerate(tool_calls):
        current_step = cl.context.current_step
        current_step.name = f"xpander-ai-tools"
        current_step.input = tc.payload

        fn_args = llm_response.choices[0].message.tool_calls[i]['function']['arguments']
        local_params = json.loads(fn_args)
        result = {}

        if tc.type == ToolCallType.LOCAL:
            current_step.input = local_params
            if tc.name == "fetch-youtube-transcript":
                # Optimized YouTube handling
                video_url = local_params["video_url"]
                video_id = video_url.split("v=")[-1].split("&")[0]
                file_path = f"knowledge_repo/{video_id}_transcript.txt"
                
                # Fetch and process transcript in one go
                r = fetch_youtube_transcript(video_url)
                if not r.get("success"):
                    result = r
                    current_step.output = result
                    message_history.append({
                        "role": "function",
                        "name": tc.name,
                        "content": json.dumps(result)
                    })
                    continue
                
                # Save transcript file and store in vector DB
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(r.get("transcript", ""))
                vector_store.add_text(r.get("transcript", ""), f"youtube_transcript_{video_id}")
                
                # Generate summary file immediately
                if r.get("summary"):
                    summary_file = await generate_summary_file(
                        r["summary"],
                        f"YouTube_Summary_{video_id}"
                    )
                    # Add file to message attachments
                    if not hasattr(current_step, "files"):
                        current_step.files = []
                    current_step.files.append(summary_file)
                
                result = {
                    **r,
                    "file_path": file_path,
                    "note": "📄 Summary file has been generated and transcript saved."
                }
                
                # Add immediate summary response to avoid redundant reads
                message_history.append({
                    "role": "function",
                    "name": tc.name,
                    "content": json.dumps(result)
                })
                message_history.append({
                    "role": "assistant",
                    "content": f"""Here's a summary of the video:

{r.get('summary', '')}

Key topics covered: {r.get('topics', '')}

I've saved both the full transcript and a detailed summary file for your reference. Would you like me to:
1. Analyze any specific aspects of the content?
2. Focus on particular topics mentioned?
3. Provide more details about certain parts?

Just let me know what interests you most."""
                })
                current_step.output = result
                continue
                
            elif tc.name == "read-file":
                # Check if we already have this content in memory_history
                file_path = local_params["path"]
                if "transcript" in file_path:
                    video_id = file_path.split("/")[-1].replace("_transcript.txt", "")
                    # Search in message history first
                    for msg in reversed(message_history):
                        if msg["role"] == "function" and msg["name"] == "fetch-youtube-transcript":
                            try:
                                content = json.loads(msg["content"])
                                if content.get("video_id") == video_id:
                                    result = {"content": content.get("transcript", "")}
                                    break
                            except:
                                pass
                
                # If not found in history, try reading file
                if not result:
                    result = read_file(file_path, fmt=local_params.get("fmt", "string"))
                
            elif tc.name == "write-file":
                w = await write_file(
                    local_params["path"],
                    local_params["fileContent"],
                    local_params.get("fileType", "text")
                )
                result = w
            elif tc.name == "memory-search":
                r = memory_search(
                    local_params["query"],
                    local_params.get("top_k", 3)
                )
                result = r
            elif tc.name == "list-memories":
                r = list_memories()
                result = r
            elif tc.name == "get-memory-stats":
                r = get_memory_stats()
                result = r
            elif tc.name == "delete-memory":
                r = delete_memory(local_params["memory_id"])
                result = r
            elif tc.name == "delete-source":
                r = delete_source(local_params["source"])
                result = r
            elif tc.name == "clean-duplicates":
                r = clean_duplicates()
                result = r
            elif tc.name == "clear-all-memories":
                r = clear_all_memories()
                result = r
            elif tc.name == "read-query-logs":
                r = read_query_logs(
                    start_time=local_params.get("start_time"),
                    end_time=local_params.get("end_time"),
                    limit=local_params.get("limit", 100)
                )
                result = r
            elif tc.name == "get-query-stats":
                r = get_query_stats(
                    start_time=local_params.get("start_time"),
                    end_time=local_params.get("end_time")
                )
                result = r
            else:
                result = {"error": f"Unknown local tool: {tc.name}"}

            text_json = json.dumps(result, ensure_ascii=False)
            tok = len(tiktoken.encoding_for_model("gpt-4").encode(text_json))
            if tok > TOKEN_THRESHOLD:
                vector_store.add_text(text_json, tc.name)
                result = {
                    "info": "Tool result huge => chunked rest of the data to DB.",
                    "content": text_json[:int(TOKEN_THRESHOLD * 0.8)]
                }

            current_step.output = result
            current_step.language = "json"
            message_history.append({
                "role": "function",
                "name": tc.name,
                "content": json.dumps(result)
            })
            
            # For YouTube transcripts, add a helpful next step suggestion
            if tc.name == "fetch-youtube-transcript":
                message_history.append({
                    "role": "assistant",
                    "content": "I've fetched and processed the transcript. The summary has been saved and is ready for your review. Would you like me to:\n1. Analyze specific aspects of the content\n2. Generate a more detailed summary\n3. Extract key topics or themes\n\nJust let me know what interests you most about this video."
                })
        else:
            function_response = xpander_agent.run_tool(tc)
            text_repr = json.dumps(function_response.result, ensure_ascii=False)
            tok = len(tiktoken.encoding_for_model("gpt-4").encode(text_repr))
            if tok > TOKEN_THRESHOLD:
                vector_store.add_text(text_repr, tc.name)
                short_msg = {"info": f"Output from xpander tool '{tc.name}' was large => stored in DB."}
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

async def generate_summary_file(content: str, title: str) -> cl.File:
    """Generate a downloadable summary file with proper formatting."""
    if not content or not title:
        print(f"[ERROR] Cannot generate summary file: content={bool(content)}, title={bool(title)}")
        return None
        
    # Create safe filename
    safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
    if not safe_title:
        safe_title = f"summary_{int(time.time())}"
    
    # Format content
    summary_content = f"""# {title}

## Summary
{content}

## Metadata
- Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}
- Source: {title}
"""
    
    try:
        # Ensure directory exists
        dir_path = "knowledge_repo/summaries"
        os.makedirs(dir_path, exist_ok=True)
        
        # Create full file path
        file_path = os.path.join(dir_path, f"{safe_title}.md")
        
        print(f"[DEBUG] Writing summary to {file_path}")
        print(f"[DEBUG] Content length: {len(summary_content)}")
        
        # Write file with explicit encoding and verification
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(summary_content)
            f.flush()
            os.fsync(f.fileno())
        
        # Verify file was written correctly
        if os.path.exists(file_path):
            size = os.path.getsize(file_path)
            if size > 0:
                print(f"[INFO] Successfully wrote summary ({size} bytes) to {file_path}")
                return cl.File(name=os.path.basename(file_path), path=file_path)
            else:
                print(f"[ERROR] File was created but is empty: {file_path}")
        else:
            print(f"[ERROR] File was not created: {file_path}")
            
        return None
    except Exception as e:
        print(f"[ERROR] Failed to generate summary file: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

@cl.on_message
async def multi_pass_rag(msg: cl.Message):
    """
    Multi-pass approach with streaming and enhanced summary generation:
      1) auto-rag prepend
      2) for i < MAX_ITER:
         - call GPT with streaming
         - if GPT calls tools => xpander_tool
         - if GPT has final .content => done
      3) For research/summary requests:
         - Generate downloadable summary file
         - Store in vector store
    """
    # 1) auto-rag prepend
    user_txt_with_ctx = await auto_rag_prepend(msg.content, top_k=5)

    message_history = cl.user_session.get("message_history")
    message_history.append({"role": "user", "content": user_txt_with_ctx})

    cur_iter = 0
    final_ans = None

    while cur_iter < MAX_ITER:
        gpt_msg, raw_llm_resp = await call_gpt4(message_history)
        
        # If we have content but no tool calls, it means GPT used the context
        if gpt_msg.content and not gpt_msg.tool_calls:
            message_history.append({"role": "assistant", "content": gpt_msg.content})
            final_ans = gpt_msg.content
            
            # Create and send the final message
            final_message = cl.Message(content="")
            await final_message.send()
            
            # Stream the content
            for char in final_ans:
                await final_message.stream_token(char)
            
            # For research/summary requests, generate a downloadable file
            is_research = any(word in msg.content.lower() for word in ["summarize", "research", "analyze", "study"])
            if is_research and len(final_ans) > 500:  # Only for longer summaries
                try:
                    # Extract title from content or use timestamp
                    if "youtube.com/watch?v=" in msg.content:
                        video_id = msg.content.split("v=")[-1].split("&")[0]
                        title = f"YouTube_Summary_{video_id}"
                    else:
                        title = f"Research_Summary_{int(time.time())}"
                    
                    # Generate and attach summary file
                    summary_file = await generate_summary_file(final_ans, title)
                    if summary_file:
                        # Create a new message for the file attachment
                        file_message = cl.Message(content="📄 Here's your downloadable summary:")
                        await file_message.send()
                        
                        # Attach the file in a separate step
                        elements = [summary_file]
                        await cl.Message(content="", elements=elements).send()
                        
                except Exception as e:
                    print(f"Error generating summary file: {e}")
                    import traceback
                    traceback.print_exc()
                
            # Ensure message is complete
            await final_message.update()
            break
            
        # If we have tool calls, execute them before continuing
        if gpt_msg.tool_calls:
            await xpander_tool(raw_llm_resp, message_history)
            
            cur_iter += 1
            continue

        cur_iter += 1

    if cur_iter >= MAX_ITER and not final_ans:
        error_msg = cl.Message(content="⚠️ No final answer after multiple passes.")
        await error_msg.send()

    # Store the final answer in vector store if we have one
    if final_ans:
        vector_store.add_text(final_ans, "assistant_answer")

if __name__ == "__main__":
    from chainlit.cli import run_chainlit
    run_chainlit(__file__)