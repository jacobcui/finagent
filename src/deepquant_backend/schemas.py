from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class StrategyConfig(BaseModel):
    ticker: str = Field(..., description="Primary ticker symbol to test")
    start_date: str = Field(..., description="Backtest start date YYYY-MM-DD")
    end_date: str = Field(..., description="Backtest end date YYYY-MM-DD")
    short_window: int = Field(20, description="Short moving average window")
    long_window: int = Field(50, description="Long moving average window")
    initial_cash: float = Field(10000.0, description="Starting cash for the strategy")


class Policy(BaseModel):
    id: str
    prompt: str
    name: str
    strategy: StrategyConfig


class PolicyRequest(BaseModel):
    prompt: str
    name: Optional[str] = None


class PolicyResponse(BaseModel):
    policy_id: str
    strategy: StrategyConfig


class BacktestRequest(BaseModel):
    prompt: Optional[str] = Field(None, description="Policy text to parse and backtest")
    policy_id: Optional[str] = Field(None, description="Existing stored policy id")
    name: Optional[str] = None


class EquityPoint(BaseModel):
    date: str
    equity: float


class BacktestResult(BaseModel):
    policy_id: Optional[str] = None
    summary: Dict[str, Any]
    equity_curve: List[EquityPoint]


class BacktestStatus(BaseModel):
    job_id: str
    status: str
    progress: float
    message: Optional[str] = None
    result: Optional[BacktestResult] = None
