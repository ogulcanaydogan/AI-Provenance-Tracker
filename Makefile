.PHONY: help install dev test lint format typecheck run docker-up docker-down clean intel-report intel-benchmark intel-evidence intel-pipeline intel-weekly-cycle smoke-prod benchmark-public build-text-dataset

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
	@echo ""
	@echo "Intel / Evidence:"
	@echo "  make intel-report    Build trust report from INPUT JSON"
	@echo "  make intel-benchmark Benchmark report with optional LABELS"
	@echo "  make intel-evidence  Build talent visa evidence pack"
	@echo "  make intel-pipeline  Run collect->report->benchmark->pack"
	@echo "  make intel-weekly-cycle  Run one weekly cycle and auto-compare with previous run"
	@echo "  make smoke-prod      Smoke test deployed /detect endpoints"
	@echo "  make benchmark-public Run public provenance benchmark + leaderboard artifacts"
	@echo "  make build-text-dataset Build expanded labeled text corpus from benchmark samples"

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

intel-report:
	cd backend && python3 scripts/generate_x_trust_report.py --input "$${INPUT:-./x_intel_input.json}" --output "$${OUTPUT:-./x_trust_report.json}"

intel-benchmark:
	cd backend && python3 scripts/benchmark_x_intel.py --report "$${REPORT:-./x_trust_report.json}" --labels "$${LABELS:-}" --output "$${OUTPUT:-./x_trust_benchmark.json}"

intel-evidence:
	cd backend && python3 scripts/build_talent_visa_evidence_pack.py --reports-glob "$${REPORTS_GLOB:-./x_trust_report*.json}" --benchmarks-glob "$${BENCHMARKS_GLOB:-./x_trust_benchmark*.json}" --output-dir "$${OUTPUT_DIR:-./evidence}"

intel-pipeline:
	cd backend && python3 scripts/run_talent_visa_pipeline.py --handle "$${HANDLE:?Set HANDLE}" --window-days "$${WINDOW_DAYS:-90}" --max-posts "$${MAX_POSTS:-600}" --query "$${QUERY:-}" --labels "$${LABELS:-}" --output-dir "$${OUTPUT_DIR:-evidence/runs}"

intel-weekly-cycle:
	cd backend && python3 scripts/run_weekly_talent_visa_cycle.py --handle "$${HANDLE:?Set HANDLE}" --window-days "$${WINDOW_DAYS:-7}" --max-posts "$${MAX_POSTS:-60}" --query "$${QUERY:-}" --labels "$${LABELS:-}" --output-dir "$${OUTPUT_DIR:-evidence/runs/weekly}" --comparisons-dir "$${COMPARISONS_DIR:-evidence/runs/comparisons}" --summary-output "$${SUMMARY_OUTPUT:-evidence/runs/weekly/latest_summary.json}"

smoke-prod:
	cd backend && python3 scripts/smoke_detect_prod.py --base-url "$${BASE_URL:?Set BASE_URL}" --api-key "$${API_KEY:-}" --api-key-header "$${API_KEY_HEADER:-X-API-Key}" --output "$${OUTPUT:-evidence/smoke/prod_detect_smoke.json}"

benchmark-public:
	python3 benchmark/eval/run_public_benchmark.py --datasets-dir "$${DATASETS_DIR:-benchmark/datasets}" --output-dir "$${OUTPUT_DIR:-benchmark/results/latest}" --leaderboard-output "$${LEADERBOARD_OUTPUT:-benchmark/leaderboard/leaderboard.json}" --model-id "$${MODEL_ID:-baseline-heuristic-v1.0-live}" --decision-threshold "$${DECISION_THRESHOLD:-0.45}" --backend-url "$${BACKEND_URL:-http://127.0.0.1:8000}" --api-key "$${API_KEY:-}" --api-key-header "$${API_KEY_HEADER:-X-API-Key}" --live-mode "$${LIVE_MODE:-true}"
	python3 benchmark/eval/check_benchmark_regression.py --current "$${OUTPUT_DIR:-benchmark/results/latest}/benchmark_results.json" --baseline "$${BASELINE_SNAPSHOT:-benchmark/baselines/public_benchmark_snapshot.json}" --report-json "$${OUTPUT_DIR:-benchmark/results/latest}/regression_check.json" --report-md "$${OUTPUT_DIR:-benchmark/results/latest}/regression_check.md"

build-text-dataset:
	python3 backend/scripts/build_text_training_dataset.py --datasets-dir "$${DATASETS_DIR:-benchmark/datasets}" --output "$${OUTPUT:-backend/evidence/samples/text_labeled_expanded.jsonl}" --min-chars "$${MIN_CHARS:-80}"
