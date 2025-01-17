import os
import json
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
    local_tools
)

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
    """Initialize chat session."""
    cl.user_session.set("cached_outputs", {})
    cl.user_session.set("message_history", [
        {
            "role": "system",
            "content": (
                "You are an advanced AI with long-term memory capabilities. Follow these steps IN ORDER:\n"
                "1. For ANY query, ALWAYS check your memory (vector store) FIRST using semantic search.\n"
                "2. Your memory contains transcripts, summaries, previous answers, and other content.\n"
                "3. If you find relevant information in memory, use it to answer WITHOUT calling tools.\n"
                "4. Only if no relevant memories are found, then call tools to fetch new information.\n"
                "5. After getting new information from tools, it will be automatically stored in your memory.\n"
                "6. Your responses should clearly indicate if you're using stored memories or fetching new data.\n\n"
                "Remember: You have a persistent memory - use it to provide consistent and informed responses!"
            )
        }
    ])
    print("[CHAINLIT] on_chat_start complete.")

def auto_rag_prepend(user_text: str, top_k: int = 3) -> str:
    """Do a quick vector search on user_text, prepend best chunks as context."""
    print(f"[AUTO-RAG] Searching for user_text[:60]={user_text[:60]}")
    hits = vector_store.search(user_text, top_k=top_k, min_similarity=0.5)  # Lower threshold for better recall
    if not hits:
        print("[AUTO-RAG] No relevant hits. Returning user text alone.")
        return user_text
    
    # Clean up the hits to remove the [id] prefix
    clean_hits = []
    for hit in hits:
        if '] ' in hit:
            clean_hits.append(hit.split('] ', 1)[1])
        else:
            clean_hits.append(hit)
    
    ctx = "\n".join([f"- {h}" for h in clean_hits])
    return f"Auto-RAG Context:\n{ctx}\n\nUser Query: {user_text}"

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
    
    async with cl.Step(name="gpt-4", type="llm") as step:
        async for chunk in await openai_client.chat.completions.create(messages=msg_history, **settings):
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
                await step.stream_token(delta.content)
                
            collected_chunks.append(chunk)
        
        full_response = {
            "content": current_content,
            "tool_calls": current_tool_calls if current_tool_calls else None
        }
        
        step.output = current_content if current_content else "Tool call initiated"
    
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
        current_step.name = tc.name
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
    # 1) auto-rag with more context
    user_txt_with_ctx = auto_rag_prepend(msg.content, top_k=5)  # Increased context
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
            await cl.Message(content=final_ans).send()
            break
            
        # If we have tool calls, execute them before continuing
        if gpt_msg.tool_calls:
            await xpander_tool(raw_llm_resp, message_history)
            cur_iter += 1
            continue

        cur_iter += 1

    if cur_iter >= MAX_ITER and not final_ans:
        await cl.Message(content="No final answer after multiple passes.", author="AI Agent").send()
    
    if final_ans:
        vector_store.add_text(final_ans, "assistant_answer")

if __name__ == "__main__":
    from chainlit.cli import run_chainlit
    run_chainlit(__file__)