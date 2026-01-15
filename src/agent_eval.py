from __future__ import annotations

import importlib
import sys
from typing import List, Optional

import typer


def exec_command(
    agent: str = typer.Option(..., "--agent", "-a", help="Agent package name, e.g. multimodel_trading"),
    args: Optional[List[str]] = typer.Argument(None),
) -> None:
    pkg_name = agent.replace("-", "_")
    module_name = f"agents.{pkg_name}.agent"
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError:
        typer.echo(f"Agent module '{module_name}' not found", err=True)
        raise typer.Exit(code=1)
    cli = getattr(module, "cli", None)
    if cli is None:
        typer.echo(f"Agent '{agent}' does not define a 'cli' Typer app", err=True)
        raise typer.Exit(code=1)
    cli_args = list(args or [])
    cli(args=cli_args)


if __name__ == "__main__":
    argv = sys.argv[1:]
    if argv and argv[0] == "exec":
        sys.argv = [sys.argv[0]] + argv[1:]
    typer.run(exec_command)
