from __future__ import annotations

from typing import Dict, List

from fastapi import FastAPI

from core.agent_discovery import AgentInfo, discover_agents

app = FastAPI(title="FinAgent API Service")


agent_infos: Dict[str, AgentInfo] = discover_agents()

for slug, info in agent_infos.items():
    if info.router is not None:
        app.include_router(info.router, prefix=f"/api/agents/{slug}")


@app.get("/api/agents")
async def list_agents() -> Dict[str, List[str]]:
    """"""
    return {"agents": list(agent_infos.keys())}
