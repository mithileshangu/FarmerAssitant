from pathlib import Path
import os
import shelve
import uuid
from datetime import datetime, timezone

import streamlit as st
from dotenv import load_dotenv

from phi.assistant import Assistant
from phi.llm.groq import Groq
from phi.tools.duckduckgo import DuckDuckGo

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
CHAT_DB = str(ROOT / "data" / "chat_history")

st.set_page_config(
    page_title="Farmer Assistant",
    page_icon="🌾",
    layout="wide",
)

if not os.getenv("GROQ_API_KEY"):
    st.error("GROQ_API_KEY is not configured. Copy .env.example to .env and add your key.")
    st.stop()


@st.cache_resource
def get_search_tool():
    return DuckDuckGo()


@st.cache_resource
def get_assistant():
    instructions = """
You are Farmer Assistant, an AI assistant designed to help farmers, especially
Indian farmers, with practical and easy-to-understand information.

LANGUAGE POLICY:
- Detect the language used by the user from the current message.
- Reply in the same language whenever possible.
- If the user mixes languages, reply naturally in the dominant language and preserve
  important technical or agricultural terms when that improves clarity.
- Never force Tamil, English, Hindi, or any other language when the user is clearly
  using another language.
- If the user's input is a transcription of speech, treat it exactly like normal
  user text and respond in the language detected from that text.
- Do not mention language detection unless the user asks.

ANSWER QUALITY:
- Be polite, concise, practical, and easy to understand.
- Prefer step-by-step explanations for procedures.
- Clearly distinguish verified facts from uncertainty.
- For agriculture, consider the user's location, crop, soil, weather, season,
  and symptoms when those details are available.
- Do not invent government schemes, pesticide dosages, prices, weather conditions,
  or other time-sensitive facts.
- Encourage the user to consult a qualified agricultural professional for
  high-risk crop, pesticide, livestock, or health decisions.

TOOLS:
- Use web search only when current or external information is actually needed.
- When web search is used, ground the answer in the returned information and say
  when the available information is uncertain.
- Do not execute shell commands, arbitrary Python, SSH sessions, browser logins,
  or other consequential actions automatically.
"""
    return Assistant(
        name="Farmer Assistant",
        llm=Groq(model=GROQ_MODEL),
        description="A multilingual AI assistant for farmers.",
        # Web search is handled explicitly in search_web() before the LLM call.
        # Keeping DuckDuckGo out of the LLM tool list avoids tool_choice/tool-use conflicts.
        show_tool_calls=False,
        markdown=True,
        add_datetime_to_instructions=True,
        limit_tool_access=True,
        instructions=[instructions],
    )


WEB_TRIGGER_TERMS = (
    "today", "current", "latest", "now", "price", "rate", "market",
    "weather", "forecast", "news", "scheme", "subsidy", "government",
    "mandi", "apmc", "cost", "available", "recent", "2026"
)

def needs_web_search(query: str) -> bool:
    """Use web search for questions where freshness or external sources matter."""
    text = query.lower()
    return any(term in text for term in WEB_TRIGGER_TERMS)

def search_web(query: str) -> str:
    try:
        results = get_search_tool().duckduckgo_search(query, max_results=5)
        return results if results else "No web search results were returned."
    except Exception as exc:
        return f"Web search failed: {exc}"


def load_chats():
    """Load saved conversations and migrate the previous single-history format."""
    Path(CHAT_DB).parent.mkdir(parents=True, exist_ok=True)
    with shelve.open(CHAT_DB, writeback=False) as db:
        chats = db.get("chats")
        if chats is not None:
            return chats

        # Migrate history created by the previous GitHub-ready version.
        legacy_messages = db.get("messages", [])
        if legacy_messages:
            migrated = create_chat()
            migrated["title"] = format_chat_title(
                next(
                    (m["content"] for m in legacy_messages if m.get("role") == "user"),
                    "Previous chat",
                )
            )
            migrated["messages"] = legacy_messages
            migrated["updated_at"] = datetime.now(timezone.utc).isoformat()
            return {migrated["id"]: migrated}

        return {}


def save_chats(chats):
    Path(CHAT_DB).parent.mkdir(parents=True, exist_ok=True)
    with shelve.open(CHAT_DB) as db:
        db["chats"] = chats


def create_chat():
    return {
        "id": str(uuid.uuid4()),
        "title": "New chat",
        "messages": [],
    }


def format_chat_title(prompt: str) -> str:
    """Create a short sidebar title from the user's first message."""
    title = " ".join(prompt.strip().split())
    if len(title) > 38:
        title = title[:38].rstrip() + "…"
    return title or "New chat"


def main():
    if "chats" not in st.session_state:
        st.session_state.chats = load_chats()

    # A fresh page always starts with a new, empty conversation.
    if "current_chat_id" not in st.session_state:
        new_chat = create_chat()
        st.session_state.chats[new_chat["id"]] = new_chat
        st.session_state.current_chat_id = new_chat["id"]

    current_chat = st.session_state.chats[st.session_state.current_chat_id]

    with st.sidebar:
        st.title("🌾 Farmer Assistant")

        if st.button("＋ New chat", use_container_width=True, type="primary"):
            new_chat = create_chat()
            st.session_state.chats[new_chat["id"]] = new_chat
            st.session_state.current_chat_id = new_chat["id"]
            st.rerun()

        st.divider()
        st.subheader("Chats")

        saved_chats = [
            chat for chat in st.session_state.chats.values()
            if chat["messages"]
        ]
        saved_chats.sort(
            key=lambda chat: chat.get("updated_at", ""),
            reverse=True,
        )

        if saved_chats:
            for chat in saved_chats:
                label = f"💬 {chat['title']}"
                if st.button(
                    label,
                    key=f"open_{chat['id']}",
                    use_container_width=True,
                    type="secondary" if chat["id"] != st.session_state.current_chat_id else "primary",
                ):
                    st.session_state.current_chat_id = chat["id"]
                    st.rerun()
        else:
            st.caption("Your previous chats will appear here.")

        st.divider()
        st.caption(f"Model: `{GROQ_MODEL}`")

        if st.button("Delete all chat history", use_container_width=True):
            # Keep the currently visible conversation as a fresh empty chat.
            new_chat = create_chat()
            st.session_state.chats = {new_chat["id"]: new_chat}
            st.session_state.current_chat_id = new_chat["id"]
            save_chats(st.session_state.chats)
            st.rerun()

    st.title("🌾 Farmer Assistant")

    if not current_chat["messages"]:
        st.markdown("### How can I help you today?")
        st.caption("Ask your farming question in English, Tamil, Hindi, or any language you prefer.")

    for message in current_chat["messages"]:
        avatar = "👤" if message["role"] == "user" else "🌾"
        with st.chat_message(message["role"], avatar=avatar):
            st.markdown(message["content"])

    prompt = st.chat_input("Ask your farming question...")

    if not prompt:
        return

    if not current_chat["messages"]:
        current_chat["title"] = format_chat_title(prompt)

    current_chat["messages"].append({"role": "user", "content": prompt})
    current_chat["updated_at"] = datetime.now(timezone.utc).isoformat()
    st.session_state.chats[current_chat["id"]] = current_chat

    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar="🌾"):
        try:
            if needs_web_search(prompt):
                search_results = search_web(prompt)
                context = f"""
Fresh web-search context:
{search_results}

Use this context when relevant. Treat it as potentially time-sensitive external
information, and do not invent facts that are not supported by it.
"""
            else:
                context = """
No web search was used because this question does not appear to require fresh
external information.
"""

            augmented_prompt = f"""
{context}

User question:
{prompt}

Answer the user in the same language as the user's message.
Be concise, practical, and clear. If fresh information is unavailable or uncertain,
say so instead of guessing.
"""
            result = get_assistant().run(augmented_prompt, stream=False)
            response = getattr(result, "content", None) or str(result)
        except Exception as exc:
            response = f"Sorry, I could not complete the request: {exc}"

        st.markdown(response)

    current_chat["messages"].append({"role": "assistant", "content": response})
    current_chat["updated_at"] = datetime.now(timezone.utc).isoformat()
    st.session_state.chats[current_chat["id"]] = current_chat
    save_chats(st.session_state.chats)


if __name__ == "__main__":
    main()
