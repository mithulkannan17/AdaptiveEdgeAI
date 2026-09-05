"""
Backend Audio Inference

Connects incoming ESP32 PCM audio to the existing
production preprocessing and prediction pipeline.

Pipeline:

    PCM16 bytes
        ↓
    float32 waveform
        ↓
    PreProcessor
        ↓
    5-second normalized Mel spectrogram
        ↓
    Predictor
        ↓
    PredictionResult
        ↓
    Unknown discovery information
"""

from __future__ import annotations

from typing import Any

import numpy as np
import torch

from inference.preprocessor import PreProcessor
from inference.predictor import Predictor


class AudioInferenceService:
    """
    Production bridge between incoming edge audio and
    the existing inference pipeline.
    """

    def __init__(
        self,
        checkpoint_path: str | None = None,
        enable_unknown_discovery: bool = True,
    ):
        # --------------------------------------------------
        # Preprocessor
        # --------------------------------------------------

        self.preprocessor = PreProcessor()

        # --------------------------------------------------
        # Predictor
        # --------------------------------------------------

        self.predictor = Predictor(
            checkpoint_path=checkpoint_path,
            enable_unknown_discovery=(
                enable_unknown_discovery
            ),
        )

    # ======================================================
    # PCM Conversion
    # ======================================================

    @staticmethod
    def pcm16_to_float32(
        audio_bytes: bytes,
    ) -> np.ndarray:
        """
        Convert signed 16-bit little-endian PCM into
        normalized float32 mono audio.
        """

        if not audio_bytes:
            raise ValueError(
                "Audio payload is empty."
            )

        if len(audio_bytes) % 2 != 0:
            raise ValueError(
                "PCM16 audio must contain an even "
                "number of bytes."
            )

        audio = np.frombuffer(
            audio_bytes,
            dtype="<i2",
        )

        waveform = (
            audio.astype(
                np.float32
            )
            / 32768.0
        )

        return np.clip(
            waveform,
            -1.0,
            1.0,
        )

    # ======================================================
    # Complete Inference
    # ======================================================

    def predict_pcm16(
        self,
        audio_bytes: bytes,
        sample_rate: int = 16000,
        top_k: int = 5,
    ) -> dict[str, Any]:
        """
        Run the complete inference pipeline on raw
        PCM16 audio.

        Parameters
        ----------
        audio_bytes:
            Signed 16-bit little-endian mono PCM.

        sample_rate:
            Sampling rate of incoming audio.

        top_k:
            Number of predictions to return.

        Returns
        -------
        dict
            JSON-compatible inference result.
        """

        # --------------------------------------------------
        # Validate
        # --------------------------------------------------

        if sample_rate <= 0:
            raise ValueError(
                "sample_rate must be greater than zero."
            )

        if top_k <= 0:
            raise ValueError(
                "top_k must be greater than zero."
            )

        # --------------------------------------------------
        # PCM → NumPy
        # --------------------------------------------------

        waveform_np = (
            self.pcm16_to_float32(
                audio_bytes
            )
        )

        if waveform_np.size == 0:
            raise ValueError(
                "Audio waveform is empty."
            )

        # --------------------------------------------------
        # NumPy → Torch
        # --------------------------------------------------

        waveform = torch.from_numpy(
            waveform_np
        )

        # --------------------------------------------------
        # Production preprocessing
        #
        # This performs:
        #
        # waveform validation
        #       ↓
        # mono conversion
        #       ↓
        # resampling to 16 kHz
        #       ↓
        # 5-second normalization
        #       ↓
        # 128-bin Mel spectrogram
        #       ↓
        # logarithmic conversion
        #       ↓
        # normalization
        # --------------------------------------------------

        spectrogram = (
            self.preprocessor.preprocess_waveform(
                waveform,
                sample_rate=sample_rate,
            )
        )

        # --------------------------------------------------
        # Model prediction
        # --------------------------------------------------

        prediction = (
            self.predictor.predict_spectrogram(
                spectrogram,
                top_k=top_k,
            )
        )

        # --------------------------------------------------
        # Convert prediction object
        # --------------------------------------------------

        prediction_result = {
            "label": getattr(
                prediction,
                "label",
                "Unknown",
            ),

            "class_id": int(
                getattr(
                    prediction,
                    "class_id",
                    -1,
                )
            ),

            "confidence": float(
                getattr(
                    prediction,
                    "confidence",
                    0.0,
                )
            ),

            "inference_time_ms": float(
                getattr(
                    prediction,
                    "inference_time_ms",
                    0.0,
                )
            ),
        }

        # --------------------------------------------------
        # Top-K predictions
        # --------------------------------------------------

        top_predictions = getattr(
            prediction,
            "top_k",
            [],
        )

        prediction_result["top_k"] = []

        for item in top_predictions:

            if isinstance(item, dict):

                prediction_result[
                    "top_k"
                ].append(
                    {
                        "label":
                            str(
                                item.get(
                                    "label",
                                    "Unknown",
                                )
                            ),

                        "confidence":
                            float(
                                item.get(
                                    "confidence",
                                    0.0,
                                )
                            ),
                    }
                )

            elif (
                isinstance(item, tuple)
                and len(item) >= 2
            ):

                prediction_result[
                    "top_k"
                ].append(
                    {
                        "label":
                            str(item[0]),

                        "confidence":
                            float(item[1]),
                    }
                )

        # --------------------------------------------------
        # Unknown discovery
        # --------------------------------------------------

        discovery = (
            self.predictor
            .get_last_discovery_result()
        )

        discovery_result = None

        if discovery is not None:

            if hasattr(
                discovery,
                "to_dict",
            ):

                discovery_result = (
                    discovery.to_dict()
                )

            elif isinstance(
                discovery,
                dict,
            ):

                discovery_result = discovery

            else:

                discovery_result = {
                    "result":
                        str(discovery)
                }

        # --------------------------------------------------
        # Audio information
        # --------------------------------------------------

        duration_seconds = (
            waveform_np.size
            / float(sample_rate)
        )

        rms = float(
            np.sqrt(
                np.mean(
                    waveform_np ** 2
                )
            )
        )

        return {
            "prediction":
                prediction_result,

            "unknown_discovery":
                discovery_result,

            "audio": {
                "sample_rate":
                    int(sample_rate),

                "samples":
                    int(waveform_np.size),

                "duration_seconds":
                    float(
                        duration_seconds
                    ),

                "rms":
                    rms,
            },

            "model": {
                "name":
                    self.predictor.get_model_name(),

                "checkpoint":
                    str(
                        self.predictor
                        .get_checkpoint_path()
                    ),
            },
        }