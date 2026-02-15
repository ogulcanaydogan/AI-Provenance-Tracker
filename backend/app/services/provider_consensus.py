"""Provider adapter layer and weighted consensus scoring."""

from __future__ import annotations

import statistics
from typing import Any

import httpx

from app.core.config import settings
from app.models.detection import ConsensusSummary, ProviderConsensusVote


class ProviderConsensusEngine:
    """Combines internal and external provider votes into one probability."""

    def __init__(self) -> None:
        self._weights = {
            "internal": settings.provider_internal_weight,
            "copyleaks": settings.provider_copyleaks_weight,
            "reality_defender": settings.provider_reality_defender_weight,
            "c2pa": settings.provider_c2pa_weight,
        }

    async def build_consensus(
        self,
        *,
        content_type: str,
        internal_probability: float,
        text: str | None = None,
        binary: bytes | None = None,
        filename: str | None = None,
    ) -> ConsensusSummary:
        """Collect provider votes and compute a weighted final probability."""
        votes: list[ProviderConsensusVote] = [
            ProviderConsensusVote(
                provider="internal",
                probability=self._clip(internal_probability),
                weight=max(0.0, self._weights["internal"]),
                status="ok",
                rationale="Local detector probability",
            )
        ]

        if settings.consensus_enabled:
            votes.extend(await self._collect_external_votes(content_type, text=text, binary=binary, filename=filename))

        active_votes = [vote for vote in votes if vote.status == "ok" and vote.weight > 0]
        if active_votes:
            weighted_total = sum(vote.probability * vote.weight for vote in active_votes)
            weight_sum = sum(vote.weight for vote in active_votes)
            final_probability = self._clip(weighted_total / weight_sum) if weight_sum > 0 else self._clip(internal_probability)
            disagreement = self._disagreement([vote.probability for vote in active_votes])
        else:
            final_probability = self._clip(internal_probability)
            disagreement = 0.0

        threshold = self._clip(settings.consensus_threshold)
        return ConsensusSummary(
            final_probability=round(final_probability, 3),
            threshold=threshold,
            is_ai_generated=final_probability >= threshold,
            disagreement=round(disagreement, 3),
            providers=votes,
        )

    async def _collect_external_votes(
        self,
        content_type: str,
        *,
        text: str | None,
        binary: bytes | None,
        filename: str | None,
    ) -> list[ProviderConsensusVote]:
        votes: list[ProviderConsensusVote] = []
        votes.append(await self._copyleaks_vote(content_type, text=text))
        votes.append(await self._reality_defender_vote(content_type, text=text, binary=binary, filename=filename))
        votes.append(self._c2pa_vote(content_type, binary=binary))
        return votes

    async def _copyleaks_vote(self, content_type: str, *, text: str | None) -> ProviderConsensusVote:
        weight = max(0.0, self._weights["copyleaks"])
        if content_type != "text":
            return ProviderConsensusVote(
                provider="copyleaks",
                probability=0.5,
                weight=weight,
                status="unsupported",
                rationale="Provider adapter enabled for text content only in this build.",
            )
        if not settings.copyleaks_api_key:
            return ProviderConsensusVote(
                provider="copyleaks",
                probability=0.5,
                weight=weight,
                status="unavailable",
                rationale="Missing COPYLEAKS_API_KEY.",
            )
        if not text:
            return ProviderConsensusVote(
                provider="copyleaks",
                probability=0.5,
                weight=weight,
                status="unsupported",
                rationale="No text payload provided.",
            )

        try:
            async with httpx.AsyncClient(timeout=settings.provider_timeout_seconds) as client:
                response = await client.post(
                    settings.copyleaks_api_url,
                    headers={
                        "Authorization": f"Bearer {settings.copyleaks_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={"text": text},
                )
        except httpx.HTTPError as exc:
            return ProviderConsensusVote(
                provider="copyleaks",
                probability=0.5,
                weight=weight,
                status="error",
                rationale=f"HTTP error: {exc}",
            )

        if response.status_code >= 400:
            return ProviderConsensusVote(
                provider="copyleaks",
                probability=0.5,
                weight=weight,
                status="error",
                rationale=f"HTTP {response.status_code}",
            )

        probability = self._extract_probability(response.json())
        if probability is None:
            return ProviderConsensusVote(
                provider="copyleaks",
                probability=0.5,
                weight=weight,
                status="error",
                rationale="No probability field in provider response.",
            )

        return ProviderConsensusVote(
            provider="copyleaks",
            probability=self._clip(probability),
            weight=weight,
            status="ok",
            rationale="External text detector vote.",
        )

    async def _reality_defender_vote(
        self,
        content_type: str,
        *,
        text: str | None,
        binary: bytes | None,
        filename: str | None,
    ) -> ProviderConsensusVote:
        weight = max(0.0, self._weights["reality_defender"])
        if not settings.reality_defender_api_key:
            return ProviderConsensusVote(
                provider="reality_defender",
                probability=0.5,
                weight=weight,
                status="unavailable",
                rationale="Missing REALITY_DEFENDER_API_KEY.",
            )

        try:
            async with httpx.AsyncClient(timeout=settings.provider_timeout_seconds) as client:
                if content_type == "text":
                    if not text:
                        return ProviderConsensusVote(
                            provider="reality_defender",
                            probability=0.5,
                            weight=weight,
                            status="unsupported",
                            rationale="No text payload provided.",
                        )
                    response = await client.post(
                        settings.reality_defender_api_url,
                        headers={"Authorization": f"Bearer {settings.reality_defender_api_key}"},
                        json={"modality": "text", "text": text},
                    )
                else:
                    if not binary:
                        return ProviderConsensusVote(
                            provider="reality_defender",
                            probability=0.5,
                            weight=weight,
                            status="unsupported",
                            rationale="No binary payload provided.",
                        )
                    response = await client.post(
                        settings.reality_defender_api_url,
                        headers={"Authorization": f"Bearer {settings.reality_defender_api_key}"},
                        data={"modality": content_type},
                        files={"file": (filename or f"{content_type}.bin", binary)},
                    )
        except httpx.HTTPError as exc:
            return ProviderConsensusVote(
                provider="reality_defender",
                probability=0.5,
                weight=weight,
                status="error",
                rationale=f"HTTP error: {exc}",
            )

        if response.status_code >= 400:
            return ProviderConsensusVote(
                provider="reality_defender",
                probability=0.5,
                weight=weight,
                status="error",
                rationale=f"HTTP {response.status_code}",
            )

        probability = self._extract_probability(response.json())
        if probability is None:
            return ProviderConsensusVote(
                provider="reality_defender",
                probability=0.5,
                weight=weight,
                status="error",
                rationale="No probability field in provider response.",
            )

        return ProviderConsensusVote(
            provider="reality_defender",
            probability=self._clip(probability),
            weight=weight,
            status="ok",
            rationale="External multimodal detector vote.",
        )

    def _c2pa_vote(self, content_type: str, *, binary: bytes | None) -> ProviderConsensusVote:
        weight = max(0.0, self._weights["c2pa"])
        if not settings.c2pa_enabled:
            return ProviderConsensusVote(
                provider="c2pa",
                probability=0.5,
                weight=weight,
                status="unavailable",
                rationale="C2PA adapter disabled in configuration.",
            )
        if content_type not in {"image", "video"}:
            return ProviderConsensusVote(
                provider="c2pa",
                probability=0.5,
                weight=weight,
                status="unsupported",
                rationale="C2PA applies to signed media assets, not text/audio payloads.",
            )
        if not binary:
            return ProviderConsensusVote(
                provider="c2pa",
                probability=0.5,
                weight=weight,
                status="unsupported",
                rationale="No media bytes to inspect for provenance markers.",
            )

        sample = binary[: min(len(binary), 256_000)].lower()
        has_marker = any(marker in sample for marker in (b"c2pa", b"contentcredentials", b"contentauth"))
        probability = 0.15 if has_marker else 0.55
        rationale = (
            "Signed provenance markers detected; lowers AI-likelihood."
            if has_marker
            else "No C2PA marker detected; provenance unverified."
        )
        return ProviderConsensusVote(
            provider="c2pa",
            probability=probability,
            weight=weight,
            status="ok",
            rationale=rationale,
        )

    def _disagreement(self, probabilities: list[float]) -> float:
        if len(probabilities) <= 1:
            return 0.0
        return min(1.0, statistics.pstdev(probabilities) * 2.5)

    @staticmethod
    def _clip(value: float) -> float:
        return max(0.0, min(float(value), 1.0))

    def _extract_probability(self, payload: dict[str, Any]) -> float | None:
        """Best-effort extraction across common provider response shapes."""
        direct_keys = ("probability", "ai_probability", "score", "confidence")
        for key in direct_keys:
            value = payload.get(key)
            if isinstance(value, (int, float)):
                return float(value)

        nested_keys = ("result", "data", "prediction")
        for key in nested_keys:
            nested = payload.get(key)
            if isinstance(nested, dict):
                value = self._extract_probability(nested)
                if value is not None:
                    return value
        return None


provider_consensus_engine = ProviderConsensusEngine()

