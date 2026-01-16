FinAgent – Agentic System With Pluggable Agents
===============================================

This project is an agentic trading and analysis system built on:
- FastAPI for HTTP APIs
- LangGraph and LangChain for agent workflows
- OpenAI models for reasoning
- A simple plugin engine so new agents and providers can be “plugged in”

Current version
---------------

- Package name: `finagent`
- Version: `0.0.1` (defined in [pyproject.toml](file:///home/jacob/projects/finagent/pyproject.toml))

Once published to PyPI, you’ll be able to install it with:

```bash
pip install finagent
```

This document explains how other developers can create and plug in their own agents.


Architecture Overview
---------------------

At a high level:
- `src/agents/multimodel_trading/agent.py` hosts the main FastAPI app, LangGraph workflow, and CLI for the trading agent.
- `src/agents/deepquant/agent.py` wraps the DeepQuant backtesting engine as an agent (see [DeepQuant Agent](file:///home/jacob/projects/finagent/src/agents/deepquant/README.md)).
- `src/core/plugin_base.py` defines the core plugin interfaces and registry.
- `src/agents/news_yfinance/agent.py` is a concrete plugin that provides market news via yfinance.
- `src/agents/weather_demo/agent.py` shows a LangChain tool-style agent example.
- `src/api_service.py` is the central FastAPI gateway that auto-discovers agent HTTP APIs.
- `src/agent_eval.py` is a generic CLI harness for invoking agent-specific Typer commands.

The plugin system is intentionally small and composable, so you can:
- Add new providers (e.g. different news sources, data sources, execution backends).
- Switch providers without changing the main engine.
- Extend to new capability types over time.


Core Plugin Concepts
--------------------

All plugin-related types live in [plugin_base.py](file:///home/jacob/projects/finagent/src/core/plugin_base.py).

Key pieces:

- `AgentPlugin`: abstract base for future multi-capability agents.
- `MarketNewsProvider`: a Protocol for “news agents”.
- `PluginRegistry`: singleton registry that tracks providers and exposes lookup methods.

The core definitions:

```python
class AgentPlugin(ABC):
    name: str
    description: str
    capabilities: List[str]

    @abstractmethod
    def invoke(self, capability: str, payload: Dict[str, Any]) -> Any:
        raise NotImplementedError


class MarketNewsProvider(Protocol):
    name: str

    def get_news(self, asset_symbol: str, limit: int = 5) -> List[str]:
        ...


class PluginRegistry:
    def __init__(self) -> None:
        self._news_providers: Dict[str, MarketNewsProvider] = {}

    def register_news_provider(self, provider: MarketNewsProvider) -> None:
        self._news_providers[provider.name] = provider

    def get_news_provider(self, name: Optional[str] = None) -> Optional[MarketNewsProvider]:
        if name is None:
            if not self._news_providers:
                return None
            return next(iter(self._news_providers.values()))
        return self._news_providers.get(name)


plugin_registry = PluginRegistry()
```

You should think of:
- `MarketNewsProvider` as “an agent that knows how to get news”.
- `PluginRegistry` as “the directory of available agents for each capability”.


Example: YFinance News Agent
----------------------------

The file [agent.py](file:///home/jacob/projects/finagent/src/agents/news_yfinance/agent.py) provides a concrete example of a plugin implementing `MarketNewsProvider`.

```python
from typing import List

import yfinance as yf

from .plugin_base import MarketNewsProvider, plugin_registry


class YFinanceNewsAgent:
    name = "yfinance_news"

    def get_news(self, asset_symbol: str, limit: int = 5) -> List[str]:
        ticker = yf.Ticker(asset_symbol)
        news = getattr(ticker, "news", None)
        if not news and hasattr(ticker, "get_news"):
            try:
                news = ticker.get_news()
            except Exception:
                news = None
        if not news:
            return []
        formatted: List[str] = []
        for item in news[:limit]:
            title = item.get("title")
            summary = item.get("summary") or item.get("content") or ""
            publisher = item.get("publisher") or item.get("source") or ""
            if not title:
                continue
            formatted.append(
                f"Title: {title} | Publisher: {publisher} | Summary: {summary}".strip()
            )
        return formatted


plugin_registry.register_news_provider(YFinanceNewsAgent())
```

Important points:
- The agent has a unique `name`.
- It implements `get_news(asset_symbol, limit) -> List[str]`.
- It calls `plugin_registry.register_news_provider(...)` at import time so the engine can discover it.


How the Engine Uses Plugins
---------------------------

The main engine in [agent.py](file:///home/jacob/projects/finagent/src/agents/multimodel_trading/agent.py) uses `FinancialDataFetcher` as the abstraction boundary for external data.

Relevant code (simplified):

```python
from core.plugin_base import plugin_registry


class FinancialDataFetcher:
    def __init__(self, news_provider_name: Optional[str] = None):
        self.news_provider_name = news_provider_name

    def fetch_price_data(self, asset_symbol: str, start: str, end: str):
        ...

    def fetch_news(self, asset_symbol: str) -> List[str]:
        provider = plugin_registry.get_news_provider(self.news_provider_name)
        if provider is None:
            return []
        try:
            return provider.get_news(asset_symbol, limit=5)
        except Exception:
            return []
```

Integration points:
- `build_finagent_graph()` instantiates `FinancialDataFetcher` and passes it into the application graph.
- The FastAPI `/fetch-financial-data` endpoint and the CLI `fetch-financial-data` command both call `fetch_news`, which is now fully plugin-based.

This means:
- To change where news comes from, you do not edit `multimodel_trading.py`.
- You add or modify a plugin and optionally select it by name when creating `FinancialDataFetcher`.


Step-by-step: Creating a New News Agent
---------------------------------------

This is the flow other developers should follow to add a new “news agent” plugin.

1. Create a new module under `src/agents`

   For example:

   - Path: `src/agents/news_myprovider_agent.py`

2. Implement the `MarketNewsProvider` interface

   The minimal shape:

   ```python
   from typing import List

   from .plugin_base import MarketNewsProvider, plugin_registry


   class MyProviderNewsAgent:
       name = "myprovider_news"

       def get_news(self, asset_symbol: str, limit: int = 5) -> List[str]:
           # 1) Call your external API/service here
           items = []  # replace with real fetch

           # 2) Normalize to a list of human-readable strings
           results: List[str] = []
           for item in items[:limit]:
               title = item["title"]
               summary = item.get("summary", "")
               publisher = item.get("publisher", "")
               results.append(
                   f"Title: {title} | Publisher: {publisher} | Summary: {summary}".strip()
               )
           return results
   ```

3. Register the agent with the plugin registry

   At the bottom of the same file:

   ```python
   plugin_registry.register_news_provider(MyProviderNewsAgent())
   ```

   This ensures that importing `news_myprovider_agent` makes the agent available to the engine.

4. Ensure the module is imported somewhere

   Typical options:
- Import it explicitly in `multimodel_trading.py`.
- Or add a small import hub in `src/agents/__init__.py` that imports all agent modules.

   Once the module is imported, your agent is registered and ready.

5. (Optional) Select your agent by name

   By default, `plugin_registry.get_news_provider()` returns the first registered provider.
   If you want to force a specific agent:

   ```python
   from agents.plugin_base import plugin_registry
   from agents import news_myprovider_agent  # noqa: F401 (ensure import)

   fetcher = FinancialDataFetcher(news_provider_name="myprovider_news")
   ```

   You can wire this into:
- `build_finagent_graph()`
- a dedicated CLI command
- a configuration mechanism (env var, config file, etc.)


Extending Beyond News: Other Agent Types
----------------------------------------

The current `MarketNewsProvider` is just one capability. You can extend the same pattern for other types of agents:

- `MarketDataProvider` – agents that fetch price, order book, on-chain data.
- `ExecutionAgent` – agents that talk to paper trading or brokerage APIs.
- `ResearchAgent` – long-form analysis agents that call LLMs and tools.

The pattern is:

1. Define a Protocol in `plugin_base.py`, for example:

   ```python
   class MarketDataProvider(Protocol):
       name: str

       def get_prices(self, asset_symbol: str, start: str, end: str) -> list[dict]:
           ...
   ```

2. Add a corresponding registry section in `PluginRegistry`:

   ```python
   self._data_providers: Dict[str, MarketDataProvider] = {}

   def register_data_provider(self, provider: MarketDataProvider) -> None:
       self._data_providers[provider.name] = provider

   def get_data_provider(self, name: Optional[str] = None) -> Optional[MarketDataProvider]:
       ...
   ```

3. Implement concrete providers in `src/agents/...`.
4. Register them on import, exactly like the news agents.
5. Use the registry from the engine code instead of hard-coding integrations.


Tool-style Agents With LangChain
--------------------------------

The file [agent.py](file:///home/jacob/projects/finagent/src/agents/weather/agent.py) shows another flavor of “agent”:
- Tools are defined with `@tool`.
- A chat model is initialized.
- `create_agent` builds an agent that uses those tools.

This pattern is ideal when:
- You want an LLM-driven agent that decides when to call tools.
- You want a structured response format (e.g., `ResponseFormat` dataclass).

You can combine this with the plugin registry by:
- Implementing tools that internally call plugin-based providers.
- Or wrapping plugin-based providers behind LangChain tools, so the same agent can switch providers without changes to the tool interface.


Summary
-------

- The plugin engine is centered on simple Protocols plus a shared `PluginRegistry`.
- Concrete agents live in `src/agents`, implement a capability-specific Protocol, and register themselves.
- The main engine (FastAPI, LangGraph, CLI) depends only on the registry and capability interfaces, not on concrete implementations.
- Adding a new agent is mainly:
- Creating a module under `src/agents`.
- Implementing the right Protocol.
- Registering with the `PluginRegistry`.
- Ensuring the module is imported.
-
With this pattern, you can grow FinAgent into a richer agentic system where new capabilities can be plugged in with minimal friction.


HTTP Agents and Central API Service
-----------------------------------

HTTP-capable agents expose an `APIRouter` and are discovered at startup by the central API service in [api_service.py](file:///home/jacob/projects/finagent/src/api_service.py).

Agent pattern:

- Each agent lives under `src/agents/<agent_name>/`.
- The main module is `src/agents/<agent_name>/agent.py`.
- It defines:
  - A FastAPI `app` if it wants to run standalone.
  - An `APIRouter` named `router` with its HTTP endpoints.

Example (multimodel trading) in [agent.py](file:///home/jacob/projects/finagent/src/agents/multimodel_trading/agent.py#L25-L27):

- `app` is created with `FastAPI(...)`.
- A router is created and endpoints are attached:
  - `router.get("/fetch-financial-data")(...)`
  - `router.post("/trade/decision")(...)`
- The router is included into the app:
  - `app.include_router(router)`

The central gateway in [api_service.py](file:///home/jacob/projects/finagent/src/api_service.py) will:

- Scan `src/agents` for packages (folders with `__init__.py`).
- Import `agents.<agent_name>.agent`.
- Look for a top-level `router: APIRouter`.
- Mount it under `/api/agents/<agent-slug>/...` where `<agent-slug>` is the folder name with `_` replaced by `-`.

For example:

- Agent package: `multimodel_trading`
- HTTP routes become:
  - `GET  /api/agents/multimodel-trading/fetch-financial-data`
  - `POST /api/agents/multimodel-trading/trade/decision`

To run the central API service:

```bash
make backend
```

or explicitly:

```bash
PYTHONPATH=src uv run uvicorn api_service:app --host 0.0.0.0 --port 8000
```

You can list discovered agents via:

```bash
curl http://127.0.0.1:8000/api/agents
```

and open the browsable docs at:

- `http://127.0.0.1:8000/docs`


CLI-style Agents and agent_eval.py
----------------------------------

Agents can also expose a Typer-based CLI so you can test or script them uniformly via [agent_eval.py](file:///home/jacob/projects/finagent/src/agent_eval.py).

CLI pattern:

- In `src/agents/<agent_name>/agent.py`:
  - Define a top-level `cli` variable of type `typer.Typer`.
  - Add commands on `cli` for agent-specific operations.

Example (multimodel trading) in [agent.py](file:///home/jacob/projects/finagent/src/agents/multimodel_trading/agent.py#L555-L604):

- `cli = typer.Typer()`
- Commands:
  - `run-api` – start the FastAPI backend.
  - `test-retrieval` – exercise the vector retrieval module.
  - `fetch-financial-data` – CLI wrapper around the data fetcher.

The evaluator in [agent_eval.py](file:///home/jacob/projects/finagent/src/agent_eval.py) works as follows:

- It takes `--agent` (or `-a`) specifying the agent package name.
- It imports `agents.<agent_name>.agent`.
- It looks up `cli` and forwards any extra arguments after `--` directly to that Typer app.

Usage pattern:

From the project root, with `PYTHONPATH=src`:

```bash
PYTHONPATH=src uv run src/agent_eval.py --help
```

Run a multimodel trading CLI command via the evaluator:

```bash
PYTHONPATH=src uv run src/agent_eval.py exec --agent multimodel_trading -- --help
PYTHONPATH=src uv run src/agent_eval.py exec --agent multimodel_trading -- test-retrieval
PYTHONPATH=src uv run src/agent_eval.py exec --agent multimodel_trading -- fetch-financial-data --asset-symbol AAPL --start-date 2024-01-01 --end-date 2024-01-10
```

Run the weather agent via the evaluator:

```bash
PYTHONPATH=src uv run src/agent_eval.py exec --agent weather -- --city Sydney
```

Notes:

- `--agent` uses the human-friendly agent name (slug) where dashes are allowed. Dashes are automatically converted to underscores to resolve the Python package, so `--agent weather` maps to `agents.weather.agent`, `--agent agent-game` maps to `agents.agent_game.agent`, and so on.
- Everything after `--` is passed verbatim to the agent’s `cli`.

To add a new CLI-capable agent:

1. Create `src/agents/<agent_name>/agent.py` and ensure there is an `__init__.py` in the folder.
2. Define a `cli = typer.Typer()` instance.
3. Add your commands on `cli` (for example, `@cli.command()` functions).
4. Optionally add a `if __name__ == "__main__": cli()` block if you want to run the agent module directly.
5. Use `agent_eval.py` to invoke the commands uniformly, without caring about the underlying module path.
