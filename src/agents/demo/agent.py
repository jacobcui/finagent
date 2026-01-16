from __future__ import annotations

import typer
from langchain.tools import tool

from core.logger import get_logger

DESCRIPTION = "Demo agent showing how to create a new agent."


logger = get_logger(__name__)


def _format_message(text: str) -> str:
    return f"[demo] {text}"


@tool
def demo_echo(text: str) -> str:
    """Echo back text with a demo prefix."""
    logger.info("demo_echo called with text=%s", text)
    return _format_message(text)


cli = typer.Typer()


@cli.command()
def echo(
    text: str = typer.Argument(..., help="Text to echo via the demo agent")
) -> None:
    result = _format_message(text)
    typer.echo(result)


TOOLS = [demo_echo]
