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
- `GET /health` - Health check

## Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
