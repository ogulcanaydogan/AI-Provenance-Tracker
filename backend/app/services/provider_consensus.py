"""Provider adapter layer and weighted consensus scoring."""

from __future__ import annotations

import asyncio
import statistics
from typing import Any

import httpx

from app.core.config import settings
from app.models.detection import ConsensusSummary, ProviderConsensusVote
from app.services.c2pa_verifier import c2pa_verifier


class ProviderConsensusEngine:
    """Combines internal and external provider votes into one probability."""

    def __init__(self) -> None:
        self._weights = {
            "internal": settings.provider_internal_weight,
            "copyleaks": settings.provider_copyleaks_weight,
            "reality_defender": settings.provider_reality_defender_weight,
            "hive": settings.provider_hive_weight,
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
            self._vote(
                provider="internal",
                probability=self._clip(internal_probability),
                weight=max(0.0, self._weights["internal"]),
                status="ok",
                rationale="Local detector probability.",
                evidence_type="heuristic",
                verification_status="verified",
            )
        ]

        if settings.consensus_enabled:
            votes.extend(
                await self._collect_external_votes(
                    content_type, text=text, binary=binary, filename=filename
                )
            )

        active_votes = [vote for vote in votes if vote.status == "ok" and vote.weight > 0]
        if active_votes:
            weighted_total = sum(vote.probability * vote.weight for vote in active_votes)
            weight_sum = sum(vote.weight for vote in active_votes)
            final_probability = (
                self._clip(weighted_total / weight_sum)
                if weight_sum > 0
                else self._clip(internal_probability)
            )
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
        votes.append(
            await self._reality_defender_vote(
                content_type, text=text, binary=binary, filename=filename
            )
        )
        votes.append(
            await self._hive_vote(content_type, text=text, binary=binary, filename=filename)
        )
        votes.append(self._c2pa_vote(content_type, binary=binary, filename=filename))
        return votes

    async def _copyleaks_vote(
        self, content_type: str, *, text: str | None
    ) -> ProviderConsensusVote:
        weight = max(0.0, self._weights["copyleaks"])
        if content_type != "text":
            return self._vote(
                provider="copyleaks",
                probability=0.5,
                weight=weight,
                status="unsupported",
                rationale="Copyleaks adapter is enabled for text content only.",
                evidence_type="external_api",
                verification_status="unsupported",
            )
        if not settings.copyleaks_api_key:
            return self._vote(
                provider="copyleaks",
                probability=0.5,
                weight=weight,
                status="unavailable",
                rationale="Missing COPYLEAKS_API_KEY.",
                evidence_type="external_api",
                verification_status="unverified",
            )
        if not text:
            return self._vote(
                provider="copyleaks",
                probability=0.5,
                weight=weight,
                status="unsupported",
                rationale="No text payload provided.",
                evidence_type="external_api",
                verification_status="unsupported",
            )

        try:
            async with httpx.AsyncClient(timeout=settings.provider_timeout_seconds) as client:
                response = await self._post_with_retry(
                    client,
                    settings.copyleaks_api_url,
                    headers={
                        "Authorization": f"Bearer {settings.copyleaks_api_key}",
                        "Content-Type": "application/json",
                    },
                    json_body={"text": text},
                )
        except RuntimeError as exc:
            return self._vote(
                provider="copyleaks",
                probability=0.5,
                weight=weight,
                status="error",
                rationale=str(exc),
                evidence_type="external_api",
                verification_status="error",
            )

        if response.status_code >= 400:
            return self._vote(
                provider="copyleaks",
                probability=0.5,
                weight=weight,
                status="error",
                rationale=f"HTTP {response.status_code}",
                evidence_type="external_api",
                evidence_ref=self._request_id(response),
                verification_status="error",
            )

        probability = self._extract_probability(response.json())
        if probability is None:
            return self._vote(
                provider="copyleaks",
                probability=0.5,
                weight=weight,
                status="error",
                rationale="Missing probability field in provider response.",
                evidence_type="external_api",
                evidence_ref=self._request_id(response),
                verification_status="error",
            )

        return self._vote(
            provider="copyleaks",
            probability=self._clip(probability),
            weight=weight,
            status="ok",
            rationale="External text detector vote.",
            evidence_type="external_api",
            evidence_ref=self._request_id(response),
            verification_status="verified",
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
            return self._vote(
                provider="reality_defender",
                probability=0.5,
                weight=weight,
                status="unavailable",
                rationale="Missing REALITY_DEFENDER_API_KEY.",
                evidence_type="external_api",
                verification_status="unverified",
            )

        if content_type == "text" and not text:
            return self._vote(
                provider="reality_defender",
                probability=0.5,
                weight=weight,
                status="unsupported",
                rationale="No text payload provided.",
                evidence_type="external_api",
                verification_status="unsupported",
            )
        if content_type != "text" and not binary:
            return self._vote(
                provider="reality_defender",
                probability=0.5,
                weight=weight,
                status="unsupported",
                rationale="No binary payload provided.",
                evidence_type="external_api",
                verification_status="unsupported",
            )

        try:
            async with httpx.AsyncClient(timeout=settings.provider_timeout_seconds) as client:
                if content_type == "text":
                    response = await self._post_with_retry(
                        client,
                        settings.reality_defender_api_url,
                        headers={"Authorization": f"Bearer {settings.reality_defender_api_key}"},
                        json_body={"modality": "text", "text": text},
                    )
                else:
                    response = await self._post_with_retry(
                        client,
                        settings.reality_defender_api_url,
                        headers={"Authorization": f"Bearer {settings.reality_defender_api_key}"},
                        data={"modality": content_type},
                        files={"file": (filename or f"{content_type}.bin", binary)},
                    )
        except RuntimeError as exc:
            return self._vote(
                provider="reality_defender",
                probability=0.5,
                weight=weight,
                status="error",
                rationale=str(exc),
                evidence_type="external_api",
                verification_status="error",
            )

        if response.status_code >= 400:
            status_label = "rate_limited" if response.status_code == 429 else "error"
            return self._vote(
                provider="reality_defender",
                probability=0.5,
                weight=weight,
                status="error",
                rationale=f"{status_label}: HTTP {response.status_code}",
                evidence_type="external_api",
                evidence_ref=self._request_id(response),
                verification_status="error",
            )

        payload = response.json()
        probability, field_path = self._extract_reality_defender_probability(payload)
        if probability is None:
            keys = sorted(payload.keys()) if isinstance(payload, dict) else []
            return self._vote(
                provider="reality_defender",
                probability=0.5,
                weight=weight,
                status="error",
                rationale=f"Unsupported response schema: top-level keys={keys}",
                evidence_type="external_api",
                evidence_ref=self._request_id(response),
                verification_status="error",
            )

        return self._vote(
            provider="reality_defender",
            probability=self._clip(probability),
            weight=weight,
            status="ok",
            rationale=f"External multimodal detector vote ({field_path}).",
            evidence_type="external_api",
            evidence_ref=self._request_id(response),
            verification_status="verified",
        )

    async def _hive_vote(
        self,
        content_type: str,
        *,
        text: str | None,
        binary: bytes | None,
        filename: str | None,
    ) -> ProviderConsensusVote:
        weight = max(0.0, self._weights["hive"])
        if not settings.hive_api_key:
            return self._vote(
                provider="hive",
                probability=0.5,
                weight=weight,
                status="unavailable",
                rationale="Missing HIVE_API_KEY.",
                evidence_type="external_api",
                verification_status="unverified",
            )

        if content_type == "text" and not text:
            return self._vote(
                provider="hive",
                probability=0.5,
                weight=weight,
                status="unsupported",
                rationale="No text payload provided.",
                evidence_type="external_api",
                verification_status="unsupported",
            )
        if content_type != "text" and not binary:
            return self._vote(
                provider="hive",
                probability=0.5,
                weight=weight,
                status="unsupported",
                rationale="No binary payload provided.",
                evidence_type="external_api",
                verification_status="unsupported",
            )

        try:
            async with httpx.AsyncClient(timeout=settings.provider_timeout_seconds) as client:
                headers = {"Authorization": f"Token {settings.hive_api_key}"}
                if content_type == "text":
                    response = await self._post_with_retry(
                        client,
                        settings.hive_api_url,
                        headers=headers,
                        json_body={"input": {"text": text}},
                    )
                else:
                    response = await self._post_with_retry(
                        client,
                        settings.hive_api_url,
                        headers=headers,
                        data={"modality": content_type},
                        files={"media": (filename or f"{content_type}.bin", binary)},
                    )
        except RuntimeError as exc:
            return self._vote(
                provider="hive",
                probability=0.5,
                weight=weight,
                status="error",
                rationale=str(exc),
                evidence_type="external_api",
                verification_status="error",
            )

        if response.status_code >= 400:
            return self._vote(
                provider="hive",
                probability=0.5,
                weight=weight,
                status="error",
                rationale=f"HTTP {response.status_code}",
                evidence_type="external_api",
                evidence_ref=self._request_id(response),
                verification_status="error",
            )

        payload = response.json()
        probability, field_path = self._extract_hive_probability(payload)
        if probability is None:
            keys = sorted(payload.keys()) if isinstance(payload, dict) else []
            return self._vote(
                provider="hive",
                probability=0.5,
                weight=weight,
                status="error",
                rationale=f"Unsupported response schema: top-level keys={keys}",
                evidence_type="external_api",
                evidence_ref=self._request_id(response),
                verification_status="error",
            )

        return self._vote(
            provider="hive",
            probability=self._clip(probability),
            weight=weight,
            status="ok",
            rationale=f"External multimodal detector vote ({field_path}).",
            evidence_type="external_api",
            evidence_ref=self._request_id(response),
            verification_status="verified",
        )

    def _c2pa_vote(
        self, content_type: str, *, binary: bytes | None, filename: str | None
    ) -> ProviderConsensusVote:
        weight = max(0.0, self._weights["c2pa"])
        if not settings.c2pa_enabled:
            return self._vote(
                provider="c2pa",
                probability=0.5,
                weight=weight,
                status="unavailable",
                rationale="C2PA verifier disabled in configuration.",
                evidence_type="c2pa_manifest",
                verification_status="unverified",
            )
        if content_type not in {"image", "video"}:
            return self._vote(
                provider="c2pa",
                probability=0.5,
                weight=weight,
                status="unsupported",
                rationale="C2PA applies to signed image/video assets, not text/audio payloads.",
                evidence_type="c2pa_manifest",
                verification_status="unsupported",
            )

        verification = c2pa_verifier.verify_bytes(binary or b"", filename=filename)
        if verification.status == "verified":
            probability = 0.15
            status = "ok"
            verification_status = "verified"
        elif verification.status == "unverified":
            probability = 0.52 if verification.manifest_present else 0.58
            status = "ok"
            verification_status = "unverified"
        elif verification.status == "unsupported":
            probability = 0.5
            status = "unsupported"
            verification_status = "unsupported"
        elif verification.status == "unavailable":
            probability = 0.5
            status = "unavailable"
            verification_status = "unverified"
        else:
            probability = 0.5
            status = "error"
            verification_status = "error"

        issuer_text = f"; issuer={verification.issuer}" if verification.issuer else ""
        assertions_text = (
            f"; assertions={','.join(verification.assertions[:3])}"
            if verification.assertions
            else ""
        )
        return self._vote(
            provider="c2pa",
            probability=probability,
            weight=weight,
            status=status,
            rationale=f"{verification.rationale}{issuer_text}{assertions_text}",
            evidence_type="c2pa_manifest",
            evidence_ref=verification.manifest_id,
            verification_status=verification_status,
        )

    async def _post_with_retry(
        self,
        client: httpx.AsyncClient,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        json_body: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        files: dict[str, Any] | None = None,
    ) -> httpx.Response:
        attempts = max(1, int(settings.provider_retry_attempts))
        backoff = max(0.0, float(settings.provider_retry_backoff_seconds))
        last_error = ""

        for attempt in range(1, attempts + 1):
            try:
                response = await client.post(
                    url,
                    headers=headers,
                    json=json_body,
                    data=data,
                    files=files,
                )
            except httpx.HTTPError as exc:
                last_error = f"HTTP error: {exc}"
                if attempt < attempts:
                    await asyncio.sleep(backoff * attempt)
                    continue
                raise RuntimeError(last_error) from exc

            if response.status_code >= 500 and attempt < attempts:
                await asyncio.sleep(backoff * attempt)
                continue
            return response

        raise RuntimeError(last_error or "Provider request failed after retries.")

    def _extract_reality_defender_probability(self, payload: Any) -> tuple[float | None, str]:
        if not isinstance(payload, dict):
            return None, ""

        candidates = (
            ("result.score", self._path_value(payload, "result.score")),
            ("result.ai_probability", self._path_value(payload, "result.ai_probability")),
            ("prediction.ai_probability", self._path_value(payload, "prediction.ai_probability")),
            ("prediction.score", self._path_value(payload, "prediction.score")),
            ("data.ai_probability", self._path_value(payload, "data.ai_probability")),
            ("data.score", self._path_value(payload, "data.score")),
        )
        for path, value in candidates:
            if isinstance(value, (int, float)):
                return float(value), path
        return None, ""

    def _extract_hive_probability(self, payload: Any) -> tuple[float | None, str]:
        if not isinstance(payload, dict):
            return None, ""

        direct_candidates = (
            ("score", payload.get("score")),
            ("ai_probability", payload.get("ai_probability")),
            ("result.score", self._path_value(payload, "result.score")),
            ("result.ai_probability", self._path_value(payload, "result.ai_probability")),
            ("output.score", self._path_value(payload, "output.score")),
            ("output.ai_probability", self._path_value(payload, "output.ai_probability")),
        )
        for path, value in direct_candidates:
            if isinstance(value, (int, float)):
                return float(value), path

        # Hive-like schema: status[0].response.output[0].classes=[{class,score}, ...]
        classes = self._path_value(payload, "status.0.response.output.0.classes")
        class_probability = self._collect_hive_class_score(classes)
        if class_probability is not None:
            return class_probability, "status.0.response.output.0.classes"

        return None, ""

    def _collect_hive_class_score(self, classes: Any) -> float | None:
        if not isinstance(classes, list):
            return None

        best_score: float | None = None
        for item in classes:
            if not isinstance(item, dict):
                continue
            raw_label = item.get("class")
            raw_score = item.get("score")
            if not isinstance(raw_label, str) or not isinstance(raw_score, (int, float)):
                continue
            label = raw_label.lower()
            if "ai" not in label and "synthetic" not in label and "deepfake" not in label:
                continue
            score = float(raw_score)
            if best_score is None or score > best_score:
                best_score = score
        return best_score

    def _path_value(self, payload: dict[str, Any], path: str) -> Any:
        node: Any = payload
        for key in path.split("."):
            if isinstance(node, list):
                try:
                    index = int(key)
                except ValueError:
                    return None
                if index < 0 or index >= len(node):
                    return None
                node = node[index]
                continue
            if not isinstance(node, dict) or key not in node:
                return None
            node = node[key]
        return node

    def _disagreement(self, probabilities: list[float]) -> float:
        if len(probabilities) <= 1:
            return 0.0
        return min(1.0, statistics.pstdev(probabilities) * 2.5)

    @staticmethod
    def _clip(value: float) -> float:
        return max(0.0, min(float(value), 1.0))

    def _extract_probability(self, payload: Any) -> float | None:
        """Best-effort extraction across common provider response shapes."""
        if not isinstance(payload, dict):
            return None

        direct_keys = ("probability", "ai_probability", "score", "confidence")
        for key in direct_keys:
            value = payload.get(key)
            if isinstance(value, (int, float)):
                return float(value)

        nested_keys = ("result", "data", "prediction")
        for key in nested_keys:
            nested = payload.get(key)
            value = self._extract_probability(nested)
            if value is not None:
                return value
        return None

    def _request_id(self, response: httpx.Response) -> str | None:
        for key in ("x-request-id", "request-id", "x-correlation-id"):
            value = response.headers.get(key)
            if value:
                return value
        return None

    def _vote(
        self,
        *,
        provider: str,
        probability: float,
        weight: float,
        status: str,
        rationale: str,
        evidence_type: str | None = None,
        evidence_ref: str | None = None,
        verification_status: str | None = None,
    ) -> ProviderConsensusVote:
        return ProviderConsensusVote(
            provider=provider,  # type: ignore[arg-type]
            probability=self._clip(probability),
            weight=max(0.0, weight),
            status=status,  # type: ignore[arg-type]
            rationale=rationale,
            evidence_type=evidence_type,  # type: ignore[arg-type]
            evidence_ref=evidence_ref,
            verification_status=verification_status,  # type: ignore[arg-type]
        )


provider_consensus_engine = ProviderConsensusEngine()
