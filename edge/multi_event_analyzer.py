"""
AuraForest Multi-Event Acoustic Analyzer

Adds multi-event candidate analysis without changing the existing
single-label MobileNetV3 prediction path.

The analyzer works on the full softmax probability vector, applies
per-frame candidate thresholds, and uses temporal persistence to avoid
reporting one-frame probability spikes as simultaneous events.

Important:
    This is multi-event candidate detection, not physical source
    separation. A single microphone cannot perfectly separate overlapping
    sources; this layer provides a conservative, explainable event view.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Iterable

import numpy as np

from training.label_encoder import LabelEncoder


@dataclass(frozen=True)
class MultiEventCandidate:
    """A sound candidate supported by the current model output."""

    label: str
    class_id: int
    confidence: float
    role: str
    persistent: bool
    evidence_count: int

    def to_dict(self) -> dict:
        return {
            "label": self.label,
            "class_id": self.class_id,
            "confidence": self.confidence,
            "role": self.role,
            "persistent": self.persistent,
            "evidence_count": self.evidence_count,
        }


class MultiEventAnalyzer:
    """
    Conservative multi-event analyzer for a stream of model outputs.

    Parameters
    ----------
    candidate_threshold:
        Minimum probability for a class to become a candidate.
    secondary_threshold:
        Minimum probability for a non-primary event to be reported.
    persistence_window:
        Number of recent inference frames retained per class.
    persistence_required:
        Number of recent frames in which a candidate must appear before
        being marked persistent.
    max_events:
        Maximum number of events returned for one inference.
    min_margin:
        Secondary events must have at least this much probability margin
        over the probability floor. This prevents numerical noise from
        becoming an event.
    """

    def __init__(
        self,
        candidate_threshold: float = 0.10,
        secondary_threshold: float = 0.20,
        persistence_window: int = 5,
        persistence_required: int = 2,
        max_events: int = 4,
        min_margin: float = 0.05,
    ):
        if not 0.0 <= candidate_threshold <= 1.0:
            raise ValueError("candidate_threshold must be in [0, 1].")
        if not 0.0 <= secondary_threshold <= 1.0:
            raise ValueError("secondary_threshold must be in [0, 1].")
        if persistence_window < 1:
            raise ValueError("persistence_window must be >= 1.")
        if persistence_required < 1:
            raise ValueError("persistence_required must be >= 1.")
        if persistence_required > persistence_window:
            raise ValueError("persistence_required cannot exceed persistence_window.")
        if max_events < 1:
            raise ValueError("max_events must be >= 1.")
        if not 0.0 <= min_margin <= 1.0:
            raise ValueError("min_margin must be in [0, 1].")

        self.candidate_threshold = float(candidate_threshold)
        self.secondary_threshold = float(secondary_threshold)
        self.persistence_window = int(persistence_window)
        self.persistence_required = int(persistence_required)
        self.max_events = int(max_events)
        self.min_margin = float(min_margin)

        self.encoder = LabelEncoder()
        self._history: dict[int, deque[float]] = defaultdict(
            lambda: deque(maxlen=self.persistence_window)
        )
        self._last_result: dict = {
            "enabled": True,
            "primary_event": None,
            "simultaneous_events": [],
            "candidates": [],
            "frame_count": 0,
            "explanation": "No inference has been analyzed yet.",
        }
        self._frame_count = 0

    def reset(self) -> None:
        """Clear temporal evidence while retaining configuration."""
        self._history.clear()
        self._frame_count = 0
        self._last_result = {
            "enabled": True,
            "primary_event": None,
            "simultaneous_events": [],
            "candidates": [],
            "frame_count": 0,
            "explanation": "Temporal evidence was reset.",
        }

    def analyze(self, probabilities: Iterable[float]) -> dict:
        """Analyze one complete softmax probability vector."""
        vector = np.asarray(list(probabilities), dtype=np.float32).reshape(-1)

        if vector.size == 0:
            raise ValueError("probabilities cannot be empty.")
        if not np.all(np.isfinite(vector)):
            raise ValueError("probabilities contain non-finite values.")
        if np.any(vector < 0.0):
            raise ValueError("probabilities cannot contain negative values.")

        total = float(vector.sum())
        if total <= 0.0:
            raise ValueError("probability vector must have a positive sum.")

        # Be tolerant of tiny floating-point drift while keeping the
        # analyzer independent of the exact tensor implementation.
        if not np.isclose(total, 1.0, atol=1e-3):
            vector = vector / total

        self._frame_count += 1

        primary_id = int(np.argmax(vector))
        primary_probability = float(vector[primary_id])

        # Update temporal evidence for every class. Keeping a value for every
        # class makes the persistence decision deterministic and inexpensive.
        for class_id, probability in enumerate(vector):
            self._history[class_id].append(float(probability))

        candidates: list[MultiEventCandidate] = []

        # The primary event is always represented when it has crossed the
        # general candidate threshold. This does not replace the existing
        # classifier result.
        if primary_probability >= self.candidate_threshold:
            primary_history = self._history[primary_id]
            primary_count = sum(
                p >= self.candidate_threshold for p in primary_history
            )
            candidates.append(
                MultiEventCandidate(
                    label=self._decode(primary_id),
                    class_id=primary_id,
                    confidence=primary_probability,
                    role="primary",
                    persistent=primary_count >= self.persistence_required,
                    evidence_count=primary_count,
                )
            )

        # Secondary events need a substantially higher floor than the generic
        # candidate threshold and must have a meaningful probability margin.
        for class_id, probability in enumerate(vector):
            class_id = int(class_id)
            probability = float(probability)
            if class_id == primary_id:
                continue
            if probability < self.secondary_threshold:
                continue
            if probability < primary_probability * self.min_margin:
                continue

            history = self._history[class_id]
            evidence_count = sum(
                p >= self.secondary_threshold for p in history
            )
            candidates.append(
                MultiEventCandidate(
                    label=self._decode(class_id),
                    class_id=class_id,
                    confidence=probability,
                    role="secondary",
                    persistent=evidence_count >= self.persistence_required,
                    evidence_count=evidence_count,
                )
            )

        # Rank by current confidence. The primary candidate remains first.
        candidates.sort(
            key=lambda item: (
                0 if item.role == "primary" else 1,
                -item.confidence,
            )
        )
        candidates = candidates[: self.max_events]

        primary = next(
            (candidate for candidate in candidates if candidate.role == "primary"),
            None,
        )

        # A secondary event is considered simultaneous only after temporal
        # persistence. This prevents a one-frame model spike from becoming a
        # dashboard alarm.
        simultaneous = [
            candidate
            for candidate in candidates
            if candidate.role == "secondary" and candidate.persistent
        ]

        if simultaneous:
            explanation = (
                "Multiple acoustic candidates are supported by the model "
                "and at least one secondary event has persisted across "
                "multiple inference frames."
            )
        elif any(candidate.role == "secondary" for candidate in candidates):
            explanation = (
                "A secondary acoustic candidate is present, but temporal "
                "evidence is not yet sufficient to confirm simultaneous sound."
            )
        elif primary is not None:
            explanation = (
                "One dominant acoustic event is currently supported; no "
                "secondary event passed the conservative threshold."
            )
        else:
            explanation = (
                "No acoustic event passed the candidate threshold."
            )

        result = {
            "enabled": True,
            "primary_event": primary.to_dict() if primary else None,
            "simultaneous_events": [item.to_dict() for item in simultaneous],
            "candidates": [item.to_dict() for item in candidates],
            "frame_count": self._frame_count,
            "configuration": {
                "candidate_threshold": self.candidate_threshold,
                "secondary_threshold": self.secondary_threshold,
                "persistence_window": self.persistence_window,
                "persistence_required": self.persistence_required,
                "max_events": self.max_events,
                "min_margin": self.min_margin,
            },
            "explanation": explanation,
            "source": "full_softmax_probability_vector",
            "source_separation": False,
        }

        self._last_result = result
        return result

    def get_last_result(self) -> dict:
        """Return the most recent analysis result."""
        return self._last_result

    def _decode(self, class_id: int) -> str:
        try:
            return str(self.encoder.decode(int(class_id)))
        except Exception:
            return f"Class_{int(class_id)}"
