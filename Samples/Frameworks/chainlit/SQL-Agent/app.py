## This is example code of how to use LLamaIndex to handle the data and query the SQL database and xpander.ai to orchestrate and power the AI Agent with the tools.
## The frontend is handled by Chainlit and the backend is handled by LlamaIndex and xpander.ai.

## OCR
## pip install tesseract-ocr, docline
from docling.document_converter import DocumentConverter

## Standard Libraries
import os
import uuid
from typing import Callable, Dict
from dotenv import load_dotenv
import mimetypes
from pathlib import Path

## Llama Index
from llama_index.llms.openai import AsyncOpenAI, OpenAI
from llama_index.core import SQLDatabase
from llama_index.core.query_engine import NLSQLTableQueryEngine

## xpander.ai
from xpander_utils.sdk.adapters import ChainlitAdapter

## Chainlit
import chainlit as cl

## Database
from db import engine, add_file_record

## Environment Variables
load_dotenv()

## xpander.ai
xpander_api_key = os.environ.get("XPANDER_API_KEY","") 
xpander_agent_id = os.environ.get("XPANDER_AGENT", "") 
openai_key = os.environ.get("OPENAI_API_KEY", "") 

## LLMs
chat_llm = AsyncOpenAI(api_key=openai_key)
agent_llm = OpenAI(api_key=openai_key,model="gpt-4o")

## Database
sql_database = SQLDatabase(engine)

## Query Engine (Llama Index)
query_engine = NLSQLTableQueryEngine(
    sql_database=sql_database,
    llm=agent_llm,
    table_name="file_tracking"
)

def perform_ocr(file_path: str) -> str:
    """
    Reads a local file and perform OCR on it
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found at path: {file_path}")
        
    converter = DocumentConverter()
    
    doc = converter.convert(file_path).document
    ocr_result = doc.export_to_markdown()
    return ocr_result

## File tracking database function
def query_file_tracking(query: str) -> str:
    """
    Query the file tracking database using natural language and return the results
    """
    response = query_engine.query(query)
    return response.response

def track_file(original_filename: str, original_url: str, generated_filename: str, generated_url: str) -> int:
    """
    Add a new file record to the tracking database
    """
    return add_file_record(
        original_filename=original_filename,
        original_download_url=original_url,
        generated_filename=generated_filename,
        generated_download_url=generated_url
    )

## Database Function Schemes (loaded into the AI Agent)
file_tracking_tools = [
    {
        "declaration": {
            "type": "function",
            "function": {
                "name": "query_file_tracking",
                "description": "Query the file tracking database to get information about processed files. The database contains timestamps, original and generated file names and their download URLs.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "A natural language query about the file tracking database (e.g., 'Show me all files processed today' or 'Find the download URL for file X')"
                        }
                    },
                    "required": ["query"]
                }
            }
        },
        "fn": query_file_tracking
    },
    {
        "declaration": {
            "type": "function",
            "function": {
                "name": "track_file",
                "description": "Add a new file record to the tracking database",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "original_filename": {
                            "type": "string",
                            "description": "The original name of the uploaded file"
                        },
                        "original_url": {
                            "type": "string",
                            "description": "The download URL for the original file"
                        },
                        "generated_filename": {
                            "type": "string",
                            "description": "The name of the generated/processed file"
                        },
                        "generated_url": {
                            "type": "string",
                            "description": "The download URL for the generated file"
                        }
                    },
                    "required": ["original_filename", "original_url", "generated_filename", "generated_url"]
                }
            }
        },
        "fn": track_file
    }
]

## Helper function to load the tools into the AI Agent
local_tools_list = [tool['declaration'] for tool in file_tracking_tools]
local_tools_by_name: Dict[str, Callable] = {}
for tool in file_tracking_tools:
    local_tools_by_name[tool['declaration']['function']['name']] = tool['fn']

##  Instrument the OpenAI client to the Chainlit session
cl.instrument_openai()

##  Define the chat start event (When loading the chat interface)
@cl.on_chat_start
def start_chat():
    # set xpander instance to the user session
    xpander = ChainlitAdapter(agent_id=xpander_agent_id, api_key=xpander_api_key, with_agent_end_tool=True, should_reset_cache=True)
    xpander.agent.add_local_tools(local_tools_list)
    cl.user_session.set("xpander", xpander)

##  Define the chat message event (When a message is sent)
@cl.on_message
async def main(message: cl.Message):
    xpander: ChainlitAdapter = cl.user_session.get("xpander")
    thread_id: str = xpander.get_thread_id()
    
    # create task and updates the chainlit session
    xpander.add_task(message.content,thread_id=thread_id)
    
    settings = {
        "model": "gpt-4o",
        "tools": xpander.agent.get_tools()
    }
    
    ##  Define the chat completion event (LLM completion)
    def run_completion():
        return chat_llm.chat.completions.create(
            messages=xpander.agent.messages, tool_choice=xpander.agent.tool_choice, stream=True, **settings
    )
        
    # create chainlit message
    msg = cl.Message(content="")
    
    PDFs = [file for file in message.elements if "application/pdf" in file.mime]
    for pdf in PDFs:
        pdf_content = perform_ocr(pdf.path)
        xpander.agent.add_messages(messages=[{"role": "user", "content": f"I have uploaded a PDF file, name: {pdf.name}"}])
        xpander.agent.add_messages(messages=[{"role": "user", "content": f"The file content is: {pdf_content}"}])

    ## Process the chat completion (The AI Agent main business logic)
    while not xpander.agent.is_finished():
        stream = await run_completion()

        # Prepeare the tool calls from the stream (Tool calls are the AI Agent's actions)
        tool_calls = xpander.aggregate_tool_calls_stream()
        
        # Handles the stream of the LLM completion
        async for part in stream:
            if token := part.choices[0].delta.content or "":
                await msg.stream_token(token)
            
            # handle tool calling
            if tool_call_requests := part.choices[0].delta.tool_calls or []:
                tool_calls = xpander.aggregate_tool_calls_stream(tool_call_requests=tool_call_requests, tool_calls=tool_calls, completion_response=part.model_dump())
        
        # has tool calls, add to memory, run & run completion
        if len(tool_calls) != 0:
            run_id = str(uuid.uuid4())
            final_answer = await xpander.process_tool_calls(tool_calls=tool_calls, local_tools=local_tools_by_name, run_id=run_id)
            if final_answer:
                await msg.stream_token(final_answer)
        else: # no tools, break
            break

    xpander.agent.add_messages(messages=[{"role": "assistant", "content": msg.content}])
    await msg.update()

if __name__ == "__main__":
    from chainlit.cli import run_chainlit
    run_chainlit(__file__)