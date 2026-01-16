from __future__ import annotations

"""
DeepQuant agent that exposes backtesting APIs and a CLI on top of the
DeepQuant strategy parser, backtester, and policy store.
"""

from typing import List, Optional

import typer
from fastapi import APIRouter, BackgroundTasks

from deepquant_backend.backtest import BacktestRunner
from deepquant_backend.main import backtest_status as dq_backtest_status
from deepquant_backend.main import create_policy as dq_create_policy
from deepquant_backend.main import health as dq_health
from deepquant_backend.main import list_policies as dq_list_policies
from deepquant_backend.main import start_backtest as dq_start_backtest
from deepquant_backend.policy_parser import LangChainPolicyParser
from deepquant_backend.schemas import (
    BacktestRequest,
    BacktestStatus,
    PolicyRequest,
    PolicyResponse,
)

DESCRIPTION = "DeepQuant backtesting agent for strategy prompts and stored policies."


router = APIRouter()


@router.get("/health")
def health() -> dict:
    return dq_health()


@router.post("/policies", response_model=PolicyResponse)
def create_policy(payload: PolicyRequest) -> PolicyResponse:
    return dq_create_policy(payload)


@router.get("/policies")
def list_policies():
    return dq_list_policies()


@router.post("/backtests", response_model=BacktestStatus)
def start_backtest(
    payload: BacktestRequest, background_tasks: BackgroundTasks
) -> BacktestStatus:
    return dq_start_backtest(payload, background_tasks=background_tasks)


@router.get("/backtests/{job_id}", response_model=BacktestStatus)
def get_backtest_status(job_id: str) -> BacktestStatus:
    return dq_backtest_status(job_id)


cli = typer.Typer()


@cli.command()
def backtest(
    prompt: List[str] = typer.Argument(...),
    name: Optional[str] = None,
) -> None:
    prompt_text = " ".join(prompt)
    parser = LangChainPolicyParser()
    parsed = parser.parse(prompt_text, name)
    runner = BacktestRunner()
    result = runner.run(parsed.strategy)
    typer.echo(result.model_dump_json(indent=2))
