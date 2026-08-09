"""
Unknown Sound Buffer

Temporarily stores uncertain acoustic events before
they are passed to the clustering system.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

import torch


@dataclass
class UnknownSample:
    """
    One unknown acoustic observation.
    """

    embedding: torch.Tensor

    predicted_class: int

    confidence: float

    timestamp: float

    audio_path: Optional[str] = None

    def to_dict(self) -> dict:
        """
        Convert metadata to a serializable dictionary.

        The embedding itself is intentionally excluded.
        """

        return {
            "predicted_class":
                self.predicted_class,

            "confidence":
                self.confidence,

            "timestamp":
                self.timestamp,

            "audio_path":
                self.audio_path,
        }


class UnknownBuffer:
    """
    In-memory buffer for unknown acoustic events.

    The buffer has a maximum capacity so that an edge
    device cannot accumulate unlimited samples.
    """

    def __init__(
        self,
        max_size: int = 500,
    ):

        if max_size <= 0:

            raise ValueError(
                "max_size must be greater than zero."
            )

        self.max_size = max_size

        self._samples: list[
            UnknownSample
        ] = []

    def add(
        self,
        embedding: torch.Tensor,
        predicted_class: int,
        confidence: float,
        audio_path: Optional[str] = None,
        timestamp: Optional[float] = None,
    ) -> None:
        """
        Add an unknown acoustic sample.
        """

        if embedding is None:

            raise ValueError(
                "embedding cannot be None."
            )

        if embedding.ndim != 1:

            raise ValueError(
                "embedding must be one-dimensional."
            )

        confidence = max(
            0.0,
            min(
                1.0,
                float(confidence),
            ),
        )

        if timestamp is None:

            timestamp = time.time()

        sample = UnknownSample(

            embedding=embedding.detach().cpu(),

            predicted_class=int(
                predicted_class
            ),

            confidence=confidence,

            timestamp=float(timestamp),

            audio_path=audio_path,

        )

        self._samples.append(sample)

        # FIFO behaviour.
        if len(self._samples) > self.max_size:

            self._samples.pop(0)

    def size(self) -> int:
        """
        Return number of buffered samples.
        """

        return len(self._samples)

    def is_ready(
        self,
        minimum_samples: int,
    ) -> bool:
        """
        Determine whether enough samples are available
        for clustering.
        """

        if minimum_samples <= 0:

            raise ValueError(
                "minimum_samples must be greater than zero."
            )

        return (
            len(self._samples)
            >= minimum_samples
        )

    def get_samples(
        self,
    ) -> list[UnknownSample]:
        """
        Return a copy of the current samples.
        """

        return list(
            self._samples
        )

    def embeddings(self) -> torch.Tensor:
        """
        Return all embeddings as a single tensor.

        Shape:
            [N, embedding_dimension]
        """

        if not self._samples:

            return torch.empty(
                (0, 0),
                dtype=torch.float32,
            )

        return torch.stack(
            [
                sample.embedding
                for sample in self._samples
            ]
        )

    def clear(self) -> None:
        """
        Remove all buffered samples.
        """

        self._samples.clear()

    def pop_batch(
        self,
        batch_size: int,
    ) -> list[UnknownSample]:
        """
        Remove and return the oldest samples.
        """

        if batch_size <= 0:

            raise ValueError(
                "batch_size must be greater than zero."
            )

        batch = self._samples[
            :batch_size
        ]

        self._samples = self._samples[
            batch_size:
        ]

        return batch