"""
Tests for NoiseRobustnessEngine and NoiseSynthesizer.
"""

import numpy as np
import pytest
import torch

from edge.noise_robustness import (
    NoiseRobustnessEngine,
    NoiseSynthesizer,
    NoiseRobustnessResult,
)


class TestNoiseSynthesizer:

    @pytest.mark.parametrize("noise_type", ["wind", "rain", "vehicle", "human_speech", "machinery"])
    def test_noise_generation(self, noise_type):
        num_samples = 16000
        noise = NoiseSynthesizer.generate_noise(noise_type, num_samples, sample_rate=16000, seed=123)

        assert isinstance(noise, np.ndarray)
        assert noise.shape == (num_samples,)
        assert np.isfinite(noise).all()
        # Verify unit RMS normalization
        rms = np.sqrt(np.mean(np.square(noise)))
        assert np.isclose(rms, 1.0, atol=0.1)

    def test_invalid_noise_type(self):
        with pytest.raises(ValueError):
            NoiseSynthesizer.generate_noise("invalid_noise", 1000)

    def test_mix_at_snr(self):
        # Create pure 440Hz tone
        t = np.linspace(0, 1.0, 16000, endpoint=False, dtype=np.float32)
        clean = 0.5 * np.sin(2 * np.pi * 440 * t)
        noise = NoiseSynthesizer.generate_noise("wind", 16000, seed=42)

        target_snr_db = 10.0
        mixed = NoiseSynthesizer.mix_at_snr(clean, noise, snr_db=target_snr_db)

        assert mixed.shape == clean.shape
        assert np.isfinite(mixed).all()

        clean_rms = np.sqrt(np.mean(np.square(clean)))
        diff = mixed - clean
        diff_rms = np.sqrt(np.mean(np.square(diff)))
        measured_snr = 20 * np.log10(clean_rms / max(diff_rms, 1e-12))

        # Check measured SNR is within 1 dB of target
        assert np.isclose(measured_snr, target_snr_db, atol=1.0)


class TestNoiseRobustnessEngine:

    def test_engine_initialization(self):
        engine = NoiseRobustnessEngine()
        cfg = engine.get_config()
        assert cfg["enabled"] is True
        assert cfg["subtraction_strength"] > 0
        assert cfg["gain_floor"] > 0

    def test_clean_audio_preservation(self):
        engine = NoiseRobustnessEngine()
        t = np.linspace(0, 1.0, 16000, endpoint=False, dtype=np.float32)
        clean = 0.6 * np.sin(2 * np.pi * 500 * t)

        out, result = engine.process(clean, sample_rate=16000)

        assert isinstance(result, NoiseRobustnessResult)
        assert out.shape == clean.shape
        assert np.isfinite(out).all()
        assert result.output_rms > 0.0

    def test_stationary_noise_suppression(self):
        engine = NoiseRobustnessEngine(
            subtraction_strength=0.85,
            gain_floor=0.20,
        )
        t = np.linspace(0, 2.0, 32000, endpoint=False, dtype=np.float32)
        # Signal: tone
        clean = 0.4 * np.sin(2 * np.pi * 600 * t)
        # Noise: persistent machinery hum
        noise = NoiseSynthesizer.generate_noise("machinery", 32000, seed=7)
        noisy = NoiseSynthesizer.mix_at_snr(clean, noise, snr_db=5.0)

        out, result = engine.process(noisy, sample_rate=16000)

        assert result.applied is True
        assert result.attenuation_db < 0.0  # background power reduced
        assert out.shape == noisy.shape

    def test_empty_audio_handling(self):
        engine = NoiseRobustnessEngine()
        empty = np.array([], dtype=np.float32)
        out, result = engine.process(empty)
        assert out.size == 0
        assert result.applied is False
        assert result.reason == "empty_audio"

    def test_short_audio_handling(self):
        engine = NoiseRobustnessEngine()
        short_clip = np.random.randn(100).astype(np.float32)
        out, result = engine.process(short_clip)
        assert result.applied is False
        assert result.reason == "audio_too_short_for_noise_estimation"

    def test_result_to_dict(self):
        engine = NoiseRobustnessEngine()
        t = np.linspace(0, 1.0, 16000, endpoint=False, dtype=np.float32)
        signal = 0.3 * np.sin(2 * np.pi * 300 * t)
        _, result = engine.process(signal)
        d = result.to_dict()
        assert isinstance(d, dict)
        assert "enabled" in d
        assert "applied" in d
        assert "attenuation_db" in d
