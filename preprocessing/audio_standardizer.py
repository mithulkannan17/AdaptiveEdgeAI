"""
Audio Standardizer

Converts audio into:
- 16 kHz
- Mono
- 5 seconds
- Peak Normalized

Unreadable audio files raise a RuntimeError so the batch
processor can skip them instead of crashing.
"""

from pathlib import Path

import librosa
import numpy as np
import soundfile as sf


class AudioStandardizer:

    def __init__(
        self,
        sample_rate: int = 16000,
        duration: int = 5
    ):

        self.sample_rate = sample_rate
        self.duration = duration
        self.target_length = sample_rate * duration

    def process(
        self,
        input_path,
        output_path
    ):

        input_path = Path(input_path)
        output_path = Path(output_path)

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        # -----------------------------
        # Load Audio
        # -----------------------------
        try:

            audio, sr = librosa.load(
                input_path,
                sr=self.sample_rate,
                mono=True
            )

        except Exception as e:

            raise RuntimeError(
                f"Unable to read audio file: {input_path}"
            ) from e

        # Empty audio check
        if audio is None or len(audio) == 0:
            raise RuntimeError(
                f"Empty audio file: {input_path}"
            )

        # -----------------------------
        # Standardize
        # -----------------------------
        audio = self._fix_length(audio)
        audio = self._normalize(audio)

        # -----------------------------
        # Save
        # -----------------------------
        try:

            sf.write(
                output_path,
                audio,
                self.sample_rate
            )

        except Exception as e:

            raise RuntimeError(
                f"Unable to save audio: {output_path}"
            ) from e

        return {
            "sample_rate": self.sample_rate,
            "duration": len(audio) / self.sample_rate,
            "channels": 1
        }

    def _fix_length(self, audio):

        if len(audio) > self.target_length:

            return audio[:self.target_length]

        if len(audio) < self.target_length:

            padding = self.target_length - len(audio)

            return np.pad(
                audio,
                (0, padding),
                mode="constant"
            )

        return audio

    def _normalize(self, audio):

        peak = np.max(np.abs(audio))

        if peak > 0:

            audio = audio / peak

        return audio.astype(np.float32)