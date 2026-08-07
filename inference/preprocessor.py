"""
Preprocessor

Converts raw audio into a model-ready spectrogram.
"""

from __future__ import annotations

from pathlib import Path

import torch
import torchaudio

from managers.config_manager import ConfigManager


class PreProcessor:
    """
    Audio preprocessing pipeline for inference.
    """

    def __init__(self):

        config = ConfigManager()

        feature_config = config.feature_extraction()

        self.sample_rate = feature_config["sample_rate"]

        self.n_fft = feature_config["n_fft"]

        self.hop_length = feature_config["hop_length"]

        self.n_mels = feature_config["n_mels"]

        self.mel_transform = torchaudio.transforms.MelSpectrogram(

            sample_rate=self.sample_rate,

            n_fft=self.n_fft,

            hop_length=self.hop_length,

            n_mels=self.n_mels,

        )

        self.amplitude_to_db = (

            torchaudio.transforms.AmplitudeToDB()

        )

    def load_audio(

        self,

        file_path: str | Path,

    ) -> torch.Tensor:
        """
        Loads an audio file.
        """

        waveform, sample_rate = torchaudio.load(

            file_path

        )

        # Stereo → Mono
        if waveform.shape[0] > 1:

            waveform = waveform.mean(

                dim=0,

                keepdim=True

            )

        # Resample if necessary
        if sample_rate != self.sample_rate:

            waveform = torchaudio.functional.resample(

                waveform,

                sample_rate,

                self.sample_rate,

            )

        return waveform

    def waveform_to_spectrogram(

        self,

        waveform: torch.Tensor,

    ) -> torch.Tensor:
        """
        Converts waveform into a normalized
        log-mel spectrogram.
        """

        spectrogram = self.mel_transform(

            waveform

        )

        spectrogram = self.amplitude_to_db(

            spectrogram

        )

        # Same normalization used during training
        spectrogram = (

            spectrogram

            - spectrogram.mean()

        ) / (

            spectrogram.std()

            + 1e-8

        )

        return spectrogram

    def preprocess(

        self,

        file_path: str | Path,

    ) -> torch.Tensor:
        """
        Complete preprocessing pipeline.
        """

        waveform = self.load_audio(

            file_path

        )

        spectrogram = self.waveform_to_spectrogram(

            waveform

        )

        return spectrogram