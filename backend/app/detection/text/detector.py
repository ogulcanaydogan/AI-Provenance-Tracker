"""Text AI detection engine with ML-based classification."""

import json
import math
import re
import time
from collections import Counter
from pathlib import Path
from typing import Optional

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
from app.models.detection import AIModel, TextAnalysis, TextDetectionResponse


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
        inferred_domain = self._normalize_domain(domain) or self._infer_domain(cleaned_text)
        calibration_profile, calibration_key = self._resolve_calibration_profile(inferred_domain)
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

        ml_score = self._get_ml_prediction(text) if self.model_loaded else None

        (
            is_ai,
            confidence,
            model_pred,
            decision_band,
            distance_to_threshold,
            uncertainty_reason,
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
        )

        explanation = self._generate_explanation(
            decision_band=decision_band,
            confidence=confidence,
            perplexity=perplexity,
            burstiness=burstiness,
            distance_to_threshold=distance_to_threshold,
            uncertainty_reason=uncertainty_reason,
            ml_score=ml_score,
            calibration_domain=calibration_key,
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
                perplexity=perplexity,
                burstiness=burstiness,
                vocabulary_richness=vocab_richness,
                average_sentence_length=avg_sentence_length,
                repetition_score=repetition,
                punctuation_diversity=punctuation_diversity,
                stopword_ratio=stopword_ratio,
                sentence_length_variance=sentence_variance,
                sentence_length_kurtosis=sentence_kurtosis,
            ),
            explanation=explanation,
            processing_time_ms=processing_time,
            model_version=f"text-detector:{self._loaded_model_id}",
            calibration_version=self._profile_version_label(calibration_profile, calibration_key),
        )

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
        )

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
            "decision_threshold": 0.5,
            "uncertainty_margin": 0.08,
            "short_text_min_words": 80,
            "short_text_min_sentences": 3,
            "ml_weight": 0.32,
            "weights": {
                "perplexity": 0.2,
                "burstiness": 0.18,
                "vocabulary_richness": 0.12,
                "repetition": 0.16,
                "sentence_length": 0.1,
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
                "news": {"decision_threshold": 0.45, "uncertainty_margin": 0.05},
                "social": {"decision_threshold": 0.47, "uncertainty_margin": 0.06},
                "marketing": {"decision_threshold": 0.49, "uncertainty_margin": 0.06},
                "academic": {"decision_threshold": 0.43, "uncertainty_margin": 0.05},
                "code-doc": {"decision_threshold": 0.46, "uncertainty_margin": 0.05},
                "general": {"decision_threshold": 0.45, "uncertainty_margin": 0.05},
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
            "academic": "academic",
            "education": "academic",
            "science": "academic",
            "legal": "academic",
            "news": "news",
            "social": "social",
            "marketing": "marketing",
            "general": "general",
            "finance": "general",
            "health": "general",
        }
        return aliases.get(normalized, "general")

    def _infer_domain(self, text: str) -> str:
        lowered = text.lower()

        code_markers = (
            "```",
            "def ",
            "class ",
            "import ",
            "const ",
            "function ",
            "api endpoint",
        )
        if any(marker in lowered for marker in code_markers):
            return "code-doc"

        social_markers = ("#", "@", "rt ", "dm ", "viral", "followers", "thread")
        if any(marker in lowered for marker in social_markers):
            return "social"

        marketing_markers = (
            "cta",
            "conversion",
            "campaign",
            "brand",
            "funnel",
            "audience",
            "roi",
            "click-through",
        )
        if any(marker in lowered for marker in marketing_markers):
            return "marketing"

        academic_markers = ("hypothesis", "methodology", "citation", "peer-reviewed", "dataset")
        if any(marker in lowered for marker in academic_markers):
            return "academic"

        news_markers = ("reported", "breaking", "according to", "official statement")
        if any(marker in lowered for marker in news_markers):
            return "news"

        return "general"

    def _resolve_calibration_profile(self, domain: Optional[str]) -> tuple[dict[str, object], str]:
        normalized_domain = self._normalize_domain(domain) or "general"
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
                return merged, normalized_domain

        return base_profile, "general"

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

        reason_text = ", ".join(reasons) if reasons else "mixed signals"
        return (
            f"Text appears {verdict} ({conf_level} confidence). "
            f"Domain profile: {calibration_domain}. "
            f"Distance to threshold: {distance_to_threshold:.3f}. "
            f"Key indicators: {reason_text}."
        )
