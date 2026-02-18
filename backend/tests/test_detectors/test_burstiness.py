from app.detection.text.detector import TextDetector


def test_burstiness_returns_normalized_score():
    detector = TextDetector()
    sentences = ["One sentence with seven words.", "Another sentence with eight words here."]

    score = detector._calculate_burstiness(sentences)

    assert 0.0 <= score <= 1.0


def test_burstiness_short_input_returns_default():
    detector = TextDetector()

    score = detector._calculate_burstiness(["Only one sentence."])

    assert score == 0.5


def test_burstiness_differs_for_uniform_vs_varied_sentences():
    detector = TextDetector()

    uniform = [
        "A simple sentence with five words.",
        "Another phrase with five words.",
        "Third short line with five words.",
    ]
    varied = [
        "Tiny sentence.",
        "This sentence is much longer and includes many more words for variance.",
        "Medium length sentence with moderate variety.",
    ]

    uniform_score = detector._calculate_burstiness(uniform)
    varied_score = detector._calculate_burstiness(varied)

    # This metric increases with sentence-length variation.
    assert varied_score >= uniform_score
