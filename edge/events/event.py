"""
Event Data Structure

Represents an acoustic event after adaptive
detection and prioritization.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class Event:
    """
    Represents a detected environmental acoustic event.

    Attributes
    ----------
    label:
        Human-readable event class.

    class_id:
        Numerical class identifier.

    confidence:
        Original CNN confidence.

    adjusted_confidence:
        Confidence after applying adaptive class
        sensitivity.

    detection_threshold:
        Threshold used by the adaptive policy.

    detected:
        Whether the event passed adaptive detection.

    priority:
        Event priority.

    environment_type:
        Environmental context at detection time.

    reason:
        Explanation for the detection decision.

    inference_time_ms:
        CNN inference latency.

    metadata:
        Optional additional event metadata.
    """

    label: str

    class_id: int

    confidence: float

    adjusted_confidence: float

    detection_threshold: float

    detected: bool

    priority: int

    environment_type: str

    reason: str = ""

    inference_time_ms: float = 0.0

    metadata: dict = field(
        default_factory=dict
    )

    def to_dict(
        self,
    ) -> dict:
        """
        Convert the event into a serializable dictionary.
        """

        return {

            "label":
                self.label,

            "class_id":
                self.class_id,

            "confidence":
                self.confidence,

            "adjusted_confidence":
                self.adjusted_confidence,

            "detection_threshold":
                self.detection_threshold,

            "detected":
                self.detected,

            "priority":
                self.priority,

            "environment_type":
                self.environment_type,

            "reason":
                self.reason,

            "inference_time_ms":
                self.inference_time_ms,

            "metadata":
                dict(self.metadata),

        }