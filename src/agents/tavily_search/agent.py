from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional
from urllib.request import Request, urlopen

import typer
from dotenv import find_dotenv, load_dotenv
from fastapi import APIRouter, HTTPException, Query

DESCRIPTION = "Agent that performs international web search via Tavily."
load_dotenv(find_dotenv(), override=True)


TAVILY_SEARCH_URL = "https://api.tavily.com/search"

router = APIRouter()


cli = typer.Typer()


def _resolve_api_key(explicit: Optional[str]) -> str:
    if explicit:
        return explicit
    value = os.getenv("TAVILI_API_KEY") or os.getenv("TAVILY_API_KEY")
    if not value:
        raise RuntimeError(
            "TAVILI_API_KEY or TAVILY_API_KEY must be set or provided via --api-key."
        )
    return value


def _tavily_search(
    query: str,
    api_key: str,
    topic: Optional[str],
    search_depth: Optional[str],
    language: Optional[str],
    country: Optional[str],
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"query": query}
    if topic:
        payload["topic"] = topic
    if search_depth:
        payload["search_depth"] = search_depth
    if language:
        payload["language"] = language
    if country:
        payload["country"] = country
    data = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    request = Request(TAVILY_SEARCH_URL, data=data, headers=headers, method="POST")
    with urlopen(request, timeout=15) as resp:
        raw = resp.read().decode("utf-8")
    return json.loads(raw)


@router.get("/search")
async def search_http(
    query: str = Query(..., description="Search query text"),
    topic: Optional[str] = Query(
        None,
        description="Topic hint such as general, news, finance, or research",
    ),
    search_depth: Optional[str] = Query(
        None, description="Search depth, e.g. basic or advanced"
    ),
    language: Optional[str] = Query(
        None, description="Two-letter language code, for example en or fr"
    ),
    country: Optional[str] = Query(
        None, description="Two-letter country code, for example us or de"
    ),
    api_key: Optional[str] = Query(
        None,
        description="Override Tavily API key, otherwise env TAVILI_API_KEY "
        "or TAVILY_API_KEY is used",
    ),
) -> Dict[str, Any]:
    try:
        key = _resolve_api_key(api_key)
        return _tavily_search(query, key, topic, search_depth, language, country)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@cli.command()
def search(
    query: str = typer.Argument(..., help="Search query text"),
    topic: Optional[str] = typer.Option(
        None, "--topic", help="Topic hint such as general, news, finance, or research"
    ),
    search_depth: Optional[str] = typer.Option(
        None, "--search-depth", help="Search depth, for example basic or advanced"
    ),
    language: Optional[str] = typer.Option(
        None,
        "--language",
        help="Two-letter language code, for example en or fr",
    ),
    country: Optional[str] = typer.Option(
        None,
        "--country",
        help="Two-letter country code, for example us or de",
    ),
    api_key: Optional[str] = typer.Option(
        None,
        "--api-key",
        help="Override Tavily API key, otherwise env TAVILI_API_KEY "
        "or TAVILY_API_KEY is used",
    ),
) -> None:
    try:
        key = _resolve_api_key(api_key)
        result = _tavily_search(query, key, topic, search_depth, language, country)
    except Exception as exc:
        typer.echo(f"Error calling Tavily: {exc}")
        raise typer.Exit(code=1)
    typer.echo(json.dumps(result, ensure_ascii=False, indent=2))
