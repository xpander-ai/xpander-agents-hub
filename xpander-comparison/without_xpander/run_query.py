import json
import time

from agents.memory_messaging import MemoryMessaging
from agents.parser_agent import ParserAgent
from agents.planner_agent import PlannerAgent
from agents.tool_selector_agent import ToolSelectorAgent
from handler.gpt_handle import OpenAIHandler
from utils.consts import *
from utils.generic import *
from utils.prompts import *
from without_xpander.tools.tool_router import route_tool_call


def run_company_analysis(company, model, tools=None):

    start_time = time.time()
    handler = OpenAIHandler(model_name=model)
    planner_agent = PlannerAgent(system_message=system_prompt_planner.format(company_name=company), task_message=task_prompt_planner.format(company_name=company), tools=tools, handler=handler)
    tool_selector = ToolSelectorAgent(system_message=system_prompt_selected_tools.format(company_name=company),task_message = task_prompt_selected_tools.format(company_name=company), tools=tools, handler=handler)
    parser_agent = ParserAgent(system_message=system_prompt_parser.format(company_name=company),task_message = task_prompt_parser.format(company_name=company), tools=tools, handler=handler)
    metadata =  {"input_tokens": 0, "output_tokens": 0}
    memory = MemoryMessaging()
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
            result = [{func_call.function.name: func_call.function.arguments} for func_call in tool_select_response.choices[0].message.tool_calls][0]
            method, params = extract_operation_and_params(result)
            tool_response = route_tool_call(name=method, parameters=params)
            selected_operation, tool_message = build_tool_message(planner_response, tool_select_response, tool_response, result)
            _, parser_metadata = parser_agent.invoke_llm(new_message=tool_message, memory=memory, add_to_memory=True, tmp_tools=tools)

            metadata = update_metadata(metadata, parser_metadata)
        except Exception as e:
            error_message = f"Error in step {number_of_steps}: {str(e)[:min(MAX_ERROR_MESSAGE_LENGTH, len(str(e)))]}. Tool: {json.dumps(result)}"
            memory.add_message(error_message)

        add_available_tool_names(tools, planner_agent, memory)
        planner_response, planner_metadata = planner_agent.invoke_llm(memory=memory, add_to_memory=True)
        # too many iterations
        if number_of_steps >= MAX_STEPS:
            metadata = close_metadata(planner_agent, metadata, number_of_steps, start_time)
            return metadata

    metadata = close_metadata(planner_agent, metadata, number_of_steps, start_time)
    return metadata



