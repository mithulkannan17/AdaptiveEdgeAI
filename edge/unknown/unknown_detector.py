"""
Unknown Sound Detector

Determines whether a model prediction should be
accepted as a known event or rejected as unknown.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UnknownDecision:
    """
    Result of open-set sound detection.
    """

    is_unknown: bool

    predicted_class: int

    confidence: float

    margin: float

    reason: str

    def to_dict(self) -> dict:
        """
        Convert decision to a serializable dictionary.
        """

        return {
            "is_unknown": self.is_unknown,
            "predicted_class": self.predicted_class,
            "confidence": self.confidence,
            "margin": self.margin,
            "reason": self.reason,
        }


class UnknownDetector:
    """
    Confidence-based open-set detector.

    This is the baseline unknown detector.

    It uses:
        1. Maximum class probability.
        2. Margin between the top two classes.

    A later version can incorporate embedding distance
    and calibrated confidence.
    """

    def __init__(
        self,
        confidence_threshold: float = 0.60,
        margin_threshold: float = 0.15,
    ):

        if not 0.0 <= confidence_threshold <= 1.0:

            raise ValueError(
                "confidence_threshold must be "
                "between 0 and 1."
            )

        if not 0.0 <= margin_threshold <= 1.0:

            raise ValueError(
                "margin_threshold must be "
                "between 0 and 1."
            )

        self.confidence_threshold = (
            confidence_threshold
        )

        self.margin_threshold = (
            margin_threshold
        )

    def decide(
        self,
        probabilities,
    ) -> UnknownDecision:
        """
        Decide whether a probability distribution
        represents a known or unknown event.

        Parameters
        ----------
        probabilities:
            Iterable of class probabilities.

        Returns
        -------
        UnknownDecision
        """

        if probabilities is None:

            raise ValueError(
                "probabilities cannot be None."
            )

        probabilities = list(
            float(value)
            for value in probabilities
        )

        if len(probabilities) < 2:

            raise ValueError(
                "At least two class probabilities "
                "are required."
            )

        if any(
            value < 0.0 or value > 1.0
            for value in probabilities
        ):

            raise ValueError(
                "Probabilities must be between 0 and 1."
            )

        ranked = sorted(
            enumerate(probabilities),
            key=lambda item: item[1],
            reverse=True,
        )

        top_class, top_probability = ranked[0]

        second_probability = ranked[1][1]

        margin = (
            top_probability
            - second_probability
        )

        if top_probability < self.confidence_threshold:

            return UnknownDecision(

                is_unknown=True,

                predicted_class=top_class,

                confidence=top_probability,

                margin=margin,

                reason=(
                    "Low classification confidence."
                ),
            )

        if margin < self.margin_threshold:

            return UnknownDecision(

                is_unknown=True,

                predicted_class=top_class,

                confidence=top_probability,

                margin=margin,

                reason=(
                    "Low prediction margin between "
                    "top competing classes."
                ),
            )

        return UnknownDecision(

            is_unknown=False,

            predicted_class=top_class,

            confidence=top_probability,

            margin=margin,

            reason=(
                "Prediction exceeds confidence "
                "and margin thresholds."
            ),
        )