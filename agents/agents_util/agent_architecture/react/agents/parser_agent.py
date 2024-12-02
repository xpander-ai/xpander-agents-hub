from typing import Any, Optional

from .base_agent import BaseAgent

class ParserAgent(BaseAgent):
    def __init__(self, handler, tools: Optional[list],
                 task_message: str = None,
                 system_message: str = None,
                 agent_log_color: str = "RED"):
        agent_type = "ParserAgent"
        super().__init__(agent_type=agent_type, handler=handler, tools=tools, tool_choice=None,
                         system_message=system_message, task_message=task_message, agent_log_color=agent_log_color)
        self.step_number = 1

    def run_post_processing(self, response: Any):
        self.logger.info("Parser agent response:")
        self.logger.info(response)
        return response