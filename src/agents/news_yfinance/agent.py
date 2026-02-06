from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import List
from urllib.parse import quote_plus
from urllib.request import urlopen

import typer
import yfinance as yf

from core.logger import get_logger
from core.plugin_base import plugin_registry

DESCRIPTION = (
    "Market news provider agent based on yfinance with Google News RSS fallback."
)


logger = get_logger(__name__)


class YFinanceNewsAgent:
    name = "yfinance_news"

    def _fetch_google_news(self, query: str, limit: int = 5) -> List[str]:
        url = (
            "https://news.google.com/rss/search?q="
            + quote_plus(query)
            + "&hl=en-US&gl=US&ceid=US:en"
        )
        try:
            with urlopen(url, timeout=5) as resp:
                data = resp.read()
        except Exception:
            return []
        try:
            root = ET.fromstring(data)
        except Exception:
            return []
        items: List[str] = []
        for item in root.findall(".//item")[:limit]:
            title_el = item.find("title")
            source_el = item.find("{http://www.w3.org/2005/Atom}source")
            # Some feeds use 'source' without namespace; try both
            if source_el is None:
                source_el = item.find("source")
            title = (
                title_el.text.strip() if title_el is not None and title_el.text else ""
            )
            source = (
                source_el.text.strip()
                if source_el is not None and source_el.text
                else ""
            )
            if not title:
                continue
            items.append(f"Title: {title} | Publisher: {source}".strip())
        return items

    def get_news(self, asset_symbol: str, limit: int = 5) -> List[str]:
        try:
            ticker = yf.Ticker(asset_symbol)
        except Exception:
            ticker = None
        news = None
        if ticker is not None:
            news = getattr(ticker, "news", None)
            if not news and hasattr(ticker, "get_news"):
                try:
                    news = ticker.get_news()
                except Exception:
                    news = None
        if news:
            formatted: List[str] = []
            for item in news[:limit]:
                title = item.get("title")
                summary = item.get("summary") or item.get("content") or ""
                publisher = item.get("publisher") or item.get("source") or ""
                if not title:
                    continue
                formatted.append(
                    f"Title: {title} | Publisher: {publisher} | "
                    f"Summary: {summary}".strip()
                )
            if formatted:
                return formatted
        logger.info(
            "yfinance returned no news for symbol=%s; falling back to Google News RSS",
            asset_symbol,
        )
        return self._fetch_google_news(asset_symbol, limit=limit)


plugin_registry.register_news_provider(YFinanceNewsAgent())


cli = typer.Typer()


@cli.command()
def fetch(
    asset_symbol: str = typer.Option(
        ..., "--asset-symbol", "-s", help="Asset symbol, e.g. AAPL"
    ),
    limit: int = typer.Option(5, "--limit", "-l", help="Maximum number of news items"),
) -> None:
    agent = YFinanceNewsAgent()
    items = agent.get_news(asset_symbol, limit=limit)
    if not items:
        typer.echo(f"No news found for {asset_symbol}")
        raise typer.Exit(code=0)
    for item in items:
        typer.echo(item)


@cli.callback(invoke_without_command=True)
def main(
    asset_symbol: str = typer.Option(
        None, "--asset-symbol", "-s", help="Asset symbol, e.g. AAPL"
    ),
    limit: int = typer.Option(5, "--limit", "-l", help="Maximum number of news items"),
) -> None:
    if asset_symbol:
        fetch(asset_symbol=asset_symbol, limit=limit)
    else:
        typer.echo("Usage: --asset-symbol SYMBOL [--limit N] or use subcommand 'fetch'")
