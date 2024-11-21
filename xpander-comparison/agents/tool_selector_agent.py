from typing import Any

from agents.base_agent import BaseAgent
from agents.memory_messaging import MemoryMessaging


class ToolSelectorAgent(BaseAgent):
    def __init__(self, handler, tools: list,
                 task_message: str = None,
                 system_message: str = None,
                 agent_log_color: str = "BLUE"):
        agent_type = "ToolSelectorAgent"

        super().__init__(agent_type=agent_type, handler=handler, tools=tools, tool_choice="required",
                         system_message=system_message, task_message=task_message, agent_log_color=agent_log_color)
        self.is_finished = False
        self.step_number = 1

    def run_post_processing(self, response: Any):
        self.logger.info(response)
        return response
