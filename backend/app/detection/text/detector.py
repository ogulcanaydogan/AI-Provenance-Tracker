"""Text AI detection engine with ML-based classification."""

import json
import math
import re
import time
from collections import Counter
from pathlib import Path
from typing import Any, Optional

import numpy as np

# Optional ML dependencies - fall back to heuristics if not available
try:
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    torch = None

from app.core.config import settings
from app.detection.text.expert_bundle import load_text_expert_bundle
from app.models.detection import (
    AIModel,
    ChunkConsistencySummary,
    TextAnalysis,
    TextChunkSummary,
    TextDetectionResponse,
)


STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "has",
    "he",
    "in",
    "is",
    "it",
    "its",
    "of",
    "on",
    "that",
    "the",
    "to",
    "was",
    "were",
    "will",
    "with",
    "this",
    "these",
    "those",
    "you",
    "your",
    "we",
    "our",
    "they",
    "their",
    "i",
    "me",
    "my",
    "or",
    "if",
    "then",
    "than",
    "but",
    "about",
    "into",
    "over",
    "under",
    "not",
}


class TextDetector:
    """
    Detects AI-generated text using multiple signals and ML classification.

    Detection methods:
    1. Transformer-based classifier (RoBERTa fine-tuned)
    2. Perplexity analysis - AI text tends to have lower perplexity
    3. Burstiness - AI text has more uniform sentence structure
    4. Vocabulary analysis - Word choice patterns
    5. Stylometry analysis - punctuation/stopwords/sentence moments
    """

    def __init__(self, lazy_load: bool = True, apply_runtime_calibration: bool = True) -> None:
        """Initialize the text detector with ML models."""
        self.device = "cpu"
        if ML_AVAILABLE and torch is not None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = None
        self.tokenizer = None
        self.model_loaded = False
        self._loading = False
        self._apply_runtime_calibration = bool(apply_runtime_calibration)
        self._loaded_model_id = settings.text_detection_model
        self._calibration_profile = self._load_calibration_profile()
        self._expert_bundle = load_text_expert_bundle()
        if not lazy_load and ML_AVAILABLE:
            self._load_model()

    def _load_model(self) -> None:
        """Load the transformer model for classification."""
        if not ML_AVAILABLE:
            return

        if self._loading or self.model_loaded:
            return

        self._loading = True
        try:
            model_name = self._resolve_model_id()
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(
                model_name,
                num_labels=2,
                ignore_mismatched_sizes=True,
            )
            self.model.to(self.device)
            self.model.eval()
            self.model_loaded = True
            self._loaded_model_id = model_name
        except Exception:
            self.model_loaded = False
        finally:
            self._loading = False

    def _resolve_model_id(self) -> str:
        """Select fine-tuned local model path first, fallback to configured base model."""
        model_path = settings.text_detection_model_path.strip()
        if model_path:
            candidate = Path(model_path)
            if not candidate.is_absolute():
                backend_root = Path(__file__).resolve().parents[3]
                candidate = (backend_root / model_path).resolve()
            if candidate.exists():
                return str(candidate)
        return settings.text_detection_model or "distilroberta-base"

    async def detect(self, text: str, domain: Optional[str] = None) -> TextDetectionResponse:
        """
        Analyze text and determine if it's AI-generated.

        Args:
            text: The text to analyze

        Returns:
            TextDetectionResponse with detection results
        """
        if ML_AVAILABLE and not self.model_loaded and not self._loading:
            self._load_model()

        start_time = time.time()
        cleaned_text = self._preprocess_text(text)
        routing = self._profile_input(text, cleaned_text, requested_domain=domain)
        calibration_profile, calibration_key, length_band = self._resolve_calibration_profile(
            routing["resolved_domain"],
            word_count=routing["word_count"],
        )
        case_score = self._score_text_unit(
            text=text,
            cleaned_text=cleaned_text,
            resolved_domain=calibration_key,
            calibration_profile=calibration_profile,
        )
        chunk_consistency = self._build_chunk_consistency(
            raw_text=text,
            base_confidence=case_score["confidence"],
            resolved_domain=calibration_key,
            base_threshold=float(calibration_profile["decision_threshold"]),
        )
        confidence = self._aggregate_case_confidence(case_score["confidence"], chunk_consistency)
        (
            decision_band,
            distance_to_threshold,
            uncertainty_reason,
            uncertainty_flags,
        ) = self._finalize_text_decision(
            confidence=confidence,
            threshold=float(calibration_profile["decision_threshold"]),
            word_count=routing["word_count"],
            sentence_count=routing["sentence_count"],
            routing=routing,
            rewrite_sensitivity=case_score["rewrite_sensitivity"],
            hard_negative_similarity=case_score["hard_negative_similarity"],
            chunk_consistency=chunk_consistency,
            calibration_profile=calibration_profile,
        )
        is_ai = decision_band == "ai"
        model_pred = case_score["model_prediction"] if is_ai else None
        explanation = self._generate_explanation(
            decision_band=decision_band,
            confidence=confidence,
            perplexity=case_score["perplexity"],
            burstiness=case_score["burstiness"],
            distance_to_threshold=distance_to_threshold,
            uncertainty_reason=uncertainty_reason,
            ml_score=case_score["ml_score"],
            calibration_domain=calibration_key,
            uncertainty_flags=uncertainty_flags,
            length_band=length_band,
        )

        processing_time = (time.time() - start_time) * 1000

        return TextDetectionResponse(
            is_ai_generated=is_ai,
            confidence=confidence,
            decision_band=decision_band,
            distance_to_threshold=distance_to_threshold,
            uncertainty_reason=uncertainty_reason,
            model_prediction=model_pred,
            analysis=TextAnalysis(
                perplexity=case_score["perplexity"],
                burstiness=case_score["burstiness"],
                vocabulary_richness=case_score["vocab_richness"],
                average_sentence_length=case_score["avg_sentence_length"],
                repetition_score=case_score["repetition"],
                punctuation_diversity=case_score["punctuation_diversity"],
                stopword_ratio=case_score["stopword_ratio"],
                sentence_length_variance=case_score["sentence_variance"],
                sentence_length_kurtosis=case_score["sentence_kurtosis"],
                rewrite_sensitivity=case_score["rewrite_sensitivity"],
                hard_negative_similarity=case_score["hard_negative_similarity"],
            ),
            explanation=explanation,
            processing_time_ms=processing_time,
            model_version=f"text-detector:{self._loaded_model_id}",
            calibration_version=self._profile_version_label(calibration_profile, calibration_key),
            domain_profile=calibration_key,
            uncertainty_flags=uncertainty_flags,
            chunk_consistency=chunk_consistency,
        )

    def _profile_input(
        self,
        raw_text: str,
        cleaned_text: str,
        *,
        requested_domain: Optional[str],
    ) -> dict[str, Any]:
        words = self._tokenize(cleaned_text)
        sentences = self._split_sentences(cleaned_text)
        inferred_domain, inferred_confidence, input_type = self._infer_domain_with_confidence(
            raw_text, cleaned_text, words, sentences
        )
        requested = self._normalize_domain(requested_domain)
        resolved = requested or inferred_domain
        route_mismatch = bool(
            requested
            and requested != inferred_domain
            and inferred_confidence >= float(settings.text_domain_confidence_uncertain_threshold)
        )
        return {
            "requested_domain": requested,
            "resolved_domain": resolved,
            "inferred_domain": inferred_domain,
            "domain_confidence": inferred_confidence,
            "input_type": input_type,
            "route_mismatch": route_mismatch,
            "word_count": len(words),
            "sentence_count": len(sentences),
        }

    def _infer_domain_with_confidence(
        self,
        raw_text: str,
        cleaned_text: str,
        words: list[str],
        sentences: list[str],
    ) -> tuple[str, float, str]:
        lowered = cleaned_text.lower()
        keyword_hits: dict[str, float] = {}
        domain_keywords = self._expert_bundle.get("domain_keywords", {})
        if isinstance(domain_keywords, dict):
            for domain, markers in domain_keywords.items():
                score = 0.0
                if not isinstance(markers, list):
                    continue
                for marker in markers:
                    candidate = str(marker).strip().lower()
                    if candidate and candidate in lowered:
                        score += 1.0
                if score > 0:
                    keyword_hits[str(domain)] = score

        if raw_text.count("\n") >= 2 and len(words) >= 220:
            keyword_hits["news"] = keyword_hits.get("news", 0.0) + 0.6
        if any(token.startswith("#") or token.startswith("@") for token in raw_text.split()):
            keyword_hits["social-short"] = keyword_hits.get("social-short", 0.0) + 1.0
        if len(words) <= 120:
            keyword_hits["social-short"] = keyword_hits.get("social-short", 0.0) + 0.3

        if not keyword_hits:
            return "general", 0.0, "generic-text"

        sorted_hits = sorted(keyword_hits.items(), key=lambda item: item[1], reverse=True)
        best_domain, best_score = sorted_hits[0]
        second_score = sorted_hits[1][1] if len(sorted_hits) > 1 else 0.0
        confidence = best_score / max(best_score + second_score, 1.0)
        input_type = "article" if len(words) >= 180 else "short-form"
        if best_domain == "code-doc":
            input_type = "code-doc"
        elif best_domain == "social-short":
            input_type = "social-short"
        return best_domain, round(float(np.clip(confidence, 0.0, 1.0)), 3), input_type

    def _score_text_unit(
        self,
        *,
        text: str,
        cleaned_text: str,
        resolved_domain: str,
        calibration_profile: dict[str, object],
    ) -> dict[str, Any]:
        sentences = self._split_sentences(cleaned_text)
        words = self._tokenize(cleaned_text)
        perplexity = self._calculate_perplexity(cleaned_text, words)
        burstiness = self._calculate_burstiness(sentences)
        vocab_richness = self._calculate_vocabulary_richness(words)
        avg_sentence_length = self._calculate_avg_sentence_length(sentences)
        repetition = self._calculate_repetition_score(cleaned_text)
        punctuation_diversity = self._calculate_punctuation_diversity(cleaned_text)
        stopword_ratio = self._calculate_stopword_ratio(words)
        sentence_variance, sentence_kurtosis = self._calculate_sentence_length_moments(sentences)
        rewrite_sensitivity = self._calculate_rewrite_sensitivity(cleaned_text, sentences)
        hard_negative_similarity = self._calculate_hard_negative_similarity(cleaned_text)
        ml_score = self._get_ml_prediction(text) if self.model_loaded else None

        (
            _is_ai,
            confidence,
            model_pred,
            _decision_band,
            _distance_to_threshold,
            _uncertainty_reason,
        ) = self._make_prediction(
            perplexity=perplexity,
            burstiness=burstiness,
            vocab_richness=vocab_richness,
            avg_sentence_length=avg_sentence_length,
            repetition=repetition,
            punctuation_diversity=punctuation_diversity,
            stopword_ratio=stopword_ratio,
            sentence_length_variance=sentence_variance,
            sentence_length_kurtosis=sentence_kurtosis,
            word_count=len(words),
            sentence_count=len(sentences),
            ml_score=ml_score,
            calibration_profile=calibration_profile,
            rewrite_sensitivity=rewrite_sensitivity,
            hard_negative_similarity=hard_negative_similarity,
        )
        return {
            "resolved_domain": resolved_domain,
            "word_count": len(words),
            "sentence_count": len(sentences),
            "perplexity": perplexity,
            "burstiness": burstiness,
            "vocab_richness": vocab_richness,
            "avg_sentence_length": avg_sentence_length,
            "repetition": repetition,
            "punctuation_diversity": punctuation_diversity,
            "stopword_ratio": stopword_ratio,
            "sentence_variance": sentence_variance,
            "sentence_kurtosis": sentence_kurtosis,
            "rewrite_sensitivity": rewrite_sensitivity,
            "hard_negative_similarity": hard_negative_similarity,
            "ml_score": ml_score,
            "confidence": confidence,
            "model_prediction": model_pred,
        }

    def _segment_text(self, raw_text: str) -> list[str]:
        target_words = max(60, int(settings.text_chunk_target_words))
        min_words = max(40, int(settings.text_chunk_min_words))
        max_chunks = max(1, int(settings.text_chunk_max_count))

        paragraphs = [segment.strip() for segment in re.split(r"\n{2,}", raw_text) if segment.strip()]
        if len(paragraphs) <= 1:
            paragraphs = self._split_sentences(raw_text)
        chunks: list[str] = []
        current_parts: list[str] = []
        current_words = 0
        for part in paragraphs:
            part_words = len(self._tokenize(part))
            if current_parts and current_words >= target_words:
                chunks.append(" ".join(current_parts).strip())
                current_parts = [part]
                current_words = part_words
            else:
                current_parts.append(part)
                current_words += part_words
            if len(chunks) >= max_chunks:
                break

        if current_parts and len(chunks) < max_chunks:
            chunks.append(" ".join(current_parts).strip())

        if len(chunks) > 2 and len(self._tokenize(chunks[-1])) < min_words:
            chunks[-2] = f"{chunks[-2]} {chunks[-1]}".strip()
            chunks.pop()
        return [chunk for chunk in chunks if chunk]

    def _build_chunk_consistency(
        self,
        *,
        raw_text: str,
        base_confidence: float,
        resolved_domain: str,
        base_threshold: float,
    ) -> ChunkConsistencySummary | None:
        chunks = self._segment_text(raw_text)
        if len(chunks) <= 1:
            return None

        summaries: list[TextChunkSummary] = []
        routed_domains: list[str] = []
        confidences: list[float] = []
        bands: list[str] = []
        for index, chunk in enumerate(chunks):
            cleaned_chunk = self._preprocess_text(chunk)
            routing = self._profile_input(chunk, cleaned_chunk, requested_domain=resolved_domain)
            profile, chunk_domain, _length_band = self._resolve_calibration_profile(
                routing["resolved_domain"],
                word_count=routing["word_count"],
            )
            score = self._score_text_unit(
                text=chunk,
                cleaned_text=cleaned_chunk,
                resolved_domain=chunk_domain,
                calibration_profile=profile,
            )
            band, distance, _reason = self.apply_decision_band(
                confidence=score["confidence"],
                threshold=float(profile["decision_threshold"]),
                word_count=score["word_count"],
                sentence_count=score["sentence_count"],
                calibration_profile=profile,
            )
            summaries.append(
                TextChunkSummary(
                    index=index,
                    word_count=score["word_count"],
                    sentence_count=score["sentence_count"],
                    confidence=score["confidence"],
                    decision_band=band,
                    distance_to_threshold=distance,
                    domain_profile=chunk_domain,
                )
            )
            routed_domains.append(chunk_domain)
            confidences.append(score["confidence"])
            bands.append(band)

        mean_confidence = sum(confidences) / len(confidences)
        confidence_spread = max(confidences) - min(confidences)
        majority_band = max(set(bands), key=bands.count)
        disagreement_ratio = sum(1 for band in bands if band != majority_band) / len(bands)
        dominant_domain = max(set(routed_domains), key=routed_domains.count)
        route_mismatch = dominant_domain != resolved_domain
        disagreement_penalty = min(0.18, (confidence_spread * 0.35) + (disagreement_ratio * 0.25))
        aggregate_confidence = float(
            np.clip((0.65 * base_confidence) + (0.35 * mean_confidence) - disagreement_penalty, 0.0, 1.0)
        )

        return ChunkConsistencySummary(
            chunk_count=len(summaries),
            aggregate_confidence=round(aggregate_confidence, 3),
            mean_confidence=round(mean_confidence, 3),
            confidence_spread=round(confidence_spread, 3),
            disagreement_ratio=round(disagreement_ratio, 3),
            dominant_domain=dominant_domain,
            route_mismatch=route_mismatch,
            chunks=summaries,
        )

    def _aggregate_case_confidence(
        self,
        base_confidence: float,
        chunk_consistency: ChunkConsistencySummary | None,
    ) -> float:
        if chunk_consistency is None:
            return round(float(np.clip(base_confidence, 0.0, 1.0)), 3)
        aggregated = (0.55 * base_confidence) + (0.45 * chunk_consistency.aggregate_confidence)
        return round(float(np.clip(aggregated, 0.0, 1.0)), 3)

    def _finalize_text_decision(
        self,
        *,
        confidence: float,
        threshold: float,
        word_count: int,
        sentence_count: int,
        routing: dict[str, Any],
        rewrite_sensitivity: float,
        hard_negative_similarity: float,
        chunk_consistency: ChunkConsistencySummary | None,
        calibration_profile: dict[str, object],
    ) -> tuple[str, float, str | None, list[str]]:
        decision_band, distance_to_threshold, uncertainty_reason = self.apply_decision_band(
            confidence=confidence,
            threshold=threshold,
            word_count=word_count,
            sentence_count=sentence_count,
            calibration_profile=calibration_profile,
        )

        uncertainty_flags: list[str] = []
        if word_count < int(calibration_profile["short_text_min_words"]) or sentence_count < int(
            calibration_profile["short_text_min_sentences"]
        ):
            uncertainty_flags.append("short_text")
        if float(routing["domain_confidence"]) < float(
            settings.text_domain_confidence_uncertain_threshold
        ):
            uncertainty_flags.append("weak_domain_signal")
        if bool(routing["route_mismatch"]):
            uncertainty_flags.append("route_domain_mismatch")
        if chunk_consistency and (
            chunk_consistency.disagreement_ratio
            >= float(settings.text_chunk_disagreement_uncertain_threshold)
            or chunk_consistency.route_mismatch
        ):
            uncertainty_flags.append("chunk_disagreement")
        if rewrite_sensitivity >= 0.55:
            uncertainty_flags.append("paraphrase_style_transfer")
        if hard_negative_similarity >= 0.5 and distance_to_threshold <= float(
            settings.text_hard_negative_gate_margin
        ):
            uncertainty_flags.append("human_hard_negative_overlap")

        if uncertainty_flags:
            decision_band = "uncertain"
            reasons = {
                "short_text": "Insufficient text signal for a stable decision.",
                "weak_domain_signal": "Domain routing confidence is weak.",
                "route_domain_mismatch": "Requested route conflicts with inferred domain profile.",
                "chunk_disagreement": "Long-form chunks do not agree on one stable verdict.",
                "paraphrase_style_transfer": "Rewrite or style-transfer markers make attribution ambiguous.",
                "human_hard_negative_overlap": "Text overlaps with known human hard-negative patterns.",
            }
            reason_parts = [reasons[flag] for flag in uncertainty_flags if flag in reasons]
            if uncertainty_reason:
                reason_parts.insert(0, uncertainty_reason)
            uncertainty_reason = " ".join(dict.fromkeys(reason_parts))

        return decision_band, distance_to_threshold, uncertainty_reason, uncertainty_flags

    def apply_decision_band(
        self,
        *,
        confidence: float,
        threshold: Optional[float] = None,
        word_count: Optional[int] = None,
        sentence_count: Optional[int] = None,
        calibration_profile: Optional[dict[str, object]] = None,
    ) -> tuple[str, float, Optional[str]]:
        """Classify score into human/uncertain/ai using profile thresholds."""
        profile = calibration_profile or self._calibration_profile
        effective_threshold = (
            float(threshold) if threshold is not None else float(profile["decision_threshold"])
        )
        margin = float(profile["uncertainty_margin"])
        min_words = int(profile["short_text_min_words"])
        min_sentences = int(profile["short_text_min_sentences"])
        distance = round(abs(float(confidence) - effective_threshold), 3)

        if word_count is not None and sentence_count is not None:
            if word_count < min_words or sentence_count < min_sentences:
                reason = (
                    "Insufficient text signal: "
                    f"needs >= {min_words} words and >= {min_sentences} sentences."
                )
                return "uncertain", distance, reason

        lower_bound = effective_threshold - margin
        upper_bound = effective_threshold + margin
        if lower_bound <= confidence <= upper_bound:
            reason = f"Score falls inside uncertainty margin (+/-{margin:.2f}) around threshold."
            return "uncertain", distance, reason
        if confidence > upper_bound:
            return "ai", distance, None
        return "human", distance, None

    def _get_ml_prediction(self, text: str) -> Optional[float]:
        """Get prediction from transformer model."""
        if not self.model_loaded or self.model is None or self.tokenizer is None:
            return None

        try:
            inputs = self.tokenizer(
                text,
                return_tensors="pt",
                truncation=True,
                max_length=512,
                padding=True,
            )
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            with torch.no_grad():
                outputs = self.model(**inputs)
                probs = torch.softmax(outputs.logits, dim=-1)
                ai_prob = probs[0][1].item()

            return ai_prob
        except Exception:
            return None

    def _preprocess_text(self, text: str) -> str:
        """Clean and normalize text."""
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r'[^\w\s.,!?;:\'"()-]', "", text)
        return text.strip()

    def _split_sentences(self, text: str) -> list[str]:
        """Split text into sentences."""
        sentences = re.split(r"[.!?]+", text)
        return [s.strip() for s in sentences if s.strip()]

    def _tokenize(self, text: str) -> list[str]:
        """Tokenize text into words."""
        return re.findall(r"\b\w+\b", text.lower())

    def _calculate_perplexity(self, text: str, words: list[str]) -> float:
        """
        Calculate pseudo-perplexity score using entropy.

        Lower perplexity = more predictable = more likely AI-generated.
        """
        if len(words) < 10:
            return 50.0

        word_counts = Counter(words)
        total_words = len(words)

        entropy = 0.0
        for count in word_counts.values():
            prob = count / total_words
            entropy -= prob * math.log2(prob)

        perplexity = 2**entropy
        return round(perplexity, 2)

    def _calculate_burstiness(self, sentences: list[str]) -> float:
        """
        Calculate burstiness - variation in sentence complexity.

        AI text tends to have more uniform sentence lengths.
        """
        if len(sentences) < 3:
            return 0.5

        lengths = [len(s.split()) for s in sentences]
        mean_length = np.mean(lengths)

        if mean_length == 0:
            return 0.5

        std_length = np.std(lengths)
        burstiness = std_length / mean_length
        normalized = min(1.0, burstiness / 0.8)
        return round(normalized, 3)

    def _calculate_vocabulary_richness(self, words: list[str]) -> float:
        """Calculate vocabulary richness (type-token ratio)."""
        if len(words) < 10:
            return 0.5

        unique_words = len(set(words))
        total_words = len(words)
        richness = unique_words / math.sqrt(total_words)
        normalized = min(1.0, richness / 10)
        return round(normalized, 3)

    def _calculate_avg_sentence_length(self, sentences: list[str]) -> float:
        """Calculate average sentence length in words."""
        if not sentences:
            return 0.0

        lengths = [len(s.split()) for s in sentences]
        return round(float(np.mean(lengths)), 1)

    def _calculate_repetition_score(self, text: str) -> float:
        """Detect phrase repetition patterns."""
        words = text.lower().split()
        if len(words) < 10:
            return 0.0

        trigrams = [" ".join(words[i : i + 3]) for i in range(len(words) - 2)]
        trigram_counts = Counter(trigrams)

        repeated = sum(1 for count in trigram_counts.values() if count > 1)
        total = len(trigrams)
        if total == 0:
            return 0.0

        repetition_rate = repeated / total
        return round(min(1.0, repetition_rate * 10), 3)

    def _calculate_punctuation_diversity(self, text: str) -> float:
        """Calculate punctuation diversity ratio."""
        punctuation_marks = re.findall(r"[.,!?;:'\"()\-]", text)
        total = len(punctuation_marks)
        if total == 0:
            return 0.0
        return round(min(1.0, len(set(punctuation_marks)) / total), 3)

    def _calculate_stopword_ratio(self, words: list[str]) -> float:
        """Calculate stopword ratio for stylometric smoothing."""
        if not words:
            return 0.0
        stopword_hits = sum(1 for word in words if word in STOPWORDS)
        return round(stopword_hits / len(words), 3)

    def _calculate_sentence_length_moments(self, sentences: list[str]) -> tuple[float, float]:
        """Calculate variance and kurtosis over sentence lengths."""
        if len(sentences) < 3:
            return 0.0, 0.0

        lengths = np.array([len(s.split()) for s in sentences], dtype=float)
        variance = float(np.var(lengths))
        centered = lengths - float(np.mean(lengths))
        m2 = float(np.mean(centered**2))
        if m2 <= 1e-9:
            kurtosis = 0.0
        else:
            m4 = float(np.mean(centered**4))
            kurtosis = (m4 / (m2**2)) - 3.0
        return round(max(0.0, variance), 3), round(kurtosis, 3)

    def _make_prediction(
        self,
        *,
        perplexity: float,
        burstiness: float,
        vocab_richness: float,
        avg_sentence_length: float,
        repetition: float,
        punctuation_diversity: float,
        stopword_ratio: float,
        sentence_length_variance: float,
        sentence_length_kurtosis: float,
        word_count: int,
        sentence_count: int,
        ml_score: Optional[float] = None,
        calibration_profile: Optional[dict[str, object]] = None,
        rewrite_sensitivity: float = 0.0,
        hard_negative_similarity: float = 0.0,
    ) -> tuple[bool, float, Optional[AIModel], str, float, Optional[str]]:
        """Combine signals using a calibrated profile from expanded labeled samples."""
        profile = calibration_profile or self._calibration_profile
        ranges = profile["ranges"]
        weights = profile["weights"]

        perplexity_signal = self._normalize_inverse(
            perplexity,
            low=float(ranges["perplexity_low"]),
            high=float(ranges["perplexity_high"]),
        )
        burstiness_signal = self._normalize_inverse(
            burstiness,
            low=float(ranges["burstiness_low"]),
            high=float(ranges["burstiness_high"]),
        )
        vocabulary_signal = self._normalize_inverse(
            vocab_richness,
            low=float(ranges["vocab_richness_low"]),
            high=float(ranges["vocab_richness_high"]),
        )
        repetition_signal = self._normalize_direct(
            repetition,
            low=float(ranges["repetition_low"]),
            high=float(ranges["repetition_high"]),
        )
        sentence_signal = self._normalize_direct(
            avg_sentence_length,
            low=float(ranges["sentence_len_low"]),
            high=float(ranges["sentence_len_high"]),
        )
        punctuation_signal = self._normalize_inverse(
            punctuation_diversity,
            low=float(ranges["punctuation_diversity_low"]),
            high=float(ranges["punctuation_diversity_high"]),
        )
        stopword_signal = self._normalize_inverse(
            stopword_ratio,
            low=float(ranges["stopword_ratio_low"]),
            high=float(ranges["stopword_ratio_high"]),
        )
        sentence_variance_signal = self._normalize_inverse(
            sentence_length_variance,
            low=float(ranges["sentence_var_low"]),
            high=float(ranges["sentence_var_high"]),
        )
        sentence_kurtosis_signal = self._normalize_inverse(
            sentence_length_kurtosis,
            low=float(ranges["sentence_kurtosis_low"]),
            high=float(ranges["sentence_kurtosis_high"]),
        )
        rewrite_signal = self._normalize_direct(
            rewrite_sensitivity,
            low=0.1,
            high=0.75,
        )
        hard_negative_signal = self._normalize_direct(
            hard_negative_similarity,
            low=0.1,
            high=0.7,
        )

        heuristic_score = (
            perplexity_signal * float(weights["perplexity"])
            + burstiness_signal * float(weights["burstiness"])
            + vocabulary_signal * float(weights["vocabulary_richness"])
            + repetition_signal * float(weights["repetition"])
            + sentence_signal * float(weights["sentence_length"])
            + punctuation_signal * float(weights["punctuation_diversity"])
            + stopword_signal * float(weights["stopword_ratio"])
            + sentence_variance_signal * float(weights["sentence_length_variance"])
            + sentence_kurtosis_signal * float(weights["sentence_length_kurtosis"])
            + (rewrite_signal * 0.05)
        )
        heuristic_score -= hard_negative_signal * 0.08

        if ml_score is not None:
            ml_weight = float(profile["ml_weight"])
            raw_confidence = (ml_weight * float(ml_score)) + ((1.0 - ml_weight) * heuristic_score)
        else:
            raw_confidence = heuristic_score

        raw_confidence = float(np.clip(raw_confidence, 0.02, 0.98))
        confidence = (
            self._apply_calibration_map(raw_confidence, profile)
            if self._apply_runtime_calibration
            else raw_confidence
        )
        threshold = float(profile["decision_threshold"])
        decision_band, distance_to_threshold, uncertainty_reason = self.apply_decision_band(
            confidence=confidence,
            threshold=threshold,
            word_count=word_count,
            sentence_count=sentence_count,
            calibration_profile=profile,
        )
        is_ai = decision_band == "ai"

        model_pred = None
        if is_ai:
            if avg_sentence_length > 20 and burstiness < 0.4:
                model_pred = AIModel.GPT4
            elif avg_sentence_length > 15:
                model_pred = AIModel.CLAUDE
            else:
                model_pred = AIModel.GPT35

        return (
            is_ai,
            round(confidence, 3),
            model_pred,
            decision_band,
            distance_to_threshold,
            uncertainty_reason,
        )

    def _load_calibration_profile(self) -> dict[str, object]:
        """Load detector calibration profile generated from larger labeled corpora."""
        default_profile: dict[str, object] = {
            "version": "default-v2-tristate",
            "decision_threshold": 0.45,
            "uncertainty_margin": 0.08,
            "short_text_min_words": 120,
            "short_text_min_sentences": 4,
            "ml_weight": 0.38,
            "weights": {
                "perplexity": 0.18,
                "burstiness": 0.16,
                "vocabulary_richness": 0.1,
                "repetition": 0.14,
                "sentence_length": 0.08,
                "punctuation_diversity": 0.08,
                "stopword_ratio": 0.06,
                "sentence_length_variance": 0.07,
                "sentence_length_kurtosis": 0.03,
            },
            "ranges": {
                "perplexity_low": 8.0,
                "perplexity_high": 42.0,
                "burstiness_low": 0.12,
                "burstiness_high": 0.72,
                "vocab_richness_low": 0.20,
                "vocab_richness_high": 0.95,
                "repetition_low": 0.01,
                "repetition_high": 0.30,
                "sentence_len_low": 8.0,
                "sentence_len_high": 28.0,
                "punctuation_diversity_low": 0.08,
                "punctuation_diversity_high": 0.70,
                "stopword_ratio_low": 0.16,
                "stopword_ratio_high": 0.62,
                "sentence_var_low": 2.5,
                "sentence_var_high": 60.0,
                "sentence_kurtosis_low": -1.2,
                "sentence_kurtosis_high": 4.0,
            },
            "domain_profiles": {
                "news": {"decision_threshold": 0.44, "uncertainty_margin": 0.06},
                "social-short": {"decision_threshold": 0.49, "uncertainty_margin": 0.09},
                "finance-business": {"decision_threshold": 0.47, "uncertainty_margin": 0.07},
                "legal-policy": {"decision_threshold": 0.46, "uncertainty_margin": 0.07},
                "science-academic": {"decision_threshold": 0.43, "uncertainty_margin": 0.06},
                "code-doc": {"decision_threshold": 0.46, "uncertainty_margin": 0.05},
                "general": {"decision_threshold": 0.45, "uncertainty_margin": 0.05},
            },
            "length_band_profiles": {
                "short-form": {"decision_threshold": 0.5, "uncertainty_margin": 0.11},
                "standard": {"decision_threshold": 0.45, "uncertainty_margin": 0.08},
                "long-form": {"decision_threshold": 0.43, "uncertainty_margin": 0.06},
            },
        }

        configured_path = settings.text_calibration_profile_path.strip()
        if not configured_path:
            return default_profile

        profile_path = Path(configured_path)
        if not profile_path.is_absolute():
            backend_root = Path(__file__).resolve().parents[3]
            profile_path = (backend_root / profile_path).resolve()
        if not profile_path.exists():
            return default_profile

        try:
            payload = json.loads(profile_path.read_text(encoding="utf-8"))
        except Exception:
            return default_profile

        if not isinstance(payload, dict):
            return default_profile

        merged = {
            **default_profile,
            **payload,
            "weights": {
                **default_profile["weights"],  # type: ignore[index]
                **(payload.get("weights") if isinstance(payload.get("weights"), dict) else {}),
            },
            "ranges": {
                **default_profile["ranges"],  # type: ignore[index]
                **(payload.get("ranges") if isinstance(payload.get("ranges"), dict) else {}),
            },
            "domain_profiles": {
                **(
                    default_profile["domain_profiles"]  # type: ignore[index]
                    if isinstance(default_profile.get("domain_profiles"), dict)
                    else {}
                ),
                **(
                    payload.get("domain_profiles")
                    if isinstance(payload.get("domain_profiles"), dict)
                    else {}
                ),
            },
            "length_band_profiles": {
                **(
                    default_profile["length_band_profiles"]  # type: ignore[index]
                    if isinstance(default_profile.get("length_band_profiles"), dict)
                    else {}
                ),
                **(
                    payload.get("length_band_profiles")
                    if isinstance(payload.get("length_band_profiles"), dict)
                    else {}
                ),
            },
        }
        return merged

    def _normalize_domain(self, value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        normalized = value.strip().lower().replace("_", "-")
        aliases = {
            "code": "code-doc",
            "code-doc": "code-doc",
            "codedoc": "code-doc",
            "academic": "science-academic",
            "education": "science-academic",
            "science": "science-academic",
            "science-academic": "science-academic",
            "legal": "legal-policy",
            "legal-policy": "legal-policy",
            "news": "news",
            "social": "social-short",
            "social-short": "social-short",
            "marketing": "finance-business",
            "finance": "finance-business",
            "finance-business": "finance-business",
            "general": "general",
            "health": "general",
        }
        return aliases.get(normalized, "general")

    def _infer_domain(self, text: str) -> str:
        words = self._tokenize(text)
        sentences = self._split_sentences(text)
        inferred_domain, _confidence, _input_type = self._infer_domain_with_confidence(
            text,
            text,
            words,
            sentences,
        )
        return inferred_domain

    def _length_band_for_words(self, word_count: int) -> str:
        if word_count < 120:
            return "short-form"
        if word_count >= 400:
            return "long-form"
        return "standard"

    def _resolve_calibration_profile(
        self, domain: Optional[str], *, word_count: Optional[int] = None
    ) -> tuple[dict[str, object], str, str]:
        normalized_domain = self._normalize_domain(domain) or "general"
        length_band = self._length_band_for_words(int(word_count or 0))
        domain_applied = False
        base_profile = {
            **self._calibration_profile,
            "weights": dict(self._calibration_profile.get("weights", {})),  # type: ignore[arg-type]
            "ranges": dict(self._calibration_profile.get("ranges", {})),  # type: ignore[arg-type]
        }

        raw_domain_profiles = self._calibration_profile.get("domain_profiles", {})
        if isinstance(raw_domain_profiles, dict):
            domain_override = raw_domain_profiles.get(normalized_domain)
            if isinstance(domain_override, dict):
                merged = {
                    **base_profile,
                    **domain_override,
                    "weights": {
                        **base_profile["weights"],  # type: ignore[index]
                        **(
                            domain_override.get("weights")
                            if isinstance(domain_override.get("weights"), dict)
                            else {}
                        ),
                    },
                    "ranges": {
                        **base_profile["ranges"],  # type: ignore[index]
                        **(
                            domain_override.get("ranges")
                            if isinstance(domain_override.get("ranges"), dict)
                            else {}
                        ),
                    },
                }
                base_profile = merged
                domain_applied = True

        raw_length_profiles = self._calibration_profile.get("length_band_profiles", {})
        if isinstance(raw_length_profiles, dict):
            band_override = raw_length_profiles.get(length_band)
            if isinstance(band_override, dict):
                merged = {
                    **base_profile,
                    "weights": {
                        **base_profile["weights"],  # type: ignore[index]
                        **(
                            band_override.get("weights")
                            if isinstance(band_override.get("weights"), dict)
                            else {}
                        ),
                    },
                    "ranges": {
                        **base_profile["ranges"],  # type: ignore[index]
                        **(
                            band_override.get("ranges")
                            if isinstance(band_override.get("ranges"), dict)
                            else {}
                        ),
                    },
                }
                if not domain_applied or normalized_domain == "general":
                    merged.update(band_override)
                else:
                    if "uncertainty_margin" in band_override:
                        merged["uncertainty_margin"] = max(
                            float(base_profile["uncertainty_margin"]),
                            float(band_override["uncertainty_margin"]),
                        )
                base_profile = merged

        return base_profile, normalized_domain, length_band

    def _profile_version_label(self, profile: dict[str, object], domain: str) -> str:
        base_version = str(profile.get("version", "default-v2-tristate"))
        return f"{base_version}:{domain}"

    def _normalize_inverse(self, value: float, *, low: float, high: float) -> float:
        if high <= low:
            return 0.5
        clipped = float(np.clip(value, low, high))
        return float(np.clip((high - clipped) / (high - low), 0.0, 1.0))

    def _normalize_direct(self, value: float, *, low: float, high: float) -> float:
        if high <= low:
            return 0.5
        clipped = float(np.clip(value, low, high))
        return float(np.clip((clipped - low) / (high - low), 0.0, 1.0))

    def _apply_calibration_map(self, score: float, profile: dict[str, object]) -> float:
        clipped_score = float(np.clip(score, 0.0, 1.0))
        calibration_map = profile.get("calibration_map")
        if not isinstance(calibration_map, dict):
            return clipped_score
        if str(calibration_map.get("type", "")).lower() != "platt":
            return clipped_score

        try:
            coef = float(calibration_map["coef"])
            intercept = float(calibration_map["intercept"])
        except (KeyError, TypeError, ValueError):
            return clipped_score

        logit = float(np.clip((coef * clipped_score) + intercept, -60.0, 60.0))
        calibrated = 1.0 / (1.0 + math.exp(-logit))
        return float(np.clip(calibrated, 0.0, 1.0))

    def _calculate_rewrite_sensitivity(self, text: str, sentences: list[str]) -> float:
        lowered = text.lower()
        markers = self._expert_bundle.get("rewrite_markers", [])
        marker_hits = 0
        if isinstance(markers, list):
            marker_hits = sum(1 for marker in markers if str(marker).strip().lower() in lowered)

        pairwise_overlap: list[float] = []
        for left, right in zip(sentences, sentences[1:]):
            left_tokens = set(self._tokenize(left))
            right_tokens = set(self._tokenize(right))
            if not left_tokens or not right_tokens:
                continue
            overlap = len(left_tokens & right_tokens) / max(len(left_tokens | right_tokens), 1)
            pairwise_overlap.append(overlap)
        overlap_score = float(np.mean(pairwise_overlap)) if pairwise_overlap else 0.0
        raw = min(1.0, (marker_hits * 0.22) + (overlap_score * 0.85))
        return round(raw, 3)

    def _calculate_hard_negative_similarity(self, text: str) -> float:
        lowered = text.lower()
        markers = self._expert_bundle.get("hard_negative_markers", [])
        if not isinstance(markers, list) or not markers:
            return 0.0
        hits = sum(1 for marker in markers if str(marker).strip().lower() in lowered)
        lexical_markers = (
            (" i ", 0.08),
            (" yesterday ", 0.08),
            (" meeting ", 0.08),
            (" note ", 0.05),
            (" rewrote ", 0.12),
        )
        lexical_boost = sum(weight for marker, weight in lexical_markers if marker in f" {lowered} ")
        raw = min(1.0, (hits / max(len(markers), 1)) * 2.4 + lexical_boost)
        return round(raw, 3)

    def _generate_explanation(
        self,
        *,
        decision_band: str,
        confidence: float,
        perplexity: float,
        burstiness: float,
        distance_to_threshold: float,
        uncertainty_reason: Optional[str],
        ml_score: Optional[float] = None,
        calibration_domain: str = "general",
        uncertainty_flags: Optional[list[str]] = None,
        length_band: str = "standard",
    ) -> str:
        """Generate human-readable explanation."""
        if decision_band == "ai":
            verdict = "likely AI-generated"
        elif decision_band == "human":
            verdict = "likely human-written"
        else:
            verdict = "uncertain"

        conf_level = "high" if confidence > 0.75 else "moderate" if confidence > 0.5 else "low"
        reasons: list[str] = []

        if uncertainty_reason:
            reasons.append(uncertainty_reason)

        if ml_score is not None:
            if ml_score > 0.7:
                reasons.append("ML classifier indicates AI patterns")
            elif ml_score < 0.3:
                reasons.append("ML classifier indicates human writing")

        if perplexity < 25:
            reasons.append("predictable word patterns")
        if burstiness < 0.4:
            reasons.append("uniform sentence structure")
        if perplexity > 40:
            reasons.append("varied and unpredictable text")
        if burstiness > 0.6:
            reasons.append("natural variation in sentence complexity")
        if uncertainty_flags:
            reasons.append("conservative safeguards: " + ", ".join(uncertainty_flags))

        reason_text = ", ".join(reasons) if reasons else "mixed signals"
        return (
            f"Text appears {verdict} ({conf_level} confidence). "
            f"Domain profile: {calibration_domain}. Length band: {length_band}. "
            f"Distance to threshold: {distance_to_threshold:.3f}. "
            f"Key indicators: {reason_text}."
        )
