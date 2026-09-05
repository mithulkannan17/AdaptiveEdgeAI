"""
Hardware Microphone Interfaces

Defines the abstraction used by the edge runtime to
capture environmental audio.

The interface is hardware-independent.

Current implementation:
    DummyMicrophone

Future implementation:
    INMP441Microphone

The runtime only depends on MicrophoneSensor and therefore
does not need to change when the physical microphone is
introduced.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np


class MicrophoneSensor(ABC):
    """
    Abstract interface for an edge microphone.

    Implementations must return mono float32 PCM audio.
    """

    @abstractmethod
    def read_audio(
        self,
        duration_seconds: float,
        sample_rate: int,
    ) -> np.ndarray:
        """
        Capture audio from the microphone.

        Parameters
        ----------
        duration_seconds:
            Duration of the requested audio window.

        sample_rate:
            Requested sampling rate in Hz.

        Returns
        -------
        numpy.ndarray
            Mono float32 PCM waveform with shape:

                [samples]
        """
        raise NotImplementedError


class DummyMicrophone(
    MicrophoneSensor
):
    """
    Software-only microphone used for development.

    Generates deterministic synthetic audio so the complete
    edge pipeline can be tested without physical hardware.

    The generated signal contains a small combination of
    tones rather than pure silence. This ensures the
    preprocessing pipeline receives meaningful non-zero
    audio.
    """

    def __init__(
        self,
        amplitude: float = 0.2,
        frequencies: tuple[float, ...] = (
            440.0,
            880.0,
        ),
    ):
        self.amplitude = float(
            amplitude
        )

        self.frequencies = tuple(
            float(frequency)
            for frequency in frequencies
        )

        if self.amplitude < 0:

            raise ValueError(
                "amplitude cannot be negative."
            )

        if not self.frequencies:

            raise ValueError(
                "frequencies cannot be empty."
            )

        for frequency in self.frequencies:

            if frequency <= 0:

                raise ValueError(
                    "frequencies must be greater than zero."
                )

    def read_audio(
        self,
        duration_seconds: float,
        sample_rate: int,
    ) -> np.ndarray:
        """
        Generate synthetic mono float32 PCM audio.
        """

        duration_seconds = float(
            duration_seconds
        )

        sample_rate = int(
            sample_rate
        )

        if duration_seconds <= 0:

            raise ValueError(
                "duration_seconds must be greater than zero."
            )

        if sample_rate <= 0:

            raise ValueError(
                "sample_rate must be greater than zero."
            )

        sample_count = int(

            round(
                duration_seconds
                * sample_rate
            )

        )

        if sample_count <= 0:

            raise ValueError(
                "Requested audio window is too small."
            )

        # --------------------------------------------------
        # Time axis
        # --------------------------------------------------

        time = (
            np.arange(
                sample_count,
                dtype=np.float32,
            )
            / sample_rate
        )

        # --------------------------------------------------
        # Synthetic acoustic signal
        # --------------------------------------------------

        audio = np.zeros(
            sample_count,
            dtype=np.float32,
        )

        amplitude_per_tone = (
            self.amplitude
            / len(self.frequencies)
        )

        for frequency in self.frequencies:

            audio += (
                amplitude_per_tone
                * np.sin(
                    2.0
                    * np.pi
                    * frequency
                    * time
                )
            )

        return audio.astype(
            np.float32,
            copy=False,
        )


class SilentMicrophone(
    MicrophoneSensor
):
    """
    Development microphone that produces silence.

    Useful for testing the pipeline's behaviour when the
    acoustic environment contains no meaningful signal.
    """

    def read_audio(
        self,
        duration_seconds: float,
        sample_rate: int,
    ) -> np.ndarray:
        """
        Return a zero-valued mono waveform.
        """

        duration_seconds = float(
            duration_seconds
        )

        sample_rate = int(
            sample_rate
        )

        if duration_seconds <= 0:

            raise ValueError(
                "duration_seconds must be greater than zero."
            )

        if sample_rate <= 0:

            raise ValueError(
                "sample_rate must be greater than zero."
            )

        sample_count = int(

            round(
                duration_seconds
                * sample_rate
            )

        )

        return np.zeros(
            sample_count,
            dtype=np.float32,
        )