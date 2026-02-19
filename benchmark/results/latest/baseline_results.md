# Public Benchmark Baseline Results

- Model ID: `baseline-heuristic-v1.0-live`
- Generated: `2026-02-18T22:01:28.661667+00:00`
- Live mode: `True`

## Baseline Table

| Task | Primary Metric | Value |
| --- | --- | ---: |
| AI vs Human Detection | F1 | 0.7333 |
| AI vs Human Detection | ROC-AUC | 1.0 |
| Audio AI vs Human Detection | F1 | 1.0 |
| Video AI vs Human Detection | F1 | 1.0 |
| Source Attribution (heuristic baseline) | Accuracy | 0.8 |
| Tamper Robustness | Robustness Score | 1.0 |

## Trust Report Metrics

- Calibration ECE: `0.1222`
- Brier Score: `0.2195`
- False Positive Rate by Domain: `{"code": 0.7143, "finance": 0.7407, "legal": 0.7143, "science": 0.7407}`
