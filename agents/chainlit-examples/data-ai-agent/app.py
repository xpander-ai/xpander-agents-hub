import chainlit as cl
from src.chainlit_handlers.chat_handlers import ChainlitHandlers

handlers = None

@cl.on_chat_start
def start_chat():
    """Initialize the chat session"""
    global handlers
    handlers = ChainlitHandlers()
    cl.user_session.set("cached_outputs", {})
    cl.user_session.set("message_history", [
        {
            "role": "system",
            "content": (
                "You are an advanced AI with Agentic RAG. "
                "For each user query, do an immediate vector search for context. "
                "If you need more data, call xpander/local tools. "
                "After each tool call, we re-run GPT so it can incorporate the new data. "
                "We store user queries, transcripts, final answers in the local DB. "
                "Stop if you have provided a final answer."
            )
        }
    ])
    print("[CHAINLIT] on_chat_start complete.")

@cl.on_message
async def on_message(msg: cl.Message):
    """Handle incoming messages"""
    global handlers
    if handlers is None:
        handlers = ChainlitHandlers()
    await handlers.handle_message(msg)

if __name__ == "__main__":
    from chainlit.cli import run_chainlit
    run_chainlit(__file__)