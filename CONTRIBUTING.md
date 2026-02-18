# Contributing to AI Provenance Tracker

Thank you for your interest in contributing. This document covers how to set up your development environment, our coding standards, and how to submit changes.

---

## Getting Started

1. Fork the repository
2. Clone your fork locally
3. Set up the development environment

```bash
# Backend
cd ai-provenance-tracker/backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

# Frontend
cd ../frontend
npm install
```

---

## Development Workflow

### Branch Naming

Use descriptive branch names with a type prefix:

```
feature/add-audio-detection
fix/text-detection-accuracy
docs/api-documentation
refactor/detection-pipeline
test/image-detector-coverage
chore/update-dependencies
```

### Code Style

We use the following tools for code quality:

- **ruff** for linting and formatting (Python)
- **mypy** for type checking (strict mode)
- **pytest** for testing with coverage
- **ESLint** for frontend linting

Run checks before committing:

```bash
# Backend (from backend/)
ruff check .
ruff format .
mypy app/
pytest tests/ -v

# Frontend (from frontend/)
npm run lint
npm run build
```

### Commit Messages

Use conventional commit format:

```
feat: add audio detection endpoint
fix: improve text perplexity calculation
docs: update API documentation
test: add image detection tests
refactor: extract signal weighting logic
chore: update dependencies
```

### Pull Requests

1. Create a branch from `main`
2. Make your changes
3. Ensure all tests pass and linting is clean
4. Update documentation if needed
5. Submit a pull request

#### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Performance improvement
- [ ] Test improvement

## Testing
Describe testing performed

## Checklist
- [ ] Tests pass locally (`pytest tests/ -v`)
- [ ] Linting passes (`ruff check . && ruff format --check .`)
- [ ] Type checking passes (`mypy app/`)
- [ ] Frontend builds (`npm run build`)
- [ ] Documentation updated if needed
```

---

## Project Structure

```
ai-provenance-tracker/
├── backend/           # FastAPI + Python backend
│   ├── app/
│   │   ├── api/v1/    # REST API endpoints
│   │   ├── detection/ # Detection engines (text, image, audio, video)
│   │   ├── services/  # Business logic (consensus, scheduling, webhooks)
│   │   ├── db/        # Database models and async operations
│   │   └── core/      # Configuration, security, logging
│   └── tests/         # Test suite (pytest)
├── frontend/          # Next.js 16 web application
├── extension/         # Chrome extension (Manifest V3)
├── benchmark/         # Public benchmark datasets and evaluation
├── deploy/
│   ├── helm/          # Kubernetes Helm charts
│   └── terraform/     # AWS infrastructure-as-code
└── scripts/           # Deployment and utility scripts
```

---

## Areas for Contribution

### High Priority

- **Detection accuracy** — improve signal weighting, add new detection features, or train better classifiers
- **Test coverage** — add tests for error paths, edge cases, and integration scenarios
- **Benchmark datasets** — contribute labelled datasets for detection evaluation
- **Documentation** — improve API docs, add tutorials, or improve inline code comments

### Good First Issues

- Add unit tests for untested utility functions
- Improve error messages in API responses
- Add input validation edge cases
- Fix documentation typos or unclear sections
- Add type hints to any untyped code

### Component-Specific

| Component | What to Contribute |
|-----------|-------------------|
| **Text Detector** | New NLP signals, better perplexity models, multi-language support |
| **Image Detector** | Improved FFT analysis, new artifact patterns, better CNN training |
| **Audio Detector** | ML-based detection models to complement spectral analysis |
| **Video Detector** | Frame-level ML classifiers to complement byte-pattern heuristics |
| **Browser Extension** | UI improvements, Firefox port, additional page analysis features |
| **Benchmark** | New evaluation tasks, additional labelled datasets, cross-domain tests |
| **Infrastructure** | Monitoring setup (Prometheus/Grafana), performance profiling |

---

## Detection Model Improvements

If you are working on detection models:

1. Document your methodology
2. Run the public benchmark and include results
3. Include test cases showing improvement
4. Consider edge cases (adversarial inputs, mixed content, short inputs)

### Running the Benchmark

```bash
python benchmark/eval/run_public_benchmark.py \
  --datasets-dir benchmark/datasets \
  --output-dir benchmark/results/latest \
  --leaderboard-output benchmark/leaderboard/leaderboard.json \
  --model-id your-model-id
```

### Evaluation Metrics

When submitting model improvements, include:

- **Accuracy** on AI-generated content (per domain if available)
- **False positive rate** on human-written content
- **ROC-AUC** and **Brier score** from the benchmark
- **Processing time** benchmarks
- **Dataset** used for evaluation

---

## Questions?

Open an issue for discussion before starting major changes. This helps avoid duplicate work and ensures your approach aligns with the project direction.

---

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
