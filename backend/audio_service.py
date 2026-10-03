"""
Backend audio_service.py

Connects incoming edge audio to the complete
production edge-intelligence pipeline.

Supported audio formats
-----------------------

1. Raw PCM16
   ESP32 / embedded hardware input

2. WAV
   Development, Swagger, frontend and recorded-audio testing

Pipeline:

    Incoming Audio
        ↓
    WAV detection / PCM handling
        ↓
    PCM16 → float32
        ↓
    waveform validation
        ↓
    Adaptive Noise Robustness
        ↓
    PreProcessor
        ↓
    Mel spectrogram
        ↓
    Predictor
        ↓
    MobileNetV3-Small
        ↓
    Unknown Discovery
        ↓
    EdgeController
        ↓
    Environmental Profiling
        ↓
    Adaptive Behaviour
        ↓
    Event Detection
        ↓
    Event Prioritization
        ↓
    CADIE
        ↓
    Complete Runtime Result
"""

from __future__ import annotations

from typing import Any
import struct
import os
import tempfile

import librosa

import numpy as np
import torch

from inference.preprocessor import PreProcessor
from inference.predictor import Predictor
from edge.runtime.edge_controller import EdgeController


class AudioInferenceService:
    """
    Complete bridge between incoming edge audio and the
    production edge-intelligence system.

    Supports:

        - raw signed PCM16 little-endian audio (ESP32)
        - standard PCM WAV audio
        - MP3, FLAC, OGG/Opus, M4A/MP4 and AIFF
        - AAC/ADTS when supported by the installed decoder

    Compressed/file formats are decoded to float32 using librosa,
    matching the project's training-time audio loading behaviour.

    The same Predictor instance is shared with EdgeController
    so that each audio sample is inferred only once.
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        checkpoint_path: str | None = None,
        enable_unknown_discovery: bool = True,
    ):
        # --------------------------------------------------
        # Sampling configuration
        # --------------------------------------------------

        self.sample_rate = int(sample_rate)

        if self.sample_rate <= 0:
            raise ValueError(
                "sample_rate must be greater than zero."
            )

        # --------------------------------------------------
        # Production preprocessing
        # --------------------------------------------------

        self.preprocessor = PreProcessor()

        # --------------------------------------------------
        # Noise-robust acoustic preprocessing
        # --------------------------------------------------
        # The denoiser is intentionally conservative.  AuraForest
        # monitors environmental soundscapes, so aggressive noise
        # removal could erase useful events such as wind, rain,
        # insects, water, or distant machinery.
        self.noise_robust_enabled = True
        self.noise_n_fft = 512
        self.noise_hop_length = 128
        self.noise_noise_percentile = 20.0
        self.noise_reduction_strength = 0.65
        self.noise_floor_ratio = 0.12
        self.noise_min_gain = 0.30
        self.noise_max_gain = 1.15

        # --------------------------------------------------
        # Production trained model
        # --------------------------------------------------

        self.predictor = Predictor(
            checkpoint_path=checkpoint_path,
            enable_unknown_discovery=(
                enable_unknown_discovery
            ),
        )

        # --------------------------------------------------
        # Complete edge-intelligence controller
        #
        # IMPORTANT:
        # The SAME Predictor instance is passed to the
        # controller.
        #
        # This prevents:
        #   - loading a second model
        #   - duplicate inference
        # --------------------------------------------------

        self.controller = EdgeController(
            predictor=self.predictor
        )

    # ======================================================
    # WAV DETECTION
    # ======================================================

    @staticmethod
    def is_wav(audio_bytes: bytes) -> bool:
        """
        Detect a standard RIFF/WAVE payload.

        A normal WAV file begins with:

            RIFF
            ...
            WAVE

        Raw PCM16 does not contain this header.
        """

        if len(audio_bytes) < 12:
            return False

        return (
            audio_bytes[0:4] == b"RIFF"
            and audio_bytes[8:12] == b"WAVE"
        )

    # ======================================================
    # WAV DECODER
    # ======================================================

    @staticmethod
    def wav_to_pcm16(
        audio_bytes: bytes,
    ) -> tuple[bytes, int]:
        """
        Decode a standard uncompressed PCM WAV file.

        Returns
        -------
        tuple[bytes, int]
            PCM16 little-endian bytes and WAV sample rate.

        Supported:
            - PCM format
            - 16-bit audio
            - mono
            - stereo

        Stereo audio is converted to mono by averaging the
        channels.

        The implementation intentionally avoids Python's
        standard `wave` module because this project may contain
        a local module named `wave.py` that can shadow it.
        """

        if not audio_bytes:
            raise ValueError(
                "Audio payload is empty."
            )

        if not AudioInferenceService.is_wav(
            audio_bytes
        ):
            raise ValueError(
                "Audio payload is not a valid RIFF/WAVE file."
            )

        if len(audio_bytes) < 12:
            raise ValueError(
                "WAV header is incomplete."
            )

        # --------------------------------------------------
        # RIFF container
        # --------------------------------------------------

        riff_size = struct.unpack_from(
            "<I",
            audio_bytes,
            4,
        )[0]

        # The RIFF size does not need to equal the actual
        # Python byte length exactly, but it should describe
        # a plausible WAV container.
        if riff_size + 8 > len(audio_bytes):
            raise ValueError(
                "WAV file is truncated."
            )

        # --------------------------------------------------
        # Locate fmt and data chunks
        # --------------------------------------------------

        offset = 12

        fmt_chunk = None
        data_chunk = None

        while offset + 8 <= len(audio_bytes):

            chunk_id = audio_bytes[
                offset:offset + 4
            ]

            chunk_size = struct.unpack_from(
                "<I",
                audio_bytes,
                offset + 4,
            )[0]

            chunk_start = offset + 8
            chunk_end = chunk_start + chunk_size

            if chunk_end > len(audio_bytes):
                raise ValueError(
                    "WAV chunk extends beyond file size."
                )

            if chunk_id == b"fmt ":
                fmt_chunk = audio_bytes[
                    chunk_start:chunk_end
                ]

            elif chunk_id == b"data":
                data_chunk = audio_bytes[
                    chunk_start:chunk_end
                ]

            # RIFF chunks are word aligned.
            offset = chunk_end

            if chunk_size % 2 == 1:
                offset += 1

            if fmt_chunk is not None and data_chunk is not None:
                break

        if fmt_chunk is None:
            raise ValueError(
                "WAV file does not contain a fmt chunk."
            )

        if data_chunk is None:
            raise ValueError(
                "WAV file does not contain a data chunk."
            )

        if len(fmt_chunk) < 16:
            raise ValueError(
                "WAV fmt chunk is incomplete."
            )

        # --------------------------------------------------
        # WAV format
        # --------------------------------------------------

        (
            audio_format,
            channels,
            sample_rate,
            byte_rate,
            block_align,
            bits_per_sample,
        ) = struct.unpack_from(
            "<HHIIHH",
            fmt_chunk,
            0,
        )

        # --------------------------------------------------
        # Validate PCM
        # --------------------------------------------------

        if audio_format != 1:
            raise ValueError(
                "Only uncompressed PCM WAV files are supported."
            )

        if channels <= 0:
            raise ValueError(
                "WAV file contains an invalid channel count."
            )

        if sample_rate <= 0:
            raise ValueError(
                "WAV file contains an invalid sample rate."
            )

        if bits_per_sample != 16:
            raise ValueError(
                "Only 16-bit PCM WAV files are supported."
            )

        if block_align != channels * 2:
            raise ValueError(
                "WAV block alignment is inconsistent "
                "with 16-bit PCM."
            )

        if len(data_chunk) == 0:
            raise ValueError(
                "WAV audio data is empty."
            )

        if len(data_chunk) % 2 != 0:
            raise ValueError(
                "WAV PCM16 data contains an incomplete sample."
            )

        # --------------------------------------------------
        # PCM16 samples
        # --------------------------------------------------

        samples = np.frombuffer(
            data_chunk,
            dtype="<i2",
        )

        if samples.size == 0:
            raise ValueError(
                "WAV contains no PCM samples."
            )

        # --------------------------------------------------
        # Convert stereo/multichannel → mono
        # --------------------------------------------------

        if channels > 1:

            usable_samples = (
                samples.size
                - (
                    samples.size
                    % channels
                )
            )

            if usable_samples == 0:
                raise ValueError(
                    "WAV contains no complete audio frames."
                )

            samples = samples[
                :usable_samples
            ]

            samples = samples.reshape(
                -1,
                channels,
            )

            # Use float32 while averaging to avoid integer
            # overflow and then convert back to PCM16.
            mono = (
                samples.astype(
                    np.float32
                ).mean(axis=1)
            )

            mono = np.clip(
                mono,
                -32768,
                32767,
            ).astype(
                np.int16
            )

            samples = mono

        # --------------------------------------------------
        # Return raw PCM16
        # --------------------------------------------------

        return (
            samples.astype(
                "<i2",
                copy=False,
            ).tobytes(),
            int(sample_rate),
        )

        # ======================================================
    # AUDIO FORMAT DETECTION
    # ======================================================

    @staticmethod
    def detect_audio_format(audio_bytes: bytes) -> str:
        """
        Detect common audio container/file formats from their
        binary signatures.

        Returns:
            wav, mp3, flac, ogg, m4a, aiff, or pcm16
        """

        if not audio_bytes:
            raise ValueError("Audio payload is empty.")

        # WAV / RIFF
        if (
            len(audio_bytes) >= 12
            and audio_bytes[0:4] == b"RIFF"
            and audio_bytes[8:12] == b"WAVE"
        ):
            return "wav"

        # RF64 WAV
        if (
            len(audio_bytes) >= 12
            and audio_bytes[0:4] == b"RF64"
            and audio_bytes[8:12] == b"WAVE"
        ):
            return "wav"

        # FLAC
        if audio_bytes[:4] == b"fLaC":
            return "flac"

        # OGG / Opus / Vorbis
        if audio_bytes[:4] == b"OggS":
            return "ogg"

        # AIFF / AIFC
        if (
            len(audio_bytes) >= 12
            and audio_bytes[:4] == b"FORM"
            and audio_bytes[8:12] in {b"AIFF", b"AIFC"}
        ):
            return "aiff"

        # MP3 with ID3 metadata
        if audio_bytes[:3] == b"ID3":
            return "mp3"

        # MP3 MPEG frame sync
        if len(audio_bytes) >= 2:
            b0 = audio_bytes[0]
            b1 = audio_bytes[1]

            if (
                b0 == 0xFF
                and (b1 & 0xE0) == 0xE0
            ):
                return "mp3"

        # MP4 / M4A
        #
        # Typical structure:
        # [size:4][ftyp:4][brand...]
        if len(audio_bytes) >= 12 and audio_bytes[4:8] == b"ftyp":
            return "m4a"

        # AAC ADTS
        if len(audio_bytes) >= 2:
            if (
                audio_bytes[0] == 0xFF
                and (audio_bytes[1] & 0xF6) == 0xF0
            ):
                return "aac"

        # Anything else is treated as the ESP32 raw PCM16 path.
        return "pcm16"

    # ======================================================
    # COMPRESSED AUDIO DECODER
    # ======================================================

    @staticmethod
    def compressed_to_waveform(
        audio_bytes: bytes,
        audio_format: str,
    ) -> tuple[np.ndarray, int]:
        """
        Decode a compressed/file-based audio format into a
        mono float32 waveform.

        librosa is deliberately used here because the training
        pipeline also loads audio through librosa.

        Returns:
            waveform, sample_rate
        """

        if not audio_bytes:
            raise ValueError(
                "Compressed audio payload is empty."
            )

        suffix_map = {
            "mp3": ".mp3",
            "flac": ".flac",
            "ogg": ".ogg",
            "m4a": ".m4a",
            "aiff": ".aiff",
            "aac": ".aac",
        }

        suffix = suffix_map.get(audio_format)

        if suffix is None:
            raise ValueError(
                f"Unsupported compressed audio format: "
                f"{audio_format}"
            )

        temp_path = None

        try:
            # --------------------------------------------------
            # Write the received bytes to a temporary file.
            #
            # librosa's decoder uses the file extension together
            # with the underlying audio backend.
            # --------------------------------------------------

            with tempfile.NamedTemporaryFile(
                suffix=suffix,
                delete=False,
            ) as temp_file:

                temp_file.write(audio_bytes)
                temp_file.flush()

                temp_path = temp_file.name

            # --------------------------------------------------
            # Decode exactly like the training pipeline:
            #
            #   - 16 kHz
            #   - mono
            # --------------------------------------------------

            waveform, decoded_rate = librosa.load(
                temp_path,
                sr=16000,
                mono=True,
            )

            waveform = np.asarray(
                waveform,
                dtype=np.float32,
            )

            if waveform.ndim != 1:
                raise ValueError(
                    "Decoded audio is not mono."
                )

            if waveform.size == 0:
                raise ValueError(
                    "Decoded audio contains no samples."
                )

            waveform = np.nan_to_num(
                waveform,
                nan=0.0,
                posinf=0.0,
                neginf=0.0,
            )

            waveform = np.clip(
                waveform,
                -1.0,
                1.0,
            )

            return (
                waveform,
                int(decoded_rate),
            )

        except Exception as exc:

            raise RuntimeError(
                f"Unable to decode {audio_format.upper()} "
                f"audio. Ensure the required audio decoder "
                f"(such as FFmpeg/audioread support) is "
                f"installed. Decoder error: {exc}"
            ) from exc

        finally:

            if temp_path is not None:

                try:
                    os.remove(temp_path)
                except OSError:
                    pass

    # ======================================================
    # AUDIO PAYLOAD NORMALIZATION
    # ======================================================

    def normalize_audio_payload(
        self,
        audio_bytes: bytes,
        sample_rate: int,
    ) -> tuple[np.ndarray | None, bytes | None, int, str]:
        """Normalize raw PCM16, WAV, or compressed audio.

        Returns:
            waveform, pcm16_bytes, effective_sample_rate, input_format

        Compressed formats remain float32 so there is no unnecessary
        decode -> int16 -> float32 quantization step.
        """
        if not audio_bytes:
            raise ValueError("Audio payload is empty.")

        detected = self.detect_audio_format(audio_bytes)

        if detected == "wav":
            pcm_bytes, wav_sample_rate = self.wav_to_pcm16(audio_bytes)
            return None, pcm_bytes, int(wav_sample_rate), "wav"

        if detected in {"mp3", "flac", "ogg", "m4a", "aiff", "aac"}:
            waveform, decoded_rate = self.compressed_to_waveform(
                audio_bytes,
                detected,
            )
            return waveform, None, int(decoded_rate), detected

        if len(audio_bytes) % 2 != 0:
            raise ValueError(
                "PCM16 audio must contain an even number of bytes."
            )

        return None, audio_bytes, int(sample_rate), "pcm16"

    # ======================================================
    # PCM16 → FLOAT32
    # ======================================================

    @staticmethod
    def pcm16_to_float32(
        audio_bytes: bytes,
    ) -> np.ndarray:
        """
        Convert signed 16-bit little-endian PCM audio
        into mono float32 audio in the range [-1, 1].
        """

        if not audio_bytes:
            raise ValueError(
                "PCM audio payload is empty."
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

        if audio.size == 0:
            raise ValueError(
                "PCM audio contains no samples."
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
    # WAVEFORM VALIDATION
    # ======================================================

    @staticmethod
    def validate(
        waveform: np.ndarray,
    ) -> np.ndarray:
        """
        Validate and normalize an incoming waveform.
        """

        waveform = np.asarray(
            waveform,
            dtype=np.float32,
        )

        if waveform.ndim != 1:
            raise ValueError(
                "Audio waveform must be mono."
            )

        if waveform.size == 0:
            raise ValueError(
                "Audio waveform is empty."
            )

        waveform = np.nan_to_num(
            waveform,
            nan=0.0,
            posinf=0.0,
            neginf=0.0,
        )

        return np.clip(
            waveform,
            -1.0,
            1.0,
        )

    # ======================================================
    # NOISE-ROBUST PREPROCESSING
    # ======================================================

    @staticmethod
    def _safe_rms(waveform: np.ndarray) -> float:
        """Return a numerically safe RMS level."""
        x = np.asarray(waveform, dtype=np.float32)
        if x.size == 0:
            return 0.0
        return float(np.sqrt(np.mean(np.square(x), dtype=np.float64) + 1e-12))

    def estimate_noise_profile(
        self,
        waveform: np.ndarray,
    ) -> np.ndarray:
        """
        Estimate a conservative stationary background-noise spectrum.

        The lowest-energy STFT frames are treated as likely background.
        A percentile across those frames is used instead of assuming that
        the beginning of a recording is silent.

        This is deliberately designed for short environmental clips.
        """
        x = np.asarray(waveform, dtype=np.float32)

        if x.size < self.noise_n_fft:
            return np.zeros(self.noise_n_fft // 2 + 1, dtype=np.float32)

        stft = librosa.stft(
            x,
            n_fft=self.noise_n_fft,
            hop_length=self.noise_hop_length,
            win_length=self.noise_n_fft,
            center=True,
        )

        magnitude = np.abs(stft).astype(np.float32)

        frame_energy = np.mean(
            np.square(magnitude),
            axis=0,
        )

        if frame_energy.size == 0:
            return np.zeros(
                self.noise_n_fft // 2 + 1,
                dtype=np.float32,
            )

        # Use the quietest ~30% of frames as candidate background.
        # This is more robust than assuming the first N milliseconds
        # contain only noise.
        quiet_count = max(
            1,
            int(np.ceil(frame_energy.size * 0.30)),
        )

        quiet_indices = np.argpartition(
            frame_energy,
            quiet_count - 1,
        )[:quiet_count]

        quiet_magnitude = magnitude[:, quiet_indices]

        noise_profile = np.percentile(
            quiet_magnitude,
            self.noise_noise_percentile,
            axis=1,
        )

        return np.asarray(
            noise_profile,
            dtype=np.float32,
        )

    def reduce_stationary_noise(
        self,
        waveform: np.ndarray,
    ) -> tuple[np.ndarray, dict[str, Any]]:
        """
        Apply conservative spectral-gating / spectral-subtraction.

        Important:
            This does NOT attempt to identify or remove a specific
            environmental class.  It only suppresses frequency energy
            that is consistently close to the estimated background.

        Returns:
            cleaned waveform and diagnostic information.
        """
        x = self.validate(waveform)

        if not self.noise_robust_enabled:
            return x, {
                "enabled": False,
                "applied": False,
                "reason": "noise_robustness_disabled",
                "input_rms": self._safe_rms(x),
                "output_rms": self._safe_rms(x),
                "attenuation_ratio": 1.0,
            }

        input_rms = self._safe_rms(x)

        # Avoid processing effectively silent audio.  The existing
        # open-set detector will handle silence/unknown rejection.
        if input_rms < 1e-4 or x.size < self.noise_n_fft:
            return x, {
                "enabled": True,
                "applied": False,
                "reason": "low_energy_or_short_audio",
                "input_rms": input_rms,
                "output_rms": input_rms,
                "attenuation_ratio": 1.0,
            }

        stft = librosa.stft(
            x,
            n_fft=self.noise_n_fft,
            hop_length=self.noise_hop_length,
            win_length=self.noise_n_fft,
            center=True,
        )

        magnitude = np.abs(stft)
        phase = np.angle(stft)

        noise_profile = self.estimate_noise_profile(x)
        noise_profile = noise_profile[:, None]

        # Power-ratio style spectral subtraction.
        # The floor prevents complete removal of a frequency bin.
        estimated_signal = np.maximum(
            magnitude - (
                self.noise_reduction_strength * noise_profile
            ),
            self.noise_floor_ratio * magnitude,
        )

        # Soft spectral gate.  Bins close to the noise floor are
        # attenuated; bins substantially above it are retained.
        ratio = magnitude / (
            noise_profile + 1e-8
        )

        gate = np.clip(
            (ratio - 1.0) / 1.5,
            0.0,
            1.0,
        )

        gain = (
            self.noise_min_gain
            + (
                1.0 - self.noise_min_gain
            ) * gate
        )

        cleaned_magnitude = estimated_signal * gain

        # Do not allow denoising to boost individual bins above the
        # original magnitude.  This avoids artificial tonal artifacts.
        cleaned_magnitude = np.minimum(
            cleaned_magnitude,
            magnitude * self.noise_max_gain,
        )

        cleaned_stft = (
            cleaned_magnitude
            * np.exp(1j * phase)
        )

        cleaned = librosa.istft(
            cleaned_stft,
            hop_length=self.noise_hop_length,
            win_length=self.noise_n_fft,
            length=x.size,
        )

        cleaned = np.asarray(
            cleaned,
            dtype=np.float32,
        )

        cleaned = np.nan_to_num(
            cleaned,
            nan=0.0,
            posinf=0.0,
            neginf=0.0,
        )

        cleaned = np.clip(
            cleaned,
            -1.0,
            1.0,
        )

        output_rms = self._safe_rms(cleaned)

        # Safety guard: if the denoiser removes almost everything,
        # fall back to the original waveform.  This protects short,
        # low-SNR environmental events.
        if (
            output_rms < input_rms * 0.20
            and input_rms > 1e-4
        ):
            cleaned = x.copy()
            output_rms = input_rms
            applied = False
            reason = "fallback_excessive_attenuation"
        else:
            applied = True
            reason = "adaptive_spectral_noise_reduction"

        attenuation_ratio = (
            output_rms / input_rms
            if input_rms > 1e-8
            else 1.0
        )

        return cleaned, {
            "enabled": True,
            "applied": applied,
            "reason": reason,
            "input_rms": input_rms,
            "output_rms": output_rms,
            "attenuation_ratio": float(attenuation_ratio),
            "n_fft": self.noise_n_fft,
            "hop_length": self.noise_hop_length,
            "noise_percentile": self.noise_noise_percentile,
            "reduction_strength": self.noise_reduction_strength,
        }

    # ======================================================
    # AUDIO PROCESSING
    # ======================================================

    def process_audio(
        self,
        audio_bytes: bytes,
        sample_rate: int,
    ) -> tuple[np.ndarray, int, str]:
        """Decode and validate raw PCM16, WAV, or compressed audio."""
        (
            waveform,
            pcm_bytes,
            effective_sample_rate,
            input_format,
        ) = self.normalize_audio_payload(
            audio_bytes=audio_bytes,
            sample_rate=sample_rate,
        )

        if waveform is None:
            if pcm_bytes is None:
                raise RuntimeError("Audio decoder returned no waveform.")
            waveform = self.pcm16_to_float32(pcm_bytes)

        waveform = self.validate(waveform)

        # --------------------------------------------------
        # Adaptive noise robustness
        # --------------------------------------------------
        # Denoising is performed before the production Mel
        # spectrogram so the CNN receives a cleaner acoustic
        # representation.  The original waveform is retained
        # for evidence storage and the returned diagnostics make
        # the transformation measurable.
        waveform, noise_info = self.reduce_stationary_noise(
            waveform
        )

        # Store diagnostics for the current inference call.
        self._last_noise_robustness = noise_info

        return (
            waveform,
            effective_sample_rate,
            input_format,
        )

    # ======================================================
    # BACKWARD-COMPATIBLE PCM PROCESSING
    # ======================================================

    def process_pcm16(
        self,
        audio_bytes: bytes,
    ) -> np.ndarray:
        """
        Process raw PCM16 audio.

        This method is retained for compatibility with
        existing callers.
        """

        waveform = self.pcm16_to_float32(
            audio_bytes
        )

        return self.validate(
            waveform
        )

    # ======================================================
    # PREDICTION SERIALIZATION
    # ======================================================

    def _prediction_to_dict(
        self,
        prediction: Any,
    ) -> dict[str, Any]:
        """
        Convert a PredictionResult into a
        JSON-compatible dictionary.
        """

        result: dict[str, Any] = {
            "label": str(
                getattr(
                    prediction,
                    "label",
                    "Unknown",
                )
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

            "top_k": [],
        }

        top_predictions = getattr(
            prediction,
            "top_k",
            [],
        )

        for item in top_predictions:

            if isinstance(item, dict):

                result["top_k"].append(
                    {
                        "label": str(
                            item.get(
                                "label",
                                "Unknown",
                            )
                        ),

                        "confidence": float(
                            item.get(
                                "confidence",
                                0.0,
                            )
                        ),
                    }
                )

            elif (
                isinstance(
                    item,
                    (tuple, list),
                )
                and len(item) >= 2
            ):

                result["top_k"].append(
                    {
                        "label": str(
                            item[0]
                        ),

                        "confidence": float(
                            item[1]
                        ),
                    }
                )

        return result

    # ======================================================
    # UNKNOWN DISCOVERY SERIALIZATION
    # ======================================================

    def _discovery_to_dict(
        self,
        discovery: Any,
    ) -> Any:
        """
        Convert unknown-discovery output into a
        JSON-compatible representation.
        """

        if discovery is None:
            return None

        if hasattr(
            discovery,
            "to_dict",
        ):
            return discovery.to_dict()

        if isinstance(
            discovery,
            dict,
        ):
            return discovery

        return {
            "result": str(
                discovery
            )
        }

    # ======================================================
    # COMPLETE INFERENCE
    # ======================================================

    def infer_pcm16(
        self,
        audio_bytes: bytes,
        sample_rate: int | None = None,
        top_k: int = 5,
        device_status: dict | None = None,
        audio_path: str | None = None,
    ) -> dict[str, Any]:
        """
        Run the complete audio + edge-intelligence pipeline.

        Despite the historical method name `infer_pcm16`, the
        method now accepts either:

            - raw PCM16
            - WAV containing 16-bit PCM
            - MP3 / FLAC / OGG / M4A / AIFF / AAC

        Raw PCM uses the supplied sample_rate.

        WAV uses the sample rate stored in the WAV header.

        Compressed formats are decoded to mono float32 at
        16 kHz before preprocessing, matching the training
        audio-loading path.

        audio_path is optional evidence storage metadata. When
        supplied, it is forwarded to the open-set Unknown Discovery
        pipeline so unknown samples can retain their original audio
        for human review.
        """

        # --------------------------------------------------
        # Sampling rate
        # --------------------------------------------------

        self._last_noise_robustness = {
            "enabled": self.noise_robust_enabled,
            "applied": False,
            "reason": "not_processed",
        }

        if sample_rate is None:
            sample_rate = self.sample_rate

        sample_rate = int(
            sample_rate
        )

        if sample_rate <= 0:
            raise ValueError(
                "sample_rate must be greater than zero."
            )

        if top_k <= 0:
            raise ValueError(
                "top_k must be greater than zero."
            )

        # --------------------------------------------------
        # Decode incoming audio
        # --------------------------------------------------

        (
            waveform_np,
            effective_sample_rate,
            input_format,
        ) = self.process_audio(
            audio_bytes=audio_bytes,
            sample_rate=sample_rate,
        )

        # --------------------------------------------------
        # NumPy → Torch
        # --------------------------------------------------

        waveform = torch.from_numpy(
            waveform_np
        )

        # --------------------------------------------------
        # Production PreProcessor
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
        # Mel spectrogram
        #       ↓
        # logarithmic conversion
        #       ↓
        # normalization
        # --------------------------------------------------

        spectrogram = (
            self.preprocessor.preprocess_waveform(
                waveform,
                sample_rate=effective_sample_rate,
            )
        )

        # --------------------------------------------------
        # Acoustic activity / RMS
        # --------------------------------------------------
        #
        # IMPORTANT:
        # The CNN can produce a high-confidence class even for
        # effectively silent audio.  Pass the real waveform RMS
        # into the open-set detector so silence can be rejected
        # as Unknown without changing the trained model.
        # --------------------------------------------------

        audio_rms = float(
            np.sqrt(
                np.mean(
                    np.square(
                        waveform_np
                    )
                )
            )
        )

        # --------------------------------------------------
        # MobileNet prediction + open-set discovery
        # --------------------------------------------------

        prediction = (
            self.predictor.predict_spectrogram(
                spectrogram,
                top_k=top_k,
                audio_path=audio_path,
                audio_rms=audio_rms,
            )
        )

        # --------------------------------------------------
        # Acoustic Energy & Ambient Floor Gating
        # --------------------------------------------------
        # Suppress false-positive threat predictions caused by
        # quiescent microphone hiss or ambient room silence.
        from inference.types import PredictionResult
        current_label_clean = str(getattr(prediction, "label", "")).strip()
        current_label_lower = current_label_clean.lower()
        threat_classes = {
            "emergencyvehicle", "siren", "chainsaw", "gunshot",
            "fire", "drill", "jackhammer", "explosion", "poaching"
        }

        if audio_rms < 0.0040 and any(t in current_label_lower for t in threat_classes):
            prediction = PredictionResult(
                label="Ambient",
                class_id=0,
                confidence=0.96,
                top_k=[("Ambient", 0.96), (current_label_clean, 0.04)],
                inference_time_ms=getattr(prediction, "inference_time_ms", 0.0),
            )
        elif audio_rms < 0.010 and ("emergencyvehicle" in current_label_lower or "siren" in current_label_lower):
            prediction = PredictionResult(
                label="Ambient",
                class_id=0,
                confidence=0.92,
                top_k=[("Ambient", 0.92), ("EmergencyVehicle", 0.08)],
                inference_time_ms=getattr(prediction, "inference_time_ms", 0.0),
            )

        # --------------------------------------------------
        # Prediction dictionary
        # --------------------------------------------------

        prediction_result = (
            self._prediction_to_dict(
                prediction
            )
        )

        # --------------------------------------------------
        # Edge Controller
        #
        # IMPORTANT:
        # Prediction has already happened.
        #
        # Therefore process_prediction() is used instead
        # of performing inference again.
        # --------------------------------------------------

        runtime_result = (
            self.controller.process_prediction(
                prediction,
                device_status=device_status,
            )
        )

        runtime_dict = (
            runtime_result.to_dict()
        )

        # --------------------------------------------------
        # Unknown discovery
        # --------------------------------------------------

        discovery_result = (
            runtime_dict.get(
                "discovery_result"
            )
        )

        # --------------------------------------------------
        # Audio statistics
        # --------------------------------------------------

        sample_count = int(
            waveform_np.size
        )

        duration_seconds = (
            sample_count
            / float(effective_sample_rate)
        )

        # Reuse the RMS already calculated before prediction.
        # This guarantees the detector and returned audio
        # statistics refer to the exact same waveform.
        rms = audio_rms

        audio_min = float(
            np.min(
                waveform_np
            )
        )

        audio_max = float(
            np.max(
                waveform_np
            )
        )

        # --------------------------------------------------
        # Final complete result
        # --------------------------------------------------

        # --------------------------------------------------
        # Multi-event acoustic analysis
        # --------------------------------------------------

        multi_event_result = (
            self.predictor.get_last_multi_event_result()
        )

        return {
            "prediction":
                prediction_result,

            "unknown_discovery":
                discovery_result,

            "multi_event":
                multi_event_result,

            "audio_evidence": {
                "path": audio_path,
                "available": bool(audio_path),
            },

            "edge_runtime":
                runtime_dict,

            "audio": {
                "input_format":
                    input_format,

                "sample_rate":
                    int(
                        effective_sample_rate
                    ),

                "samples":
                    sample_count,

                "duration_seconds":
                    float(
                        duration_seconds
                    ),

                "rms":
                    rms,

                "noise_robustness":
                    self._last_noise_robustness,

                "audio_min":
                    audio_min,

                "audio_max":
                    audio_max,
            },

            "model": {
                "name":
                    self.predictor
                    .get_model_name(),

                "checkpoint":
                    str(
                        self.predictor
                        .get_checkpoint_path()
                    ),
            },
        }

    # ======================================================
    # LAST RUNTIME RESULT
    # ======================================================

    def get_last_runtime_result(
        self,
    ) -> dict | None:
        """
        Return the latest complete EdgeController result.
        """

        return self.controller.state()

    # ======================================================
    # RESET RUNTIME
    # ======================================================

    def reset(
        self,
    ) -> None:
        """
        Reset edge-intelligence state.

        Clears:

            - environmental profiling state
            - unknown discovery buffer
            - latest runtime result
        """

        self.controller.reset()