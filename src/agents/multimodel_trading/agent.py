from __future__ import annotations

"""
Multimodal trading agent that combines market data, vector retrieval, and LLMs
to generate trading decisions and expose them via a FastAPI service and CLI.
"""

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import faiss
import numpy as np
import pandas as pd
import typer
import yfinance as yf
from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI, File, Query, UploadFile
from fastapi.staticfiles import StaticFiles
from langchain_core.output_parsers import XMLOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from pydantic import BaseModel
from uvloop import run as uv_run

from core.plugin_base import plugin_registry

# yfinance uses Yahoo Finance tickers and supports many global exchanges.
# Common examples:
# - US (NYSE / Nasdaq): plain symbols, e.g. AAPL, MSFT, SPY
# - Canada (TSX): ".TO" suffix, e.g. SHOP.TO
# - UK (LSE): ".L" suffix, e.g. VOD.L
# - Australia (ASX): ".AX" suffix, e.g. CBA.AX, BHP.AX; ASX 200 index "^AXJO"
# - Germany (XETRA): ".DE" suffix, e.g. BMW.DE
# - Hong Kong (HKEX): ".HK" suffix, e.g. 0005.HK
# - Japan (TSE): ".T" suffix, e.g. 7203.T
# - Singapore (SGX): ".SI" suffix, e.g. C6L.SI
# Major indices use a "^" prefix, e.g. ^GSPC (S&P 500), ^DJI, ^IXIC.
# For a full list of supported exchanges and suffixes, see:
# https://help.yahoo.com/kb/SLN2310.html


DESCRIPTION = "Multimodal trading agent with vector retrieval, FastAPI, and CLI."


app = FastAPI(
    title="FinAgent - Financial Trading Multimodal Agent (with Vector Retrieval)"
)
load_dotenv()
app.mount("/", StaticFiles(directory="src/frontend", html=True), name="static")
router = APIRouter()

llm_text = ChatOpenAI(model="gpt-4", temperature=0.1)
llm_vision = ChatOpenAI(model="gpt-4-vision-preview", temperature=0.1)
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
EMBEDDING_DIM = 1536


class VectorRetrievalModule:
    def __init__(self):
        self.indexes = {
            "market_intel": self._build_index(),
            "low_level_reflection": self._build_index(),
            "high_level_reflection": self._build_index(),
        }
        self.raw_data = {
            "market_intel": [],
            "low_level_reflection": [],
            "high_level_reflection": [],
        }
        self.retrieval_types = [
            "short_term_impact",
            "medium_long_term_impact",
            "price_increase",
            "price_decrease",
            "bullish_trend",
            "bearish_trend",
            "news_based",
            "technical_indicator_based",
        ]

    def _build_index(self) -> faiss.IndexFlatL2:
        index = faiss.IndexFlatL2(EMBEDDING_DIM)
        return index

    def add_data(self, data_type: str, data: Dict[str, Any]):
        if data_type not in self.indexes:
            raise ValueError(f"Unsupported data type: {data_type}")
        query_text = self._generate_retrieval_query(data_type, data)
        embedding = embeddings.embed_query(query_text)
        self.indexes[data_type].add(np.array([embedding], dtype=np.float32))
        self.raw_data[data_type].append(
            {
                "id": len(self.raw_data[data_type]),
                "query_text": query_text,
                "embedding": embedding,
                "raw_data": data,
                "timestamp": datetime.now().isoformat(),
            }
        )

    def _generate_retrieval_query(self, data_type: str, data: Dict[str, Any]) -> str:
        if data_type == "market_intel":
            impact_period = data.get("impact_period", "LONG-TERM")
            sentiment = data.get("sentiment", "NEUTRAL")
            core_event = data.get("core_event", "")
            return f"[{impact_period}] [{sentiment}] {core_event}"
        elif data_type == "low_level_reflection":
            time_horizon = data.get("time_horizon", "medium_term")
            price_cause = data.get("price_cause", "")
            return f"[{time_horizon}] Price change reason: {price_cause}"
        elif data_type == "high_level_reflection":
            decision_result = data.get("decision_result", "HOLD")
            improvement = data.get("improvement", "")
            return f"[{decision_result}] Improvement suggestion: {improvement}"
        return ""

    def retrieve(
        self, data_type: str, query: Dict[str, str], top_k: int = 5
    ) -> List[Dict[str, Any]]:
        if data_type not in self.indexes:
            return []
        query_embeddings: List[List[float]] = []
        query_types: List[str] = []
        for retrieval_type, query_text in query.items():
            if retrieval_type in self.retrieval_types and query_text.strip():
                embedding = embeddings.embed_query(query_text)
                query_embeddings.append(embedding)
                query_types.append(retrieval_type)
        if not query_embeddings:
            return []
        query_embeddings_arr = np.array(query_embeddings, dtype=np.float32)
        faiss.normalize_L2(query_embeddings_arr)
        distances, indices = self.indexes[data_type].search(query_embeddings_arr, top_k)
        results: List[Dict[str, Any]] = []
        seen_ids = set()
        for i, (dist, idx) in enumerate(zip(distances, indices)):
            for d, id_ in zip(dist, idx):
                if id_ < len(self.raw_data[data_type]) and id_ not in seen_ids:
                    seen_ids.add(id_)
                    result = self.raw_data[data_type][id_].copy()
                    result["retrieval_type"] = query_types[i]
                    result["distance"] = float(d)
                    results.append(result)
        results.sort(key=lambda x: x["distance"])
        return results[:top_k]


class MarketIntelligenceData(BaseModel):
    asset_symbol: str
    core_event: str
    impact_period: str
    sentiment: str
    raw_text: str
    price_data: Optional[Dict[str, float]] = None


class ReflectionData(BaseModel):
    asset_symbol: str
    time_horizon: str
    price_cause: str
    decision_result: Optional[str] = None
    improvement: Optional[str] = None


class MarketData(BaseModel):
    asset_symbol: str
    price_data: Optional[Dict[str, float]] = None
    news_text: Optional[str] = None
    expert_guidance: Optional[str] = None
    kline_image_path: Optional[str] = None


class TradingState(BaseModel):
    market_data: MarketData
    latest_market_intel: Optional[Dict[str, Any]] = None
    low_level_reflection: Optional[Dict[str, Any]] = None
    high_level_reflection: Optional[Dict[str, Any]] = None
    final_decision: Optional[Dict[str, Any]] = None
    memory: Dict[str, Any] = {}


class MarketIntelligenceModule:
    def __init__(self, vector_retriever: VectorRetrievalModule):
        self.vector_retriever = vector_retriever
        self.prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a financial market expert. Analyze multimodal market data and extract key insights.",
                ),
                (
                    "user",
                    """
        Latest market data:
        Asset symbol: {asset_symbol}
        Price data: {price_data}
        News: {news_text}
        Expert guidance: {expert_guidance}

        Please output in the following XML format:
        <output>
            <string name="analysis">Analysis of each news item (ID + impact period + sentiment + core event)</string>
            <string name="summary">Summary of investment insights (including market sentiment)</string>
            <map name="query">
                <string name="short_term_impact">Retrieval keywords for short-term impact</string>
                <string name="medium_long_term_impact">Retrieval keywords for medium/long-term impact</string>
                <string name="bullish_trend">Retrieval keywords for bullish trend</string>
                <string name="bearish_trend">Retrieval keywords for bearish trend</string>
            </map>
            <map name="market_intel_data">
                <string name="core_event">Core event</string>
                <string name="impact_period">Impact period</string>
                <string name="sentiment">Market sentiment</string>
            </map>
        </output>
            """,
                ),
            ]
        )
        self.parser = XMLOutputParser()

    def run(self, state: TradingState) -> Dict[str, Any]:
        md = state.market_data
        inputs = {
            "asset_symbol": md.asset_symbol,
            "price_data": json.dumps(md.price_data) if md.price_data else "None",
            "news_text": md.news_text or "None",
            "expert_guidance": md.expert_guidance or "None",
        }
        chain = self.prompt | llm_text | self.parser
        result = chain.invoke(inputs)
        if md.kline_image_path:
            vision_prompt = ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        "Analyze price trends and technical indicators (MA/BB) from candlestick charts.",
                    ),
                    (
                        "user",
                        [
                            {
                                "type": "text",
                                "text": "Please analyze the short/medium/long-term trends in this candlestick chart.",
                            },
                            {
                                "type": "image_url",
                                "image_url": {"url": f"file://{md.kline_image_path}"},
                            },
                        ],
                    ),
                ]
            )
            vision_result = vision_prompt | llm_vision
            result["kline_analysis"] = vision_result.invoke({}).content
        market_intel_data = result.get("market_intel_data", {})
        self.vector_retriever.add_data(
            "market_intel",
            {
                "asset_symbol": md.asset_symbol,
                "core_event": market_intel_data.get("core_event", ""),
                "impact_period": market_intel_data.get("impact_period", "LONG-TERM"),
                "sentiment": market_intel_data.get("sentiment", "NEUTRAL"),
                "raw_text": md.news_text or "",
            },
        )
        retrieval_query = result.get("query", {})
        past_market_intel = self.vector_retriever.retrieve(
            data_type="market_intel", query=retrieval_query, top_k=3
        )
        result["past_market_intel"] = past_market_intel
        return {"latest_market_intel": result}


class ReflectionModule:
    def __init__(self, vector_retriever: VectorRetrievalModule):
        self.vector_retriever = vector_retriever
        self.low_level_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "Analyze the relationship between market intelligence and price changes.",
                ),
                (
                    "user",
                    """
            Market intelligence summary: {market_intel_summary}
            Candlestick chart analysis: {kline_analysis}
            Price changes: {price_changes}

            Please output in the following XML format:
            <output>
                <map name="reasoning">
                    <string name="short_term_reasoning">Short-term price change reason</string>
                    <string name="medium_term_reasoning">Medium-term price change reason</string>
                    <string name="long_term_reasoning">Long-term price change reason</string>
                </map>
                <map name="query">
                    <string name="price_increase">Retrieval keywords for price increase</string>
                    <string name="price_decrease">Retrieval keywords for price decrease</string>
                    <string name="technical_indicator_based">Retrieval keywords for technical indicators</string>
                </map>
                <map name="reflection_data">
                    <string name="time_horizon">Primary analysis time horizon</string>
                    <string name="price_cause">Core price change reason</string>
                </map>
            </output>
            """,
                ),
            ]
        )
        self.high_level_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "Reflect on the correctness of historical trading decisions and optimize them.",
                ),
                (
                    "user",
                    """
            Historical trading records: {trading_history}
            Market trend analysis: {market_trend}
            Previous decision results: {previous_decisions}

            Please output in the following XML format:
            <output>
                <string name="reasoning">Analysis of decision correctness</string>
                <string name="improvement">Optimization suggestions</string>
                <string name="summary">Summary of experience</string>
                <map name="query">
                    <string name="bullish_trend">Retrieval keywords for bullish decisions</string>
                    <string name="bearish_trend">Retrieval keywords for bearish decisions</string>
                    <string name="news_based">Retrieval keywords for news-driven decisions</string>
                </map>
                <map name="reflection_data">
                    <string name="decision_result">Current decision result</string>
                    <string name="improvement">Core improvement suggestion</string>
                </map>
            </output>
            """,
                ),
            ]
        )
        self.parser = XMLOutputParser()

    def low_level_reflect(self, state: TradingState) -> Dict[str, Any]:
        mi = state.latest_market_intel
        inputs = {
            "market_intel_summary": mi["summary"],
            "kline_analysis": mi.get("kline_analysis", "None"),
            "price_changes": (
                json.dumps(state.market_data.price_data)
                if state.market_data.price_data
                else "None"
            ),
        }
        chain = self.low_level_prompt | llm_text | self.parser
        result = chain.invoke(inputs)
        reflection_data = result.get("reflection_data", {})
        self.vector_retriever.add_data(
            "low_level_reflection",
            {
                "asset_symbol": state.market_data.asset_symbol,
                "time_horizon": reflection_data.get("time_horizon", "medium_term"),
                "price_cause": reflection_data.get("price_cause", ""),
            },
        )
        retrieval_query = result.get("query", {})
        past_reflections = self.vector_retriever.retrieve(
            data_type="low_level_reflection",
            query=retrieval_query,
            top_k=2,
        )
        result["past_reflections"] = past_reflections
        return {"low_level_reflection": result}

    def high_level_reflect(self, state: TradingState) -> Dict[str, Any]:
        trading_history = (
            state.memory.get("trading_history", [])[-10:] if state.memory else []
        )
        inputs = {
            "trading_history": json.dumps(trading_history),
            "market_trend": state.low_level_reflection["reasoning"][
                "medium_term_reasoning"
            ],
            "previous_decisions": (
                json.dumps(state.final_decision) if state.final_decision else "None"
            ),
        }
        chain = self.high_level_prompt | llm_text | self.parser
        result = chain.invoke(inputs)
        reflection_data = result.get("reflection_data", {})
        self.vector_retriever.add_data(
            "high_level_reflection",
            {
                "asset_symbol": state.market_data.asset_symbol,
                "decision_result": reflection_data.get("decision_result", "HOLD"),
                "improvement": reflection_data.get("improvement", ""),
            },
        )
        retrieval_query = result.get("query", {})
        past_reflections = self.vector_retriever.retrieve(
            data_type="high_level_reflection",
            query=retrieval_query,
            top_k=2,
        )
        result["past_reflections"] = past_reflections
        return {"high_level_reflection": result}


class ToolAugmentedDecisionModule:
    def __init__(self):
        self.prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a trading decision assistant. Use market analysis and reflections to choose an action.",
                ),
                (
                    "user",
                    """
            Market analysis summary: {market_summary}
            Low-level reasoning: {low_level_reasoning}
            High-level summary: {high_level_summary}

            Please output in the following XML format:
            <output>
                <string name="action">Decision action: BUY, SELL, or HOLD</string>
                <string name="reasoning">Short explanation of the decision</string>
            </output>
            """,
                ),
            ]
        )
        self.parser = XMLOutputParser()

    def run(self, state: TradingState) -> Dict[str, Any]:
        latest = state.latest_market_intel or {}
        low = state.low_level_reflection or {}
        high = state.high_level_reflection or {}
        market_summary = latest.get("summary", "")
        low_reasoning = ""
        reasoning_map = low.get("reasoning")
        if isinstance(reasoning_map, Dict):
            low_reasoning = (
                reasoning_map.get("medium_term_reasoning")
                or reasoning_map.get("short_term_reasoning")
                or reasoning_map.get("long_term_reasoning")
                or ""
            )
        high_summary = high.get("summary", "")
        inputs = {
            "market_summary": market_summary,
            "low_level_reasoning": low_reasoning,
            "high_level_summary": high_summary,
        }
        chain = self.prompt | llm_text | self.parser
        result = chain.invoke(inputs)
        action = result.get("action", "HOLD")
        reasoning = result.get("reasoning", "")
        state.final_decision = {"action": action, "reasoning": reasoning}
        return {"final_decision": state.final_decision}


class FinancialDataFetcher:
    def __init__(self, news_provider_name: Optional[str] = None):
        self.news_provider_name = news_provider_name

    def fetch_price_data(
        self, asset_symbol: str, start_date: str, end_date: str
    ) -> Optional[pd.DataFrame]:
        try:
            if asset_symbol.upper() == "ETHUSD":
                asset_symbol = "ETH-USD"
            data = yf.download(asset_symbol, start=start_date, end=end_date)
            if data.empty:
                return None
            if isinstance(data.columns, pd.MultiIndex):
                data = data.xs(asset_symbol, axis=1, level=1)
            available_cols = [
                c
                for c in ["Open", "High", "Low", "Close", "Adj Close"]
                if c in data.columns
            ]
            if not available_cols:
                return None
            data = data[available_cols]
            rename_map = {
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Adj Close": "adj_close",
            }
            data.columns = [rename_map[c] for c in available_cols]
            data = data.reset_index()
            idx_name = data.columns[0]
            data["date"] = data[idx_name].astype(str)
            return data.to_dict("records")
        except Exception as e:
            print(f"Failed to fetch price data: {e}")
            return None

    def fetch_news(self, asset_symbol: str) -> List[str]:
        provider = plugin_registry.get_news_provider(self.news_provider_name)
        if provider is None:
            return []
        try:
            return provider.get_news(asset_symbol, limit=5)
        except Exception:
            return []


def build_finagent_graph():
    vector_retriever = VectorRetrievalModule()
    data_fetcher = FinancialDataFetcher()
    market_intel_node = MarketIntelligenceModule(vector_retriever).run
    low_reflect_node = ReflectionModule(vector_retriever).low_level_reflect
    high_reflect_node = ReflectionModule(vector_retriever).high_level_reflect
    decision_node = ToolAugmentedDecisionModule().run
    graph = StateGraph(TradingState)
    graph.add_node("market_intelligence", market_intel_node)
    graph.add_node("low_level_reflection", low_reflect_node)
    graph.add_node("high_level_reflection", high_reflect_node)
    graph.add_node("decision_making", decision_node)
    graph.set_entry_point("market_intelligence")
    graph.add_edge("market_intelligence", "low_level_reflection")
    graph.add_edge("low_level_reflection", "high_level_reflection")
    graph.add_edge("high_level_reflection", "decision_making")
    graph.add_edge("decision_making", END)
    memory = MemorySaver()
    return graph.compile(checkpointer=memory), data_fetcher


finagent_graph: Optional[Any] = None
data_fetcher: Optional[FinancialDataFetcher] = None


@router.get("/fetch-financial-data", response_model=Dict[str, Any])
async def fetch_financial_data(
    asset_symbol: str = Query(..., description="Asset symbol (e.g., AAPL, ETHUSD)"),
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
):
    global data_fetcher
    if data_fetcher is None:
        _, data_fetcher = build_finagent_graph()
    price_data = data_fetcher.fetch_price_data(asset_symbol, start_date, end_date)
    news = data_fetcher.fetch_news(asset_symbol)
    return {
        "asset_symbol": asset_symbol,
        "price_data": price_data,
        "latest_news": news,
        "fetch_time": datetime.now().isoformat(),
    }


@router.post("/trade/decision", response_model=Dict[str, Any])
async def get_trading_decision(
    asset_symbol: str,
    news_text: Optional[str] = None,
    expert_guidance: Optional[str] = None,
    price_data: Optional[str] = None,
    kline_image: Optional[UploadFile] = File(None),
    use_real_data: bool = Query(
        False, description="Whether to use real financial data"
    ),
):
    global finagent_graph, data_fetcher
    if finagent_graph is None or data_fetcher is None:
        finagent_graph, data_fetcher = build_finagent_graph()
    if use_real_data:
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - pd.Timedelta(days=7)).strftime("%Y-%m-%d")
        real_data = await fetch_financial_data(asset_symbol, start_date, end_date)
        price_dict = real_data["price_data"][-1] if real_data["price_data"] else None
        news_text = (
            "\n".join(real_data["latest_news"])
            if real_data["latest_news"]
            else news_text
        )
    else:
        price_dict = json.loads(price_data) if price_data else None
    kline_path = None
    if kline_image:
        kline_path = f"temp_{asset_symbol}_kline.png"
        with open(kline_path, "wb") as f:
            f.write(await kline_image.read())
    market_data = MarketData(
        asset_symbol=asset_symbol,
        price_data=price_dict,
        news_text=news_text,
        expert_guidance=expert_guidance,
        kline_image_path=kline_path,
    )
    initial_state = TradingState(
        market_data=market_data,
        memory={"trading_history": []},
    )
    result = finagent_graph.invoke(
        initial_state, config={"configurable": {"thread_id": "finagent-001"}}
    )
    if kline_path and os.path.exists(kline_path):
        os.remove(kline_path)
    return {
        "asset_symbol": asset_symbol,
        "decision": result["final_decision"]["action"],
        "reasoning": result["final_decision"]["reasoning"],
        "market_analysis": result["latest_market_intel"]["summary"],
        "retrieved_historical_data": len(
            result["latest_market_intel"].get("past_market_intel", [])
        )
        > 0,
    }


app.include_router(router)


cli = typer.Typer()


@cli.command()
def run_api(host: str = "0.0.0.0", port: int = 8000):
    import uvicorn

    uv_run(uvicorn.run(app, host=host, port=port))


@cli.command()
def test_retrieval(asset_symbol: str = "AAPL"):
    vector_retriever = VectorRetrievalModule()
    vector_retriever.add_data(
        "market_intel",
        {
            "asset_symbol": asset_symbol,
            "core_event": "Launch of new AR/VR product",
            "impact_period": "MEDIUM-TERM",
            "sentiment": "POSITIVE",
        },
    )
    results = vector_retriever.retrieve(
        data_type="market_intel",
        query={
            "medium_long_term_impact": "Medium/long-term impact of AR/VR product",
            "bullish_trend": "Bullish trend",
        },
        top_k=1,
    )
    typer.echo(
        f"Retrieval results: {json.dumps(results, ensure_ascii=False, indent=2)}"
    )


@cli.command(name="fetch-financial-data")
def fetch_financial_data_cli(
    asset_symbol: str = typer.Option(
        ..., "--asset-symbol", help="Asset symbol, e.g. AAPL or ETHUSD"
    ),
    start_date: str = typer.Option(..., "--start-date", help="Start date (YYYY-MM-DD)"),
    end_date: str = typer.Option(..., "--end-date", help="End date (YYYY-MM-DD)"),
):
    fetcher = FinancialDataFetcher()
    price_data = fetcher.fetch_price_data(asset_symbol, start_date, end_date)
    news = fetcher.fetch_news(asset_symbol)
    output = {
        "asset_symbol": asset_symbol,
        "start_date": start_date,
        "end_date": end_date,
        "price_data": price_data,
        "latest_news": news,
    }
    typer.echo(json.dumps(output, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    cli()
