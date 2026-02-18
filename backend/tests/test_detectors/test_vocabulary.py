from app.detection.text.detector import TextDetector


def test_vocabulary_returns_normalized_score():
    detector = TextDetector()
    words = detector._tokenize("This is a reasonable sample with repeated repeated words.")

    score = detector._calculate_vocabulary_richness(words)

    assert 0.0 <= score <= 1.0


def test_vocabulary_short_input_returns_default():
    detector = TextDetector()
    words = detector._tokenize("Only a few words.")

    score = detector._calculate_vocabulary_richness(words)

    assert score == 0.5


def test_vocabulary_richness_higher_for_more_diverse_text():
    detector = TextDetector()

    repetitive_words = detector._tokenize("word " * 80)
    diverse_words = detector._tokenize(" ".join(f"word{i}" for i in range(80)))

    repetitive_score = detector._calculate_vocabulary_richness(repetitive_words)
    diverse_score = detector._calculate_vocabulary_richness(diverse_words)

    assert diverse_score >= repetitive_score
