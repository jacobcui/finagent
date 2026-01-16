from __future__ import annotations

from importlib import import_module
from typing import Any, List, Optional

from langchain.agents import create_agent

from core.agent_discovery import discover_agents


def gather_tools(excluding_agents: Optional[List[str]] = None) -> List[Any]:
    excluding = set(excluding_agents or [])
    tools: List[Any] = []
    agents = discover_agents()
    for slug, info in agents.items():
        if slug in excluding:
            continue
        try:
            module = import_module(info.module)
        except Exception:
            continue
        module_tools = getattr(module, "TOOLS", None)
        if isinstance(module_tools, list) and module_tools:
            tools.extend(module_tools)
    return tools


def create_agent_with_tools(
    model: Any,
    system_prompt: str,
    context_schema: Any,
    response_format: Any,
    checkpointer: Any,
    excluding_agents: Optional[List[str]] = None,
):
    tools = gather_tools(excluding_agents=excluding_agents)
    return create_agent(
        model=model,
        system_prompt=system_prompt,
        tools=tools,
        context_schema=context_schema,
        response_format=response_format,
        checkpointer=checkpointer,
    )
