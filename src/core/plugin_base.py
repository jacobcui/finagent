from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Protocol


class AgentPlugin(ABC):
    name: str
    description: str
    capabilities: List[str]

    @abstractmethod
    def invoke(self, capability: str, payload: Dict[str, Any]) -> Any:
        raise NotImplementedError


class MarketNewsProvider(Protocol):
    name: str

    def get_news(self, asset_symbol: str, limit: int = 5) -> List[str]: ...


class PluginRegistry:
    def __init__(self) -> None:
        self._news_providers: Dict[str, MarketNewsProvider] = {}

    def register_news_provider(self, provider: MarketNewsProvider) -> None:
        self._news_providers[provider.name] = provider

    def get_news_provider(
        self, name: Optional[str] = None
    ) -> Optional[MarketNewsProvider]:
        if name is None:
            if not self._news_providers:
                return None
            return next(iter(self._news_providers.values()))
        return self._news_providers.get(name)


plugin_registry = PluginRegistry()
