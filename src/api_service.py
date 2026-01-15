from __future__ import annotations

from importlib import import_module
from pathlib import Path
from typing import Dict

from fastapi import APIRouter, FastAPI


app = FastAPI(title="FinAgent API Service")


def discover_agent_routers() -> Dict[str, APIRouter]:
    base_dir = Path(__file__).parent / "agents"
    routers: Dict[str, APIRouter] = {}
    if not base_dir.exists():
        return routers
    for path in base_dir.iterdir():
        if not path.is_dir():
            continue
        if not (path / "__init__.py").exists():
            continue
        pkg_name = path.name
        module_name = f"agents.{pkg_name}.agent"
        try:
            module = import_module(module_name)
        except Exception:
            continue
        router = getattr(module, "router", None)
        if not isinstance(router, APIRouter):
            continue
        slug = pkg_name.replace("_", "-")
        routers[slug] = router
    return routers


agent_routers = discover_agent_routers()

for slug, router in agent_routers.items():
    app.include_router(router, prefix=f"/api/agents/{slug}")


@app.get("/api/agents")
async def list_agents() -> Dict[str, list[str]]:
    return {"agents": list(agent_routers.keys())}
