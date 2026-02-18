# Public Benchmark and Leaderboard

This folder contains the first public benchmark slice for Provenance-as-a-Service.

## Tasks
1. AI-generated vs human detection (multi-domain)
2. Source attribution (model family)
3. Tamper robustness (paraphrase, translation, human edits)
4. Audio AI-vs-human detection (mini-set)
5. Video AI-vs-human detection (mini-set)

## Run locally
```bash
python benchmark/eval/run_public_benchmark.py \
  --datasets-dir benchmark/datasets \
  --output-dir benchmark/results/latest \
  --leaderboard-output benchmark/leaderboard/leaderboard.json \
  --model-id baseline-heuristic-v0.1

python benchmark/eval/check_benchmark_regression.py \
  --current benchmark/results/latest/benchmark_results.json \
  --baseline benchmark/baselines/public_benchmark_snapshot.json \
  --report-json benchmark/results/latest/regression_check.json \
  --report-md benchmark/results/latest/regression_check.md
```

## Outputs
- `benchmark/results/latest/benchmark_results.json`
- `benchmark/results/latest/baseline_results.md`
- `benchmark/results/latest/regression_check.json`
- `benchmark/results/latest/regression_check.md`
- `benchmark/leaderboard/leaderboard.json`

Open `benchmark/leaderboard/index.html` to view leaderboard results.

## Publish as public page
- Workflow: `/Users/ogulcanaydogan/Desktop/Projects/YaPAY/ai-provenance-tracker/.github/workflows/publish-leaderboard.yml`
- It rebuilds `benchmark/leaderboard/leaderboard.json` and deploys `benchmark/leaderboard` to GitHub Pages.
- To enable deployment, set repository variable `ENABLE_GH_PAGES_DEPLOY=true` and enable Pages in repository settings.
