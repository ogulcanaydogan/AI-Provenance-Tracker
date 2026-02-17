# Public Benchmark and Leaderboard

This folder contains the first public benchmark slice for Provenance-as-a-Service.

## Tasks
1. AI-generated vs human detection (multi-domain)
2. Source attribution (model family)
3. Tamper robustness (paraphrase, translation, human edits)

## Run locally
```bash
python benchmark/eval/run_public_benchmark.py \
  --datasets-dir benchmark/datasets \
  --output-dir benchmark/results/latest \
  --leaderboard-output benchmark/leaderboard/leaderboard.json \
  --model-id baseline-heuristic-v0.1
```

## Outputs
- `benchmark/results/latest/benchmark_results.json`
- `benchmark/results/latest/baseline_results.md`
- `benchmark/leaderboard/leaderboard.json`

Open `benchmark/leaderboard/index.html` to view leaderboard results.

## Publish as public page
- Workflow: `/Users/ogulcanaydogan/Desktop/Projects/YaPAY/ai-provenance-tracker/.github/workflows/publish-leaderboard.yml`
- It rebuilds `benchmark/leaderboard/leaderboard.json` and deploys `benchmark/leaderboard` to GitHub Pages.
