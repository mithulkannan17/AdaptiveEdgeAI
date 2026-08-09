"""
Adaptive Policy

Defines the runtime behaviour selected by the
Adaptive Behaviour Engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict


@dataclass(frozen=True)
class AdaptivePolicy:
    """
    Runtime policy produced by the Adaptive Behaviour Engine.

    The policy describes how the edge node should behave
    under the currently detected environmental conditions.
    """

    environment_type: str

    detection_threshold: float

    transmission_mode: str

    sampling_mode: str

    class_sensitivity: Dict[str, float] = field(
        default_factory=dict
    )

    class_priority: Dict[str, int] = field(
        default_factory=dict
    )

    ignored_classes: tuple[str, ...] = ()

    reason: str = ""

    # ======================================================
    # Class Sensitivity
    # ======================================================

    def sensitivity_for(
        self,
        label: str,
    ) -> float:
        """
        Return the sensitivity multiplier for a class.

        A value greater than 1.0 increases sensitivity.

        A value below 1.0 decreases sensitivity.

        1.0 means no adjustment.
        """

        return self.class_sensitivity.get(
            label,
            1.0,
        )

    # ======================================================
    # Class Priority
    # ======================================================

    def priority_for(
        self,
        label: str,
    ) -> int:
        """
        Return the priority assigned to a class.

        Higher values indicate greater event priority.
        """

        return self.class_priority.get(
            label,
            1,
        )

    # ======================================================
    # Ignored Classes
    # ======================================================

    def is_ignored(
        self,
        label: str,
    ) -> bool:
        """
        Determine whether a class is currently ignored.
        """

        return (
            label
            in self.ignored_classes
        )

    # ======================================================
    # Serialization
    # ======================================================

    def to_dict(
        self,
    ) -> dict:
        """
        Convert policy into a serializable dictionary.
        """

        return {

            "environment_type":
                self.environment_type,

            "detection_threshold":
                self.detection_threshold,

            "transmission_mode":
                self.transmission_mode,

            "sampling_mode":
                self.sampling_mode,

            "class_sensitivity":
                dict(
                    self.class_sensitivity
                ),

            "class_priority":
                dict(
                    self.class_priority
                ),

            "ignored_classes":
                list(
                    self.ignored_classes
                ),

            "reason":
                self.reason,

        }