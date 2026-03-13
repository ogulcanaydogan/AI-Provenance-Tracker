.PHONY: help install dev test lint format typecheck run docker-up docker-down clean intel-report intel-benchmark intel-evidence intel-pipeline intel-weekly-cycle smoke-prod benchmark-public benchmark-public-smoke benchmark-public-full benchmark-public-nightly benchmark-health cost-governance package-policy slo-report runtime-observability build-text-dataset build-hard-negatives calibrate-text text-quality-gate train-text-model train-text-a100 sweep-text-v100

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
	@echo "  make benchmark-public Run smoke profile public provenance benchmark"
	@echo "  make benchmark-public-smoke Explicit smoke profile benchmark run"
	@echo "  make benchmark-public-full Full_v3 profile benchmark run"
	@echo "  make benchmark-public-nightly Alias for full_v3 profile benchmark run"
	@echo "  make benchmark-health Dataset size/coverage tracker for selected target profile"
	@echo "  make calibrate-text Domain-aware text calibration refresh from benchmark dataset"
	@echo "  make text-quality-gate Enforce FP/ECE calibration thresholds"
	@echo "  make build-hard-negatives Extract hard FP/FN samples from scored benchmark outputs"
	@echo "  make train-text-model Run targeted text fine-tuning"
	@echo "  make train-text-a100 Recommended A100 profile for targeted fine-tuning"
	@echo "  make sweep-text-v100 Print/execute V100 hyperparameter sweep commands (PROFILE=<name>|all)"
	@echo "  make cost-governance Generate CI/CD spend governance snapshot"
	@echo "  make package-policy Enforce dependency source allow/deny policy"
	@echo "  make slo-report      Generate observability SLO report from workflow history"
	@echo "  make runtime-observability Generate runtime latency/error report from /metrics"
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
	BENCHMARK_PROFILE=smoke TARGET_PROFILE=smoke_v2 BASELINE_SNAPSHOT=benchmark/baselines/public_benchmark_snapshot_smoke.json bash scripts/run_benchmark_public.sh

benchmark-public-smoke:
	BENCHMARK_PROFILE=smoke TARGET_PROFILE=smoke_v2 BASELINE_SNAPSHOT=benchmark/baselines/public_benchmark_snapshot_smoke.json bash scripts/run_benchmark_public.sh

benchmark-public-full:
	BENCHMARK_PROFILE=full_v3 TARGET_PROFILE=full_v3 BASELINE_SNAPSHOT=benchmark/baselines/public_benchmark_snapshot_full.json bash scripts/run_benchmark_public.sh

benchmark-public-nightly: benchmark-public-full

benchmark-health:
	python3 benchmark/eval/dataset_health.py --datasets-dir "$${DATASETS_DIR:-benchmark/datasets}" --output-json "$${OUTPUT_JSON:-benchmark/results/latest/dataset_health.json}" --output-md "$${OUTPUT_MD:-benchmark/results/latest/dataset_health.md}" --targets-config "$${TARGETS_CONFIG:-benchmark/config/benchmark_targets.yaml}" --target-profile "$${TARGET_PROFILE:-full_v3}" $${MIN_METADATA_ROWS:+--min-metadata-rows "$${MIN_METADATA_ROWS}"} $${TARGET_TOTAL:+--target-total "$${TARGET_TOTAL}"} $${WARN_TOTAL:+--warn-total "$${WARN_TOTAL}"} $${TARGET_DETECTION:+--task-target "ai_vs_human_detection=$${TARGET_DETECTION}"} $${TARGET_ATTRIBUTION:+--task-target "source_attribution=$${TARGET_ATTRIBUTION}"} $${TARGET_TAMPER:+--task-target "tamper_detection=$${TARGET_TAMPER}"} $${TARGET_AUDIO:+--task-target "audio_ai_vs_human_detection=$${TARGET_AUDIO}"} $${TARGET_VIDEO:+--task-target "video_ai_vs_human_detection=$${TARGET_VIDEO}"} $${ENFORCE:+--enforce}

cost-governance:
	python3 scripts/cost_governance_snapshot.py --repo "$${REPO:-$${GITHUB_REPOSITORY:?Set REPO or GITHUB_REPOSITORY}}" --window-days "$${WINDOW_DAYS:-30}" --output-json "$${OUTPUT_JSON:-ops/reports/cost_governance_snapshot.json}" --output-md "$${OUTPUT_MD:-ops/reports/cost_governance_snapshot.md}" --gh-token "$${GH_TOKEN:-$${GITHUB_TOKEN:-}}" --vercel-token "$${VERCEL_TOKEN:-}" --vercel-project-id "$${VERCEL_PROJECT_ID:-}" --vercel-team-id "$${VERCEL_TEAM_ID:-}" --policy-file "$${POLICY_FILE:-config/cost_policy.yaml}" --workflow-name "$${WORKFLOW_NAME:-$${GITHUB_WORKFLOW:-local-cli}}" --fail-on-alert-level "$${FAIL_ON_ALERT_LEVEL:-none}"

package-policy:
	python3 scripts/check_package_policy.py --policy-file "$${POLICY_FILE:-config/package_policy.yaml}" --npm-lock "$${NPM_LOCK:-frontend/package-lock.json}" --requirements "$${REQUIREMENTS_FILE:-backend/requirements.txt}" --output-json "$${OUTPUT_JSON:-ops/reports/package_policy_report.json}" --output-md "$${OUTPUT_MD:-ops/reports/package_policy_report.md}"

slo-report:
	python3 scripts/slo_observability_report.py --repo "$${REPO:-$${GITHUB_REPOSITORY:?Set REPO or GITHUB_REPOSITORY}}" --window-days "$${WINDOW_DAYS:-7}" --output-json "$${OUTPUT_JSON:-ops/reports/slo_observability_report.json}" --output-md "$${OUTPUT_MD:-ops/reports/slo_observability_report.md}" --gh-token "$${GH_TOKEN:-$${GITHUB_TOKEN:-}}" --fail-on-alert-level "$${FAIL_ON_ALERT_LEVEL:-none}"

runtime-observability:
	python3 scripts/runtime_observability_report.py --metrics-url "$${METRICS_URL:-$${PRODUCTION_METRICS_URL:-}}" --api-url "$${API_URL:-$${PRODUCTION_API_URL:-}}" --api-key "$${API_KEY:-$${PRODUCTION_API_KEY:-}}" --api-key-header "$${API_KEY_HEADER:-$${PRODUCTION_API_KEY_HEADER:-X-API-Key}}" --output-json "$${OUTPUT_JSON:-ops/reports/runtime_observability_report.json}" --output-md "$${OUTPUT_MD:-ops/reports/runtime_observability_report.md}" --fail-on-alert-level "$${FAIL_ON_ALERT_LEVEL:-none}"

build-text-dataset:
	python3 backend/scripts/build_text_training_dataset.py --datasets-dir "$${DATASETS_DIR:-benchmark/datasets}" --output "$${OUTPUT:-backend/evidence/samples/text_labeled_expanded.jsonl}" --min-chars "$${MIN_CHARS:-80}"

build-hard-negatives:
	python3 backend/scripts/build_text_hard_negative_dataset.py --scored-samples "$${SCORED_SAMPLES:-benchmark/results/latest/scored_samples.jsonl}" --output "$${OUTPUT:-backend/evidence/samples/text_hard_negatives.jsonl}" $${INCLUDE_FALSE_NEGATIVES:+--include-false-negatives} --max-per-domain "$${MAX_PER_DOMAIN:-120}" --priority-domains "$${PRIORITY_DOMAINS:-code,finance,legal,science}" --priority-max-per-domain "$${PRIORITY_MAX_PER_DOMAIN:-220}" --min-score-gap "$${MIN_SCORE_GAP:-0.05}"

calibrate-text:
	cd backend && python3 scripts/evaluate_detection_calibration.py --input "$${INPUT:-../benchmark/datasets/detection_multidomain.jsonl}" --content-type text --output "$${OUTPUT:-evidence/calibration/text/latest_text_calibration.json}" --write-profile --profile-output "$${PROFILE_OUTPUT:-app/detection/text/calibration_profile.json}" --min-samples "$${MIN_SAMPLES:-120}" --include-domain-profiles --min-domain-samples "$${MIN_DOMAIN_SAMPLES:-40}" --register

text-quality-gate:
	python3 backend/scripts/check_text_quality_gate.py --report "$${REPORT:-backend/evidence/calibration/text/latest_text_calibration.json}" --max-fp-rate "$${MAX_FP_RATE:-0.08}" --max-ece "$${MAX_ECE:-0.08}" --min-sample-count "$${MIN_SAMPLE_COUNT:-100}" --max-uncertainty-margin "$${MAX_UNCERTAINTY_MARGIN:-0.18}" --max-domain-fp-rate "$${MAX_DOMAIN_FP_RATE:-0.30}" --min-domain-sample-count "$${MIN_DOMAIN_SAMPLE_COUNT:-30}" --output-json "$${OUTPUT_JSON:-backend/evidence/calibration/text/quality_gate.json}" --output-md "$${OUTPUT_MD:-backend/evidence/calibration/text/quality_gate.md}"

train-text-model:
	python3 backend/scripts/train_text_detector.py --dataset "$${DATASET:-backend/evidence/samples/text_labeled_expanded.jsonl}" --hard-negatives "$${HARD_NEGATIVES:-backend/evidence/samples/text_hard_negatives.jsonl}" --base-model "$${BASE_MODEL:-distilroberta-base}" --output-dir "$${OUTPUT_DIR:-backend/evidence/models/text}" --run-name "$${RUN_NAME:-v11_text_fp}" --epochs "$${EPOCHS:-2}" --learning-rate "$${LEARNING_RATE:-2e-5}" --train-batch-size "$${TRAIN_BATCH_SIZE:-16}" --eval-batch-size "$${EVAL_BATCH_SIZE:-32}" --fp-penalty "$${FP_PENALTY:-1.7}" --seed "$${SEED:-42}" --max-train-samples "$${MAX_TRAIN_SAMPLES:-0}"

train-text-a100:
	$(MAKE) train-text-model BASE_MODEL="$${BASE_MODEL:-distilroberta-base}" EPOCHS="$${EPOCHS:-3}" TRAIN_BATCH_SIZE="$${TRAIN_BATCH_SIZE:-32}" EVAL_BATCH_SIZE="$${EVAL_BATCH_SIZE:-64}" RUN_NAME="$${RUN_NAME:-v11_text_fp_a100}" FP_PENALTY="$${FP_PENALTY:-1.8}" LEARNING_RATE="$${LEARNING_RATE:-2e-5}"

sweep-text-v100:
	python3 backend/scripts/sweep_text_training.py --dataset "$${DATASET:-backend/evidence/samples/text_labeled_expanded.jsonl}" --hard-negatives "$${HARD_NEGATIVES:-backend/evidence/samples/text_hard_negatives.jsonl}" --output-dir "$${OUTPUT_DIR:-backend/evidence/models/text}" --base-model "$${BASE_MODEL:-distilroberta-base}" --profile "$${PROFILE:-all}" $${EXECUTE:+--execute}
