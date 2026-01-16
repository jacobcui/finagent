import math
import time
from datetime import datetime
from typing import Callable, Dict, List

import pandas as pd

from .schemas import BacktestResult, EquityPoint, StrategyConfig
from .yfinance_op import YFinanceOp

ProgressCb = Callable[[float, str], None]


class BacktestRunner:
    def __init__(self, progress_cb: ProgressCb | None = None):
        self.progress_cb = progress_cb or (lambda progress, message: None)
        self.data_source = YFinanceOp(progress_cb=self.progress_cb)

    def run(
        self, strategy: StrategyConfig, policy_id: str | None = None
    ) -> BacktestResult:
        self.progress_cb(0.1, "Parsing strategy")
        data = self._load_data(strategy)

        self.progress_cb(0.4, "Calculating indicators")
        data = self._apply_indicators(data, strategy)

        self.progress_cb(0.6, "Simulating trades")
        equity_curve = self._simulate(data, strategy)

        self.progress_cb(0.9, "Calculating summary statistics")
        summary = self._summarize(equity_curve)

        self.progress_cb(1.0, "Completed")
        return BacktestResult(
            policy_id=policy_id,
            summary=summary,
            equity_curve=[
                EquityPoint(date=pt["date"], equity=pt["equity"]) for pt in equity_curve
            ],
        )

    def _load_data(self, strategy: StrategyConfig) -> pd.DataFrame:
        ticker = strategy.ticker
        return self.data_source.fetch(ticker, strategy.start_date, strategy.end_date)

    def _apply_indicators(
        self, data: pd.DataFrame, strategy: StrategyConfig
    ) -> pd.DataFrame:
        data["sma_short"] = data["Close"].rolling(strategy.short_window).mean()
        data["sma_long"] = data["Close"].rolling(strategy.long_window).mean()
        data["signal"] = 0
        data.loc[data["sma_short"] > data["sma_long"], "signal"] = 1
        data.loc[data["sma_short"] < data["sma_long"], "signal"] = -1
        return data.dropna()

    def _simulate(
        self, data: pd.DataFrame, strategy: StrategyConfig
    ) -> List[Dict[str, float]]:
        cash = strategy.initial_cash
        position = 0
        equity_curve: List[Dict[str, float]] = []

        last_signal = 0
        for _, row in data.iterrows():
            close_val = row["Close"]
            if isinstance(close_val, pd.Series):
                close_val = close_val.iloc[0]
            price = float(close_val)
            sig_val = row["signal"]
            if isinstance(sig_val, pd.Series):
                sig_val = sig_val.iloc[0]
            signal = int(sig_val)
            date_val = row["Date"]
            if isinstance(date_val, pd.Series):
                date_val = date_val.iloc[0]
            date_str = (
                date_val.strftime("%Y-%m-%d")
                if isinstance(date_val, datetime)
                else str(date_val)
            )

            if signal != last_signal:
                if signal == 1 and position == 0:
                    position = cash / price
                    cash = 0
                elif signal == -1 and position > 0:
                    cash = position * price
                    position = 0
                last_signal = signal

            equity = cash + position * price
            equity_curve.append({"date": date_str, "equity": equity})

            if len(equity_curve) % 25 == 0:
                pct = 0.6 + 0.3 * (len(equity_curve) / len(data))
                self.progress_cb(min(pct, 0.9), f"Simulating {date_str}")
                time.sleep(0.01)

        if position > 0:
            last_close = data.iloc[-1]["Close"]
            if isinstance(last_close, pd.Series):
                last_close = last_close.iloc[0]
            cash = position * float(last_close)
            position = 0
            equity_curve[-1]["equity"] = cash
        return equity_curve

    def _summarize(self, equity_curve: List[Dict[str, float]]) -> Dict[str, float]:
        if not equity_curve:
            return {
                "total_return_pct": 0.0,
                "cagr_pct": 0.0,
                "max_drawdown_pct": 0.0,
                "sharpe": 0.0,
            }

        start_equity = equity_curve[0]["equity"]
        end_equity = equity_curve[-1]["equity"]
        total_return = (end_equity - start_equity) / start_equity

        values = [pt["equity"] for pt in equity_curve]
        peak = values[0]
        max_dd = 0.0
        for val in values:
            peak = max(peak, val)
            drawdown = (peak - val) / peak
            max_dd = max(max_dd, drawdown)

        daily_returns = self._daily_returns(values)
        sharpe = (
            pd.Series(daily_returns).mean() / (pd.Series(daily_returns).std() + 1e-9)
        ) * math.sqrt(252)

        years = max((len(equity_curve) / 252), 1e-5)
        cagr = (end_equity / start_equity) ** (1 / years) - 1

        return {
            "total_return_pct": round(total_return * 100, 2),
            "cagr_pct": round(cagr * 100, 2),
            "max_drawdown_pct": round(max_dd * 100, 2),
            "sharpe": round(sharpe, 2),
            "start_equity": start_equity,
            "end_equity": end_equity,
        }

    def _daily_returns(self, values: List[float]) -> List[float]:
        returns = []
        for i in range(1, len(values)):
            if values[i - 1] == 0:
                continue
            returns.append((values[i] - values[i - 1]) / values[i - 1])
        return returns
