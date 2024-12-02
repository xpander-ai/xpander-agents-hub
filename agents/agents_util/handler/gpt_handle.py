import os
import time

from openai import OpenAI
from .handler import BaseHandler

class OpenAIHandler(BaseHandler):
    def __init__(self, model_name, temperature=0.0, top_p=1, max_tokens=4096) -> None:
        super().__init__(model_name, temperature, top_p, max_tokens)
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def agent_inference(self, message, tmp_tools, tool_choice):
        start = time.time()
        if tmp_tools is not None:
            tool_choice = "none" if tool_choice is None else tool_choice
            response = self.client.chat.completions.create(
                messages=message,
                model=self.model_name,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                top_p=self.top_p,
                tool_choice=tool_choice,
                tools=tmp_tools,
                parallel_tool_calls=True,
            )
        else:
            response = self.client.chat.completions.create(
                messages=message,
                model=self.model_name,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                top_p=self.top_p
            )
        try:
            result = [
                {func_call.function.name: func_call.function.arguments}
                for func_call in response.choices[0].message.tool_calls
            ]
            if len(result) > 0:
                latency = time.time() - start
                return response, {"input_tokens": response.usage.prompt_tokens, "output_tokens": response.usage.total_tokens - response.usage.prompt_tokens,
                                  "latency": latency}
        except:
            result = response.choices[0].message.content
        latency = time.time() - start
        return result, {"input_tokens": response.usage.prompt_tokens, "output_tokens": response.usage.total_tokens - response.usage.prompt_tokens,
                        "latency": latency}