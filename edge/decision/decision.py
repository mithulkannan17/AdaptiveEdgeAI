"""
CADIE Decision Data Types

Defines the standardized decision produced by the
Context-Aware Decision Intelligence Engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DecisionResult:
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
        Convert the decision into a serializable
        dictionary.
        """

        return {
            "risk_level": self.risk_level,
            "decision_score": self.decision_score,
            "recommended_action": (
                self.recommended_action
            ),
            "requires_attention": (
                self.requires_attention
            ),
            "confidence": self.confidence,
            "reason": self.reason,
            "contributing_factors": list(
                self.contributing_factors
            ),
        }