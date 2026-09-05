"""
AuraForest Audio PreProcessor

Converts raw audio or audio files into the same model-ready
log-mel spectrogram representation used during training.

Training-equivalent pipeline:

    Audio
        ↓
    librosa.load(
        sr=16000,
        mono=True
    )
        ↓
    Exactly 5 seconds
        ├── longer → first 5 seconds
        └── shorter → zero-pad at end
        ↓
    Peak normalization
        ↓
    librosa.feature.melspectrogram
        ├── n_fft=1024
        ├── hop_length=512
        ├── n_mels=128
        ├── fmin=20
        ├── fmax=8000
        └── power=2.0
        ↓
    librosa.power_to_db(
        ref=np.max
    )
        ↓
    Per-spectrogram z-score normalization
        ↓
    Model
"""

from __future__ import annotations

from pathlib import Path

import librosa
import numpy as np
import torch


class PreProcessor:
    """
    Production audio preprocessing pipeline.

    IMPORTANT
    ---------
    This implementation intentionally mirrors the training
    feature-extraction pipeline.

    Training uses:
        librosa.load()
        librosa.feature.melspectrogram()
        librosa.power_to_db()

    Therefore inference uses the same librosa operations.
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        duration: int = 5,
        n_fft: int = 1024,
        hop_length: int = 512,
        n_mels: int = 128,
        fmin: float = 20.0,
        fmax: float = 8000.0,
    ):
        # ==================================================
        # Audio Configuration
        # ==================================================

        self.sample_rate = int(sample_rate)
        self.duration = int(duration)

        if self.sample_rate <= 0:
            raise ValueError(
                "sample_rate must be greater than zero."
            )

        if self.duration <= 0:
            raise ValueError(
                "duration must be greater than zero."
            )

        self.target_length = (
            self.sample_rate * self.duration
        )

        # ==================================================
        # Mel Configuration
        # ==================================================

        self.n_fft = int(n_fft)
        self.hop_length = int(hop_length)
        self.n_mels = int(n_mels)

        self.fmin = float(fmin)
        self.fmax = float(fmax)

        if self.n_fft <= 0:
            raise ValueError(
                "n_fft must be greater than zero."
            )

        if self.hop_length <= 0:
            raise ValueError(
                "hop_length must be greater than zero."
            )

        if self.n_mels <= 0:
            raise ValueError(
                "n_mels must be greater than zero."
            )

        if self.fmin < 0:
            raise ValueError(
                "fmin cannot be negative."
            )

        if self.fmax <= self.fmin:
            raise ValueError(
                "fmax must be greater than fmin."
            )

        if self.fmax > self.sample_rate / 2:
            raise ValueError(
                "fmax cannot exceed the Nyquist frequency."
            )

    # ======================================================
    # Audio Loading
    # ======================================================

    def load_audio(
        self,
        file_path: str | Path,
    ) -> torch.Tensor:
        """
        Load audio using the same method used during training.

        Training reference:

            librosa.load(
                audio_path,
                sr=16000,
                mono=True
            )

        Returns
        -------
        torch.Tensor
            Shape:
                [1, samples]

            Audio is mono and sampled at 16 kHz.
        """

        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(
                f"Audio file not found: {file_path}"
            )

        if not file_path.is_file():
            raise ValueError(
                f"Audio path is not a file: {file_path}"
            )

        try:
            audio, _ = librosa.load(
                file_path,
                sr=self.sample_rate,
                mono=True,
            )

        except Exception as e:
            raise RuntimeError(
                f"Unable to read audio file: {file_path}"
            ) from e

        if audio is None or len(audio) == 0:
            raise RuntimeError(
                f"Audio file is empty: {file_path}"
            )

        audio = np.asarray(
            audio,
            dtype=np.float32,
        )

        if not np.all(
            np.isfinite(audio)
        ):
            raise ValueError(
                f"Audio contains NaN or infinite values: "
                f"{file_path}"
            )

        waveform = torch.from_numpy(
            audio
        ).unsqueeze(0)

        return waveform.float()

    # ======================================================
    # Raw Waveform Validation
    # ======================================================

    def validate_waveform(
        self,
        waveform: torch.Tensor,
    ) -> torch.Tensor:
        """
        Validate raw microphone/audio waveform.

        Accepted shapes:

            [samples]
            [channels, samples]

        Output:

            [1, samples]

        Stereo audio is converted to mono by averaging
        channels, matching the intended mono inference path.
        """

        if not isinstance(
            waveform,
            torch.Tensor,
        ):
            raise TypeError(
                "waveform must be a torch.Tensor."
            )

        if waveform.ndim == 1:

            waveform = waveform.unsqueeze(0)

        elif waveform.ndim != 2:

            raise ValueError(
                "waveform must have shape "
                "[samples] or [channels, samples]."
            )

        if waveform.shape[-1] <= 0:
            raise ValueError(
                "waveform cannot be empty."
            )

        waveform = waveform.float()

        if not torch.isfinite(
            waveform
        ).all():

            raise ValueError(
                "waveform contains NaN or infinite values."
            )

        # --------------------------------------------------
        # Stereo → Mono
        # --------------------------------------------------

        if waveform.shape[0] > 1:

            waveform = waveform.mean(
                dim=0,
                keepdim=True,
            )

        return waveform

    # ======================================================
    # Peak Normalization
    # ======================================================

    def peak_normalize(
        self,
        waveform: torch.Tensor,
    ) -> torch.Tensor:
        """
        Peak-normalize waveform exactly as training does.

        Training:

            peak = np.max(np.abs(audio))

            if peak > 0:
                audio = audio / peak

        Silence remains silence.
        """

        if not isinstance(
            waveform,
            torch.Tensor,
        ):
            raise TypeError(
                "waveform must be a torch.Tensor."
            )

        peak = torch.max(
            torch.abs(waveform)
        )

        if float(peak.item()) > 0.0:

            waveform = (
                waveform / peak
            )

        return waveform.float()

    # ======================================================
    # Resampling
    # ======================================================

    def resample_waveform(
        self,
        waveform: torch.Tensor,
        sample_rate: int,
    ) -> torch.Tensor:
        """
        Resample a waveform to the production sample rate.

        For file-based inference, librosa.load() already performs
        resampling.

        This method exists for raw microphone input where the
        supplied sampling rate may differ.
        """

        if not isinstance(
            waveform,
            torch.Tensor,
        ):
            raise TypeError(
                "waveform must be a torch.Tensor."
            )

        if sample_rate <= 0:
            raise ValueError(
                "sample_rate must be greater than zero."
            )

        if sample_rate == self.sample_rate:
            return waveform.float()

        audio_np = (
            waveform
            .squeeze(0)
            .detach()
            .cpu()
            .numpy()
            .astype(np.float32)
        )

        resampled = librosa.resample(
            audio_np,
            orig_sr=sample_rate,
            target_sr=self.sample_rate,
        )

        return torch.from_numpy(
            np.asarray(
                resampled,
                dtype=np.float32,
            )
        ).unsqueeze(0)

    # ======================================================
    # Duration Normalization
    # ======================================================

    def normalize_duration(
        self,
        waveform: torch.Tensor,
    ) -> torch.Tensor:
        """
        Make the waveform exactly 5 seconds.

        IMPORTANT:
        This exactly matches AudioStandardizer used during
        training.

        Short audio:
            zero-pad at the END.

        Long audio:
            keep the FIRST 5 seconds.

        There is NO center crop.
        """

        if not isinstance(
            waveform,
            torch.Tensor,
        ):
            raise TypeError(
                "waveform must be a torch.Tensor."
            )

        if waveform.ndim != 2:
            raise ValueError(
                "waveform must have shape "
                "[channels, samples]."
            )

        target_samples = (
            self.target_length
        )

        current_samples = (
            waveform.shape[-1]
        )

        # --------------------------------------------------
        # Exact length
        # --------------------------------------------------

        if current_samples == target_samples:

            return waveform

        # --------------------------------------------------
        # Short audio → zero-pad at END
        # --------------------------------------------------

        if current_samples < target_samples:

            padding = (
                target_samples
                - current_samples
            )

            waveform = torch.nn.functional.pad(
                waveform,
                (
                    0,
                    padding,
                ),
                mode="constant",
                value=0.0,
            )

            return waveform

        # --------------------------------------------------
        # Long audio → FIRST 5 seconds
        # --------------------------------------------------

        return waveform[
            :,
            :target_samples,
        ]

    # ======================================================
    # Waveform → Log-Mel Spectrogram
    # ======================================================

    def waveform_to_spectrogram(
        self,
        waveform: torch.Tensor,
    ) -> torch.Tensor:
        """
        Convert waveform into the exact training
        log-mel representation.

        Training reference:

            mel = librosa.feature.melspectrogram(
                y=audio,
                sr=16000,
                n_fft=1024,
                hop_length=512,
                n_mels=128,
                fmin=20,
                fmax=8000,
                power=2.0
            )

            log_mel = librosa.power_to_db(
                mel,
                ref=np.max
            )

        Then:

            (spec - mean) / (std + 1e-8)

        Returns
        -------
        torch.Tensor

            Shape:
                [1, 128, time]
        """

        if not isinstance(
            waveform,
            torch.Tensor,
        ):
            raise TypeError(
                "waveform must be a torch.Tensor."
            )

        if waveform.ndim != 2:
            raise ValueError(
                "waveform must have shape "
                "[channels, samples]."
            )

        if waveform.shape[0] != 1:
            raise ValueError(
                "waveform must be mono before "
                "spectrogram extraction."
            )

        # --------------------------------------------------
        # Torch → NumPy
        # --------------------------------------------------

        audio = (
            waveform
            .squeeze(0)
            .detach()
            .cpu()
            .numpy()
            .astype(np.float32)
        )

        # --------------------------------------------------
        # Exact training Mel extraction
        # --------------------------------------------------

        mel = librosa.feature.melspectrogram(
            y=audio,
            sr=self.sample_rate,
            n_fft=self.n_fft,
            hop_length=self.hop_length,
            n_mels=self.n_mels,
            fmin=self.fmin,
            fmax=self.fmax,
            power=2.0,
        )

        # --------------------------------------------------
        # Exact training log conversion
        # --------------------------------------------------

        log_mel = librosa.power_to_db(
            mel,
            ref=np.max,
        )

        log_mel = np.asarray(
            log_mel,
            dtype=np.float32,
        )

        # --------------------------------------------------
        # Exact training spectrogram normalization
        # --------------------------------------------------

        mean = float(
            log_mel.mean()
        )

        std = float(
            log_mel.std()
        )

        log_mel = (
            log_mel - mean
        ) / (
            std + 1e-8
        )

        spectrogram = torch.from_numpy(
            log_mel
        ).float()

        # [mel, time]
        # →
        # [channel, mel, time]

        spectrogram = spectrogram.unsqueeze(0)

        return spectrogram

    # ======================================================
    # Raw Waveform Pipeline
    # ======================================================

    def preprocess_waveform(
        self,
        waveform: torch.Tensor,
        sample_rate: int | None = None,
    ) -> torch.Tensor:
        """
        Complete raw-waveform preprocessing pipeline.

        Pipeline:

            Raw waveform
                ↓
            Validation
                ↓
            Mono
                ↓
            Resampling
                ↓
            5-second normalization
                ↓
            Peak normalization
                ↓
            librosa Mel
                ↓
            librosa dB
                ↓
            Z-score normalization
                ↓
            Model-ready tensor
        """

        # --------------------------------------------------
        # Validate
        # --------------------------------------------------

        waveform = self.validate_waveform(
            waveform
        )

        # --------------------------------------------------
        # Sampling rate
        # --------------------------------------------------

        if sample_rate is None:
            sample_rate = (
                self.sample_rate
            )

        if sample_rate <= 0:
            raise ValueError(
                "sample_rate must be greater than zero."
            )

        # --------------------------------------------------
        # Resample
        # --------------------------------------------------

        waveform = self.resample_waveform(
            waveform,
            sample_rate,
        )

        # --------------------------------------------------
        # Exact 5-second training duration
        # --------------------------------------------------

        waveform = self.normalize_duration(
            waveform
        )

        # --------------------------------------------------
        # Exact training peak normalization
        # --------------------------------------------------

        waveform = self.peak_normalize(
            waveform
        )

        # --------------------------------------------------
        # Spectrogram
        # --------------------------------------------------

        spectrogram = (
            self.waveform_to_spectrogram(
                waveform
            )
        )

        return spectrogram

    # ======================================================
    # Complete File Pipeline
    # ======================================================

    def preprocess(
        self,
        file_path: str | Path,
    ) -> torch.Tensor:
        """
        Complete file-based inference pipeline.

        This intentionally mirrors:

            AudioStandardizer
                ↓
            LogMelExtractor
                ↓
            EnvironmentalDataset normalization
        """

        # --------------------------------------------------
        # Load
        # --------------------------------------------------

        waveform = self.load_audio(
            file_path
        )

        # --------------------------------------------------
        # Exact training duration
        # --------------------------------------------------

        waveform = self.normalize_duration(
            waveform
        )

        # --------------------------------------------------
        # Exact training peak normalization
        # --------------------------------------------------

        waveform = self.peak_normalize(
            waveform
        )

        # --------------------------------------------------
        # Exact training feature extraction
        # --------------------------------------------------

        spectrogram = (
            self.waveform_to_spectrogram(
                waveform
            )
        )

        return spectrogram

    # ======================================================
    # Configuration
    # ======================================================

    def get_config(
        self,
    ) -> dict:
        """
        Return the active preprocessing configuration.
        """

        return {
            "sample_rate":
                self.sample_rate,

            "duration":
                self.duration,

            "target_length":
                self.target_length,

            "n_fft":
                self.n_fft,

            "hop_length":
                self.hop_length,

            "n_mels":
                self.n_mels,

            "fmin":
                self.fmin,

            "fmax":
                self.fmax,

            "power":
                2.0,

            "feature_extractor":
                "librosa",

            "db_conversion":
                "librosa.power_to_db",

            "db_reference":
                "np.max",

            "duration_strategy":
                "first_5_seconds",

            "short_audio_strategy":
                "zero_pad_end",

            "waveform_normalization":
                "peak",

            "spectrogram_normalization":
                "z_score",
        }