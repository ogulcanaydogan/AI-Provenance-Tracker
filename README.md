# AI Provenance Tracker

> Detect AI-generated content, trace its origins, and verify authenticity.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

---

## The Problem

With generative AI producing increasingly realistic content, distinguishing human-created from AI-generated material has become critical for:

- **Journalists** verifying sources and content authenticity
- **Researchers** ensuring academic integrity
- **Content Moderators** identifying synthetic media
- **Legal Teams** establishing content provenance
- **Everyone** navigating an AI-saturated information landscape

## The Solution

AI Provenance Tracker is an open-source platform that:

1. **Detects** AI-generated content across text, images, audio, and video
2. **Analyzes** creation patterns and metadata signatures
3. **Scores** confidence levels with explainable reasoning
4. **Tracks** content lineage when possible

---

## Features

### Text Detection
- GPT, Claude, Llama, and other LLM detection
- Perplexity and burstiness analysis
- Writing style fingerprinting
- Multi-language support

### Image Detection
- DALL-E, Midjourney, Stable Diffusion detection
- Frequency domain analysis
- Artifact pattern recognition
- Metadata forensics

### Audio Detection (MVP)
- WAV audio detection endpoint
- Spectral flatness and dynamic range analysis
- Clipping and zero-crossing anomaly checks

### Video Detection (MVP Scaffold)
- Video upload endpoint
- Byte-pattern and container-signature analysis
- Confidence scoring with explainable flags

### Browser Extension (MVP)
- Analyze visible text from the current page
- Uses the same `POST /api/v1/detect/text` backend endpoint
- Displays confidence and explanation in the popup

### X Reputation Intelligence Input (MVP)
- Collects target-handle X data (default 14-day window)
- Normalizes posts/network/bot/AI/claim fields into a single JSON schema
- Exposes `POST /api/v1/intel/x/collect` and `backend/scripts/collect_x_input.py`
- Generates explainable trust-and-safety reports (`/api/v1/intel/x/report`)
- Includes benchmark + talent-visa evidence pack tooling

### Public Benchmark + Leaderboard (Flagship v0.1)
- Reproducible benchmark tasks under `benchmark/datasets` + `benchmark/eval`
- Task 1: AI-vs-human detection (multi-domain)
- Task 2: Source attribution (model-family accuracy)
- Task 3: Tamper robustness (paraphrase/translate/human-edit stress)
- Trust metrics: ROC-AUC, calibration ECE, Brier, false-positive by domain
- Static leaderboard page at `benchmark/leaderboard/index.html`

### Batch Processing
- Batch text detection endpoint: `POST /api/v1/batch/text`
- Per-item success/error results in request order
- Configurable item cap via `MAX_BATCH_ITEMS`

### API Analytics Dashboard
- Dashboard metrics endpoint: `GET /api/v1/analyze/dashboard`
- Windowed totals, AI-rate, source/type breakdowns, and daily timeline
- Frontend dashboard page at `/dashboard`

### Persistent History + Controls (Phase 2)
- Detection history/analytics persisted to database (`analysis_records`)
- Optional API key requirement with endpoint-aware quotas
- Daily spend-cap points to avoid runaway API usage

### X Drill-Down + Alerting
- `POST /api/v1/intel/x/drilldown` returns cluster drill-down, claim timeline, and alert list
- Deterministic talent-visa pipeline run IDs + canonical artifact checksums
- Added threshold calibration script for labeled evaluation

### Provider Consensus + Automation (Phase 3)
- Provider adapter layer with weighted consensus (`internal`, `copyleaks`, `reality_defender`, `c2pa`)
- Scheduler with retries for recurring X collect/report runs
- Scheduler monthly request cap + auto kill-switch (`SCHEDULER_MONTHLY_REQUEST_CAP`)
- Webhook delivery for scheduled run results and alert events
- Webhook retry queue + dead-letter logging
- Dashboard evaluation trend (precision/recall/F1 over time)
- X request budget guardrails (`X_COST_GUARD_ENABLED`, `X_MAX_REQUESTS_PER_RUN`)

---

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+ (for frontend)
- Docker (optional)

### Installation

```bash
# Clone the repository
git clone https://github.com/ogulcanaydogan/ai-provenance-tracker.git
cd ai-provenance-tracker

# Backend setup
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

# Run the API server
uvicorn app.main:app --reload --port 8000
```

### Using Docker

```bash
# Build and run with Docker Compose
docker-compose up --build

# API available at http://localhost:8000
# Frontend available at http://localhost:3000
```

---

## API Usage

### Detect Text

```bash
curl -X POST "http://localhost:8000/api/v1/detect/text" \
  -H "Content-Type: application/json" \
  -d '{"text": "Your text to analyze..."}'
```

**Response:**
```json
{
  "is_ai_generated": true,
  "confidence": 0.87,
  "model_prediction": "gpt-4",
  "analysis": {
    "perplexity": 12.4,
    "burstiness": 0.23,
    "vocabulary_richness": 0.67
  },
  "explanation": "High confidence AI detection based on low perplexity and uniform sentence structure."
}
```

### Detect Image

```bash
curl -X POST "http://localhost:8000/api/v1/detect/image" \
  -F "file=@image.png"
```

**Response:**
```json
{
  "is_ai_generated": true,
  "confidence": 0.92,
  "model_prediction": "stable-diffusion",
  "analysis": {
    "frequency_anomaly": 0.84,
    "artifact_score": 0.71,
    "metadata_flags": ["missing_exif", "unusual_compression"]
  },
  "explanation": "Image shows characteristic frequency patterns of diffusion models."
}
```

### Detect Audio (WAV)

```bash
curl -X POST "http://localhost:8000/api/v1/detect/audio" \
  -F "file=@sample.wav"
```

### Detect Video (MVP)

```bash
curl -X POST "http://localhost:8000/api/v1/detect/video" \
  -F "file=@clip.mp4"
```

### Collect X Intelligence Input

```bash
curl -X POST "http://localhost:8000/api/v1/intel/x/collect" \
  -H "Content-Type: application/json" \
  -d '{"target_handle":"@example","window_days":30,"max_posts":300,"query":"anthropic OR claudecode"}'
```

### Generate Trust Report + Evidence Pack

```bash
cd backend
python scripts/generate_x_trust_report.py --input ./x_intel_input.json --output ./x_trust_report.json
python scripts/benchmark_x_intel.py --report ./x_trust_report.json --labels ./evidence/labels_template.json --output ./x_trust_benchmark.json
python scripts/build_talent_visa_evidence_pack.py --reports-glob "./x_trust_report*.json" --benchmarks-glob "./x_trust_benchmark*.json" --output-dir ./evidence
```

### X Drill-Down Dataset

```bash
curl -X POST "http://localhost:8000/api/v1/intel/x/drilldown" \
  -H "Content-Type: application/json" \
  --data-binary @./backend/x_intel_input.json
```

### Batch Detect Text

```bash
curl -X POST "http://localhost:8000/api/v1/batch/text" \
  -H "Content-Type: application/json" \
  -d '{"items":[{"item_id":"a","text":"Sample text one..."},{"item_id":"b","text":"Sample text two..."}]}'
```

### API Dashboard Metrics

```bash
curl "http://localhost:8000/api/v1/analyze/dashboard?days=30"
```

### Detection Calibration Script

```bash
cd backend
python scripts/evaluate_detection_calibration.py --input ./labels_text.jsonl --content-type text --output ./calibration_text.json --register
python scripts/evaluate_detection_calibration.py --input ./labels_audio.jsonl --content-type audio --output ./calibration_audio.json --register
python scripts/evaluate_detection_calibration.py --input ./labels_video.jsonl --content-type video --output ./calibration_video.json --register
```

Audio/video JSONL samples should use `audio_path`/`video_path` (or `path`/`file_path`) and `label_is_ai`.
Template files: `backend/evidence/samples/audio_labeled_template.jsonl`, `backend/evidence/samples/video_labeled_template.jsonl`.

### Production Smoke Test (All Detect Endpoints)

```bash
cd backend
python scripts/smoke_detect_prod.py --base-url https://your-api-domain --output ./evidence/smoke/prod_detect_smoke.json
```

### Weekly Evidence Cycle + Run Comparison

```bash
cd backend
python scripts/run_weekly_talent_visa_cycle.py --handle @example --window-days 7 --max-posts 60 --output-dir ./evidence/runs/weekly --comparisons-dir ./evidence/runs/comparisons --summary-output ./evidence/runs/weekly/latest_summary.json
```

### Public Benchmark + Leaderboard

```bash
python benchmark/eval/run_public_benchmark.py \
  --datasets-dir benchmark/datasets \
  --output-dir benchmark/results/latest \
  --leaderboard-output benchmark/leaderboard/leaderboard.json \
  --model-id baseline-heuristic-v0.1
```

Outputs:
- `benchmark/results/latest/benchmark_results.json`
- `benchmark/results/latest/baseline_results.md`
- `benchmark/leaderboard/leaderboard.json`

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Web Interface                            │
│                    Next.js + TypeScript                          │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                          REST API                                │
│                     FastAPI + Python                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐    │
│  │ /detect  │  │ /analyze │  │ /batch   │  │ /api/v1/...  │    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Detection Engine                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │    Text     │  │    Image    │  │    Audio/Video          │  │
│  │  Detector   │  │  Detector   │  │    Detector             │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Data Layer                                 │
│              PostgreSQL + Redis + S3                             │
└─────────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
ai-provenance-tracker/
├── backend/
│   ├── app/
│   │   ├── api/v1/           # API endpoints
│   │   ├── core/             # Config, security, logging
│   │   ├── detection/        # Detection engines
│   │   │   ├── text/         # Text AI detection
│   │   │   ├── image/        # Image AI detection
│   │   │   ├── audio/        # Audio deepfake detection
│   │   │   └── video/        # Video deepfake detection
│   │   ├── models/           # Pydantic models
│   │   ├── services/         # Business logic
│   │   └── utils/            # Utilities
│   ├── tests/                # Test suite
│   └── pyproject.toml        # Python dependencies
├── frontend/                 # Next.js web app
├── extension/                # Chrome extension (MVP)
├── docs/                     # Documentation
├── scripts/                  # Utility scripts
├── docker-compose.yml
└── README.md
```

---

## Detection Methodology

### Text Detection

Our text detection uses multiple signals:

| Signal | Description | Weight |
|--------|-------------|--------|
| Perplexity | How "surprised" a language model is by the text | 30% |
| Burstiness | Variation in sentence complexity | 25% |
| Vocabulary | Word choice patterns and repetition | 20% |
| Structure | Paragraph and sentence structure uniformity | 15% |
| Classifier | Fine-tuned RoBERTa model prediction | 10% |

### Image Detection

| Signal | Description | Weight |
|--------|-------------|--------|
| Frequency Analysis | FFT patterns characteristic of AI | 35% |
| Artifact Detection | AI-specific generation artifacts | 30% |
| Metadata | EXIF data anomalies | 20% |
| CNN Classifier | Trained binary classifier | 15% |

---

## Roadmap

- [x] Project structure and API foundation
- [x] Text detection engine (MVP)
- [x] Image detection engine (MVP)
- [x] Web interface
- [x] Public API with rate limiting
- [x] Browser extension (Chrome MVP)
- [x] Audio detection (MVP)
- [x] Video detection (MVP scaffold)
- [x] Batch processing
- [x] API analytics dashboard
- [x] Prod smoke test script (`/detect/text|image|audio|video`)
- [x] Weekly talent-visa evidence automation + run comparison
- [x] Public benchmark + leaderboard baseline (detection/attribution/tamper)

---

## Browser Extension

Load the unpacked extension from `extension/` in Chrome to analyze the active page text.

See setup details: [extension/README.md](extension/README.md)

---

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Setup

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run linting
ruff check .

# Run type checking
mypy app/
```

---

## API Documentation

Once running, access the interactive API docs:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

## Acknowledgments

- Research papers on AI detection methodologies
- Open source ML community
- Contributors and early adopters

---

**Disclaimer:** No detection system is 100% accurate. Results should be considered as one data point in content verification, not definitive proof.
