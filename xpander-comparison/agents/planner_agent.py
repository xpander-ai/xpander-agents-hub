import re
from typing import Any

from agents.base_agent import BaseAgent
from agents.memory_messaging import MemoryMessaging


class PlannerAgent(BaseAgent):
    def __init__(self, handler, tools: list,
                 task_message: str = None,
                 system_message: str = None,
                 finish_message: str = "Final Answer",
                 agent_log_color: str = "GREEN"):
        agent_type = "PlannerAgent"
        super().__init__(agent_type=agent_type, handler=handler, tools=tools, tool_choice="none",
                         system_message=system_message, task_message=task_message, agent_log_color=agent_log_color)
        self.finish_message = finish_message
        self.is_finished = False
        self.step_number = 1

    def run_post_processing(self, response: Any):
        if re.search(self.finish_message, response):
            self.is_finished = True 
        self.logger.info(response)
        return response

    def finished(self) -> bool:
        return self.is_finished
