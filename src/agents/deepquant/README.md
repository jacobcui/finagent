DeepQuant Agent
===============

Overview
--------

The DeepQuant agent exposes a simple SMA-crossover backtesting engine as a
FinAgent-compatible agent. It lets you:

- Turn natural-language strategy prompts into structured configs.
- Run historical backtests using yfinance price data.
- Store and reuse parsed policies via a TinyDB-backed store.

Location
--------

- Package: `agents.deepquant`
- Agent module: `src/agents/deepquant/agent.py`
- Backend logic: `src/deepquant_backend/`

HTTP API
--------

When the FinAgent API service is running, the DeepQuant agent is available
under the `/api/agents/deepquant` prefix:

- `GET  /api/agents/deepquant/health`
- `POST /api/agents/deepquant/policies`
- `GET  /api/agents/deepquant/policies`
- `POST /api/agents/deepquant/backtests`
- `GET  /api/agents/deepquant/backtests/{job_id}`

CLI Usage
---------

You can run backtests via the shared `agent_eval.py` harness:

```bash
make exec AGENT=deepquant ARGS="Backtest AAPL from 2020-01-01 to 2020-12-31 with 10000 usd and sma 20 and sma 50"
```

This:

- Parses the prompt into `StrategyConfig`.
- Downloads price data via yfinance (with a safe fallback).
- Runs the SMA strategy and prints JSON summary and equity curve.

