# AI Provenance Tracker - Backend

FastAPI backend for detecting AI-generated content.

## Quick Start

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e ".[dev]"

# Run the server
uvicorn app.main:app --reload
```

## API Endpoints

- `POST /api/v1/detect/text` - Detect AI-generated text
- `POST /api/v1/detect/image` - Detect AI-generated images
- `POST /api/v1/detect/audio` - Detect AI-generated audio (WAV)
- `POST /api/v1/detect/video` - Detect AI-generated video (MVP)
- `POST /api/v1/batch/text` - Batch text detection
- `POST /api/v1/intel/x/collect` - Collect X data into trust-and-safety input schema
- `POST /api/v1/intel/x/collect/estimate` - Estimate X request cost without external calls
- `POST /api/v1/intel/x/report` - Generate trust-and-safety report from normalized input
- `POST /api/v1/intel/x/drilldown` - Build cluster/claim drill-down + alerts dataset
- `GET /api/v1/intel/x/scheduler/status` - Check recurring job status
- `POST /api/v1/intel/x/scheduler/run` - Trigger one immediate scheduled run
- `GET /api/v1/analyze/dashboard` - Dashboard-ready analytics metrics
- `GET /api/v1/analyze/evaluation` - Calibration precision/recall trend for dashboard
- `GET /health` - Health check

## X Intelligence Collection

Set `X_BEARER_TOKEN` in `.env`, then either call API:

```bash
curl -X POST "http://localhost:8000/api/v1/intel/x/collect" \
  -H "Content-Type: application/json" \
  -d '{"target_handle":"@example","window_days":30,"max_posts":300,"query":"anthropic OR claudecode"}'
```

or use CLI utility:

```bash
python scripts/collect_x_input.py --handle @example --window-days 30 --max-posts 300 --query "anthropic OR claudecode" --output ./x_intel_input.json --show-request-estimate
```

Low-cost run (tight request budget):

```bash
X_MAX_PAGES=1 X_MAX_REQUESTS_PER_RUN=4 python scripts/collect_x_input.py --handle @example --window-days 7 --max-posts 60 --output ./x_intel_input.json --show-request-estimate
```

Cost precheck endpoint (no external X calls):

```bash
curl -X POST "http://localhost:8000/api/v1/intel/x/collect/estimate" \
  -H "Content-Type: application/json" \
  -d '{"window_days":7,"max_posts":60,"max_pages":1}'
```

Batch text detection:

```bash
curl -X POST "http://localhost:8000/api/v1/batch/text" \
  -H "Content-Type: application/json" \
  -d '{"items":[{"item_id":"a","text":"Sample text one..."},{"item_id":"b","text":"Sample text two..."}]}'
```

Dashboard metrics:

```bash
curl "http://localhost:8000/api/v1/analyze/dashboard?days=30"
```

Dashboard drill-down from normalized input:

```bash
curl -X POST "http://localhost:8000/api/v1/intel/x/drilldown" \
  -H "Content-Type: application/json" \
  --data-binary @./x_intel_input.json
```

## Trust Report, Benchmark, Evidence Pack

Generate trust report:

```bash
python scripts/generate_x_trust_report.py --input ./x_intel_input.json --output ./x_trust_report.json
```

Benchmark (optional labels file):

```bash
python scripts/benchmark_x_intel.py --report ./x_trust_report.json --labels ./evidence/labels_template.json --output ./x_trust_benchmark.json
```

Build talent-visa evidence pack:

```bash
python scripts/build_talent_visa_evidence_pack.py --reports-glob "./x_trust_report*.json" --benchmarks-glob "./x_trust_benchmark*.json" --output-dir ./evidence
```

Run full pipeline:

```bash
python scripts/run_talent_visa_pipeline.py --handle @example --window-days 90 --max-posts 600 --query "anthropic OR claudecode OR claudeai OR usagelimits"
```

Run pipeline from pre-collected input JSON (offline mode):

```bash
python scripts/run_talent_visa_pipeline.py --input-json ./x_intel_input.json --output-dir ./evidence/runs/manual_input --run-id run_snapshot
```

Compare two run directories:

```bash
python scripts/compare_talent_visa_runs.py --base-run-dir ./evidence/runs/run_a --candidate-run-dir ./evidence/runs/run_b --output-json ./evidence/runs/comparisons/run_a_vs_run_b.json --output-md ./evidence/runs/comparisons/run_a_vs_run_b.md
```

Evaluate confidence-threshold calibration on labeled data:

```bash
python scripts/evaluate_detection_calibration.py --input ./labels_text.jsonl --content-type text --output ./calibration_text.json --register
```

Trigger a scheduler run manually:

```bash
curl -X POST "http://localhost:8000/api/v1/intel/x/scheduler/run?handle=@example"
```

Check scheduler status:

```bash
curl "http://localhost:8000/api/v1/intel/x/scheduler/status"
```

## Persistence and Migrations

Runtime analysis history is persisted in `analysis_records` (SQLite by default).

```bash
alembic upgrade head
```

## Security and Spend Controls

Configure optional API key enforcement and endpoint spend controls in `.env`:

- `REQUIRE_API_KEY`
- `API_KEYS`
- `DAILY_SPEND_CAP_POINTS`
- `RATE_LIMIT_MEDIA_REQUESTS`
- `RATE_LIMIT_BATCH_REQUESTS`
- `RATE_LIMIT_INTEL_REQUESTS`
- `X_COST_GUARD_ENABLED`
- `X_MAX_REQUESTS_PER_RUN`
- `CONSENSUS_ENABLED`
- `COPYLEAKS_API_KEY`
- `REALITY_DEFENDER_API_KEY`
- `SCHEDULER_ENABLED`
- `SCHEDULER_HANDLES`
- `SCHEDULER_MONTHLY_REQUEST_CAP`
- `SCHEDULER_KILL_SWITCH_ON_CAP`
- `SCHEDULER_USAGE_FILE`
- `WEBHOOK_URLS`
- `WEBHOOK_RETRY_ATTEMPTS`
- `WEBHOOK_RETRY_BACKOFF_SECONDS`
- `WEBHOOK_QUEUE_FILE`
- `WEBHOOK_DEAD_LETTER_FILE`

## Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
