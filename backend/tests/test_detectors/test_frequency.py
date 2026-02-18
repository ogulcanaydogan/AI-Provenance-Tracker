import numpy as np

from app.detection.image.detector import ImageDetector


def test_frequency_score_is_normalized():
    detector = ImageDetector()
    image = np.random.randint(0, 255, (128, 128, 3), dtype=np.uint8)

    score = detector._analyze_frequency_domain(image)

    assert 0.0 <= score <= 1.0


def test_frequency_zero_energy_returns_default():
    detector = ImageDetector()
    image = np.zeros((64, 64, 3), dtype=np.uint8)

    score = detector._analyze_frequency_domain(image)

    assert score == 0.5


def test_frequency_scores_valid_for_different_patterns():
    detector = ImageDetector()

    noise = np.random.randint(0, 255, (128, 128, 3), dtype=np.uint8)
    gradient = np.dstack(
        [np.tile(np.arange(128, dtype=np.uint8), (128, 1)) for _ in range(3)]
    )

    noise_score = detector._analyze_frequency_domain(noise)
    gradient_score = detector._analyze_frequency_domain(gradient)

    assert 0.0 <= noise_score <= 1.0
    assert 0.0 <= gradient_score <= 1.0
