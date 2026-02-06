"""
Agent for checking presence of model API tokens in environment variables and verifying
their validity by making a test call.

Usage:
    make exec AGENT=model-verify ARGS="\
      verify \
      --key-name DASHSCOPE_API_KEY \
      --model qwen-plus \
      --base-url https://dashscope.aliyuncs.com/compatible-mode/v1 \
    "
"""

from __future__ import annotations

import os
from typing import Optional

import typer
from dotenv import find_dotenv, load_dotenv
from fastapi import APIRouter
from openai import OpenAI

DESCRIPTION = "Agent for verifying model connectivity given an API token and endpoint."
load_dotenv(find_dotenv(), override=True)


router = APIRouter()


cli = typer.Typer()


def _run_verification(
    key_name: str, model: str, base_url: Optional[str] = None
) -> None:
    value = os.getenv(key_name)
    if not value:
        typer.echo(f"Key '{key_name}' is not set in environment for model '{model}'.")
        raise typer.Exit(code=1)
    length = len(value)
    typer.echo(
        f"Key '{key_name}' is set in environment for model '{model}' "
        f"(length {length} characters)."
    )
    try:
        if base_url is not None:
            client = OpenAI(api_key=value, base_url=base_url)
        else:
            client = OpenAI(api_key=value)
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Who are you?"}],
            max_tokens=50,
        )
        choice = response.choices[0]
        content = getattr(choice.message, "content", "")
        text = str(content).strip()
        typer.echo(f"Model responded: {text}")
    except Exception as exc:
        typer.echo(f"Failed to verify token and model: {exc}")
        raise typer.Exit(code=1)


@cli.callback(invoke_without_command=True)
def main(
    key_name: Optional[str] = typer.Option(
        None,
        "--key-name",
        "-k",
        help="Environment variable name that holds the API token",
    ),
    model: Optional[str] = typer.Option(
        None,
        "--model",
        "-m",
        help="Model name associated with this token",
    ),
    base_url: Optional[str] = typer.Option(
        None,
        "--base-url",
        help="Base URL for the OpenAI-compatible API endpoint",
    ),
) -> None:
    if key_name is None and model is None:
        return
    if key_name is None or model is None:
        typer.echo("Both --key-name and --model must be provided.")
        raise typer.Exit(code=1)
    _run_verification(key_name, model, base_url)


@cli.command()
def verify(
    key_name: str = typer.Option(
        ...,
        "--key-name",
        "-k",
        help="Environment variable name that holds the API token",
    ),
    model: str = typer.Option(
        ...,
        "--model",
        "-m",
        help="Model name associated with this token",
    ),
    base_url: Optional[str] = typer.Option(
        None,
        "--base-url",
        help="Base URL for the OpenAI-compatible API endpoint",
    ),
) -> None:
    _run_verification(key_name, model, base_url)
