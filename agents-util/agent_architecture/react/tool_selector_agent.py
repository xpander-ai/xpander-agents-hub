from typing import Any

from agents.base_agent import BaseAgent
from agents.memory_messaging import MemoryMessaging

DEFAULT_SYSTEM_MESSAGE = """You are an tool selector agent responsible for selecting the correct tool with the most relevant parameters that will fullfil the task your will received from the planner agent to execute the plan."""
DEFAULT_TASK_MESSAGE = """
Your task:
1. Select the most accurate tool to fulfill the current task provided by the planner agent. most of the time you will have only one tool to use.
2. Generate all required parameters by the schema you got that will fulfill the task.
3. You must return your answer as a tool_call with the function name and relevant arguments.
4. If the planer explain about the error and how to fix it, you should fix the last tool call parameters and return the new tool call.
5. you must be accurate with the required input parameters and specified how they should be in the output request.


This is the expected input template:

Plan step [i]: [the current step of your plan for how to solve the query (can be also how to fix your last error)].


Here are examples:

Example 1:
Input:
Plan step 2: Generate a story about football in a maximum of 100 characters and post this story message to user ID: [user_id].
Tool Name: PostMessage
Output:
Your answer: arguments: {'message': 'Hey Bob, did you know a dog once stopped a football match by running onto the field?🐶⚽️', 'user_id': [user_id]}, function: PostMessage

Begin!
return here the tool name with all required parameters.
"""


class ToolSelectorAgent(BaseAgent):
    def __init__(self, handler, tools: list,
                 task_message: str = DEFAULT_TASK_MESSAGE,
                 system_message: str = DEFAULT_SYSTEM_MESSAGE,
                 agent_log_color: str = "BLUE"):
        agent_type = "ToolSelectorAgent"

        super().__init__(agent_type=agent_type, handler=handler, tools=tools, tool_choice="required",
                         system_message=system_message, task_message=task_message, agent_log_color=agent_log_color)
        self.is_finished = False
        self.step_number = 1

    def run_post_processing(self, response: Any, memory: MemoryMessaging = None, extract_data: dict = None):
        return response
