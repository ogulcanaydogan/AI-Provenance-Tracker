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
- `POST /api/v1/intel/x/report` - Generate trust-and-safety report from normalized input
- `POST /api/v1/intel/x/drilldown` - Build cluster/claim drill-down + alerts dataset
- `GET /api/v1/analyze/dashboard` - Dashboard-ready analytics metrics
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
python scripts/collect_x_input.py --handle @example --window-days 30 --max-posts 300 --query "anthropic OR claudecode" --output ./x_intel_input.json
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

Evaluate confidence-threshold calibration on labeled data:

```bash
python scripts/evaluate_detection_calibration.py --input ./labels_text.jsonl --content-type text --output ./calibration_text.json
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

## Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
