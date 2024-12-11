import os
import time
import json
import logging
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
from xpander_sdk import XpanderClient, LLMProvider
from agents import SharedMemory, PlannerAgent, ToolSelectorAgent, ParserAgent
from prompts import *

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def initialize_clients():
    # Load environment variables
    load_dotenv()
    
    openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))
    xpander_client = XpanderClient(api_key=os.environ.get("XPANDER_API_KEY", ""))
    xpander_agent = xpander_client.agents.get(agent_id=os.environ.get("XPANDER_AGENT_ID", ""))
    
    return openai_client, xpander_client, xpander_agent

def initialize_sub_graph(xpander_client, xpander_agent, planner_agent, tool_selector_agent, tools):
    shared_memory = SharedMemory()
        # initialize the propmts groups sub graph
    planner_response = planner_agent.invoke_llm(memory=planner_agent.local_memory,tools=planner_agent.tools)
    shared_memory.add_message(planner_response.choices[0].message.content,role="assistant",agent_name="PlannerAgent")

    tool_selector_response = tool_selector_agent.invoke_llm(memory=tool_selector_agent.local_memory+shared_memory.get_memory(),tools=tools)
    tool_calls = xpander_client.extract_tool_calls(llm_response=tool_selector_response.model_dump())
    _ = xpander_agent.run_tools(tool_calls)
    

def run_research_agent(user_query: str, progress_callback=None):
    """
    Run the research agent with optional progress callback
    Args:
        query: The research query
        progress_callback: Optional callback function that takes tool_name as argument
    """
    openai_client, xpander_client, xpander_agent = initialize_clients()
    tools = xpander_agent.get_tools()
    
    # Initialize Agents
    planner_agent = PlannerAgent(handler=openai_client,tools=tools, task_message=planner_task_prompt.format(user_query=user_query), system_message=system_prompt_planner.format(user_query=user_query))
    tool_selector_agent = ToolSelectorAgent(handler=openai_client,tools=tools,task_message=tool_selector_task_prompt.format(user_query=user_query),system_message=tool_selector_system_prompt)
    parser_agent = ParserAgent(handler=openai_client, tools=tools, task_message=parser_task_prompt.format(user_query=user_query) ,system_message=parser_system_prompt.format(user_query=user_query))
    initialize_sub_graph(xpander_client, xpander_agent, planner_agent, tool_selector_agent, tools)
    shared_memory = SharedMemory()
    tools = xpander_agent.get_tools()

    planner_response = planner_agent.invoke_llm(memory=planner_agent.local_memory,tools=tools)
    shared_memory.add_message(planner_response.choices[0].message.content,role="assistant",agent_name="PlannerAgent")
    logger.info("Planner Response: %s", planner_response.choices[0].message.content)
    
    while True:
        try:
            
            tool_selector_response = tool_selector_agent.invoke_llm(memory=tool_selector_agent.local_memory+shared_memory.get_memory(),tools=tools)
            tool_calls = xpander_client.extract_tool_calls(llm_response=tool_selector_response.model_dump(), llm_provider=LLMProvider.OPEN_AI)
            if tool_calls:
                for i,tool_call in enumerate(tool_calls):
                    logger.info("Tool calls: %s", tool_call.name)
                    tool_response = xpander_agent.run_tool(tool_call)
                    logger.info("Tool response: %s", tool_response.result)
                    if progress_callback:
                        progress_callback(tool_call.name)
                    
                    # Check for completion
                    if tool_call.name == "pdf-operations-convertMarkdownToPDF":
                        if isinstance(tool_response.result, dict) and 'presigned_url' in tool_response.result:
                            logger.info("PDF generation complete! URL: %s", tool_response.result['presigned_url'])
                            return tool_response.result['presigned_url']
                        else:
                            logger.error("Unexpected tool response format: %s", tool_response.result)
                            return None

                    selected_tool_params = json.dumps(tool_selector_response.model_dump()['choices'][0]['message']['tool_calls'][i])
                    selected_tool_data = {
                        "selected_tool": tool_call.name,
                        "tool_call_id": tool_call.tool_call_id,
                        "params": selected_tool_params,
                        "response": tool_response.result
                    }
                    logger.info("Tool selector response: %s", json.dumps(selected_tool_data))
                
                    parser_message = (
                        f"Current Task: {planner_response.choices[0].message.content}\n"
                        f"The selected Tool: {tool_call.name}\n"
                        f"The params Tool: {json.dumps(selected_tool_data)}\n"
                    )

                    parser_response = parser_agent.invoke_llm(memory=parser_agent.local_memory+shared_memory.get_memory()+[{"role": "user", "content": parser_message}],tools=tools)
                    shared_memory.add_message(parser_response.choices[0].message.content,role="assistant",agent_name="ParserAgent")
                    logger.info("Parser response: %s", parser_response.choices[0].message.content)

        except Exception as e:
            logger.error(f"Pipeline error: {e}")
            break
    
        tools = xpander_agent.get_tools()
        planner_response = planner_agent.invoke_llm(memory=planner_agent.local_memory+shared_memory.get_memory(),tools=tools)
        shared_memory.add_message(planner_response.choices[0].message.content,role="assistant",agent_name="PlannerAgent")
        logger.info("Planner response: %s", planner_response.choices[0].message.content)
    





    
    





