"""C2PA manifest verification via c2patool CLI."""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.core.config import settings


@dataclass(slots=True)
class C2PAVerificationResult:
    """Normalized C2PA verification output."""

    status: str
    manifest_present: bool
    signature_valid: bool
    issuer: str | None = None
    assertions: list[str] = field(default_factory=list)
    manifest_id: str | None = None
    rationale: str = ""


class C2PAVerifier:
    """Verifies media provenance manifest and signature using c2patool."""

    def verify_bytes(self, media_bytes: bytes, filename: str | None = None) -> C2PAVerificationResult:
        if not media_bytes:
            return C2PAVerificationResult(
                status="unsupported",
                manifest_present=False,
                signature_valid=False,
                rationale="No media payload provided for C2PA verification.",
            )

        tool = settings.c2pa_cli_path.strip() or "c2patool"
        if shutil.which(tool) is None:
            return C2PAVerificationResult(
                status="unavailable",
                manifest_present=False,
                signature_valid=False,
                rationale=f"{tool} is not installed on this runtime.",
            )

        suffix = Path(filename or "asset.bin").suffix or ".bin"
        with tempfile.NamedTemporaryFile(prefix="c2pa-", suffix=suffix, delete=True) as handle:
            handle.write(media_bytes)
            handle.flush()
            payload, error = self._run_c2pa_tool(tool, Path(handle.name))
            if payload is None:
                return C2PAVerificationResult(
                    status="error",
                    manifest_present=False,
                    signature_valid=False,
                    rationale=error or "Unable to parse c2patool output.",
                )
            return self._parse_payload(payload)

    def _run_c2pa_tool(self, tool: str, media_path: Path) -> tuple[dict[str, Any] | None, str]:
        attempts = [
            [tool, str(media_path), "--detailed", "--json"],
            [tool, "--detailed", "--json", str(media_path)],
            [tool, str(media_path), "--json"],
        ]
        last_error = ""
        timeout_seconds = max(1.0, float(settings.c2pa_verify_timeout_seconds))

        for command in attempts:
            try:
                completed = subprocess.run(
                    command,
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=timeout_seconds,
                )
            except (subprocess.SubprocessError, OSError) as exc:
                last_error = f"CLI execution error: {exc}"
                continue

            if completed.returncode != 0:
                stderr = (completed.stderr or "").strip()
                stdout = (completed.stdout or "").strip()
                details = stderr or stdout or f"exit={completed.returncode}"
                last_error = f"c2patool command failed ({' '.join(command)}): {details}"
                continue

            payload = self._parse_json_output(completed.stdout)
            if payload is None:
                last_error = "c2patool returned non-JSON output."
                continue
            return payload, ""

        return None, last_error

    def _parse_json_output(self, output: str) -> dict[str, Any] | None:
        cleaned = (output or "").strip()
        if not cleaned:
            return None
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            if start == -1 or end == -1 or end <= start:
                return None
            try:
                parsed = json.loads(cleaned[start : end + 1])
            except json.JSONDecodeError:
                return None
        return parsed if isinstance(parsed, dict) else None

    def _parse_payload(self, payload: dict[str, Any]) -> C2PAVerificationResult:
        manifest_present = bool(
            self._first(payload, ("active_manifest", "manifest_store.active_manifest", "claim_generator"))
            or self._first(payload, ("manifests",))
        )

        signature_valid = self._infer_signature_valid(payload)
        issuer = self._as_str(
            self._first(
                payload,
                (
                    "active_manifest.claim_generator",
                    "manifest_store.active_manifest.claim_generator",
                    "claim_generator",
                    "active_manifest.issuer",
                    "manifest_store.active_manifest.issuer",
                ),
            )
        )
        manifest_id = self._as_str(
            self._first(
                payload,
                (
                    "active_manifest.label",
                    "manifest_store.active_manifest.label",
                    "active_manifest.id",
                    "manifest_store.active_manifest.id",
                ),
            )
        )
        assertions = self._extract_assertions(payload)

        if manifest_present and signature_valid:
            status = "verified"
            rationale = "C2PA manifest and signature validation succeeded."
        elif manifest_present:
            status = "unverified"
            rationale = "C2PA manifest exists but signature validation was not successful."
        else:
            status = "unverified"
            rationale = "No C2PA manifest detected."

        return C2PAVerificationResult(
            status=status,
            manifest_present=manifest_present,
            signature_valid=signature_valid,
            issuer=issuer,
            assertions=assertions,
            manifest_id=manifest_id,
            rationale=rationale,
        )

    def _infer_signature_valid(self, payload: dict[str, Any]) -> bool:
        flag = self._first(
            payload,
            (
                "validation_results.active_manifest.valid",
                "validation_results.valid",
                "active_manifest.validation.valid",
                "signature.valid",
                "signature.validated",
                "manifest_store.active_manifest.validation.valid",
            ),
        )
        if isinstance(flag, bool):
            return flag
        status = self._as_str(
            self._first(
                payload,
                (
                    "validation_results.active_manifest.status",
                    "active_manifest.validation_status",
                    "manifest_store.active_manifest.validation_status",
                    "signature.status",
                ),
            )
        )
        return status in {"valid", "verified", "ok", "success"}

    def _extract_assertions(self, payload: dict[str, Any]) -> list[str]:
        assertion_payload = self._first(
            payload,
            (
                "active_manifest.assertions",
                "manifest_store.active_manifest.assertions",
                "assertions",
            ),
        )
        if not isinstance(assertion_payload, list):
            return []

        result: list[str] = []
        for item in assertion_payload:
            if isinstance(item, str):
                result.append(item)
            elif isinstance(item, dict):
                label = item.get("label") or item.get("name") or item.get("type")
                if isinstance(label, str):
                    result.append(label)
        return result

    def _first(self, payload: dict[str, Any], paths: tuple[str, ...]) -> Any:
        for path in paths:
            node: Any = payload
            ok = True
            for key in path.split("."):
                if not isinstance(node, dict) or key not in node:
                    ok = False
                    break
                node = node[key]
            if ok and node is not None:
                return node
        return None

    @staticmethod
    def _as_str(value: Any) -> str | None:
        return value if isinstance(value, str) and value.strip() else None


c2pa_verifier = C2PAVerifier()
