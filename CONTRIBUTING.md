# Contributing to AI Provenance Tracker

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Getting Started

1. Fork the repository
2. Clone your fork locally
3. Set up the development environment

```bash
cd ai-provenance-tracker/backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Development Workflow

### Branch Naming

Use descriptive branch names:
- `feature/add-audio-detection`
- `fix/text-detection-accuracy`
- `docs/api-documentation`

### Code Style

We use the following tools for code quality:
- **ruff** for linting and formatting
- **mypy** for type checking
- **pytest** for testing

Run checks before committing:

```bash
# Lint
ruff check .

# Format
ruff format .

# Type check
mypy app/

# Test
pytest tests/ -v
```

### Commit Messages

Use conventional commit format:
- `feat: add audio detection endpoint`
- `fix: improve text perplexity calculation`
- `docs: update API documentation`
- `test: add image detection tests`

### Pull Requests

1. Create a branch from `main`
2. Make your changes
3. Ensure all tests pass
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

## Testing
Describe testing performed

## Checklist
- [ ] Tests pass locally
- [ ] Code follows style guidelines
- [ ] Documentation updated
```

## Areas for Contribution

### High Priority
- Improve detection accuracy
- Add new content type support (audio, video)
- Browser extension development
- Documentation improvements

### Good First Issues
- Add unit tests
- Improve error messages
- Add input validation
- Documentation typos

## Detection Model Improvements

If you're working on detection models:

1. Document your methodology
2. Provide benchmark results
3. Include test cases showing improvement
4. Consider edge cases

### Evaluation Metrics

When submitting model improvements, include:
- Accuracy on AI-generated content
- False positive rate on human content
- Processing time benchmarks
- Dataset used for evaluation

## Questions?

Open an issue for discussion before starting major changes.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
