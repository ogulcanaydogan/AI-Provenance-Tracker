#!/usr/bin/env python3
"""Targeted fine-tuning pipeline for text AI detection."""

from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import random
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

try:
    import torch
    from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
    from torch import nn
    from transformers import (
        AutoModelForSequenceClassification,
        AutoTokenizer,
        DataCollatorWithPadding,
        Trainer,
        TrainingArguments,
    )
except ImportError as exc:  # pragma: no cover - runtime dependency check
    raise SystemExit(
        "Missing training dependencies. Install with: cd backend && pip install -e '.[dev,ml]'"
    ) from exc


@dataclass(slots=True)
class TextSample:
    text: str
    label: int
    domain: str


class JsonlTextDataset(torch.utils.data.Dataset):
    def __init__(self, encodings: dict[str, Any], labels: list[int]) -> None:
        self.encodings = encodings
        self.labels = labels

    def __len__(self) -> int:
        return len(self.labels)

    def __getitem__(self, idx: int) -> dict[str, torch.Tensor]:
        item = {key: torch.tensor(val[idx]) for key, val in self.encodings.items()}
        item["labels"] = torch.tensor(self.labels[idx], dtype=torch.long)
        return item


class WeightedTrainer(Trainer):
    def __init__(self, *args: Any, class_weights: torch.Tensor, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.class_weights = class_weights

    def compute_loss(  # type: ignore[override]
        self,
        model: torch.nn.Module,
        inputs: dict[str, torch.Tensor],
        return_outputs: bool = False,
        num_items_in_batch: int | None = None,
    ) -> torch.Tensor | tuple[torch.Tensor, Any]:
        labels = inputs.pop("labels")
        outputs = model(**inputs)
        logits = outputs.get("logits")
        loss_fct = nn.CrossEntropyLoss(weight=self.class_weights.to(logits.device))
        loss = loss_fct(logits, labels)
        return (loss, outputs) if return_outputs else loss


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fine-tune text detector with FP-focused objective."
    )
    parser.add_argument(
        "--dataset",
        default="backend/evidence/samples/text_labeled_expanded.jsonl",
        help="Primary labeled JSONL dataset.",
    )
    parser.add_argument(
        "--hard-negatives",
        default="backend/evidence/samples/text_hard_negatives.jsonl",
        help="Optional hard-negative JSONL to up-weight FP error regions.",
    )
    parser.add_argument("--base-model", default="distilroberta-base")
    parser.add_argument("--output-dir", default="backend/evidence/models/text")
    parser.add_argument("--run-name", default="v1_1_text_fp")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--epochs", type=float, default=2.0)
    parser.add_argument("--learning-rate", type=float, default=2e-5)
    parser.add_argument("--train-batch-size", type=int, default=16)
    parser.add_argument("--eval-batch-size", type=int, default=32)
    parser.add_argument("--max-length", type=int, default=512)
    parser.add_argument("--eval-ratio", type=float, default=0.15)
    parser.add_argument("--min-domain-samples", type=int, default=20)
    parser.add_argument(
        "--fp-penalty",
        type=float,
        default=1.7,
        help="Class weight multiplier for human class (label=0) to reduce false positives.",
    )
    parser.add_argument("--max-train-samples", type=int, default=0)
    return parser.parse_args()


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def _normalize_domain(value: Any) -> str:
    if not isinstance(value, str):
        return "general"
    raw = value.strip().lower().replace("_", "-")
    aliases = {
        "news": "news",
        "social": "social",
        "marketing": "marketing",
        "finance": "marketing",
        "academic": "academic",
        "education": "academic",
        "science": "academic",
        "legal": "academic",
        "code": "code-doc",
        "code-doc": "code-doc",
        "general": "general",
    }
    return aliases.get(raw, "general")


def _row_to_sample(row: dict[str, Any]) -> TextSample | None:
    text = str(row.get("text", "")).strip()
    if not text:
        return None
    label = int(row.get("label_is_ai", 0))
    domain = _normalize_domain(row.get("domain"))
    return TextSample(text=text, label=label, domain=domain)


def _load_samples(path: Path) -> list[TextSample]:
    if not path.exists():
        return []
    samples: list[TextSample] = []
    for row in _load_jsonl(path):
        sample = _row_to_sample(row)
        if sample is not None:
            samples.append(sample)
    return samples


def _domain_balanced_filter(samples: list[TextSample], min_domain_samples: int) -> list[TextSample]:
    by_domain: dict[str, list[TextSample]] = {}
    for sample in samples:
        by_domain.setdefault(sample.domain, []).append(sample)

    filtered: list[TextSample] = []
    for _domain, domain_samples in sorted(by_domain.items()):
        if len(domain_samples) < min_domain_samples:
            continue
        filtered.extend(domain_samples)
    return filtered


def _train_eval_split(
    samples: list[TextSample], eval_ratio: float, seed: int
) -> tuple[list[TextSample], list[TextSample]]:
    rng = random.Random(seed)
    shuffled = samples[:]
    rng.shuffle(shuffled)
    eval_count = max(1, int(len(shuffled) * eval_ratio))
    eval_samples = shuffled[:eval_count]
    train_samples = shuffled[eval_count:]
    if not train_samples:
        train_samples = eval_samples
    return train_samples, eval_samples


def _dataset_hash(samples: list[TextSample]) -> str:
    hasher = hashlib.sha256()
    for sample in samples:
        hasher.update(sample.text.encode("utf-8", errors="ignore"))
        hasher.update(str(sample.label).encode("utf-8"))
        hasher.update(sample.domain.encode("utf-8"))
    return hasher.hexdigest()


def _to_dataset(
    samples: list[TextSample], tokenizer: AutoTokenizer, max_length: int
) -> JsonlTextDataset:
    texts = [sample.text for sample in samples]
    labels = [sample.label for sample in samples]
    encodings = tokenizer(texts, truncation=True, padding=False, max_length=max_length)
    return JsonlTextDataset(encodings, labels)


def _compute_metrics(eval_pred: tuple[np.ndarray, np.ndarray]) -> dict[str, float]:
    logits, labels = eval_pred
    predictions = np.argmax(logits, axis=1)
    precision = precision_score(labels, predictions, zero_division=0)
    recall = recall_score(labels, predictions, zero_division=0)
    f1 = f1_score(labels, predictions, zero_division=0)
    acc = accuracy_score(labels, predictions)

    fp = int(np.sum((predictions == 1) & (labels == 0)))
    tn = int(np.sum((predictions == 0) & (labels == 0)))
    fp_rate = float(fp / (fp + tn)) if (fp + tn) else 0.0

    return {
        "precision": round(float(precision), 4),
        "recall": round(float(recall), 4),
        "f1": round(float(f1), 4),
        "accuracy": round(float(acc), 4),
        "fp_rate": round(fp_rate, 4),
    }


def _build_training_args(run_dir: Path, args: argparse.Namespace) -> TrainingArguments:
    """Build TrainingArguments compatible with multiple transformers versions."""
    supported = set(inspect.signature(TrainingArguments.__init__).parameters)

    kwargs: dict[str, Any] = {
        "output_dir": str(run_dir / "checkpoints"),
        "save_strategy": "epoch",
        "learning_rate": float(args.learning_rate),
        "per_device_train_batch_size": int(args.train_batch_size),
        "per_device_eval_batch_size": int(args.eval_batch_size),
        "num_train_epochs": float(args.epochs),
        "weight_decay": 0.01,
        "logging_steps": 25,
        "load_best_model_at_end": True,
        "metric_for_best_model": "f1",
        "report_to": "none",
        "save_total_limit": 2,
        "seed": int(args.seed),
    }

    # transformers renamed this field in some versions.
    if "eval_strategy" in supported:
        kwargs["eval_strategy"] = "epoch"
    elif "evaluation_strategy" in supported:
        kwargs["evaluation_strategy"] = "epoch"

    if "overwrite_output_dir" in supported:
        kwargs["overwrite_output_dir"] = True

    return TrainingArguments(**kwargs)


def run() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[2]
    dataset_path = (repo_root / args.dataset).resolve()
    hard_negatives_path = (repo_root / args.hard_negatives).resolve()

    if not dataset_path.exists():
        raise SystemExit(f"Dataset not found: {dataset_path}")

    base_samples = _load_samples(dataset_path)
    hard_samples = _load_samples(hard_negatives_path)
    samples = base_samples + hard_samples
    samples = _domain_balanced_filter(samples, int(args.min_domain_samples))

    if int(args.max_train_samples) > 0:
        samples = samples[: int(args.max_train_samples)]

    if len(samples) < 200:
        raise SystemExit(f"Not enough samples for training: {len(samples)}")

    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)

    train_samples, eval_samples = _train_eval_split(samples, float(args.eval_ratio), int(args.seed))

    tokenizer = AutoTokenizer.from_pretrained(args.base_model)
    model = AutoModelForSequenceClassification.from_pretrained(args.base_model, num_labels=2)

    train_dataset = _to_dataset(train_samples, tokenizer, int(args.max_length))
    eval_dataset = _to_dataset(eval_samples, tokenizer, int(args.max_length))

    output_root = (repo_root / args.output_dir).resolve()
    run_id = f"{args.run_name}_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}"
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    training_args = _build_training_args(run_dir, args)

    class_weights = torch.tensor([float(args.fp_penalty), 1.0], dtype=torch.float)

    trainer = WeightedTrainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        tokenizer=tokenizer,
        data_collator=DataCollatorWithPadding(tokenizer=tokenizer),
        compute_metrics=_compute_metrics,
        class_weights=class_weights,
    )

    trainer.train()
    eval_metrics = trainer.evaluate()

    final_model_dir = run_dir / "model"
    trainer.save_model(str(final_model_dir))
    tokenizer.save_pretrained(str(final_model_dir))

    metadata = {
        "generated_at": datetime.now(UTC).isoformat(),
        "run_id": run_id,
        "base_model": args.base_model,
        "model_version": f"text-finetune:{run_id}",
        "calibration_version": f"calibration:{datetime.now(UTC).strftime('%Y%m%d')}",
        "seed": int(args.seed),
        "fp_penalty": float(args.fp_penalty),
        "train_samples": len(train_samples),
        "eval_samples": len(eval_samples),
        "dataset_hash": _dataset_hash(samples),
        "dataset_path": str(dataset_path),
        "hard_negatives_path": str(hard_negatives_path),
        "metrics": {
            key: float(value)
            for key, value in eval_metrics.items()
            if isinstance(value, (int, float))
        },
        "device": "cuda" if torch.cuda.is_available() else "cpu",
        "model_path": str(final_model_dir),
        "model_path_repo_relative": str(final_model_dir.relative_to(repo_root)),
    }

    manifest_path = run_dir / "training_manifest.json"
    manifest_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

    latest_pointer = output_root / "latest.json"
    latest_pointer.write_text(
        json.dumps(
            {
                "run_id": run_id,
                "manifest": str(manifest_path),
                "model_path": str(final_model_dir),
                "model_path_repo_relative": str(final_model_dir.relative_to(repo_root)),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"Training completed: {run_dir}")
    print(f"Manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
