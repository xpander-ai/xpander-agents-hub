from typing import Any, Optional

from colorama import Fore, init

from .memory_messaging import MemoryMessaging
from .logger import Logger

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
                   tmp_tools: list = None):
        """ Invoke the LLM provider to generate a response. """
        openai_temp_messages = self.init_completions_messages(new_message, memory)
        tmp_tools = self.tools if tmp_tools is None else tmp_tools
        
        response, metadata = self.handler.agent_inference(openai_temp_messages, tmp_tools, self.tool_choice)
        
        results = self.run_post_processing(response=response)
        
        if isinstance(results, object) and hasattr(results, 'choices'):
            for choice in results.choices:
                if(hasattr(choice, 'message')):
                    if(hasattr(choice.message, 'content')):
                        if add_to_memory:
                            memory.add_message(message=choice.message.content)
                    if(hasattr(choice.message, "tool_calls")):
                        for tool_call in choice.message.tool_calls:
                            if add_to_memory:
                                memory.add_message(message={"role": "tool", "tool_call_id": tool_call.function.name})
        elif isinstance(results, str):
            memory.add_message(message=results)
        return results, metadata

    def run_post_processing(self, response: Any):
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
        tmp_messages = []
        if self.system_message:
            tmp_messages.append({"role": "system", "content": self.system_message})
        if self.task_message:
            tmp_messages.append({"role": "user", "content": self.task_message})
        tmp_messages.extend([{"role": "user", "content": message} for message in memory_messages])
        return tmp_messages
