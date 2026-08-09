"""
PreProcessor

Converts raw audio into the exact model-ready
spectrogram used during training.
"""

from __future__ import annotations

from pathlib import Path

import torch
import torchaudio


class PreProcessor:
    """
    Production audio preprocessing pipeline.

    The preprocessing parameters MUST remain consistent
    with the parameters used during model training.
    """

    def __init__(self):

        # ==================================================
        # Training Feature Configuration
        # ==================================================

        self.sample_rate = 16000

        self.duration = 5

        self.n_fft = 1024

        self.hop_length = 512

        self.n_mels = 128

        # ==================================================
        # Mel Spectrogram
        # ==================================================

        self.mel_transform = (
            torchaudio.transforms.MelSpectrogram(

                sample_rate=self.sample_rate,

                n_fft=self.n_fft,

                hop_length=self.hop_length,

                n_mels=self.n_mels,

            )
        )

        self.amplitude_to_db = (
            torchaudio.transforms.AmplitudeToDB()
        )

    # ======================================================
    # Audio Loading
    # ======================================================

    def load_audio(
        self,
        file_path: str | Path,
    ) -> torch.Tensor:
        """
        Load audio and convert it to mono at 16 kHz.
        """

        file_path = Path(file_path)

        if not file_path.exists():

            raise FileNotFoundError(
                f"Audio file not found: {file_path}"
            )

        waveform, sample_rate = (
            torchaudio.load(file_path)
        )

        # --------------------------------------------------
        # Stereo → Mono
        # --------------------------------------------------

        if waveform.shape[0] > 1:

            waveform = waveform.mean(
                dim=0,
                keepdim=True
            )

        # --------------------------------------------------
        # Resampling
        # --------------------------------------------------

        if sample_rate != self.sample_rate:

            waveform = (
                torchaudio.functional.resample(

                    waveform,

                    sample_rate,

                    self.sample_rate,

                )
            )

        return waveform

    # ======================================================
    # Duration Normalization
    # ======================================================

    def normalize_duration(
        self,
        waveform: torch.Tensor,
    ) -> torch.Tensor:
        """
        Make every input exactly 5 seconds.

        Short audio:
            Zero padded.

        Long audio:
            Center cropped.
        """

        target_samples = int(
            self.sample_rate
            * self.duration
        )

        current_samples = (
            waveform.shape[-1]
        )

        # --------------------------------------------------
        # Already correct
        # --------------------------------------------------

        if current_samples == target_samples:

            return waveform

        # --------------------------------------------------
        # Short audio → Zero Padding
        # --------------------------------------------------

        if current_samples < target_samples:

            padding = (
                target_samples
                - current_samples
            )

            waveform = (
                torch.nn.functional.pad(

                    waveform,

                    (
                        0,
                        padding
                    ),

                )
            )

            return waveform

        # --------------------------------------------------
        # Long audio → Center Crop
        # --------------------------------------------------

        start = (
            current_samples
            - target_samples
        ) // 2

        end = (
            start
            + target_samples
        )

        return waveform[
            :,
            start:end
        ]

    # ======================================================
    # Waveform → Spectrogram
    # ======================================================

    def waveform_to_spectrogram(
        self,
        waveform: torch.Tensor,
    ) -> torch.Tensor:
        """
        Convert waveform into normalized log-mel
        spectrogram.
        """

        spectrogram = (
            self.mel_transform(
                waveform
            )
        )

        spectrogram = (
            self.amplitude_to_db(
                spectrogram
            )
        )

        # --------------------------------------------------
        # Normalization
        # --------------------------------------------------

        mean = spectrogram.mean()

        std = spectrogram.std()

        spectrogram = (

            spectrogram - mean

        ) / (

            std + 1e-8

        )

        return spectrogram

    # ======================================================
    # Complete Pipeline
    # ======================================================

    def preprocess(
        self,
        file_path: str | Path,
    ) -> torch.Tensor:
        """
        Complete:

            Audio
              ↓
            Mono
              ↓
            16 kHz
              ↓
            5 seconds
              ↓
            Mel Spectrogram
              ↓
            Log scale
              ↓
            Normalization
        """

        waveform = self.load_audio(
            file_path
        )

        waveform = self.normalize_duration(
            waveform
        )

        spectrogram = (
            self.waveform_to_spectrogram(
                waveform
            )
        )

        return spectrogram

    # ======================================================
    # Configuration Information
    # ======================================================

    def get_config(self) -> dict:
        """
        Return the active preprocessing configuration.
        """

        return {

            "sample_rate":
                self.sample_rate,

            "duration":
                self.duration,

            "n_fft":
                self.n_fft,

            "hop_length":
                self.hop_length,

            "n_mels":
                self.n_mels,

        }