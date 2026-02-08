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

### Audio Detection (Coming Soon)
- Voice cloning detection
- Speech synthesis identification
- Audio deepfake analysis

### Video Detection (Coming Soon)
- Face swap detection
- Lip sync anomaly detection
- Temporal consistency analysis

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
- [ ] Text detection engine (MVP)
- [ ] Image detection engine (MVP)
- [ ] Web interface
- [ ] Public API with rate limiting
- [ ] Browser extension
- [ ] Audio detection
- [ ] Video detection
- [ ] Batch processing
- [ ] API analytics dashboard

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
