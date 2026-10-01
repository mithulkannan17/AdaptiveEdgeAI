"""
Conservative adaptive stationary-background suppression and noise validation for AuraForest.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Literal, Optional
import numpy as np
import torch


@dataclass
class NoiseRobustnessResult:
    """Result of noise robustness processing."""

    enabled: bool
    applied: bool
    input_rms: float
    output_rms: float
    estimated_noise_rms: float
    estimated_snr_db: float | None
    attenuation_db: float
    reason: str

    def to_dict(self) -> dict:
        return {
            "enabled": bool(self.enabled),
            "applied": bool(self.applied),
            "input_rms": float(self.input_rms),
            "output_rms": float(self.output_rms),
            "estimated_noise_rms": float(self.estimated_noise_rms),
            "estimated_snr_db": (
                None if self.estimated_snr_db is None else float(self.estimated_snr_db)
            ),
            "attenuation_db": float(self.attenuation_db),
            "reason": str(self.reason),
        }


class NoiseRobustnessEngine:
    """
    Adaptive spectral subtraction with a gain floor to protect target events.

    AuraForest monitors natural environmental soundscapes. The denoiser is
    calibrated to suppress stationary background noise while preserving transient
    and harmonic cues from wildlife, chainsaws, human activity, and environmental hazards.
    """

    def __init__(
        self,
        enabled: bool = True,
        n_fft: int = 1024,
        hop_length: int = 256,
        noise_percentile: float = 20.0,
        subtraction_strength: float = 0.85,
        gain_floor: float = 0.25,
        activation_noise_ratio: float = 0.10,
        min_rms: float = 0.0015,
    ):
        self.enabled = bool(enabled)
        self.n_fft = int(n_fft)
        self.hop_length = int(hop_length)
        self.noise_percentile = float(noise_percentile)
        self.subtraction_strength = float(subtraction_strength)
        self.gain_floor = float(gain_floor)
        self.activation_noise_ratio = float(activation_noise_ratio)
        self.min_rms = float(min_rms)
        self._window = torch.hann_window(self.n_fft)

    @staticmethod
    def _rms(x: np.ndarray) -> float:
        x = np.asarray(x, dtype=np.float32).reshape(-1)
        return float(np.sqrt(np.mean(np.square(x), dtype=np.float64))) if x.size else 0.0

    @staticmethod
    def _snr_db(signal_rms: float, noise_rms: float) -> float | None:
        if signal_rms <= 0 or noise_rms <= 0:
            return None
        return float(20 * math.log10(max(signal_rms / noise_rms, 1e-12)))

    def _identity(self, x: np.ndarray, reason: str) -> tuple[np.ndarray, NoiseRobustnessResult]:
        rms = self._rms(x)
        return (
            x.copy(),
            NoiseRobustnessResult(
                enabled=self.enabled,
                applied=False,
                input_rms=rms,
                output_rms=rms,
                estimated_noise_rms=0.0,
                estimated_snr_db=None,
                attenuation_db=0.0,
                reason=reason,
            ),
        )

    def process(
        self,
        waveform: np.ndarray,
        sample_rate: int = 16000,
    ) -> tuple[np.ndarray, NoiseRobustnessResult]:
        """
        Suppress stationary acoustic noise in waveform.

        Returns:
            (denoised_waveform, NoiseRobustnessResult)
        """
        x = np.asarray(waveform, dtype=np.float32).reshape(-1)
        if x.size == 0:
            return self._identity(x, "empty_audio")
        if not self.enabled:
            return self._identity(x, "disabled")

        input_rms = self._rms(x)
        if input_rms < self.min_rms:
            return self._identity(x, "signal_below_activity_threshold")

        if x.size < max(self.n_fft * 3, int(sample_rate * 0.25)):
            return self._identity(x, "audio_too_short_for_noise_estimation")

        t = torch.from_numpy(x)
        w = self._window.to(dtype=t.dtype)

        with torch.no_grad():
            spec = torch.stft(
                t,
                n_fft=self.n_fft,
                hop_length=self.hop_length,
                win_length=self.n_fft,
                window=w,
                center=True,
                return_complex=True,
            )
            mag = spec.abs()
            floor = torch.quantile(mag, self.noise_percentile / 100.0, dim=-1, keepdim=True)
            noise_mag = torch.minimum(mag, floor)
            noise_spec = noise_mag * torch.exp(1j * torch.angle(spec))
            nw = torch.istft(
                noise_spec,
                n_fft=self.n_fft,
                hop_length=self.hop_length,
                win_length=self.n_fft,
                window=w,
                center=True,
                length=x.size,
            )
            noise_rms = self._rms(nw.numpy())
            ratio = noise_rms / max(input_rms, 1e-12)

            if ratio < self.activation_noise_ratio:
                return x.copy(), NoiseRobustnessResult(
                    enabled=True,
                    applied=False,
                    input_rms=input_rms,
                    output_rms=input_rms,
                    estimated_noise_rms=noise_rms,
                    estimated_snr_db=self._snr_db(input_rms, noise_rms),
                    attenuation_db=0.0,
                    reason="stationary_noise_below_activation_threshold",
                )

            residual = torch.relu(mag - self.subtraction_strength * floor)
            gain = torch.clamp(residual / mag.clamp_min(1e-8), min=self.gain_floor, max=1.0)
            clean = torch.istft(
                spec * gain,
                n_fft=self.n_fft,
                hop_length=self.hop_length,
                win_length=self.n_fft,
                window=w,
                center=True,
                length=x.size,
            )

        y = clean.numpy().astype(np.float32, copy=False)
        peak = float(np.max(np.abs(y))) if y.size else 0.0
        if peak > 1.0:
            y = y / peak

        out_rms = self._rms(y)
        att = float(20 * math.log10(max(out_rms, 1e-12) / max(input_rms, 1e-12)))

        return y, NoiseRobustnessResult(
            enabled=True,
            applied=True,
            input_rms=input_rms,
            output_rms=out_rms,
            estimated_noise_rms=noise_rms,
            estimated_snr_db=self._snr_db(input_rms, noise_rms),
            attenuation_db=att,
            reason="stationary_background_suppressed",
        )

    def get_config(self) -> dict:
        return {
            "enabled": self.enabled,
            "n_fft": self.n_fft,
            "hop_length": self.hop_length,
            "noise_percentile": self.noise_percentile,
            "subtraction_strength": self.subtraction_strength,
            "gain_floor": self.gain_floor,
            "activation_noise_ratio": self.activation_noise_ratio,
            "min_rms": self.min_rms,
        }


class NoiseSynthesizer:
    """
    Synthesizes calibrated environmental noise types and mixes them
    with clean audio at specified SNR (dB) levels for noise robustness validation.
    """

    NOISE_TYPES = ("wind", "rain", "vehicle", "human_speech", "machinery")

    @staticmethod
    def generate_noise(
        noise_type: Literal["wind", "rain", "vehicle", "human_speech", "machinery"],
        num_samples: int,
        sample_rate: int = 16000,
        seed: Optional[int] = None,
    ) -> np.ndarray:
        """
        Generate synthetic acoustic noise for experimental evaluation.

        Parameters
        ----------
        noise_type:
            'wind' | 'rain' | 'vehicle' | 'human_speech' | 'machinery'
        num_samples:
            Length of the synthesized noise in audio frames.
        sample_rate:
            Audio sample rate in Hz (default 16000).
        seed:
            Optional random seed for reproducible benchmark results.
        """
        rng = np.random.RandomState(seed)
        t = np.linspace(0, num_samples / sample_rate, num_samples, endpoint=False, dtype=np.float32)

        if noise_type == "wind":
            # Low-frequency brownian/pink noise with slow gust amplitude modulation (0.2 - 0.8 Hz)
            white = rng.randn(num_samples).astype(np.float32)
            # Integration for 1/f^2 spectrum (brown noise)
            brown = np.cumsum(white).astype(np.float32)
            brown = brown - np.mean(brown)
            gust_mod = 0.5 + 0.5 * np.sin(2 * np.pi * 0.35 * t + rng.uniform(0, 2 * np.pi))
            noise = brown * gust_mod

        elif noise_type == "rain":
            # Broadband Gaussian noise with high-frequency emphasis (800 Hz - 7000 Hz)
            white = rng.randn(num_samples).astype(np.float32)
            # Rain droplet transient pops
            num_droplets = max(10, int(num_samples / 400))
            pop_indices = rng.randint(0, num_samples, size=num_droplets)
            white[pop_indices] += rng.uniform(2.0, 5.0, size=num_droplets)
            # Gentle fluctuation
            mod = 0.8 + 0.2 * np.sin(2 * np.pi * 1.5 * t)
            noise = white * mod

        elif noise_type == "vehicle":
            # Low-frequency engine harmonics (45Hz, 90Hz, 135Hz, 180Hz) + tyre rumble
            engine = (
                0.5 * np.sin(2 * np.pi * 45 * t)
                + 0.3 * np.sin(2 * np.pi * 90 * t)
                + 0.2 * np.sin(2 * np.pi * 135 * t)
                + 0.15 * np.sin(2 * np.pi * 180 * t)
            )
            tyre_noise = rng.randn(num_samples).astype(np.float32) * 0.3
            noise = engine + tyre_noise

        elif noise_type == "human_speech":
            # Multi-speaker background babble: multi-formant modulation (500Hz, 1500Hz, 2500Hz)
            babble = np.zeros(num_samples, dtype=np.float32)
            for freq in (450.0, 800.0, 1400.0, 2200.0, 2900.0):
                syllable_rate = rng.uniform(3.0, 5.5)
                amp_mod = 0.5 + 0.5 * np.sin(2 * np.pi * syllable_rate * t + rng.uniform(0, 2 * np.pi))
                carrier = np.sin(2 * np.pi * freq * t)
                babble += carrier * amp_mod
            noise = babble + 0.2 * rng.randn(num_samples).astype(np.float32)

        elif noise_type == "machinery":
            # Mechanical continuous hum (50/60 Hz and harmonics) + metal vibration
            hum = (
                0.6 * np.sin(2 * np.pi * 60 * t)
                + 0.4 * np.sin(2 * np.pi * 120 * t)
                + 0.25 * np.sin(2 * np.pi * 240 * t)
                + 0.15 * np.sin(2 * np.pi * 480 * t)
                + 0.1 * np.sin(2 * np.pi * 1200 * t)
            )
            noise = hum + 0.2 * rng.randn(num_samples).astype(np.float32)

        else:
            raise ValueError(f"Unsupported noise_type '{noise_type}'. Must be one of {NoiseSynthesizer.NOISE_TYPES}")

        # Normalize noise to unit RMS
        rms = float(np.sqrt(np.mean(np.square(noise), dtype=np.float64)))
        if rms > 1e-8:
            noise = noise / rms

        return noise.astype(np.float32)

    @staticmethod
    def mix_at_snr(
        clean_waveform: np.ndarray,
        noise_waveform: np.ndarray,
        snr_db: float,
    ) -> np.ndarray:
        """
        Mix clean audio with noise to produce an exact target SNR (in dB).

        Formula:
            SNR_dB = 20 * log10(RMS_clean / RMS_noise)
            RMS_noise_target = RMS_clean / (10 ** (SNR_dB / 20))
        """
        clean = np.asarray(clean_waveform, dtype=np.float32).reshape(-1)
        noise = np.asarray(noise_waveform, dtype=np.float32).reshape(-1)

        if clean.size != noise.size:
            if noise.size < clean.size:
                repeats = int(np.ceil(clean.size / max(1, noise.size)))
                noise = np.tile(noise, repeats)[: clean.size]
            else:
                noise = noise[: clean.size]

        clean_rms = float(np.sqrt(np.mean(np.square(clean), dtype=np.float64)))
        if clean_rms <= 1e-8:
            return clean + noise

        noise_rms = float(np.sqrt(np.mean(np.square(noise), dtype=np.float64)))
        if noise_rms <= 1e-8:
            return clean

        target_noise_rms = clean_rms / (10.0 ** (snr_db / 20.0))
        scaled_noise = noise * (target_noise_rms / noise_rms)

        noisy = clean + scaled_noise

        # Soft limit / normalization if clipping occurs
        peak = float(np.max(np.abs(noisy)))
        if peak > 1.0:
            noisy = noisy / peak

        return noisy.astype(np.float32)

