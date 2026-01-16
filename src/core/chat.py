from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import typer
from dotenv import find_dotenv, load_dotenv
from langchain.agents.structured_output import ToolStrategy
from langchain.chat_models import init_chat_model
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver

from core.agent_discovery import agents_summary
from core.agent_tools import create_agent_with_tools
from core.context import Context
from core.session import load_session, save_session

try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.history import InMemoryHistory
except Exception:
    PromptSession = None
    InMemoryHistory = None

load_dotenv(find_dotenv(), override=True)


DESCRIPTION = (
    "Interactive chat utility with session persistence and awareness of other agents."
)


@dataclass
class ChatResponse:
    reply: str


model = init_chat_model("gpt-4.1", temperature=0.5, timeout=10, max_tokens=1000)
checkpointer = InMemorySaver()

CHAT_SYSTEM_PROMPT = (
    "You are a helpful assistant. You can answer general questions, and you also have tools "
    "exposed by other agents in the system."
)


chat_agent = create_agent_with_tools(
    model=model,
    system_prompt=CHAT_SYSTEM_PROMPT,
    context_schema=Context,
    response_format=ToolStrategy(ChatResponse),
    checkpointer=checkpointer,
    excluding_agents=["chat"],
)


def build_prompt(
    messages: List[Dict[str, Any]], system_context: Optional[str]
) -> List[Dict[str, Any]]:
    result: List[Dict[str, Any]] = []
    if system_context:
        result.append({"role": "system", "content": system_context})
    result.extend(messages)
    return result


def interactive_chat(session_id: Optional[str]) -> None:
    system_context = agents_summary()
    try:
        sid, messages = load_session(session_id)
    except Exception as exc:
        typer.echo(f"Failed to load session: {exc}")
        raise typer.Exit(code=1)
    typer.echo(f"Chat session id: {sid}")
    typer.echo("Type your messages and press Enter. Type 'exit' or 'quit' to end.")
    config: RunnableConfig = {"configurable": {"thread_id": sid}}
    session: Optional["PromptSession[str]"] = None
    if PromptSession is not None and InMemoryHistory is not None:
        history = InMemoryHistory()
        for msg in messages:
            if msg.get("role") == "user":
                text = msg.get("content")
                if isinstance(text, str) and text.strip():
                    history.append_string(text)
        session = PromptSession(history=history)
    while True:
        try:
            if session is not None:
                user_input = session.prompt("You: ").strip()
            else:
                user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            typer.echo("\nSession ended.")
            break
        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit"}:
            typer.echo("Session saved. Goodbye.")
            break
        messages.append({"role": "user", "content": user_input})
        try:
            response = chat_agent.invoke(
                {"messages": build_prompt(messages, system_context)},
                config=config,
                context=Context(user_id="1", session_id=sid),
            )
        except Exception as exc:
            typer.echo(f"Error calling OpenAI: {exc}")
            typer.echo("Check that OPENAI_API_KEY is set and valid.")
            break
        structured = response.get("structured_response")
        if structured is not None:
            reply_text = getattr(structured, "reply", str(structured))
        else:
            reply_text = str(response)
        typer.echo(f"Assistant: {reply_text}")
        messages.append({"role": "assistant", "content": reply_text})
        save_session(sid, messages)


cli = typer.Typer()


@cli.callback(invoke_without_command=True)
def main(
    session_id: Optional[str] = typer.Option(
        None,
        "--session-id",
        help="Existing session id to resume",
    )
) -> None:
    interactive_chat(session_id)
