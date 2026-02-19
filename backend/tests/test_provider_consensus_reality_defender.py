from __future__ import annotations

from typing import Any

import pytest

from app.services import provider_consensus as provider_consensus_module
from app.services.c2pa_verifier import C2PAVerificationResult
from app.services.provider_consensus import ProviderConsensusEngine


class _FakeResponse:
    def __init__(
        self, status_code: int, payload: dict[str, Any], headers: dict[str, str] | None = None
    ):
        self.status_code = status_code
        self._payload = payload
        self.headers = headers or {}

    def json(self) -> dict[str, Any]:
        return self._payload


@pytest.mark.asyncio
async def test_reality_defender_vote_success_schema_locked(monkeypatch) -> None:
    engine = ProviderConsensusEngine()
    monkeypatch.setattr(provider_consensus_module.settings, "reality_defender_api_key", "rd-key")

    async def _fake_post_with_retry(*_args, **_kwargs):
        return _FakeResponse(
            200,
            {"result": {"score": 0.81}},
            headers={"x-request-id": "rd-request-123"},
        )

    monkeypatch.setattr(engine, "_post_with_retry", _fake_post_with_retry)

    vote = await engine._reality_defender_vote("text", text="sample", binary=None, filename=None)

    assert vote.status == "ok"
    assert vote.probability == 0.81
    assert vote.evidence_type == "external_api"
    assert vote.evidence_ref == "rd-request-123"
    assert vote.verification_status == "verified"
    assert "result.score" in vote.rationale


@pytest.mark.asyncio
async def test_reality_defender_vote_malformed_schema(monkeypatch) -> None:
    engine = ProviderConsensusEngine()
    monkeypatch.setattr(provider_consensus_module.settings, "reality_defender_api_key", "rd-key")

    async def _fake_post_with_retry(*_args, **_kwargs):
        return _FakeResponse(200, {"unexpected": {"nested": 1}})

    monkeypatch.setattr(engine, "_post_with_retry", _fake_post_with_retry)

    vote = await engine._reality_defender_vote("text", text="sample", binary=None, filename=None)

    assert vote.status == "error"
    assert vote.probability == 0.5
    assert "Unsupported response schema" in vote.rationale
    assert vote.verification_status == "error"


@pytest.mark.asyncio
async def test_reality_defender_vote_timeout_error(monkeypatch) -> None:
    engine = ProviderConsensusEngine()
    monkeypatch.setattr(provider_consensus_module.settings, "reality_defender_api_key", "rd-key")

    async def _fake_post_with_retry(*_args, **_kwargs):
        raise RuntimeError("HTTP error: timeout")

    monkeypatch.setattr(engine, "_post_with_retry", _fake_post_with_retry)

    vote = await engine._reality_defender_vote("text", text="sample", binary=None, filename=None)

    assert vote.status == "error"
    assert vote.probability == 0.5
    assert "timeout" in vote.rationale


@pytest.mark.asyncio
async def test_reality_defender_vote_4xx_error(monkeypatch) -> None:
    engine = ProviderConsensusEngine()
    monkeypatch.setattr(provider_consensus_module.settings, "reality_defender_api_key", "rd-key")

    async def _fake_post_with_retry(*_args, **_kwargs):
        return _FakeResponse(429, {"detail": "rate limit"}, headers={"x-request-id": "rd-429"})

    monkeypatch.setattr(engine, "_post_with_retry", _fake_post_with_retry)

    vote = await engine._reality_defender_vote("text", text="sample", binary=None, filename=None)

    assert vote.status == "error"
    assert vote.probability == 0.5
    assert vote.evidence_ref == "rd-429"
    assert "rate_limited" in vote.rationale


def test_c2pa_vote_uses_verifier_result(monkeypatch) -> None:
    engine = ProviderConsensusEngine()
    monkeypatch.setattr(provider_consensus_module.settings, "c2pa_enabled", True)

    monkeypatch.setattr(
        provider_consensus_module.c2pa_verifier,
        "verify_bytes",
        lambda *_args, **_kwargs: C2PAVerificationResult(
            status="verified",
            manifest_present=True,
            signature_valid=True,
            issuer="issuer-x",
            assertions=["c2pa.actions"],
            manifest_id="manifest-abc",
            rationale="C2PA manifest and signature validation succeeded.",
        ),
    )

    vote = engine._c2pa_vote("image", binary=b"image-bytes", filename="sample.png")

    assert vote.status == "ok"
    assert vote.probability == 0.15
    assert vote.evidence_type == "c2pa_manifest"
    assert vote.evidence_ref == "manifest-abc"
    assert vote.verification_status == "verified"
