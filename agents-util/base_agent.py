from time import sleep
from typing import Any, Optional

from colorama import Fore, init

from agents.agent_logger import Logger
from agents.memory_messaging import MemoryMessaging

# List of plugin handlers available for use
init(autoreset=True)



class BaseAgent:
    def __init__(self, agent_type: str, handler, tools: Optional[list],
                 tool_choice: Optional[str],
                 task_message: str = None, system_message: str = None, agent_log_color: str = Fore.WHITE):
        self.agent_type = agent_type
        self.tools = tools
        self.tool_choice = tool_choice
        self.system_message = system_message
        self.task_message = task_message
        self.handler = handler
        self.logger = self.set_logger(agent_log_color)

    def invoke_llm(self, new_message: Any = None, memory: MemoryMessaging = None, add_to_memory: bool = True,
                   tmp_tools: list = None, extract_data: dict = None):
        """ Invoke the LLM provider to generate a response. """
        openai_temp_messages = self.init_completions_messages(new_message, memory)
        tmp_tools = self.tools if tmp_tools is None else tmp_tools
        
        for try_id in range(3):
            try:
                response, metadata = self.handler.agent_inference(openai_temp_messages, tmp_tools, self.tool_choice)
                
                results = self.run_post_processing(response=response, memory=memory, extract_data=extract_data)
                if add_to_memory:
                    memory.add_message(message=results)
                return results, metadata
            except Exception as e:
                self.logger.error(f"Failed to generate conversation try {try_id}: {e}")
                sleep(3)
        raise Exception(f"Failed to generate conversation after 3 attempts, {e}")

    def run_post_processing(self, response: Any, memory: MemoryMessaging, extract_data: dict = None):
        return response

    def set_logger(self, agent_log_color: str):
        return Logger(color=agent_log_color, logger_name=self.agent_type).logger

    def init_completions_messages(self, message: str = None, memory: MemoryMessaging = None):
        """
        Convert an input prompt to a message object.

        Args:
            message (str): The input prompt.

        Returns:
            dict: The message object.
        """
        memory_messages = [] if memory is None else memory.get_messages()
        if message is None and memory is None:
            raise Exception("No message provided to initialize completions messages")
        if message is not None:
            if isinstance(message, str):
                memory_messages.append(message)
            else:
                raise Exception("Invalid message provided to initialize completions messages")

        tmp_messages = [{"role": "system", "content": self.system_message},
                        {"role": "user", "content": self.task_message}]
        tmp_messages.extend([{"role": "user", "content": message} for message in memory_messages])
        return tmp_messages
