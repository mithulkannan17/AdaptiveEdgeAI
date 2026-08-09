"""
Event Detector

Applies an AdaptivePolicy to a PredictionResult
to determine whether an acoustic event should be
accepted by the edge system.
"""

from __future__ import annotations

from inference.types import PredictionResult

from edge.adaptation.adaptation_policy import (
    AdaptivePolicy,
)

from edge.events.event import Event


class EventDetector:
    """
    Detects acoustic events using the current
    AdaptivePolicy.

    The detector does not modify the neural-network
    prediction. It applies the adaptive policy to it.
    """

    def detect(
        self,
        prediction: PredictionResult,
        policy: AdaptivePolicy,
    ) -> Event:
        """
        Apply an adaptive policy to a model prediction.

        Parameters
        ----------
        prediction:
            Output produced by the inference pipeline.

        policy:
            Current AdaptivePolicy.

        Returns
        -------
        Event
            Adaptive event decision.
        """

        if not isinstance(
            prediction,
            PredictionResult,
        ):

            raise TypeError(
                "prediction must be a PredictionResult."
            )

        if not isinstance(
            policy,
            AdaptivePolicy,
        ):

            raise TypeError(
                "policy must be an AdaptivePolicy."
            )

        label = prediction.label

        confidence = max(
            0.0,
            min(
                1.0,
                float(
                    prediction.confidence
                ),
            ),
        )

        # --------------------------------------------------
        # Ignored class
        # --------------------------------------------------

        if policy.is_ignored(label):

            return Event(

                label=label,

                class_id=prediction.class_id,

                confidence=confidence,

                adjusted_confidence=0.0,

                detection_threshold=(
                    policy.detection_threshold
                ),

                detected=False,

                priority=0,

                environment_type=(
                    policy.environment_type
                ),

                reason=(
                    f"Class '{label}' is ignored "
                    "by the current adaptive policy."
                ),

                inference_time_ms=(
                    prediction.inference_time_ms
                ),

            )

        # --------------------------------------------------
        # Sensitivity adjustment
        # --------------------------------------------------

        sensitivity = (
            policy.sensitivity_for(label)
        )

        adjusted_confidence = max(

            0.0,

            min(

                1.0,

                confidence
                * sensitivity,

            ),

        )

        # --------------------------------------------------
        # Detection decision
        # --------------------------------------------------

        detected = (
            adjusted_confidence
            >= policy.detection_threshold
        )

        priority = (
            policy.priority_for(label)
            if detected
            else 0
        )

        # --------------------------------------------------
        # Reason
        # --------------------------------------------------

        if detected:

            reason = (

                f"Adjusted confidence "
                f"{adjusted_confidence:.4f} "
                f"meets detection threshold "
                f"{policy.detection_threshold:.4f}."

            )

        else:

            reason = (

                f"Adjusted confidence "
                f"{adjusted_confidence:.4f} "
                f"is below detection threshold "
                f"{policy.detection_threshold:.4f}."

            )

        return Event(

            label=label,

            class_id=prediction.class_id,

            confidence=confidence,

            adjusted_confidence=(
                adjusted_confidence
            ),

            detection_threshold=(
                policy.detection_threshold
            ),

            detected=detected,

            priority=priority,

            environment_type=(
                policy.environment_type
            ),

            reason=reason,

            inference_time_ms=(
                prediction.inference_time_ms
            ),

        )