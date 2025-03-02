## This is example code of how to use LLamaIndex to handle the data and query the SQL database and xpander.ai to orchestrate and power the AI Agent with the tools.
## The frontend is handled by Chainlit and the backend is handled by LlamaIndex and xpander.ai.

## Standard Libraries
import os
from typing import Callable, Dict
from dotenv import load_dotenv

## Llama Index
from llama_index.llms.openai import AsyncOpenAI, OpenAI
from llama_index.core import SQLDatabase
from llama_index.core.query_engine import NLSQLTableQueryEngine

## xpander.ai
from xpander_utils.sdk.adapters import ChainlitAdapter
import chainlit as cl

## Database
from db import engine

## Environment Variables
load_dotenv()

## xpander.ai
xpander_api_key = os.environ.get("XPANDER_API_KEY","") 
xpander_agent_id = os.environ.get("XPANDER_AGENT_ID", "") 
openai_key = os.environ.get("OPENAI_API_KEY", "") 

## LLMs
chat_llm = AsyncOpenAI(api_key=openai_key)
agent_llm = OpenAI(api_key=openai_key)

## Database
sql_database = SQLDatabase(engine, include_tables=["city_stats"])

## Query Engine (Llama Index)
query_engine = NLSQLTableQueryEngine(
    sql_database=sql_database, tables=["city_stats"], llm=agent_llm
)

## City Stats Database function (loaded into the AI Agent)
def city_stats_db_function(query: str) -> str:
    """
    Query the database using natural language and return the results
    """
    response = query_engine.query(query)
    return response.response

## City Stats Database Function Scheme (loaded into the AI Agent)
city_stats_db_tool = [{
    "declaration": {
        "type": "function",
        "function": {
            "name": "query_database",
            "description": "Query the city statistics database using natural language",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language query about city statistics"
                    }
                },
                "required": ["query"]
            }
        }
    },
    "fn": city_stats_db_function
}]

## Helper function to load the city stats database tool into the AI Agent
local_tools_list = [tool['declaration'] for tool in city_stats_db_tool] # helper
local_tools_by_name: Dict[str, Callable] = {} # helper
for tool in city_stats_db_tool:
    local_tools_by_name[tool['declaration']['function']['name']] = tool['fn']

##  Instrument the OpenAI client to the Chainlit session
cl.instrument_openai()

##  Define the chat start event (When loading the chat interface)
@cl.on_chat_start
def start_chat():
    # set xpander instance to the user session
    xpander = ChainlitAdapter(agent_id=xpander_agent_id, api_key=xpander_api_key)
    xpander.agent.add_local_tools(local_tools_list)
    cl.user_session.set("xpander", xpander) # adding xpander_data to the existing user session

##  Define the chat message event (When a message is sent)
@cl.on_message
async def main(message: cl.Message):
    xpander: ChainlitAdapter = cl.user_session.get("xpander")
    thread_id: str = xpander.get_thread_id()
    
    # create task and updates the chainlit session
    xpander.add_task(message.content,thread_id=thread_id)
    
    settings = {
        "model": "gpt-4o-mini",
        "tools": xpander.agent.get_tools()
    }
    
    ##  Define the chat completion event (LLM completion)
    def run_completion():
        return chat_llm.chat.completions.create(
            messages=xpander.agent.messages, tool_choice=xpander.agent.tool_choice, stream=True, **settings
    )
        
    # create chainlit message
    msg = cl.Message(content="")
    
    ## Process the chat completion (The AI Agent main business logic)
    while True:
        stream = await run_completion()

        # Prepeare the tool calls from the stream (Tool calls are the AI Agent's actions)
        tool_calls = xpander.aggregate_tool_calls_stream()
        
        # Handles the stream of the LLM completion
        async for part in stream:
            if token := part.choices[0].delta.content or "":
                await msg.stream_token(token)
            
            # handle tool calling
            if tool_call_requests := part.choices[0].delta.tool_calls or []:
                tool_calls = xpander.aggregate_tool_calls_stream(tool_call_requests=tool_call_requests, tool_calls=tool_calls)
        
        # has tool calls, add to memory, run & run completion
        if len(tool_calls) != 0:
            xpander.process_tool_calls(tool_calls=tool_calls, local_tools=local_tools_by_name)
        else: # no tools, break
            break

    xpander.agent.add_messages(messages=[{"role": "assistant", "content": msg.content}])
    await msg.update()

if __name__ == "__main__":
    from chainlit.cli import run_chainlit
    run_chainlit(__file__)