import re
from dataclasses import dataclass
from typing import Optional

from .schemas import StrategyConfig


@dataclass
class ParsedPolicy:
    strategy: StrategyConfig
    prompt: str
    name: str


class LangChainPolicyParser:
    """
    Light-weight parser that mimics an LLM powered chain.
    For production, plug a true LangChain/LangGraph chain here.
    """

    DEFAULT_NAME = "Quant Policy"

    def parse(self, prompt: str, name: Optional[str] = None) -> ParsedPolicy:
        text = prompt.lower()
        ticker = self._extract_ticker(prompt)
        start, end = self._extract_dates(prompt)
        short_window, long_window = self._extract_windows(text)
        initial_cash = self._extract_cash(text)

        strategy = StrategyConfig(
            ticker=ticker or "AAPL",
            start_date=start or "2020-01-01",
            end_date=end or "2024-01-01",
            short_window=short_window,
            long_window=long_window,
            initial_cash=initial_cash,
        )
        return ParsedPolicy(
            strategy=strategy, prompt=prompt, name=name or self.DEFAULT_NAME
        )

    def _extract_ticker(self, prompt: str) -> Optional[str]:
        match = re.search(r"\b([A-Z]{1,5})\b", prompt)
        return match.group(1) if match else None

    def _extract_dates(self, prompt: str) -> tuple[Optional[str], Optional[str]]:
        matches = re.findall(r"(20\d{2}-\d{2}-\d{2})", prompt)
        if len(matches) >= 2:
            return matches[0], matches[1]
        return (matches[0], None) if matches else (None, None)

    def _extract_windows(self, text: str) -> tuple[int, int]:
        short = 20
        long = 50
        ma_matches = re.findall(r"sma\s*(\d+)", text) or re.findall(r"ma\s*(\d+)", text)
        if ma_matches:
            short = int(ma_matches[0])
            if len(ma_matches) > 1:
                long = int(ma_matches[1])
            elif short < 50:
                long = max(short * 2, 50)
        return short, long

    def _extract_cash(self, text: str) -> float:
        match = re.search(r"(\d+[.,]?\d*)\s*(usd|cash|dollars)", text)
        return float(match.group(1).replace(",", "")) if match else 10000.0
