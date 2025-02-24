import os
from typing import Dict, List
from dotenv import load_dotenv

from openai import AsyncOpenAI
from xpander_utils.sdk.adapters import ChainlitAdapter
from xpander_sdk import ToolCall,ToolCallType
import chainlit as cl

load_dotenv()

xpander_api_key = os.environ.get("XPANDER_API_KEY","") ## Your XPANDER API Personal Key
xpander_agent_id = os.environ.get("XPANDER_AGENT_ID_SINGLE", "") ## Your Agent ID
openai_key = os.environ.get("OPENAI_API_KEY", "") ## Your Agent ID

client = AsyncOpenAI(api_key=openai_key)

# Instrument the OpenAI client
cl.instrument_openai()

@cl.on_chat_start
def start_chat():
    # set xpander instance to the user session
    xpander = ChainlitAdapter(agent_id=xpander_agent_id, api_key=xpander_api_key)
    cl.user_session.set("xpander", xpander)

@cl.on_message
async def main(message: cl.Message):
    xpander: ChainlitAdapter = cl.user_session.get("xpander")
    thread_id: str = xpander.get_thread_id()
    
    # create task and updates the chainlit session
    xpander.add_task(message.content,thread_id=thread_id) # auto creates thread if needed
    
    settings = {
        "model": "gpt-4o-mini",
        "temperature": 0.0,
        "tools": xpander.agent.get_tools()
    }
    
    def run_completion():
        return client.chat.completions.create(
            messages=xpander.agent.messages, tool_choice=xpander.agent.tool_choice, stream=True, **settings
    )
        
    # create chainlit message
    msg = cl.Message(content="")
    
    while True:
        # run the completion
        stream = await run_completion()
        tool_calls = xpander.aggregate_tool_calls_stream()
        
        async for part in stream:
            if token := part.choices[0].delta.content or "":
                await msg.stream_token(token)
            
            # handle tool calling
            if tool_call_requests := part.choices[0].delta.tool_calls or []:
                tool_calls = xpander.aggregate_tool_calls_stream(tool_call_requests=tool_call_requests, tool_calls=tool_calls)
        
        # has tool calls, add to memory, run & run completion
        if len(tool_calls) != 0:
            xpander.process_tool_calls(tool_calls=tool_calls)
        else: # no tools, break
            break

    xpander.agent.add_messages(messages=[{"role": "assistant", "content": msg.content}])
    await msg.update()