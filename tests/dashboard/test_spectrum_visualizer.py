"""
Tests for dashboard/spectrum_visualizer.py
"""

import numpy as np
import pytest
from dashboard.spectrum_visualizer import (
    generate_acoustic_signal,
    compute_spectral_features,
    create_spectrogram_figure,
)


def test_generate_acoustic_signal_presets():
    presets = ["chainsaw", "gunshot", "fire", "bird", "rain", "wind", "ambient", "unknown"]
    for preset in presets:
        sig = generate_acoustic_signal(preset, mic_level=600, duration=1.0, sr=16000)
        assert isinstance(sig, np.ndarray)
        assert len(sig) == 16000
        assert np.max(np.abs(sig)) <= 1.0


def test_compute_spectral_features():
    sr = 16000
    t = np.linspace(0, 1.0, sr, endpoint=False)
    # 440 Hz pure tone
    sig = np.sin(2 * np.pi * 440 * t).astype(np.float32)

    features = compute_spectral_features(sig, sr=sr)
    assert "peak_frequency" in features
    assert "spectral_centroid" in features
    assert "spectral_rolloff" in features
    assert "rms_dbfs" in features
    assert "spectral_flatness" in features
    assert "band_energies" in features

    assert len(features["band_energies"]) == 32
    # 440 Hz should be near 440
    assert abs(features["peak_frequency"] - 440) < 5.0
    assert features["rms_dbfs"] < 0.0


def test_create_spectrogram_figure():
    sig = generate_acoustic_signal("chainsaw", duration=1.0, sr=16000)
    fig = create_spectrogram_figure(sig, sr=16000, title="Test Spectrogram")
    assert fig is not None
    assert len(fig.data) > 0
    assert fig.data[0].type == "heatmap"
