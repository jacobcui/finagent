from __future__ import annotations

from typing import List

import yfinance as yf

from core.plugin_base import MarketNewsProvider, plugin_registry


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
