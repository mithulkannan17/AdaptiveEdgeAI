"""
Predictor

Production inference interface for environmental
sound classification and unknown-sound discovery.
"""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

from inference.device import DeviceManager
from inference.model_loader import ModelLoader
from inference.postprocessor import PostProcessor
from inference.types import PredictionResult

from edge.unknown import (
    UnknownDiscoveryManager,
)
from edge.multi_event_analyzer import (
    MultiEventAnalyzer,
)


class Predictor:
    """
    Production inference interface.

    Responsibilities
    ----------------
    1. Load the configured trained model.
    2. Perform inference.
    3. Convert logits into predictions.
    4. Detect potentially unknown sounds.
    5. Store unknown acoustic events.
    6. Trigger unknown-sound clustering.

    The model architecture is determined by the project
    configuration.

    The checkpoint can optionally be overridden for testing,
    experimentation, or deployment.
    """

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
        """
        Parameters
        ----------
        checkpoint_path:
            Optional explicit model checkpoint.

            If None, the checkpoint configured in
            training_config.yaml is used.

        enable_unknown_discovery:
            Enable the unknown-sound discovery pipeline.

        unknown_confidence_threshold:
            Confidence threshold below which a prediction
            can be considered unknown.

        unknown_margin_threshold:
            Margin threshold used by the unknown detector.

        unknown_buffer_size:
            Maximum number of unknown samples stored.

        unknown_clustering_batch_size:
            Number of unknown samples required before
            clustering is triggered.

        unknown_state_path:
            Path for persisting discovered clusters.
        """

        # --------------------------------------------------
        # Device
        # --------------------------------------------------

        self.device = (
            DeviceManager.get_device()
        )

        print(
            f"\nInference Device : "
            f"{self.device}"
        )

        # --------------------------------------------------
        # Model
        # --------------------------------------------------

        self.model_loader = ModelLoader(

            device=self.device,

            checkpoint_path=checkpoint_path,

        )

        self.model = (
            self.model_loader.load()
        )

        self.model_name = (
            self.model_loader.get_model_name()
        )

        print(
            f"Model : "
            f"{self.model_name}"
        )

        print(
            f"Checkpoint : "
            f"{self.model_loader.get_checkpoint_path()}"
        )

        # --------------------------------------------------
        # Postprocessor
        # --------------------------------------------------

        self.postprocessor = (
            PostProcessor()
        )

        # --------------------------------------------------
        # Unknown discovery
        # --------------------------------------------------

        self.enable_unknown_discovery = (
            enable_unknown_discovery
        )

        self.discovery_manager = None

        self.last_discovery_result = None

        # --------------------------------------------------
        # Multi-event acoustic analysis
        # --------------------------------------------------
        self.multi_event_analyzer = MultiEventAnalyzer()
        self.last_multi_event_result = (
            self.multi_event_analyzer.get_last_result()
        )

        if self.enable_unknown_discovery:
            if unknown_state_path is None:
                default_state = Path(__file__).resolve().parent.parent / "data" / "unknown_discovery.json"
                unknown_state_path = default_state

            self.discovery_manager = (
                UnknownDiscoveryManager(

                    model=self.model,

                    device=self.device,

                    confidence_threshold=(
                        unknown_confidence_threshold
                    ),

                    margin_threshold=(
                        unknown_margin_threshold
                    ),

                    buffer_size=(
                        unknown_buffer_size
                    ),

                    clustering_batch_size=(
                        unknown_clustering_batch_size
                    ),

                    state_path=unknown_state_path,

                )
            )

    # ======================================================
    # Spectrogram Prediction
    # ======================================================

    def predict_spectrogram(
        self,
        spectrogram: np.ndarray | torch.Tensor,
        top_k: int = 5,
        audio_path: str | Path | None = None,
        audio_rms: float | None = None,
    ) -> PredictionResult:
        """
        Predict an environmental sound from a
        model-ready spectrogram.

        Parameters
        ----------
        spectrogram:
            Mel spectrogram.

        top_k:
            Number of highest-confidence predictions.

        audio_path:
            Optional source audio path.

        Returns
        -------
        PredictionResult
            Human-readable model prediction.
        """

        # --------------------------------------------------
        # Convert input to Tensor
        # --------------------------------------------------

        if isinstance(
            spectrogram,
            np.ndarray,
        ):

            spectrogram = (
                torch.from_numpy(
                    spectrogram
                ).float()
            )

        elif isinstance(
            spectrogram,
            torch.Tensor,
        ):

            spectrogram = (
                spectrogram.float()
            )

        else:

            raise TypeError(

                "spectrogram must be either "
                "numpy.ndarray or torch.Tensor."

            )

        # --------------------------------------------------
        # Normalize spectrogram dimensions
        #
        # Accepted:
        #
        # [mel, time]
        # [channel, mel, time]
        # [batch, channel, mel, time]
        # --------------------------------------------------

        if spectrogram.ndim == 2:

            spectrogram = (
                spectrogram.unsqueeze(0)
            )

        if spectrogram.ndim == 3:

            spectrogram = (
                spectrogram.unsqueeze(0)
            )

        if spectrogram.ndim != 4:

            raise ValueError(

                "Spectrogram must have shape "
                "[mel, time], "
                "[channel, mel, time], or "
                "[batch, channel, mel, time]."

            )

        # --------------------------------------------------
        # Move to inference device
        # --------------------------------------------------

        spectrogram = (
            spectrogram.to(
                self.device
            )
        )

        # --------------------------------------------------
        # Model inference
        # --------------------------------------------------

        start = time.perf_counter()

        with torch.no_grad():

            logits = self.model(
                spectrogram
            )

        inference_time_ms = (

            time.perf_counter()

            - start

        ) * 1000.0

        # --------------------------------------------------
        # Standard prediction processing
        # --------------------------------------------------

        result = (
            self.postprocessor.process(

                logits,

                top_k=top_k,

                inference_time_ms=(
                    inference_time_ms
                ),

            )
        )

        # --------------------------------------------------
        # Full probability vector
        # --------------------------------------------------

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

        # --------------------------------------------------
        # Multi-event acoustic analysis
        # --------------------------------------------------
        #
        # Analyze the complete softmax vector. Temporal
        # persistence is handled inside MultiEventAnalyzer.
        # This supplements, but does not replace, the primary
        # classifier result.
        # --------------------------------------------------

        self.last_multi_event_result = (
            self.multi_event_analyzer.analyze(
                probability_vector
            )
        )

        # --------------------------------------------------
        # Unknown Sound Discovery
        # --------------------------------------------------

        self.last_discovery_result = None

        if self.discovery_manager is not None:

            # Forward acoustic RMS and source audio metadata
            # to the unknown-discovery pipeline.
            self.last_discovery_result = (
                self.discovery_manager.process(
                    probabilities=(
                        probability_vector
                    ),
                    spectrogram=spectrogram,
                    audio_path=(
                        str(audio_path)
                        if audio_path is not None
                        else None
                    ),
                    audio_rms=audio_rms,
                )
            )

        return result

    # ==========================================================
    # Multi-Event Information
    # ==========================================================

    def get_last_multi_event_result(self) -> dict:
        """Return the latest multi-event acoustic analysis."""
        if self.last_multi_event_result is None:
            return {
                "enabled": True,
                "primary_event": None,
                "simultaneous_events": [],
                "candidates": [],
                "frame_count": 0,
                "explanation": (
                    "No inference has been analyzed yet."
                ),
            }
        return self.last_multi_event_result

    def reset_multi_event_history(self) -> None:
        """Clear temporal multi-event evidence."""
        self.multi_event_analyzer.reset()
        self.last_multi_event_result = (
            self.multi_event_analyzer.get_last_result()
        )

    # ======================================================
    # Discovery Information
    # ======================================================

    def get_last_discovery_result(
        self,
    ):
        """
        Return the unknown-discovery result generated
        by the most recent prediction.

        Returns
        -------
        DiscoveryResult | None
        """

        return (
            self.last_discovery_result
        )

    def unknown_buffer_size(
        self,
    ) -> int:
        """
        Return the number of unknown samples currently
        stored in the discovery buffer.
        """

        if self.discovery_manager is None:

            return 0

        return (
            self.discovery_manager.buffer_size()
        )

    def clear_unknown_buffer(
        self,
    ) -> None:
        """
        Clear all currently buffered unknown samples.
        """

        if self.discovery_manager is not None:

            self.discovery_manager.clear()

    def get_unknown_discovery_status(self) -> dict:
        """
        Return the current unknown-sound discovery status.

        This is used by the FastAPI dashboard/status endpoint.
        """

        if self.discovery_manager is None:
            return {
                "enabled": False,
                "message": "Unknown discovery is disabled.",
            }

        return self.discovery_manager.status()

    def get_unknown_clusters(self) -> list[dict]:
        """Return persistent discovered unknown clusters."""
        if self.discovery_manager is None:
            return []
        return self.discovery_manager.get_clusters()

    def label_unknown_cluster(
        self,
        cluster_id: str,
        label: str,
        notes: str = "",
    ) -> dict:
        """Apply a human label to a discovered unknown cluster."""
        if self.discovery_manager is None:
            raise RuntimeError("Unknown discovery is not enabled.")
        return self.discovery_manager.label_cluster(
            cluster_id=cluster_id,
            label=label,
            notes=notes,
        )

    def unlabel_unknown_cluster(
        self,
        cluster_id: str,
    ) -> dict:
        """Remove a human label from a discovered unknown cluster."""
        if self.discovery_manager is None:
            raise RuntimeError("Unknown discovery is not enabled.")
        return self.discovery_manager.unlabel_cluster(cluster_id=cluster_id)

    def trigger_clustering(
        self,
        force: bool = True,
    ) -> tuple[dict, list[str]]:
        """Trigger clustering on currently buffered unknown samples."""
        if self.discovery_manager is None:
            raise RuntimeError("Unknown discovery is not enabled.")
        result, cluster_ids = self.discovery_manager.cluster(force=force)
        return result.to_dict(), cluster_ids

    # ======================================================
    # Model Information
    # ======================================================

    def get_model_name(
        self,
    ) -> str:
        """
        Return the currently loaded model name.
        """

        return self.model_name

    def get_checkpoint_path(
        self,
    ) -> Path:
        """
        Return the checkpoint used by the predictor.
        """

        return (
            self.model_loader
            .get_checkpoint_path()
        )