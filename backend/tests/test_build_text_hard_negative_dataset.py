from __future__ import annotations

import importlib.util
import json
import sys
import types
from pathlib import Path


def _load_script_module() -> types.ModuleType:
    script_path = (
        Path(__file__).resolve().parents[1] / "scripts" / "build_text_hard_negative_dataset.py"
    )
    spec = importlib.util.spec_from_file_location("build_text_hard_negative_dataset", script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_priority_domains_allow_higher_cap(tmp_path: Path) -> None:
    module = _load_script_module()
    text_file = tmp_path / "sample.txt"
    text_file.write_text("hard negative text sample", encoding="utf-8")

    scored_path = tmp_path / "scored.jsonl"
    rows = [
        {
            "sample_id": "code-1",
            "status": "ok",
            "modality": "text",
            "label_is_ai": 0,
            "prediction": 1,
            "score": 0.8,
            "domain": "code",
            "input_ref": str(text_file),
        },
        {
            "sample_id": "code-2",
            "status": "ok",
            "modality": "text",
            "label_is_ai": 0,
            "prediction": 1,
            "score": 0.79,
            "domain": "code",
            "input_ref": str(text_file),
        },
        {
            "sample_id": "code-3",
            "status": "ok",
            "modality": "text",
            "label_is_ai": 0,
            "prediction": 1,
            "score": 0.78,
            "domain": "code",
            "input_ref": str(text_file),
        },
        {
            "sample_id": "general-1",
            "status": "ok",
            "modality": "text",
            "label_is_ai": 0,
            "prediction": 1,
            "score": 0.8,
            "domain": "general",
            "input_ref": str(text_file),
        },
        {
            "sample_id": "general-2",
            "status": "ok",
            "modality": "text",
            "label_is_ai": 0,
            "prediction": 1,
            "score": 0.8,
            "domain": "general",
            "input_ref": str(text_file),
        },
    ]
    scored_path.write_text(
        "\n".join(json.dumps(item) for item in rows) + "\n",
        encoding="utf-8",
    )

    output_path = tmp_path / "hard_negatives.jsonl"
    original_argv = sys.argv
    sys.argv = [
        "build_text_hard_negative_dataset.py",
        "--scored-samples",
        str(scored_path),
        "--output",
        str(output_path),
        "--max-per-domain",
        "1",
        "--priority-domains",
        "code",
        "--priority-max-per-domain",
        "2",
    ]
    try:
        rc = module.run()
    finally:
        sys.argv = original_argv

    assert rc == 0
    output_rows = [
        json.loads(line)
        for line in output_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    by_domain = {}
    for item in output_rows:
        by_domain[item["domain"]] = by_domain.get(item["domain"], 0) + 1

    assert by_domain["code"] == 2
    assert by_domain["general"] == 1
    assert all("priority_domain" in item for item in output_rows)


def test_domain_normalization_and_priority_flag(tmp_path: Path) -> None:
    module = _load_script_module()
    text_file = tmp_path / "sample.txt"
    text_file.write_text("hard negative text sample", encoding="utf-8")

    scored_path = tmp_path / "scored.jsonl"
    scored_path.write_text(
        json.dumps(
            {
                "sample_id": "sci-1",
                "status": "ok",
                "modality": "text",
                "label_is_ai": 0,
                "prediction": 1,
                "score": 0.8,
                "domain": "Science",
                "input_ref": str(text_file),
            }
        )
        + "\n",
        encoding="utf-8",
    )

    output_path = tmp_path / "hard_negatives.jsonl"
    original_argv = sys.argv
    sys.argv = [
        "build_text_hard_negative_dataset.py",
        "--scored-samples",
        str(scored_path),
        "--output",
        str(output_path),
        "--priority-domains",
        "science",
    ]
    try:
        rc = module.run()
    finally:
        sys.argv = original_argv

    assert rc == 0
    output_rows = [
        json.loads(line)
        for line in output_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(output_rows) == 1
    assert output_rows[0]["domain"] == "science"
    assert output_rows[0]["priority_domain"] is True
