import os
import time

from agents.memory_messaging import MemoryMessaging
from agents.parser_agent import ParserAgent
from agents.planner_agent import PlannerAgent
from agents.tool_selector_agent import ToolSelectorAgent
from handler.gpt_handle import OpenAIHandler
from utils.consts import *
from utils.generic import *
from utils.prompts import *
from xpander_sdk import XpanderClient, Agent
from dotenv import load_dotenv
load_dotenv()

xpanderClient = XpanderClient(api_key=os.environ.get("XPANDER_API_KEY", ""))

def subgraph_decision(xpander_client, planner_agent, company, tool_selector, tools):
    """
    Makes decisions about the subgraph structure for company analysis.

    Args:
        xpander_client (XpanderClient): Client instance for Xpander API
        planner_agent (PlannerAgent): Agent responsible for planning analysis steps
        company (str): Name of the company being analyzed
        tool_selector (ToolSelectorAgent): Agent for selecting appropriate tools
        tools (list): Available tools for analysis

    Returns:
        dict: Metadata containing input and output token counts
    """
    memory = MemoryMessaging()
    start_task_graph = system_prompt_graph_decision.format(company_name=company)
    memory.add_message(start_task_graph)
    metadata = {"input_tokens": 0, "output_tokens": 0}
    _, planner_metadata = planner_agent.invoke_llm(memory=memory, add_to_memory=False)
    tool_select_response, tool_selector_metadata = tool_selector.invoke_llm(memory=memory, add_to_memory=False,
                                                                            tmp_tools=tools)
    tool_to_call = XpanderClient.extract_tool_calls(tool_select_response.model_dump())
    _ = xpander_client.run_tools(tool_to_call)
    metadata = update_metadata(metadata, planner_metadata)
    metadata = update_metadata(metadata, tool_selector_metadata)
    return metadata


def run_company_analysis(company, model):
    """
    Executes a comprehensive analysis of a company using various agents and tools.

    Args:
        company (str): Name of the company to analyze
        model (str): Name of the AI model to use for analysis

    Returns:
        dict: Metadata containing analysis results, including token counts, 
             number of steps, and execution time
    """
    xpander_agent : Agent = xpanderClient.agents.get(agent_id=os.environ.get("XPANDER_AGENT_ID", ""))
    start_time = time.time()
    tools = xpander_agent.get_tools()
    handler = OpenAIHandler(model_name=model)
    planner_agent = PlannerAgent(system_message=system_prompt_planner.format(company_name=company),
                                 task_message=task_prompt_planner.format(company_name=company), tools=tools,
                                 handler=handler)
    tool_selector = ToolSelectorAgent(system_message=system_prompt_selected_tools.format(company_name=company),
                                      task_message=task_prompt_selected_tools.format(company_name=company), tools=tools,
                                      handler=handler)
    parser_agent = ParserAgent(system_message=system_prompt_parser.format(company_name=company),
                               task_message=task_prompt_parser.format(company_name=company), tools=tools, handler=handler)
    metadata = subgraph_decision(xpander_agent, planner_agent, company, tool_selector, tools)
    memory = MemoryMessaging()
    tools = xpander_agent.get_tools()
    planner_agent.tools = tools
    planner_response, planner_metadata = planner_agent.invoke_llm(memory=memory, add_to_memory=True)
    number_of_steps = 0
    while not planner_agent.finished():
        number_of_steps += 1
        try:
            metadata = update_metadata(metadata, planner_metadata)
            tool_select_response, tool_selector_metadata = tool_selector.invoke_llm(memory=memory,
                                                                                    add_to_memory=False,
                                                                                    tmp_tools=tools)
            metadata = update_metadata(metadata, tool_selector_metadata)
            
            tool_calls = XpanderClient.extract_tool_calls(tool_select_response.model_dump())
                
            if len(tool_calls) != 0:
                for tool_call in tool_calls:
                    tool_response = xpander_agent.run_tool(tool=tool_call)
                    selected_operation, tool_message = build_tool_message(planner_response, tool_select_response, tool_response)
                    _, parser_metadata = parser_agent.invoke_llm(new_message=tool_message, memory=memory, add_to_memory=True,
                                                                tmp_tools=tools)

                    metadata = update_metadata(metadata, parser_metadata)
        except Exception as e:
            selected_operations = '\n'.join([] if selected_operation else selected_operation)
            error_message = f"Error in step {number_of_steps}: {str(e)[:min(MAX_ERROR_MESSAGE_LENGTH, len(str(e)))]}. Tool: {selected_operations}"
            memory.add_message(error_message)
        tools = xpander_agent.get_tools()

        add_available_tool_names(tools, planner_agent, memory)
        planner_response, planner_metadata = planner_agent.invoke_llm(memory=memory, add_to_memory=True)
        # too many iterations
        if number_of_steps >= MAX_STEPS:
            metadata = close_metadata(planner_agent, metadata, number_of_steps, start_time)
            return metadata

    metadata = close_metadata(planner_agent, metadata, number_of_steps, start_time)
    return metadata


