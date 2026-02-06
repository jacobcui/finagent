.PHONY: help up down build logs shell-backend shell-frontend init-db

.DEFAULT_GOAL := help

help: ## List available targets
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

up: ## Build and start services in detached mode
	docker-compose up --build -d
	@echo "Services started!"
	@echo "Frontend: http://localhost:8501"
	@echo "Backend:  http://localhost:5000"

down: ## Stop and remove services
	docker-compose down

build: ## Build services without starting
	docker-compose build

logs: ## View output from containers
	docker-compose logs -f

shell-backend: ## Open a shell in the backend container
	docker-compose exec backend /bin/bash

shell-frontend: ## Open a shell in the frontend container
	docker-compose exec frontend /bin/bash

init-db: ## Initialize the database inside the backend container
	docker-compose exec backend python3 -m src.framework.init_db

verify-email: ## Verify a user's email address (Usage: make verify-email email=user@example.com)
	@if [ -z "$(email)" ]; then \
		echo "Error: email argument is required. Usage: make verify-email email=user@example.com"; \
		exit 1; \
	fi
	docker-compose exec backend python3 -m src.framework.verify_user $(email)
