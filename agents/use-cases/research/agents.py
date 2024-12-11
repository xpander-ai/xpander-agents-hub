import logging
import re
from typing import List, Dict, Any
from xpander_sdk import OpenAISupportedModels

logger = logging.getLogger(__name__)

class SharedMemory:
    def __init__(self):
        self.memory = []

    def add_message(self, content: str, role: str = "assistant", agent_name: str = None):
        self.memory.append({"role": role, "content": content, "agent_name": agent_name})

    def get_memory(self) -> list:
        return self.memory

class PlannerAgent:
    def __init__(self, handler, tools: list, task_message: str, system_message: str):
        self.handler = handler
        self.tools = tools
        self.task_message = task_message
        self.system_message = system_message
        self.local_memory = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": task_message},
        ]
        self.step_number = 1

    def invoke_llm(self, memory, tools=None, model=OpenAISupportedModels.GPT_4_O, max_tokens=4096):
        try:
            response = self.handler.chat.completions.create(
                model=model,
                messages=memory,
                tools=tools,
                tool_choice="none",
                max_tokens=max_tokens,
                temperature=0.0,
            )
            return response
        except Exception as e:
            raise RuntimeError(f"Error invoking LLM: {e}")
        

class ToolSelectorAgent:
    def __init__(self, handler, tools: list, task_message: str, system_message: str):
        self.handler = handler
        self.tools = tools
        self.task_message = task_message
        self.system_message = system_message
        self.local_memory = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": task_message},
        ]
        self.selected_tools = []

    def invoke_llm(self, memory, tools=None, model=OpenAISupportedModels.GPT_4_O, max_tokens=4096):
        try:                                
            response = self.handler.chat.completions.create(
                model=model,
                messages=memory,
                tools=tools,
                parallel_tool_calls=False,
                tool_choice="required",
                max_tokens=max_tokens,
                temperature=0.0,
            )
            return response
        except Exception as e:
            raise RuntimeError(f"Error invoking LLM: {e}")

class ParserAgent:
    def __init__(self, handler, tools: list, task_message: str, system_message: str):
        self.handler = handler
        self.task_message = task_message
        self.system_message = system_message
        self.tools = tools
        self.local_memory = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": task_message},
        ]

    def invoke_llm(self, memory, tools=None, model=OpenAISupportedModels.GPT_4_O, max_tokens=16384):
        try:
            response = self.handler.chat.completions.create(
                model=model,
                messages=memory,
                max_tokens=max_tokens,
                temperature=0.0,
            )
            return response
        except Exception as e:
            raise RuntimeError(f"Error invoking LLM ParserAgent: {e}")