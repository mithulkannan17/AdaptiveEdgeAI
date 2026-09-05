"""
Communication Schemas

Defines the standardized data contract used to transfer
edge intelligence results between the edge node and backend.

These schemas intentionally remain independent of the
internal edge implementation.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional

from communication.telemetry import (
    DeviceTelemetry,
    LocationTelemetry,
)


@dataclass
class PredictionMessage:
    """
    Model prediction transmitted by the edge node.
    """

    label: str

    class_id: int

    confidence: float

    inference_time_ms: float = 0.0

    top_k: list[tuple[str, float]] = field(
        default_factory=list
    )

    def to_dict(self) -> dict:
        """
        Convert prediction into a serializable dictionary.
        """

        return {
            "label": self.label,
            "class_id": self.class_id,
            "confidence": self.confidence,
            "inference_time_ms": self.inference_time_ms,
            "top_k": [
                {
                    "label": label,
                    "confidence": confidence,
                }
                for label, confidence in self.top_k
            ],
        }


@dataclass
class EnvironmentMessage:
    """
    Environmental context inferred by the edge node.
    """

    environment_type: str

    observation_count: int

    observation_duration_seconds: float

    event_counts: dict[str, int] = field(
        default_factory=dict
    )

    event_ratios: dict[str, float] = field(
        default_factory=dict
    )

    average_confidence: float = 0.0

    acoustic_activity: float = 0.0

    natural_score: float = 0.0

    anthropogenic_score: float = 0.0

    weather_score: float = 0.0

    aquatic_score: float = 0.0

    uncertainty: float = 1.0

    def to_dict(self) -> dict:
        """
        Convert environmental context into a dictionary.
        """

        return asdict(self)


@dataclass
class AdaptivePolicyMessage:
    """
    Adaptive policy currently applied by the edge node.
    """

    environment_type: str

    detection_threshold: float

    transmission_mode: str

    sampling_mode: str

    class_sensitivity: dict[str, float] = field(
        default_factory=dict
    )

    class_priority: dict[str, int] = field(
        default_factory=dict
    )

    ignored_classes: list[str] = field(
        default_factory=list
    )

    reason: str = ""

    def to_dict(self) -> dict:
        """
        Convert adaptive policy into a dictionary.
        """

        return asdict(self)


@dataclass
class EventMessage:
    """
    Event detection and prioritization result.
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

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def to_dict(self) -> dict:
        """
        Convert event information into a dictionary.
        """

        return asdict(self)


@dataclass
class DecisionMessage:
    """
    Context-aware decision produced by CADIE.
    """

    risk_level: str

    decision_score: float

    recommended_action: str

    requires_attention: bool

    confidence: float

    reason: str

    contributing_factors: list[str] = field(
        default_factory=list
    )

    def to_dict(self) -> dict:
        """
        Convert CADIE decision into a serializable
        dictionary.
        """

        return {
            "risk_level":
                self.risk_level,

            "decision_score":
                self.decision_score,

            "recommended_action":
                self.recommended_action,

            "requires_attention":
                self.requires_attention,

            "confidence":
                self.confidence,

            "reason":
                self.reason,

            "contributing_factors":
                list(
                    self.contributing_factors
                ),
        }


@dataclass
class EdgeMessage:
    """
    Complete message transmitted from the edge node.

    This is the main communication contract between
    edge intelligence and backend services.

    Location and device status remain dictionaries at
    the communication boundary for backward compatibility
    and direct JSON serialization.
    """

    device_id: str

    timestamp: float

    prediction: PredictionMessage

    environment: EnvironmentMessage

    adaptive_policy: AdaptivePolicyMessage

    event: EventMessage

    decision: Optional[DecisionMessage] = None

    unknown_discovery: Optional[dict] = None

    location: Optional[dict] = None

    device_status: Optional[dict] = None

    def to_dict(self) -> dict:
        """
        Convert the complete edge message into
        a JSON-compatible dictionary.
        """

        return {

            "device_id":
                self.device_id,

            "timestamp":
                self.timestamp,

            "prediction":
                self.prediction.to_dict(),

            "environment":
                self.environment.to_dict(),

            "adaptive_policy":
                self.adaptive_policy.to_dict(),

            "event":
                self.event.to_dict(),

            "decision":
                (
                    self.decision.to_dict()
                    if self.decision is not None
                    else None
                ),

            "unknown_discovery":
                self.unknown_discovery,

            "location":
                self.location,

            "device_status":
                self.device_status,

        }