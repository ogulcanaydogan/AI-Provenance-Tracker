"""Text AI detection engine."""

import math
import re
import time
from collections import Counter
from typing import Optional

import numpy as np

from app.models.detection import (
    AIModel,
    TextAnalysis,
    TextDetectionResponse,
)


class TextDetector:
    """
    Detects AI-generated text using multiple signals.

    Detection methods:
    1. Perplexity analysis - AI text tends to have lower perplexity
    2. Burstiness - AI text has more uniform sentence structure
    3. Vocabulary analysis - Word choice patterns
    4. Structural analysis - Paragraph and sentence patterns

    In production, this would use fine-tuned transformer models.
    This MVP uses statistical heuristics as a foundation.
    """

    def __init__(self) -> None:
        """Initialize the text detector."""
        # In production, load ML models here
        self.model_loaded = False

    async def detect(self, text: str) -> TextDetectionResponse:
        """
        Analyze text and determine if it's AI-generated.

        Args:
            text: The text to analyze

        Returns:
            TextDetectionResponse with detection results
        """
        start_time = time.time()

        # Clean and prepare text
        cleaned_text = self._preprocess_text(text)
        sentences = self._split_sentences(cleaned_text)
        words = self._tokenize(cleaned_text)

        # Calculate detection signals
        perplexity = self._calculate_perplexity(cleaned_text, words)
        burstiness = self._calculate_burstiness(sentences)
        vocab_richness = self._calculate_vocabulary_richness(words)
        avg_sentence_length = self._calculate_avg_sentence_length(sentences)
        repetition = self._calculate_repetition_score(cleaned_text)

        # Combine signals into final prediction
        is_ai, confidence, model_pred = self._make_prediction(
            perplexity=perplexity,
            burstiness=burstiness,
            vocab_richness=vocab_richness,
            avg_sentence_length=avg_sentence_length,
            repetition=repetition,
        )

        # Generate explanation
        explanation = self._generate_explanation(
            is_ai=is_ai,
            confidence=confidence,
            perplexity=perplexity,
            burstiness=burstiness,
        )

        processing_time = (time.time() - start_time) * 1000

        return TextDetectionResponse(
            is_ai_generated=is_ai,
            confidence=confidence,
            model_prediction=model_pred,
            analysis=TextAnalysis(
                perplexity=perplexity,
                burstiness=burstiness,
                vocabulary_richness=vocab_richness,
                average_sentence_length=avg_sentence_length,
                repetition_score=repetition,
            ),
            explanation=explanation,
            processing_time_ms=processing_time,
        )

    def _preprocess_text(self, text: str) -> str:
        """Clean and normalize text."""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters but keep punctuation
        text = re.sub(r'[^\w\s.,!?;:\'"()-]', '', text)
        return text.strip()

    def _split_sentences(self, text: str) -> list[str]:
        """Split text into sentences."""
        # Simple sentence splitting (could use nltk or spacy for better results)
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if s.strip()]

    def _tokenize(self, text: str) -> list[str]:
        """Tokenize text into words."""
        words = re.findall(r'\b\w+\b', text.lower())
        return words

    def _calculate_perplexity(self, text: str, words: list[str]) -> float:
        """
        Calculate pseudo-perplexity score.

        Lower perplexity = more predictable = more likely AI-generated.
        This is a simplified heuristic; production would use actual LM perplexity.
        """
        if len(words) < 10:
            return 50.0  # Not enough data

        # Calculate word frequency distribution entropy as proxy for perplexity
        word_counts = Counter(words)
        total_words = len(words)

        entropy = 0.0
        for count in word_counts.values():
            prob = count / total_words
            entropy -= prob * math.log2(prob)

        # Normalize to a perplexity-like scale (higher entropy = higher perplexity)
        # AI text typically has entropy in the range of 6-8
        # Human text often has higher entropy (more varied)
        perplexity = 2 ** entropy

        return round(perplexity, 2)

    def _calculate_burstiness(self, sentences: list[str]) -> float:
        """
        Calculate burstiness - variation in sentence complexity.

        AI text tends to have more uniform sentence lengths.
        Lower burstiness = more uniform = more likely AI.
        """
        if len(sentences) < 3:
            return 0.5  # Not enough data

        # Calculate sentence lengths
        lengths = [len(s.split()) for s in sentences]

        # Calculate coefficient of variation (std/mean)
        mean_length = np.mean(lengths)
        if mean_length == 0:
            return 0.5

        std_length = np.std(lengths)
        burstiness = std_length / mean_length

        # Normalize to 0-1 range (typical values 0.2-0.8)
        normalized = min(1.0, burstiness / 0.8)

        return round(normalized, 3)

    def _calculate_vocabulary_richness(self, words: list[str]) -> float:
        """
        Calculate vocabulary richness (type-token ratio).

        AI text sometimes has less varied vocabulary.
        """
        if len(words) < 10:
            return 0.5

        unique_words = len(set(words))
        total_words = len(words)

        # Type-token ratio (adjusted for text length)
        # Use root TTR for better comparison across lengths
        richness = unique_words / math.sqrt(total_words)

        # Normalize to roughly 0-1 range
        normalized = min(1.0, richness / 10)

        return round(normalized, 3)

    def _calculate_avg_sentence_length(self, sentences: list[str]) -> float:
        """Calculate average sentence length in words."""
        if not sentences:
            return 0.0

        lengths = [len(s.split()) for s in sentences]
        return round(np.mean(lengths), 1)

    def _calculate_repetition_score(self, text: str) -> float:
        """
        Detect phrase repetition patterns.

        AI text sometimes has repetitive phrase patterns.
        """
        # Find repeated 3-grams
        words = text.lower().split()
        if len(words) < 10:
            return 0.0

        trigrams = [' '.join(words[i:i+3]) for i in range(len(words)-2)]
        trigram_counts = Counter(trigrams)

        # Count repeated trigrams
        repeated = sum(1 for count in trigram_counts.values() if count > 1)
        total = len(trigrams)

        if total == 0:
            return 0.0

        repetition_rate = repeated / total
        return round(min(1.0, repetition_rate * 10), 3)  # Scale up for sensitivity

    def _make_prediction(
        self,
        perplexity: float,
        burstiness: float,
        vocab_richness: float,
        avg_sentence_length: float,
        repetition: float,
    ) -> tuple[bool, float, Optional[AIModel]]:
        """
        Combine signals to make final prediction.

        This is a weighted heuristic; production would use an ML model.
        """
        # Define thresholds (these would be learned from data in production)
        signals = []

        # Low perplexity suggests AI (but not too low)
        if 5 < perplexity < 30:
            signals.append(0.7)  # Likely AI
        elif perplexity < 5:
            signals.append(0.5)  # Very short/simple text
        else:
            signals.append(0.3)  # Likely human

        # Low burstiness suggests AI
        if burstiness < 0.3:
            signals.append(0.8)
        elif burstiness < 0.5:
            signals.append(0.5)
        else:
            signals.append(0.2)

        # Moderate vocabulary richness
        if 0.3 < vocab_richness < 0.6:
            signals.append(0.6)  # AI often in this range
        else:
            signals.append(0.4)

        # High repetition suggests AI
        if repetition > 0.3:
            signals.append(0.7)
        else:
            signals.append(0.3)

        # Weighted average
        weights = [0.35, 0.30, 0.15, 0.20]  # perplexity, burstiness, vocab, repetition
        confidence = sum(s * w for s, w in zip(signals, weights))

        # Determine prediction
        is_ai = confidence > 0.5
        model_pred = AIModel.GPT4 if is_ai else None

        return is_ai, round(confidence, 3), model_pred

    def _generate_explanation(
        self,
        is_ai: bool,
        confidence: float,
        perplexity: float,
        burstiness: float,
    ) -> str:
        """Generate human-readable explanation."""
        verdict = "likely AI-generated" if is_ai else "likely human-written"
        conf_level = "high" if confidence > 0.75 else "moderate" if confidence > 0.5 else "low"

        reasons = []
        if perplexity < 25:
            reasons.append("predictable word patterns")
        if burstiness < 0.4:
            reasons.append("uniform sentence structure")
        if perplexity > 40:
            reasons.append("varied and unpredictable text")
        if burstiness > 0.6:
            reasons.append("natural variation in sentence complexity")

        reason_text = ", ".join(reasons) if reasons else "mixed signals"

        return f"Text appears {verdict} ({conf_level} confidence). Key indicators: {reason_text}."
