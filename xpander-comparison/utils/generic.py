import json
import time

from utils.consts import *


def update_metadata(metadata, new_metadata):
    """
    Updates an existing metadata dictionary with new metadata values.

    Args:
        metadata (dict): The original metadata dictionary to update
        new_metadata (dict): New metadata to add or update

    Returns:
        dict: Updated metadata dictionary with combined values
    """
    for key, value in new_metadata.items():
        if key in metadata:
            metadata[key] += value
        else:
            metadata[key] = value
    return metadata


def add_available_tool_names(tools, planner_agent, memory):
    """
    Adds available tool names to the planner agent and memory.

    Args:
        tools (list): List of available tools with their configurations
        planner_agent (PlannerAgent): Agent responsible for planning analysis steps
        memory (MemoryMessaging): Memory object to store messages and tool information
    """
    planner_agent.tools = tools
    available_tools = []
    for tool in tools:
        available_tools.append(tool.get("function").get("name"))
    memory.add_message(
        f"here are all the available tools: {available_tools}. you must related only to these tools in this current step")


def extract_tool_info(output_response, tool_select_response, planner_response, max_length: int = MAX_RESPONSE_LENGTH):
    """
    Extracts and formats tool execution information.

    Args:
        output_response (Any): Response from tool execution
        tool_select_response (dict): Response from tool selection
        planner_response (str): Response from planner agent
        max_length (int, optional): Maximum length for response strings. Defaults to MAX_RESPONSE_LENGTH.

    Returns:
        str: Formatted message containing tool execution details
    """
    try:
        string_output_response = json.dumps(output_response)
        short_output_response = string_output_response[:min(max_length, len(string_output_response))]
        tools_with_params = json.dumps(tool_select_response['choices'][0]['message']['tool_calls'])[
                           :min(max_length, len(short_output_response))]
        tools_selected = tool_select_response['choices'][0]['message']['tool_calls'][0]['function']['name']
    except Exception:
        tools_with_params = "No tool calls found"
        tools_selected = "No tool calls found"
        output_response = "No tool calls found"
    tool_message = (
        f"Current Task: {planner_response}\n"
        f"The selected Tool: {tools_selected}\n"
        f"The params Tool: {tools_with_params}\n"
        f"Tool response: {short_output_response}"
    )
    return tool_message


def extract_operation_and_params(input_function):
    """
    Extracts operation ID and parameters from an input function.

    Args:
        input_function (dict): Dictionary containing operation ID and parameters

    Returns:
        tuple: A tuple containing (operation_id, parameters)
    """
    for operation_id, params_dict in input_function.items():
        return operation_id, json.loads(params_dict)


def build_tool_message(planner_response, tool_select_response, tool_response, first_tool=None):
    """
    Builds a formatted message containing tool execution details.

    Args:
        planner_response (str): Response from planner agent
        tool_select_response (Any): Response from tool selection
        tool_response (Union[dict, list]): Response from tool execution
        first_tool (dict, optional): First tool information if available. Defaults to None.

    Returns:
        tuple: A tuple containing (list of selected operations, formatted tool message)
    """
    parser_message = []
    selected_operation = []
    if isinstance(tool_response, dict):
        parser_message.append(json.dumps(tool_response))
        selected_operation.append(first_tool if first_tool else {})
    elif isinstance(tool_response, list):
        for tool_response in tool_response:
            parser_message.append(json.dumps(tool_response.result))
            selected_operation.append(tool_response.name)
    else:
        parser_message.append(json.dumps(tool_response.result))
        selected_operation.append(tool_response.function_name)
    parser_message = '\n'.join(parser_message)
    tool_message = extract_tool_info(parser_message, tool_select_response.model_dump(), planner_response)
    return selected_operation, tool_message


def close_metadata(planner_agent, metadata, number_of_steps, start_time):
    """
    Finalizes metadata with execution statistics.

    Args:
        planner_agent (PlannerAgent): Agent responsible for planning analysis steps
        metadata (dict): Current metadata dictionary
        number_of_steps (int): Total number of execution steps
        start_time (float): Timestamp when execution started

    Returns:
        dict: Updated metadata with execution statistics
    """
    agent_think_finished = planner_agent.finished()
    end_time = time.time()
    metadata.update({
        "number_of_steps": number_of_steps,
        "agent_think_finished": agent_think_finished,
        "latency": end_time - start_time
    })
    return metadata
