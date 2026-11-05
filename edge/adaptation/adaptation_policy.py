"""
Adaptive Policy

Defines the runtime behaviour selected by the
Adaptive Behaviour Engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict


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

    regime: str = "DAY"

    is_night: bool = False

    # ======================================================
    # Class Sensitivity & Adaptive Multipliers
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
    # Dynamic Threshold Formulation
    # Threshold_effective = (Base * Noise * Context) / Multiplier
    # ======================================================

    def effective_threshold_for(
        self,
        label: str,
    ) -> float:
        """
        Calculate the effective raw confidence threshold for a target class:
        Effective Threshold = Policy Threshold / Multiplier.

        A higher threat multiplier (e.g. 1.45 for Chainsaw) reduces the required
        confidence barrier, ensuring faint or distant threat sounds are captured.
        """

        multiplier = self.sensitivity_for(label)

        if multiplier <= 0.0:
            return 1.0

        return max(
            0.0,
            min(
                1.0,
                float(self.detection_threshold / multiplier),
            ),
        )

    def formula_breakdown(
        self,
        label: str,
    ) -> dict[str, Any]:
        """
        Break down the dynamic threshold components:
        Threshold = (Base * Noise * Context) / Multiplier
        """

        multiplier = self.sensitivity_for(label)
        effective = self.effective_threshold_for(label)

        return {
            "environment_type": self.environment_type,
            "regime": self.regime,
            "is_night": self.is_night,
            "policy_threshold": round(self.detection_threshold, 4),
            "threat_multiplier": round(multiplier, 4),
            "effective_threshold": round(effective, 4),
            "formula": (
                f"Policy Threshold ({self.detection_threshold:.2f}) ÷ "
                f"Multiplier ({multiplier:.2f}) = {effective:.4f} Required Confidence"
            ),
        }

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

            "regime":
                self.regime,

            "is_night":
                self.is_night,

        }
