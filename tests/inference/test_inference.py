"""
Inference Tests

Tests the production inference interface without
requiring a real audio file.
"""

import numpy as np
import torch

from inference.predictor import Predictor


def test_predictor_initialization():

    checkpoint_path = (
        "models/checkpoints/mobilenet_v3_small/"
        "best_model.pth"
    )

    predictor = Predictor(
        checkpoint_path=checkpoint_path
    )

    assert predictor.model is not None

    assert predictor.device is not None


def test_predict_spectrogram():

    checkpoint_path = (
        "models/checkpoints/mobilenet_v3_small/"
        "best_model.pth"
    )

    predictor = Predictor(
        checkpoint_path=checkpoint_path
    )

    # Model-ready spectrogram:
    # [batch, channels, mel_bins, time]
    spectrogram = np.random.randn(
        1,
        128,
        157
    ).astype(
        np.float32
    )

    result = predictor.predict_spectrogram(
        spectrogram
    )

    assert result is not None

    assert isinstance(
        result.label,
        str
    )

    assert 0.0 <= result.confidence <= 1.0

    assert isinstance(
        result.class_id,
        int
    )

    assert result.inference_time_ms >= 0.0


def test_predictor_accepts_torch_tensor():

    checkpoint_path = (
        "models/checkpoints/mobilenet_v3_small/"
        "best_model.pth"
    )

    predictor = Predictor(
        checkpoint_path=checkpoint_path
    )

    spectrogram = torch.randn(
        1,
        128,
        157
    )

    result = predictor.predict_spectrogram(
        spectrogram
    )

    assert result is not None

    assert result.label is not None


def test_top_k_predictions():

    checkpoint_path = (
        "models/checkpoints/mobilenet_v3_small/"
        "best_model.pth"
    )

    predictor = Predictor(
        checkpoint_path=checkpoint_path
    )

    spectrogram = np.random.randn(
        1,
        128,
        157
    ).astype(
        np.float32
    )

    result = predictor.predict_spectrogram(
        spectrogram,
        top_k=5
    )

    assert len(
        result.top_k
    ) <= 5

    assert len(
        result.top_k
    ) > 0