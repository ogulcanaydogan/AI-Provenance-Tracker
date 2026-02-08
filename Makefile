.PHONY: help install dev test lint format typecheck run docker-up docker-down clean

help:
	@echo "AI Provenance Tracker - Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install     Install production dependencies"
	@echo "  make dev         Install development dependencies"
	@echo ""
	@echo "Development:"
	@echo "  make run         Run the API server locally"
	@echo "  make test        Run tests"
	@echo "  make lint        Run linter"
	@echo "  make format      Format code"
	@echo "  make typecheck   Run type checker"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-up   Start all services with Docker"
	@echo "  make docker-down Stop all Docker services"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean       Remove build artifacts"

install:
	cd backend && pip install -e .

dev:
	cd backend && pip install -e ".[dev]"

run:
	cd backend && uvicorn app.main:app --reload --port 8000

test:
	cd backend && pytest tests/ -v

lint:
	cd backend && ruff check .

format:
	cd backend && ruff format .

typecheck:
	cd backend && mypy app/

docker-up:
	docker-compose up --build -d

docker-down:
	docker-compose down

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
