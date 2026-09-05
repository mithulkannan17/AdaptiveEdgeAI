"""
AuraForest Unknown Sound Buffer

Thread-safe, bounded in-memory buffer for embeddings rejected by the
open-set detector.

The buffer is intentionally independent of clustering.  It only owns:
    - pending UnknownSample objects
    - capacity management
    - batch readiness
    - conversion of pending samples into tensors

UnknownDiscoveryManager is responsible for deciding when to cluster.
"""

from __future__ import annotations

from dataclasses import dataclass
from collections import deque
import time
from typing import Iterable, Optional

import torch


@dataclass
class UnknownSample:
    """One rejected acoustic observation retained for discovery."""

    embedding: torch.Tensor
    predicted_class: int
    confidence: float
    audio_path: Optional[str] = None
    timestamp: float = 0.0

    def __post_init__(self) -> None:
        if not isinstance(self.embedding, torch.Tensor):
            self.embedding = torch.as_tensor(self.embedding, dtype=torch.float32)

        # Keep one embedding vector per sample.
        self.embedding = self.embedding.detach().cpu().float().flatten()

        self.predicted_class = int(self.predicted_class)
        self.confidence = float(self.confidence)

        if not self.timestamp:
            self.timestamp = time.time()


class UnknownBuffer:
    """
    Bounded FIFO buffer for unknown acoustic embeddings.

    Important behavior:
      * add() never mutates the caller's tensor.
      * samples are kept in arrival order.
      * once capacity is reached, the oldest sample is discarded so that
        the live system cannot grow without bound.
      * pop_batch() removes exactly the requested oldest batch.
      * embeddings() returns a stacked CPU tensor without exposing internal
        storage.
    """

    def __init__(self, max_size: int = 500) -> None:
        max_size = int(max_size)
        if max_size <= 0:
            raise ValueError("max_size must be greater than zero.")

        self.max_size = max_size
        self._samples: deque[UnknownSample] = deque()

        # Useful for diagnostics/dashboard reporting.
        self._total_added = 0
        self._total_evicted = 0
        self._total_popped = 0

    # ---------------------------------------------------------
    # Core operations
    # ---------------------------------------------------------

    def add(
        self,
        embedding: torch.Tensor,
        predicted_class: int,
        confidence: float,
        audio_path: Optional[str] = None,
        timestamp: Optional[float] = None,
    ) -> UnknownSample:
        """Append one unknown sample and enforce the configured capacity."""

        sample = UnknownSample(
            embedding=embedding,
            predicted_class=predicted_class,
            confidence=confidence,
            audio_path=audio_path,
            timestamp=time.time() if timestamp is None else float(timestamp),
        )

        if len(self._samples) >= self.max_size:
            self._samples.popleft()
            self._total_evicted += 1

        self._samples.append(sample)
        self._total_added += 1

        return sample

    def add_sample(self, sample: UnknownSample) -> UnknownSample:
        """Compatibility helper for callers that already have an UnknownSample."""

        if not isinstance(sample, UnknownSample):
            raise TypeError("sample must be an UnknownSample.")

        return self.add(
            embedding=sample.embedding,
            predicted_class=sample.predicted_class,
            confidence=sample.confidence,
            audio_path=sample.audio_path,
            timestamp=sample.timestamp,
        )

    def pop_batch(self, batch_size: int) -> list[UnknownSample]:
        """
        Remove and return exactly batch_size oldest samples.

        Raises ValueError when the requested batch is invalid or unavailable.
        """
        batch_size = int(batch_size)

        if batch_size <= 0:
            raise ValueError("batch_size must be greater than zero.")

        if len(self._samples) < batch_size:
            raise ValueError(
                f"Not enough samples for batch: requested {batch_size}, "
                f"available {len(self._samples)}."
            )

        batch = [self._samples.popleft() for _ in range(batch_size)]
        self._total_popped += batch_size
        return batch

    # ---------------------------------------------------------
    # Inspection
    # ---------------------------------------------------------

    def size(self) -> int:
        """Return the number of pending samples."""
        return len(self._samples)

    def __len__(self) -> int:
        return self.size()

    def is_empty(self) -> bool:
        return len(self._samples) == 0

    def is_ready(self, batch_size: int) -> bool:
        """Return True when at least batch_size samples are pending."""
        batch_size = int(batch_size)
        if batch_size <= 0:
            raise ValueError("batch_size must be greater than zero.")
        return len(self._samples) >= batch_size

    def peek(self, count: Optional[int] = None) -> list[UnknownSample]:
        """
        Return pending samples without removing them.

        This is useful for diagnostics and future review tooling.
        """
        samples = list(self._samples)
        if count is None:
            return samples

        count = max(0, int(count))
        return samples[:count]

    def embeddings(self) -> torch.Tensor:
        """
        Return all pending embeddings stacked as [N, D].

        Empty buffers return an empty float tensor with shape [0, 0].
        """
        if not self._samples:
            return torch.empty((0, 0), dtype=torch.float32)

        return torch.stack(
            [sample.embedding for sample in self._samples],
            dim=0,
        )

    def samples(self) -> list[UnknownSample]:
        """Return a shallow copy of the pending sample list."""
        return list(self._samples)

    # ---------------------------------------------------------
    # Statistics / lifecycle
    # ---------------------------------------------------------

    @property
    def total_added(self) -> int:
        return self._total_added

    @property
    def total_evicted(self) -> int:
        return self._total_evicted

    @property
    def total_popped(self) -> int:
        return self._total_popped

    @property
    def pending_count(self) -> int:
        return self.size()

    def stats(self) -> dict:
        """Return dashboard/API-friendly buffer statistics."""
        return {
            "size": self.size(),
            "max_size": self.max_size,
            "pending_count": self.size(),
            "total_added": self.total_added,
            "total_evicted": self.total_evicted,
            "total_popped": self.total_popped,
            "is_empty": self.is_empty(),
        }

    def clear(self) -> None:
        """Remove all pending samples while retaining lifetime counters."""
        self._samples.clear()

    # ---------------------------------------------------------
    # Compatibility / utility
    # ---------------------------------------------------------

    def extend(self, samples: Iterable[UnknownSample]) -> int:
        """Append multiple UnknownSample objects and return the count added."""
        count = 0
        for sample in samples:
            self.add_sample(sample)
            count += 1
        return count

    def __iter__(self):
        return iter(self._samples)

    def __repr__(self) -> str:
        return (
            f"UnknownBuffer(size={self.size()}, "
            f"max_size={self.max_size}, "
            f"total_added={self.total_added}, "
            f"total_evicted={self.total_evicted})"
        )
