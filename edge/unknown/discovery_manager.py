"""
Unknown Discovery Manager

Orchestrates unknown-sound detection, embedding extraction,
buffering, and clustering.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import torch

from edge.unknown.clusterer import (
    ClusterResult,
    UnknownClusterer,
)

from edge.unknown.embedding_extractor import (
    EmbeddingExtractor,
)

from edge.unknown.unknown_buffer import (
    UnknownBuffer,
)

from edge.unknown.unknown_detector import (
    UnknownDecision,
    UnknownDetector,
)


@dataclass
class DiscoveryResult:
    """
    Result returned after processing a prediction.
    """

    decision: UnknownDecision

    buffered: bool

    buffer_size: int

    clustering_triggered: bool

    cluster_result: Optional[ClusterResult] = None

    def to_dict(self) -> dict:
        """
        Convert result to a serializable dictionary.
        """

        data = {

            "decision":
                self.decision.to_dict(),

            "buffered":
                self.buffered,

            "buffer_size":
                self.buffer_size,

            "clustering_triggered":
                self.clustering_triggered,

        }

        if self.cluster_result is not None:

            data["cluster_result"] = (
                self.cluster_result.to_dict()
            )

        else:

            data["cluster_result"] = None

        return data


class UnknownDiscoveryManager:
    """
    Coordinates the complete unknown-sound discovery pipeline.

    Responsibilities:

        1. Detect uncertain predictions.
        2. Extract embeddings.
        3. Store unknown observations.
        4. Trigger clustering when enough observations
           are available.

    The manager does not modify the classification model.
    """

    def __init__(
        self,
        model,
        device: torch.device,
        confidence_threshold: float = 0.60,
        margin_threshold: float = 0.15,
        buffer_size: int = 500,
        clustering_batch_size: int = 30,
        clusterer: Optional[
            UnknownClusterer
        ] = None,
    ):

        self.detector = UnknownDetector(

            confidence_threshold=(
                confidence_threshold
            ),

            margin_threshold=(
                margin_threshold
            ),

        )

        self.embedding_extractor = (
            EmbeddingExtractor(

                model=model,

                device=device,

            )
        )

        self.buffer = UnknownBuffer(

            max_size=buffer_size

        )

        self.clusterer = (

            clusterer

            if clusterer is not None

            else UnknownClusterer()

        )

        self.clustering_batch_size = (
            clustering_batch_size
        )

    def process(
        self,
        probabilities,
        spectrogram: torch.Tensor,
        audio_path: Optional[str] = None,
    ) -> DiscoveryResult:
        """
        Process one model prediction.

        Parameters
        ----------
        probabilities:
            Model class probabilities.

        spectrogram:
            Model-ready spectrogram.

        audio_path:
            Optional source audio path.

        Returns
        -------
        DiscoveryResult
        """

        decision = self.detector.decide(
            probabilities
        )

        # --------------------------------------------------
        # Known sound
        # --------------------------------------------------

        if not decision.is_unknown:

            return DiscoveryResult(

                decision=decision,

                buffered=False,

                buffer_size=self.buffer.size(),

                clustering_triggered=False,

            )

        # --------------------------------------------------
        # Unknown sound
        # --------------------------------------------------

        embedding = (
            self.embedding_extractor.extract(
                spectrogram
            )
        )

        self.buffer.add(

            embedding=embedding,

            predicted_class=(
                decision.predicted_class
            ),

            confidence=(
                decision.confidence
            ),

            audio_path=audio_path,

        )

        should_cluster = (
            self.buffer.is_ready(
                self.clustering_batch_size
            )
        )

        cluster_result = None

        if should_cluster:

            cluster_result = (
                self.cluster()
            )

        return DiscoveryResult(

            decision=decision,

            buffered=True,

            buffer_size=self.buffer.size(),

            clustering_triggered=(
                should_cluster
            ),

            cluster_result=cluster_result,

        )

    def cluster(self) -> ClusterResult:
        """
        Cluster all currently buffered unknown samples.
        """

        embeddings = self.buffer.embeddings()

        result = self.clusterer.cluster(
            embeddings
        )

        return result

    def clear(self) -> None:
        """
        Clear all buffered unknown samples.
        """

        self.buffer.clear()

    def buffer_size(self) -> int:
        """
        Return current number of unknown samples.
        """

        return self.buffer.size()