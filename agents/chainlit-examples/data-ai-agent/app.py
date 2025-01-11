import json
import os
import chainlit as cl
from typing import Union
from openai import AsyncOpenAI

from xpander_sdk import XpanderClient, ToolCallType, LLMProvider
from youtube_transcript_api import YouTubeTranscriptApi

import csv
import xml.etree.ElementTree as ET
from io import StringIO
import pathlib

# ------------------------------
# 1) Setup OpenAI + xpander
# ------------------------------
api_key = os.environ.get("OPENAI_API_KEY")
client = AsyncOpenAI(api_key=api_key)

xpanderAPIKey = os.environ.get("XPANDER_API_KEY", "")
xpanderAgentID = os.environ.get("XPANDER_AGENT_ID", "")

xpander_client = XpanderClient(api_key=xpanderAPIKey)
xpander_agent = xpander_client.agents.get(agent_id=xpanderAgentID)

# ------------------------------
# 2) Local File-Handling Helpers
# (If you'd like to support reading/writing files)
# ------------------------------
def is_within_current_directory(file_path: str) -> bool:
    """
    Restrict file access to current or subdirectory, preventing climbs outside.
    """
    base_dir = pathlib.Path.cwd().resolve()
    target_path = (base_dir / file_path).resolve()
    return str(target_path).startswith(str(base_dir))

def read_file(file_path: str, output_format: str = "string") -> dict:
    """
    Safely reads a file if it's within the current directory.
    Returns a dict with either {"content"} or {"error"}.
    """
    if not is_within_current_directory(file_path):
        return {"error": "Access outside the current directory is not allowed."}

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            file_content = f.read()

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
            # Default: plain text
            return {"content": file_content}

    except FileNotFoundError:
        return {"error": f"File not found: {file_path}"}
    except Exception as e:
        return {"error": str(e)}

def write_file(file_path: str, content: Union[str, dict, list], file_type: str) -> dict:
    """
    Safely writes content to a local file (json, xml, csv, txt, etc.).
    """
    if not is_within_current_directory(file_path):
        return {"error": "Access outside the current directory is not allowed."}

    try:
        if file_type.lower() == "json":
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(content, f, indent=2)

        elif file_type.lower() == "xml":
            root = ET.Element("root")
            if isinstance(content, str):
                ET.SubElement(root, "content").text = content
            else:
                ET.SubElement(root, "content").text = json.dumps(content)
            tree = ET.ElementTree(root)
            tree.write(file_path, encoding="unicode", xml_declaration=True)

        elif file_type.lower() == "csv":
            if isinstance(content, str):
                # Convert CSV string -> rows
                content = list(csv.reader(StringIO(content)))
            with open(file_path, "w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerows(content)

        else:
            # Default text
            with open(file_path, "w", encoding="utf-8") as f:
                if isinstance(content, str):
                    f.write(content)
                else:
                    f.write(str(content))

        return {"success": f"File written to {file_path}."}

    except Exception as e:
        return {"error": str(e)}

# ------------------------------
# 3) Local YouTube Transcript
# ------------------------------
def fetch_youtube_transcript(video_url: str) -> dict:
    """
    Returns the transcript text in a dict for a valid YouTube URL.
    """
    try:
        if "youtube.com/watch?v=" in video_url:
            video_id = video_url.split("v=")[-1].split("&")[0]
        elif "youtu.be/" in video_url:
            video_id = video_url.split("/")[-1]
        else:
            return {"error": "Invalid YouTube URL pattern."}

        transcript_entries = YouTubeTranscriptApi.get_transcript(video_id)
        transcript_text = " ".join([entry["text"] for entry in transcript_entries])
        return {"transcript": transcript_text}
    except Exception as e:
        return {"error": str(e)}

# ------------------------------
# 4) Define Local Tools
# (We include read-file/write-file in case you want them.)
# ------------------------------
local_tools = [
    {
        "type": "function",
        "function": {
            # Note: xpander might rename this to xpLocal_fetch-youtube-transcript
            # We'll handle that in code below.
            "name": "fetch-youtube-transcript",
            "description": "Fetches the transcript text for a given YouTube video URL.",
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
            "description": "Writes content to a local file (json, xml, csv, or txt).",
            "parameters": {
                "type": "object",
                "properties": {
                    "filePath": {
                        "type": "string",
                        "description": "Path to save the file (within current directory)."
                    },
                    "fileContent": {
                        "type": "string",
                        "description": "Content to write. If CSV, provide raw CSV or JSON array. If JSON, provide JSON text, etc."
                    },
                    "fileType": {
                        "type": "string",
                        "description": "File type (json, xml, csv, txt)."
                    }
                },
                "required": ["filePath", "fileContent", "fileType"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read-file",
            "description": "Reads a local file (txt, csv, json, xml) from the current directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filePath": {
                        "type": "string",
                        "description": "Path to the file within the current directory."
                    },
                    "outputFormat": {
                        "type": "string",
                        "description": "Desired format to parse the file: 'string', 'csv', 'json', 'xml'. Default 'string'."
                    }
                },
                "required": ["filePath"]
            }
        }
    }
]

# ------------------------------
# 5) Register local tools with xpander
# ------------------------------
xpander_agent.add_local_tools(local_tools)

# Retrieve xpander’s remote (graph) tools for GPT-4
remote_tools = xpander_agent.get_tools()

# Combine them for usage in the GPT call
tools = remote_tools  # xpander's remote tools; xpander knows local tools already

# ------------------------------
# 6) Chainlit Setup
# ------------------------------
MAX_ITER = 5
cl.instrument_openai()

@cl.on_chat_start
def start_chat():
    # Load your system prompt from file (if present)
    cl.user_session.set(
        "message_history",
        [{"role": "system", "content": open("system_prompt.txt").read()}],
    )

# ------------------------------
# 7) xpander_tool Step: Dispatch Local vs Remote
# ------------------------------
@cl.step(type="tool")
async def xpander_tool(llm_response, message_history):
    # Extract potential tool calls from LLM
    tool_calls = XpanderClient.extract_tool_calls(
        llm_response=llm_response.model_dump()
    )

    for tool_call in tool_calls:
        current_step = cl.context.current_step
        current_step.name = tool_call.name
        current_step.input = tool_call.payload

        if tool_call.type == ToolCallType.LOCAL:
            local_params = json.loads(llm_response.choices[0].message.tool_calls[0].function.arguments)
            current_step.input = local_params
            if tool_call.name in ["fetch-youtube-transcript"]:
                video_url = local_params.get("video_url", "")
                result = fetch_youtube_transcript(video_url)

            elif tool_call.name in ["write-file"]:
                file_path = local_params.get("filePath", "")
                file_content = local_params.get("fileContent", "")
                file_type = local_params.get("fileType", "txt")
                result = write_file(file_path, file_content, file_type)

            elif tool_call.name in ["read-file"]:
                file_path = local_params.get("filePath", "")
                output_format = local_params.get("outputFormat", "string")
                result = read_file(file_path, output_format)

            else:
                result = {"error": f"Unknown local tool call: {tool_call.name}"}

            current_step.output = result
            current_step.language = "json"
            message_history.append({
                "role": "function",
                "name": tool_call.name,
                "content": json.dumps(result),
            })

        else:
            # xpander’s remote (graph) tools
            function_response = xpander_agent.run_tool(tool_call)
            current_step.output = function_response.result
            current_step.language = "json"

            message_history.append({
                "role": "function",
                "name": function_response.function_name,
                "content": json.dumps(function_response.result),
                "tool_call_id": function_response.tool_call_id
            })

# ------------------------------
# 8) LLM Chat Call
# ------------------------------
async def call_gpt4(message_history):
    """
    Calls GPT-4 with xpander + local tools. 
    xpander local tools are recognized after 'add_local_tools()'.
    We pass xpander's remote tools for function-based calls.
    """
    settings = {
        "model": "gpt-4o",    # Adjust your desired model
        "tools": tools,       # xpander's remote tool schemas
        "tool_choice": "auto" # Let GPT pick any function it sees
    }

    response = await client.chat.completions.create(
        messages=message_history,
        **settings
    )
    message = response.choices[0].message

    # If GPT calls any tool, handle it
    if message.tool_calls:
        await xpander_tool(response, message_history)

    # Display final content if any
    if message.content:
        cl.context.current_step.output = message.content

    return message

# ------------------------------
# 9) Optional Starters for UI
# ------------------------------
@cl.set_starters
async def set_starters():
    return [
        cl.Starter(
            label="Run Property Risk Assessment",
            message=(
                "Perform a detailed insurance risk assessment for the property "
                "at 3831 24th St, San Francisco, CA 94114. Include hurricane and "
                "flood risk levels using Weather API and geographic insights from Tavily"
            ),
            icon="/public/write.svg",
        ),
        cl.Starter(
            label="Calculate Insurance Premium",
            message=(
                "Calculate the insurance premium for the property at 3831 24th St, "
                "San Francisco, CA 94114 using the Premium Calculation function. "
                "Factor in earthquake retrofitting, storm windows, and low risk "
                "levels for hurricanes and floods"
            ),
            icon="/public/terminal.svg",
        )
    ]

# ------------------------------
# 10) Main Conversation Handler
# ------------------------------
@cl.on_message
async def run_conversation(message: cl.Message):
    message_history = cl.user_session.get("message_history")
    message_history.append({"name": "user", "role": "user", "content": message.content})

    cur_iter = 0
    while cur_iter < MAX_ITER:
        msg = await call_gpt4(message_history)
        if not msg.tool_calls:
            # If GPT didn't call a tool, that means final text
            await cl.Message(content=msg.content, author="AI Agent").send()
            break
        cur_iter += 1

# ------------------------------
# 11) Script Entry
# ------------------------------
if __name__ == "__main__":
    from chainlit.cli import run_chainlit
    run_chainlit(__file__)