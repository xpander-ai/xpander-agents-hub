import json
import os
from openai import AsyncOpenAI
from xpander_sdk import XpanderClient

import chainlit as cl

api_key = os.environ.get("OPENAI_API_KEY")
client = AsyncOpenAI(api_key=api_key)
xpanderAPIKey = os.environ.get("XPANDER_API_KEY","")
xpanderAgentID = os.environ.get("XPANDER_AGENT_ID", "")

xpander_client = XpanderClient(api_key=xpanderAPIKey)
xpander_agent = xpander_client.agents.get(agent_id=xpanderAgentID)

tools = xpander_agent.retrieve_all_graph_tools()

MAX_ITER = 5

cl.instrument_openai()

@cl.on_chat_start
def start_chat():
    cl.user_session.set(
        "message_history",
        [{"role": "system", "content": open("system_prompt.txt").read()}],
    )


@cl.step(type="tool")
async def xpander_tool(llm_response, message_history):
    tools_to_run = XpanderClient.extract_tool_calls(llm_response=llm_response.model_dump())
    for tool in tools_to_run:
        current_step = cl.context.current_step
        current_step.name = tool.name
        current_step.input = tool.payload
        function_response = xpander_agent.run_tool(tool)
        current_step.output = function_response.result
        current_step.language = "json"

        message_history.append(
            {
                "role": "function",
                "name": function_response.function_name,
                "content": json.dumps(function_response.result),
                "tool_call_id": function_response.tool_call_id
            }
        )


async def call_gpt4(message_history):
    settings = {
        "model": "gpt-4o",
        "tools": tools,
        "tool_choice": "auto",
    }

    response = await client.chat.completions.create(
        messages=message_history, **settings
    )

    message = response.choices[0].message

    if message.tool_calls:
        await xpander_tool(response, message_history)

    if message.content:
        cl.context.current_step.output = message.content

    return message

@cl.set_starters
async def set_starters():
    return [
        cl.Starter(
            label="Run Property Risk Assessment",
            message="Perform a detailed insurance risk assessment for the property at 3831 24th St, San Francisco, CA 94114. Include hurricane and flood risk levels using Weather API and geographic insights from Tavily",
            icon="/public/write.svg",
            ),
        cl.Starter(
            label="Calculate Insurance Premium",
            message="Calculate the insurance premium for the property at 3831 24th St, San Francisco, CA 94114 using the Premium Calculation function. Factor in earthquake retrofitting, storm windows, and low risk levels for hurricanes and floods",
            icon="/public/terminal.svg",
            )
        ]

@cl.on_message
async def run_conversation(message: cl.Message):
    message_history = cl.user_session.get("message_history")
    message_history.append({"name": "user", "role": "user", "content": message.content})

    cur_iter = 0

    while cur_iter < MAX_ITER:
        message = await call_gpt4(message_history)
        if not message.tool_calls:
            await cl.Message(content=message.content, author="AI Agent").send()
            break

        cur_iter += 1

if __name__ == "__main__":
    from chainlit.cli import run_chainlit
    run_chainlit(__file__)
