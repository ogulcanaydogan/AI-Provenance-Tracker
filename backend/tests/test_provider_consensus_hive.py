from __future__ import annotations

from typing import Any

import pytest

from app.services import provider_consensus as provider_consensus_module
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
async def test_hive_vote_success_result_score(monkeypatch) -> None:
    engine = ProviderConsensusEngine()
    monkeypatch.setattr(provider_consensus_module.settings, "hive_api_key", "hive-key")

    async def _fake_post_with_retry(*_args, **_kwargs):
        return _FakeResponse(200, {"result": {"score": 0.74}}, headers={"x-request-id": "hive-1"})

    monkeypatch.setattr(engine, "_post_with_retry", _fake_post_with_retry)

    vote = await engine._hive_vote("text", text="sample", binary=None, filename=None)

    assert vote.status == "ok"
    assert vote.probability == 0.74
    assert vote.evidence_type == "external_api"
    assert vote.evidence_ref == "hive-1"
    assert vote.verification_status == "verified"
    assert "result.score" in vote.rationale


@pytest.mark.asyncio
async def test_hive_vote_success_classes_schema(monkeypatch) -> None:
    engine = ProviderConsensusEngine()
    monkeypatch.setattr(provider_consensus_module.settings, "hive_api_key", "hive-key")

    async def _fake_post_with_retry(*_args, **_kwargs):
        return _FakeResponse(
            200,
            {
                "status": [
                    {
                        "response": {
                            "output": [
                                {
                                    "classes": [
                                        {"class": "human", "score": 0.11},
                                        {"class": "ai_generated", "score": 0.89},
                                    ]
                                }
                            ]
                        }
                    }
                ]
            },
        )

    monkeypatch.setattr(engine, "_post_with_retry", _fake_post_with_retry)

    vote = await engine._hive_vote("image", text=None, binary=b"image-bytes", filename="sample.png")

    assert vote.status == "ok"
    assert vote.probability == 0.89
    assert "classes" in vote.rationale


@pytest.mark.asyncio
async def test_hive_vote_malformed_schema(monkeypatch) -> None:
    engine = ProviderConsensusEngine()
    monkeypatch.setattr(provider_consensus_module.settings, "hive_api_key", "hive-key")

    async def _fake_post_with_retry(*_args, **_kwargs):
        return _FakeResponse(200, {"unexpected": {"nested": 1}})

    monkeypatch.setattr(engine, "_post_with_retry", _fake_post_with_retry)

    vote = await engine._hive_vote("text", text="sample", binary=None, filename=None)

    assert vote.status == "error"
    assert vote.probability == 0.5
    assert "Unsupported response schema" in vote.rationale


@pytest.mark.asyncio
async def test_hive_vote_unavailable_without_key(monkeypatch) -> None:
    engine = ProviderConsensusEngine()
    monkeypatch.setattr(provider_consensus_module.settings, "hive_api_key", "")

    vote = await engine._hive_vote("text", text="sample", binary=None, filename=None)

    assert vote.status == "unavailable"
    assert vote.probability == 0.5
    assert vote.verification_status == "unverified"


@pytest.mark.asyncio
async def test_hive_vote_4xx_error(monkeypatch) -> None:
    engine = ProviderConsensusEngine()
    monkeypatch.setattr(provider_consensus_module.settings, "hive_api_key", "hive-key")

    async def _fake_post_with_retry(*_args, **_kwargs):
        return _FakeResponse(403, {"detail": "forbidden"}, headers={"x-request-id": "hive-403"})

    monkeypatch.setattr(engine, "_post_with_retry", _fake_post_with_retry)

    vote = await engine._hive_vote("text", text="sample", binary=None, filename=None)

    assert vote.status == "error"
    assert vote.probability == 0.5
    assert vote.evidence_ref == "hive-403"
    assert vote.verification_status == "error"
