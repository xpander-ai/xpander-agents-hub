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
                "You are an advanced AI with sophisticated memory and retrieval capabilities. Follow these guidelines:\n\n"
                "1. MEMORY USAGE:\n"
                "   - ALWAYS check memory first using memory-search before using other tools\n"
                "   - If no context is provided, use memory-search to find relevant information\n"
                "   - Only proceed with other tools if memory search yields no results\n\n"
                "2. CONTEXT UTILIZATION:\n"
                "   - Always analyze the provided context thoroughly\n"
                "   - Connect information across different context pieces\n"
                "   - Acknowledge when context might be incomplete\n"
                "   - Be explicit about which context you're using\n\n"
                "3. RESPONSE QUALITY:\n"
                "   - Provide accurate, well-reasoned answers\n"
                "   - Cite specific context when relevant\n"
                "   - Acknowledge uncertainty when appropriate\n"
                "   - Maintain consistency with previous responses\n\n"
                "4. QUERY HANDLING:\n"
                "   - Process queries with dynamic similarity thresholds\n"
                "   - Consider query complexity and length\n"
                "   - Use appropriate search strategies\n"
                "   - Track and optimize query performance\n\n"
                "Remember: Your goal is to provide accurate, contextual, and helpful responses while maintaining "
                "an efficient and organized knowledge base."
            )
        }
    ])
    print("[CHAINLIT] Chat session initialized with enhanced system prompt.")

def auto_rag_prepend(user_text: str, top_k: int = 3) -> str:
    """Enhanced RAG with better context handling and query processing."""
    print(f"[AUTO-RAG] Processing query: {user_text[:60]}")
    
    # Clean and preprocess the query
    query = user_text.strip()
    if not query:
        return user_text
        
    # Get relevant chunks with dynamic similarity
    hits = vector_store.search(
        query=query,
        top_k=top_k,
        min_similarity=None  # Use dynamic threshold
    )
    
    if not hits:
        print("[AUTO-RAG] No relevant hits found in initial search.")
        # Instead of just returning, suggest using memory-search
        return (
            "No immediately relevant information found in memory. "
            "Please use the memory-search tool to look for related information before proceeding.\n\n"
            f"Original question: {user_text}"
        )
    
    # Process and format the context
    contexts = []
    for hit in hits:
        # Extract the actual text without the ID prefix
        if '] ' in hit:
            text = hit.split('] ', 1)[1]
        else:
            text = hit
            
        # Clean up the text
        text = text.strip()
        if text:
            contexts.append(text)
    
    if not contexts:
        return (
            "No immediately relevant information found in memory. "
            "Please use the memory-search tool to look for related information before proceeding.\n\n"
            f"Original question: {user_text}"
        )
        
    # Format context in a more natural way
    formatted_context = "\n\n".join([
        f"Context {i+1}:\n{ctx}" 
        for i, ctx in enumerate(contexts)
    ])
    
    # Construct the final prompt
    return (
        f"Based on the following relevant information:\n\n"
        f"{formatted_context}\n\n"
        f"Please answer this question: {user_text}"
    )

async def call_gpt4(msg_history):
    """Helper to avoid confusion. Just calls GPT once with streaming."""
    settings = {
        "model": "gpt-4",
        "tools": distinct_tools,
        "tool_choice": "auto",
        "stream": True
    }
    
    collected_chunks = []
    current_tool_calls = []
    current_content = ""
    msg = None
    
    start_time = time.time()
    
    completion = await openai_client.chat.completions.create(messages=msg_history, **settings)
    
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
    
    # Only create and send message if this is a final response (no tool calls)
    if current_content and not current_tool_calls:
        msg = cl.Message(content="")
        await msg.send()
        # Stream the content after creating the message
        for char in current_content:
            await msg.stream_token(char)
    
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
                r = fetch_youtube_transcript(local_params["video_url"])
                if "transcript" in r:
                    text = r["transcript"]
                    tok = len(tiktoken.encoding_for_model("gpt-4").encode(text))
                    vector_store.add_text(text, local_params["video_url"])
                    if tok > TOKEN_THRESHOLD:
                        cached_outputs["transcript_text"] = text
                        result = {"info": "Transcript chunked into DB."}
                    else:
                        cached_outputs["transcript_text"] = text
                        result = {"transcript": text}
                else:
                    result = r
            elif tc.name == "write-file":
                w = write_file(
                    local_params["path"],
                    local_params["fileContent"],
                    local_params["fileType"]
                )
                result.update(w)
            elif tc.name == "read-file":
                r = read_file(
                    local_params["path"],
                    fmt=local_params.get("fmt", "string")
                )
                result = r
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
                result = {"info": "Tool result huge => chunked in DB."}

            current_step.output = result
            current_step.language = "json"
            message_history.append({
                "role": "function",
                "name": tc.name,
                "content": json.dumps(result)
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

@cl.on_message
async def multi_pass_rag(msg: cl.Message):
    """
    Multi-pass approach with streaming:
      1) auto-rag prepend
      2) for i < MAX_ITER:
         - call GPT with streaming
         - if GPT calls tools => xpander_tool
         - if GPT has final .content => done
      3) store final answer => assistant_answer
    """
    # 1) auto-rag prepend
    user_txt_with_ctx = auto_rag_prepend(msg.content, top_k=5)

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