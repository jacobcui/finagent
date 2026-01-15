PY := uv run
FRONTEND_DIR := src/frontend

.PHONY: help install install-backend install-frontend backend frontend dev fetch-data build

help:
	@echo "Available targets:"
	@echo "  install          Install Python and frontend dependencies"
	@echo "  install-backend  Install Python dependencies via uv"
	@echo "  install-frontend Install frontend dependencies via npm"
	@echo "  backend          Run FastAPI backend (port 8000)"
	@echo "  frontend         Run Vite frontend dev server"
	@echo "  dev              Run backend and frontend (two processes)"
	@echo "  fetch-data       Example: fetch financial data for AAPL"
	@echo "  build            Build Python package (sdist and wheel in dist/)"

install: install-backend install-frontend

install-backend:
	uv sync

install-frontend:
	cd $(FRONTEND_DIR) && npm install

backend:
	PYTHONPATH=src $(PY) uvicorn api_service:app --host 0.0.0.0 --port 8000

frontend:
	cd $(FRONTEND_DIR) && npm start

dev:
	PYTHONPATH=src $(PY) uvicorn api_service:app --host 0.0.0.0 --port 8000 &
	cd $(FRONTEND_DIR) && npm start

fetch-data:
	$(PY) src/agents/multimodel_trading/agent.py fetch-financial-data --asset-symbol AAPL --start-date 2024-01-01 --end-date 2024-01-10

build:
	uv build
