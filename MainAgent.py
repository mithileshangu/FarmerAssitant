"""
Legacy CLI entry point.

The original project exposed shell, Python REPL, browser login, email and SSH
capabilities directly to the agent. Those capabilities are intentionally not
enabled in the GitHub-ready Streamlit application.

Use `streamlit run app.py` for the public demo.
"""

from pathlib import Path
import os

from dotenv import load_dotenv
from phi.assistant import Assistant
from phi.llm.groq import Groq

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")


def create_assistant() -> Assistant:
    if not os.getenv("GROQ_API_KEY"):
        raise RuntimeError("GROQ_API_KEY is not configured.")

    return Assistant(
        name="Farmer Assistant",
        llm=Groq(model=os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")),
        description="A multilingual assistant for farmers.",
        markdown=True,
        instructions=[
            """
Reply in the same language as the user's message. If the input is a
transcription of speech, treat it as normal text and preserve its language.
Do not force a particular language.
"""
        ],
    )


if __name__ == "__main__":
    print("Use: streamlit run app.py")
