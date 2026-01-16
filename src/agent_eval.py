from __future__ import annotations

import argparse
import importlib
import sys
from typing import List

from core.agent_discovery import slug_to_package


def main() -> None:
    argv = sys.argv[1:]
    if argv and argv[0] == "exec":
        argv = argv[1:]
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--agent",
        "-a",
        required=True,
        help="Agent package name, e.g. multimodel_trading",
    )
    parser.add_argument("args", nargs=argparse.REMAINDER)
    ns = parser.parse_args(argv)
    pkg_name = slug_to_package(ns.agent)
    if pkg_name == "chat":
        module_name = "core.chat"
    else:
        module_name = f"agents.{pkg_name}.agent"
    module = importlib.import_module(module_name)
    cli = getattr(module, "cli", None)
    if cli is None:
        raise SystemExit(f"Agent '{ns.agent}' does not define a 'cli' Typer app")
    cli_args: List[str] = list(ns.args or [])
    if cli_args and cli_args[0] == "--":
        cli_args = cli_args[1:]
    cli(args=cli_args)


if __name__ == "__main__":
    main()
