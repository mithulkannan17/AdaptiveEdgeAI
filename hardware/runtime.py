"""
Hardware Runtime Adapter

Connects hardware sensors with the production edge
inference and communication pipeline.

Runtime flow:

    Microphone
        ↓
    Raw PCM
        ↓
    PreProcessor
        ↓
    Model-ready Spectrogram
        ↓
    EdgeRuntimeService
        ↓
    EdgeController
        ↓
    CADIE
        ↓
    TransmissionPolicy
        ↓
    HardwareTelemetry
        ↓
    Backend

The same runtime works with dummy hardware during
development and real ESP32-S3 hardware in deployment.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import torch

from hardware.sensors import HardwareSensorManager
from hardware.telemetry import HardwareTelemetry
from inference.preprocessor import PreProcessor


@dataclass
class HardwareRuntimeResult:
    """
    Result produced by one hardware-runtime cycle.

    Attributes
    ----------
    runtime_response:
        Response returned by EdgeRuntimeService.

    telemetry:
        Hardware telemetry captured during the cycle.

    audio_samples:
        Number of audio samples captured.

    spectrogram_shape:
        Shape of the generated model-ready spectrogram.
    """

    runtime_response: Any

    telemetry: HardwareTelemetry | None

    audio_samples: int

    spectrogram_shape: tuple[int, ...] | None = None

    def to_dict(self) -> dict:
        """
        Convert the runtime result into a serializable
        dictionary.
        """

        return {

            "runtime_response":
                self.runtime_response,

            "telemetry": (

                self.telemetry.to_dict()

                if self.telemetry is not None

                else None

            ),

            "audio_samples":
                self.audio_samples,

            "spectrogram_shape": (

                list(
                    self.spectrogram_shape
                )

                if self.spectrogram_shape is not None

                else None

            ),

        }


class HardwareRuntime:
    """
    Hardware-facing runtime adapter.

    Responsibilities
    ----------------
    1. Capture raw audio from the microphone.
    2. Capture hardware telemetry.
    3. Normalize microphone data into torch.float32.
    4. Convert raw audio using the production
       PreProcessor.
    5. Pass the model-ready spectrogram to the
       EdgeRuntimeService.
    6. Preserve runtime state.

    This class does not implement:

        - model inference
        - environmental profiling
        - adaptive behaviour
        - event detection
        - CADIE
        - transmission
        - backend communication
    """

    def __init__(
        self,
        sensor_manager: HardwareSensorManager,
        runtime_service,
        preprocessor: PreProcessor | None = None,
        sample_rate: int | None = None,
        duration_seconds: float | None = None,
    ):
        """
        Parameters
        ----------
        sensor_manager:
            HardwareSensorManager providing microphone
            and environmental telemetry.

        runtime_service:
            EdgeRuntimeService responsible for the
            production edge pipeline.

        preprocessor:
            Production PreProcessor.

            If omitted, a default PreProcessor is created.

        sample_rate:
            Optional sampling-rate override.

            By default the value from PreProcessor is used.

        duration_seconds:
            Optional capture-duration override.

            By default the value from PreProcessor is used.
        """

        if sensor_manager is None:

            raise ValueError(
                "sensor_manager cannot be None."
            )

        if runtime_service is None:

            raise ValueError(
                "runtime_service cannot be None."
            )

        if not isinstance(
            sensor_manager,
            HardwareSensorManager,
        ):

            raise TypeError(
                "sensor_manager must be a "
                "HardwareSensorManager instance."
            )

        # --------------------------------------------------
        # Preprocessor
        # --------------------------------------------------

        if preprocessor is None:

            preprocessor = PreProcessor()

        if not isinstance(
            preprocessor,
            PreProcessor,
        ):

            raise TypeError(
                "preprocessor must be a "
                "PreProcessor instance."
            )

        self.sensor_manager = (
            sensor_manager
        )

        self.runtime_service = (
            runtime_service
        )

        self.preprocessor = (
            preprocessor
        )

        # --------------------------------------------------
        # Runtime configuration
        # --------------------------------------------------

        self.sample_rate = int(

            sample_rate

            if sample_rate is not None

            else self.preprocessor.sample_rate

        )

        self.duration_seconds = float(

            duration_seconds

            if duration_seconds is not None

            else self.preprocessor.duration

        )

        if self.sample_rate <= 0:

            raise ValueError(
                "sample_rate must be greater than zero."
            )

        if self.duration_seconds <= 0:

            raise ValueError(
                "duration_seconds must be greater than zero."
            )

        # --------------------------------------------------
        # Runtime state
        # --------------------------------------------------

        self.last_audio = None

        self.last_telemetry = None

        self.last_spectrogram = None

        self.last_result = None

    # ======================================================
    # Audio Capture
    # ======================================================

    def capture_audio(
        self,
    ) -> torch.Tensor:
        """
        Capture one audio window from the configured
        microphone sensor.

        The microphone abstraction may return:

            numpy.ndarray
            torch.Tensor

        The runtime normalizes both representations to:

            torch.float32

        This creates a stable boundary between the hardware
        layer and the production preprocessing layer.
        """

        microphone = (
            self.sensor_manager.microphone_sensor
        )

        if microphone is None:

            raise RuntimeError(
                "No microphone sensor is configured."
            )

        audio = microphone.read_audio(

            duration_seconds=(
                self.duration_seconds
            ),

            sample_rate=(
                self.sample_rate
            ),

        )

        if audio is None:

            raise RuntimeError(
                "Microphone returned no audio."
            )

        # --------------------------------------------------
        # NumPy → Torch
        # --------------------------------------------------

        if isinstance(
            audio,
            np.ndarray,
        ):

            audio = torch.from_numpy(
                audio
            )

        # --------------------------------------------------
        # Torch
        # --------------------------------------------------

        elif isinstance(
            audio,
            torch.Tensor,
        ):

            pass

        # --------------------------------------------------
        # Unsupported type
        # --------------------------------------------------

        else:

            raise TypeError(

                "Microphone must return either "
                "numpy.ndarray or torch.Tensor."

            )

        # --------------------------------------------------
        # Production dtype
        # --------------------------------------------------

        audio = audio.float()

        if audio.numel() == 0:

            raise ValueError(
                "Microphone returned empty audio."
            )

        self.last_audio = audio

        return audio

    # ======================================================
    # Telemetry
    # ======================================================

    def capture_telemetry(
        self,
    ) -> HardwareTelemetry:
        """
        Capture a complete hardware telemetry snapshot.
        """

        telemetry = (
            self.sensor_manager.read_all()
        )

        if not isinstance(
            telemetry,
            HardwareTelemetry,
        ):

            raise TypeError(
                "sensor_manager.read_all() must return "
                "HardwareTelemetry."
            )

        self.last_telemetry = telemetry

        return telemetry

    # ======================================================
    # Preprocessing
    # ======================================================

    def preprocess_audio(
        self,
        audio: torch.Tensor,
    ) -> torch.Tensor:
        """
        Convert raw microphone audio into the exact
        model-ready spectrogram used during training.

        The PreProcessor remains the single source of
        truth for feature extraction.
        """

        if not isinstance(
            audio,
            torch.Tensor,
        ):

            raise TypeError(
                "audio must be a torch.Tensor."
            )

        spectrogram = (
            self.preprocessor
            .preprocess_waveform(

                audio,

                sample_rate=(
                    self.sample_rate
                ),

            )
        )

        if spectrogram is None:

            raise RuntimeError(
                "PreProcessor returned no spectrogram."
            )

        self.last_spectrogram = (
            spectrogram
        )

        return spectrogram

    # ======================================================
    # Single Runtime Cycle
    # ======================================================

    def process_once(
        self,
        top_k: int = 5,
        audio_path: str | Path | None = None,
    ) -> HardwareRuntimeResult:
        """
        Execute one complete hardware runtime cycle.

        Pipeline
        --------

        Microphone
            ↓
        Raw PCM
            ↓
        Production PreProcessor
            ↓
        Log-mel Spectrogram
            ↓
        EdgeRuntimeService
            ↓
        EdgeController
            ↓
        CADIE
            ↓
        TransmissionPolicy
            ↓
        HardwareTelemetry
            ↓
        Backend
        """

        # --------------------------------------------------
        # Capture audio
        # --------------------------------------------------

        audio = (
            self.capture_audio()
        )

        # --------------------------------------------------
        # Capture telemetry
        # --------------------------------------------------

        telemetry = (
            self.capture_telemetry()
        )

        # --------------------------------------------------
        # Production preprocessing
        # --------------------------------------------------

        spectrogram = (
            self.preprocess_audio(
                audio
            )
        )

        # --------------------------------------------------
        # Run production edge service
        # --------------------------------------------------

        response = (
            self.runtime_service
            .process_spectrogram(

                spectrogram,

                top_k=top_k,

                audio_path=audio_path,

                telemetry=telemetry,

            )
        )

        # --------------------------------------------------
        # Spectrogram shape
        # --------------------------------------------------

        spectrogram_shape = (

            tuple(
                spectrogram.shape
            )

            if hasattr(
                spectrogram,
                "shape",
            )

            else None

        )

        # --------------------------------------------------
        # Runtime result
        # --------------------------------------------------

        result = HardwareRuntimeResult(

            runtime_response=response,

            telemetry=telemetry,

            audio_samples=int(
                audio.numel()
            ),

            spectrogram_shape=(
                spectrogram_shape
            ),

        )

        self.last_result = result

        return result

    # ======================================================
    # State
    # ======================================================

    def get_last_result(
        self,
    ) -> HardwareRuntimeResult | None:
        """
        Return the most recent hardware runtime result.
        """

        return self.last_result

    def get_last_telemetry(
        self,
    ) -> HardwareTelemetry | None:
        """
        Return the most recent hardware telemetry.
        """

        return self.last_telemetry

    def get_last_audio(
        self,
    ):
        """
        Return the most recently captured audio as a
        torch.float32 tensor.
        """

        return self.last_audio

    def get_last_spectrogram(
        self,
    ):
        """
        Return the most recently generated spectrogram.
        """

        return self.last_spectrogram

    # ======================================================
    # Configuration
    # ======================================================

    def get_config(
        self,
    ) -> dict:
        """
        Return the active hardware-runtime configuration.
        """

        return {

            "sample_rate":
                self.sample_rate,

            "duration_seconds":
                self.duration_seconds,

            "preprocessing":
                self.preprocessor.get_config(),

        }

    # ======================================================
    # Reset
    # ======================================================

    def reset(
        self,
    ) -> None:
        """
        Clear the hardware runtime state.
        """

        self.last_audio = None

        self.last_telemetry = None

        self.last_spectrogram = None

        self.last_result = None