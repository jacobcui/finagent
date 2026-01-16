from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import APIRouter


@dataclass
class AgentInfo:
    slug: str
    package: str
    module: str
    router: Optional[APIRouter]
    has_cli: bool
    description: Optional[str]


def package_to_slug(name: str) -> str:
    return name.replace("_", "-")


def slug_to_package(name: str) -> str:
    return name.replace("-", "_")


def _base_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "agents"


def discover_agents() -> Dict[str, AgentInfo]:
    base_dir = _base_dir()
    agents: Dict[str, AgentInfo] = {}
    if not base_dir.exists():
        return agents
    for path in base_dir.iterdir():
        if not path.is_dir():
            continue
        if not (path / "__init__.py").exists():
            continue
        pkg_name = path.name
        slug = package_to_slug(pkg_name)
        module_name = f"agents.{pkg_name}.agent"
        try:
            module = import_module(module_name)
        except Exception:
            continue
        router = getattr(module, "router", None)
        if not isinstance(router, APIRouter):
            router = None
        cli = getattr(module, "cli", None)
        description = getattr(module, "DESCRIPTION", None)
        if not isinstance(description, str):
            description = None
        agents[slug] = AgentInfo(
            slug=slug,
            package=pkg_name,
            module=module_name,
            router=router,
            has_cli=cli is not None,
            description=description,
        )
    return agents


def agents_summary() -> str:
    agents = discover_agents()
    if not agents:
        return "No other agents are currently registered."
    lines: List[str] = []
    for slug, info in sorted(agents.items(), key=lambda item: item[0]):
        if slug == "chat":
            continue
        text = slug
        if info.description:
            text = f"{slug}: {info.description}"
        lines.append(f"- {text}")
    if not lines:
        return "No other agents are currently registered."
    header = "Other available agents in the FinAgent system:\n"
    return header + "\n".join(lines)
