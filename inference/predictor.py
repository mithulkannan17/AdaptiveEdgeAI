"""
Predictor

Production inference interface for environmental sound classification
with open-set unknown-sound discovery.

The CNN still produces its normal closed-set prediction.  The
UnknownDiscoveryManager acts as the open-set gate.  When the gate rejects
the prediction, this class returns an explicit ``Unknown`` PredictionResult
to the rest of the edge-intelligence pipeline while retaining the original
top-k probabilities for diagnostics.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

from inference.device import DeviceManager
from inference.model_loader import ModelLoader
from inference.postprocessor import PostProcessor
from inference.types import PredictionResult

from edge.unknown import UnknownDiscoveryManager


class Predictor:
    """
    Production inference interface.

    Pipeline
    --------
    Audio/spectrogram
        -> CNN logits
        -> closed-set PredictionResult
        -> open-set UnknownDetector
        -> accepted class OR explicit Unknown
        -> embedding/buffer/clustering for unknown observations
    """

    UNKNOWN_LABEL = "Unknown"
    UNKNOWN_CLASS_ID = -1

    def __init__(
        self,
        checkpoint_path: str | Path | None = None,
        enable_unknown_discovery: bool = True,
        unknown_confidence_threshold: float = 0.60,
        unknown_margin_threshold: float = 0.15,
        unknown_buffer_size: int = 500,
        unknown_clustering_batch_size: int = 30,
        unknown_state_path: str | Path | None = None,
    ):
        self.device = DeviceManager.get_device()

        print(f"\nInference Device : {self.device}")

        self.model_loader = ModelLoader(
            device=self.device,
            checkpoint_path=checkpoint_path,
        )

        self.model = self.model_loader.load()
        self.model_name = self.model_loader.get_model_name()

        print(f"Model : {self.model_name}")
        print(
            "Checkpoint : "
            f"{self.model_loader.get_checkpoint_path()}"
        )

        self.postprocessor = PostProcessor()

        self.enable_unknown_discovery = bool(
            enable_unknown_discovery
        )

        self.discovery_manager = None
        self.last_discovery_result = None
        self.last_raw_prediction = None

        if unknown_state_path is None:
            configured_state_path = os.getenv(
                "AURAFOREST_DISCOVERY_STATE_PATH"
            )

            if configured_state_path:
                unknown_state_path = configured_state_path
            else:
                # Relative to the project working directory.  This keeps the
                # state persistent across API/dashboard restarts without
                # hard-coding a machine-specific absolute path.
                unknown_state_path = (
                    Path("data") / "unknown_discovery.json"
                )

        if self.enable_unknown_discovery:
            self.discovery_manager = UnknownDiscoveryManager(
                model=self.model,
                device=self.device,
                confidence_threshold=unknown_confidence_threshold,
                margin_threshold=unknown_margin_threshold,
                buffer_size=unknown_buffer_size,
                clustering_batch_size=unknown_clustering_batch_size,
                state_path=unknown_state_path,
            )

    # ==========================================================
    # Spectrogram Prediction
    # ==========================================================

    def predict_spectrogram(
        self,
        spectrogram: np.ndarray | torch.Tensor,
        top_k: int = 5,
        audio_path: str | Path | None = None,
        audio_rms: float | None = None,
    ) -> PredictionResult:
        """
        Predict an environmental sound from a model-ready spectrogram.

        The returned PredictionResult is open-set aware:

            KNOWN:
                normal CNN class

            UNKNOWN:
                label="Unknown", class_id=-1

        The original CNN result is retained in
        ``self.last_raw_prediction`` for diagnostics.
        """

        # ------------------------------------------------------
        # Convert input to Tensor
        # ------------------------------------------------------

        if isinstance(spectrogram, np.ndarray):
            spectrogram = torch.from_numpy(
                spectrogram
            ).float()

        elif isinstance(spectrogram, torch.Tensor):
            spectrogram = spectrogram.float()

        else:
            raise TypeError(
                "spectrogram must be either "
                "numpy.ndarray or torch.Tensor."
            )

        # ------------------------------------------------------
        # Normalize dimensions
        # ------------------------------------------------------

        if spectrogram.ndim == 2:
            spectrogram = spectrogram.unsqueeze(0)

        if spectrogram.ndim == 3:
            spectrogram = spectrogram.unsqueeze(0)

        if spectrogram.ndim != 4:
            raise ValueError(
                "Spectrogram must have shape "
                "[mel, time], "
                "[channel, mel, time], or "
                "[batch, channel, mel, time]."
            )

        if spectrogram.shape[0] != 1:
            raise ValueError(
                "Predictor currently supports exactly one "
                "spectrogram per inference call."
            )

        spectrogram = spectrogram.to(self.device)

        # ------------------------------------------------------
        # Optional acoustic activity signal
        # ------------------------------------------------------
        if audio_rms is not None:
            try:
                audio_rms = float(audio_rms)
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    "audio_rms must be a finite numeric value or None."
                ) from exc

            if not np.isfinite(audio_rms):
                raise ValueError(
                    "audio_rms must be a finite numeric value or None."
                )

            if audio_rms < 0.0:
                raise ValueError("audio_rms cannot be negative.")

        # ------------------------------------------------------
        # Model inference
        # ------------------------------------------------------

        start = time.perf_counter()

        with torch.no_grad():
            logits = self.model(spectrogram)

        inference_time_ms = (
            time.perf_counter() - start
        ) * 1000.0

        # ------------------------------------------------------
        # Standard closed-set prediction
        # ------------------------------------------------------

        raw_result = self.postprocessor.process(
            logits,
            top_k=top_k,
            inference_time_ms=inference_time_ms,
        )

        self.last_raw_prediction = raw_result

        # ------------------------------------------------------
        # Open-set discovery
        # ------------------------------------------------------

        self.last_discovery_result = None

        if self.discovery_manager is None:
            return raw_result

        probabilities = F.softmax(
            logits,
            dim=1,
        )

        probability_vector = (
            probabilities[0]
            .detach()
            .cpu()
            .numpy()
        )

        discovery_result = self.discovery_manager.process(
            probabilities=probability_vector,
            spectrogram=spectrogram,
            audio_path=(
                str(audio_path)
                if audio_path is not None
                else None
            ),
            audio_rms=audio_rms,
        )

        self.last_discovery_result = discovery_result

        # ------------------------------------------------------
        # IMPORTANT:
        # Open-set rejection overrides the closed-set class.
        #
        # The original raw result remains available through
        # last_raw_prediction and the discovery decision.
        # ------------------------------------------------------

        decision = discovery_result.decision

        if decision.is_unknown:
            return PredictionResult(
                label=self.UNKNOWN_LABEL,
                class_id=self.UNKNOWN_CLASS_ID,
                confidence=float(raw_result.confidence),
                top_k=raw_result.top_k,
                inference_time_ms=raw_result.inference_time_ms,
            )

        return raw_result

    # ==========================================================
    # Discovery Information
    # ==========================================================

    def get_last_discovery_result(self):
        """Return the discovery result from the latest prediction."""
        return self.last_discovery_result

    def get_last_raw_prediction(self):
        """
        Return the original closed-set CNN prediction.

        Useful for diagnostics when the public prediction was overridden
        to ``Unknown`` by the open-set gate.
        """
        return self.last_raw_prediction

    def get_unknown_discovery_status(self) -> dict:
        """Return complete dashboard/API discovery state."""
        if self.discovery_manager is None:
            return {
                "enabled": False,
                "buffer_size": 0,
                "clusters": [],
            }

        return self.discovery_manager.status()

    def get_unknown_clusters(self) -> list[dict]:
        """Return persistent discovered clusters."""
        if self.discovery_manager is None:
            return []

        return self.discovery_manager.get_clusters()

    def label_unknown_cluster(
        self,
        cluster_id: str,
        label: str,
        notes: str = "",
    ) -> dict:
        """Apply a human label to a discovered cluster."""
        if self.discovery_manager is None:
            raise RuntimeError(
                "Unknown discovery is disabled."
            )

        return self.discovery_manager.label_cluster(
            cluster_id=cluster_id,
            label=label,
            notes=notes,
        )

    def unlabel_unknown_cluster(
        self,
        cluster_id: str,
    ) -> dict:
        """Remove a human label from a discovered cluster."""
        if self.discovery_manager is None:
            raise RuntimeError(
                "Unknown discovery is disabled."
            )

        return self.discovery_manager.unlabel_cluster(
            cluster_id=cluster_id,
        )

    def unknown_buffer_size(self) -> int:
        """Return the number of pending unknown observations."""
        if self.discovery_manager is None:
            return 0

        return self.discovery_manager.buffer_size()

    def clear_unknown_buffer(self) -> None:
        """Clear pending unknown observations without deleting clusters."""
        if self.discovery_manager is not None:
            self.discovery_manager.clear()

    # ==========================================================
    # Model Information
    # ==========================================================

    def get_model_name(self) -> str:
        """Return the currently loaded model name."""
        return self.model_name

    def get_checkpoint_path(self) -> Path:
        """Return the checkpoint used by the predictor."""
        return self.model_loader.get_checkpoint_path()
