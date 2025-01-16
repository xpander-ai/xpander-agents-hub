import chainlit as cl
from typing import List, Dict, Any
import tiktoken
import json
from openai import AsyncOpenAI

from src.config.settings import (
    OPENAI_API_KEY,
    TOKEN_THRESHOLD,
    MAX_ITER
)
from src.db.vector_store import VectorStore
from src.tools.tool_manager import ToolManager
from src.utils.xpander_setup import XpanderSetup

class ChainlitHandlers:
    def __init__(self):
        self.vector_store = VectorStore()
        self.tool_manager = ToolManager(self.vector_store)
        self.xpander_setup = XpanderSetup(self.tool_manager)
        self.openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        cl.instrument_openai()

    def auto_rag_prepend(self, user_text: str, top_k: int = 3) -> str:
        """Do a quick vector search on user_text, prepend best chunks as context."""
        print(f"[AUTO-RAG] Searching for user_text[:60]={user_text[:60]}")
        hits = self.vector_store.search(user_text, top_k=top_k)
        if not hits:
            print("[AUTO-RAG] No relevant hits. Returning user text alone.")
            return user_text
        ctx = "\n".join([f"- {h}" for h in hits])
        return f"Auto-RAG Context:\n{ctx}\n\nUser Query: {user_text}"

    async def call_gpt4(self, msg_history):
        """Helper to avoid confusion. Just calls GPT once."""
        settings = {
            "model": "gpt-4o",
            "tools": self.xpander_setup.get_distinct_tools(),
            "tool_choice": "auto"
        }
        resp = await self.openai_client.chat.completions.create(messages=msg_history, **settings)
        return resp.choices[0].message, resp

    @cl.step(type="tool")
    async def xpander_tool(self, llm_response, message_history):
        """Intercepts GPT's tool calls, runs them, appends results to the conversation."""
        tool_calls = self.xpander_setup.extract_tool_calls(llm_response)
        cached_outputs = cl.user_session.get("cached_outputs")

        for i, tc in enumerate(tool_calls):
            current_step = cl.context.current_step
            current_step.name = tc.name
            current_step.input = tc.payload

            fn_args = llm_response.choices[0].message.tool_calls[i].function.arguments
            local_params = json.loads(fn_args)
            result = {}

            if tc.type == "LOCAL":
                current_step.input = local_params
                if tc.name == "fetch-youtube-transcript":
                    r = self.tool_manager.fetch_youtube_transcript(local_params["video_url"])
                    if "transcript" in r:
                        text = r["transcript"]
                        tok = len(tiktoken.encoding_for_model("gpt-4o").encode(text))
                        self.vector_store.add_text(text, local_params["video_url"])
                        if tok > TOKEN_THRESHOLD:
                            cached_outputs["transcript_text"] = text
                            result = {"info": "Transcript chunked into DB."}
                        else:
                            cached_outputs["transcript_text"] = text
                            result = {"transcript": text}
                    else:
                        result = r
                elif tc.name == "write-file":
                    w = self.tool_manager.write_file(
                        local_params["path"],
                        local_params["fileContent"],
                        local_params["fileType"]
                    )
                    result.update(w)
                elif tc.name == "read-file":
                    r = self.tool_manager.read_file(
                        local_params["path"],
                        fmt=local_params.get("fmt", "string")
                    )
                    result = r
                elif tc.name == "search-long-response":
                    r = self.vector_store.search_long_response(
                        local_params["query"],
                        local_params.get("top_k", 3)
                    )
                    result = r
                else:
                    result = {"error": f"Unknown local tool: {tc.name}"}

                # Possibly store big result
                text_json = json.dumps(result, ensure_ascii=False)
                tok = len(tiktoken.encoding_for_model("gpt-4o").encode(text_json))
                if tok > TOKEN_THRESHOLD:
                    self.vector_store.add_text(text_json, tc.name)
                    result = {"info": "Tool result huge => chunked in DB."}

                current_step.output = result
                current_step.language = "json"
                message_history.append({
                    "role": "function",
                    "name": tc.name,
                    "content": json.dumps(result)
                })
            else:
                # xpander remote
                function_response = self.xpander_setup.run_tool(tc)
                text_repr = json.dumps(function_response.result, ensure_ascii=False)
                tok = len(tiktoken.encoding_for_model("gpt-4o").encode(text_repr))
                if tok > TOKEN_THRESHOLD:
                    self.vector_store.add_text(text_repr, tc.name)
                    short_msg = {"info": f"Output from xpander tool '{tc.name}' was large => stored in DB."}
                    current_step.output = short_msg
                    current_step.language = "json"
                    message_history.append({
                        "role": "function",
                        "name": function_response.function_name,
                        "content": json.dumps(short_msg),
                        "tool_call_id": function_response.tool_call_id
                    })
                else:
                    current_step.output = function_response.result
                    current_step.language = "json"
                    message_history.append({
                        "role": "function",
                        "name": function_response.function_name,
                        "content": json.dumps(function_response.result),
                        "tool_call_id": function_response.tool_call_id
                    })

        cl.user_session.set("cached_outputs", cached_outputs)

    async def handle_message(self, msg: cl.Message):
        """
        Multi-pass approach:
          1) Store user query => user_query
          2) auto-rag prepend
          3) for i < MAX_ITER:
             - call GPT
             - if GPT calls tools => xpander_tool
             - if GPT has final .content => done
          4) store final answer => assistant_answer
        """
        # 1) store user query
        self.vector_store.add_text(msg.content, "user_query")

        # 2) auto-rag
        user_txt_with_ctx = self.auto_rag_prepend(msg.content)
        message_history = cl.user_session.get("message_history")
        message_history.append({"role": "user", "content": user_txt_with_ctx})

        cur_iter = 0
        final_ans = None

        while cur_iter < MAX_ITER:
            gpt_msg, raw_llm_resp = await self.call_gpt4(message_history)

            if gpt_msg.tool_calls:
                # Tools => xpander_tool
                await self.xpander_tool(raw_llm_resp, message_history)

            if gpt_msg.content:
                final_ans = gpt_msg.content
                await cl.Message(content=final_ans, author="AI Agent").send()
                break

            cur_iter += 1

        if cur_iter >= MAX_ITER and not final_ans:
            no_ans = "No final answer after multiple passes."
            await cl.Message(content=no_ans, author="AI Agent").send()

        if final_ans:
            # store final in DB
            self.vector_store.add_text(final_ans, "assistant_answer") 