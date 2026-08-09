"""
Communication Serializer

Converts internal EdgeRuntimeResult objects into the
standardized EdgeMessage used by the backend.
"""

from __future__ import annotations

import time
from typing import Optional

from communication.schemas import (
    AdaptivePolicyMessage,
    EdgeMessage,
    EnvironmentMessage,
    EventMessage,
    PredictionMessage,
)


class EdgeMessageSerializer:
    """
    Converts an EdgeRuntimeResult into an EdgeMessage.

    This class forms the boundary between the internal
    edge-intelligence implementation and the communication
    layer.
    """

    def __init__(
        self,
        device_id: str,
    ):
        if not device_id:
            raise ValueError(
                "device_id cannot be empty."
            )

        self.device_id = device_id

    def serialize(
        self,
        runtime_result,
        timestamp: Optional[float] = None,
        location: Optional[dict] = None,
        device_status: Optional[dict] = None,
    ) -> EdgeMessage:
        """
        Convert an EdgeRuntimeResult into an EdgeMessage.

        Parameters
        ----------
        runtime_result:
            EdgeRuntimeResult produced by EdgeController.

        timestamp:
            Unix timestamp. Current time is used when omitted.

        location:
            Optional GPS/device location.

        device_status:
            Optional device telemetry such as battery,
            temperature, humidity, etc.
        """

        if runtime_result is None:
            raise ValueError(
                "runtime_result cannot be None."
            )

        prediction = (
            runtime_result.prediction
        )

        profile = (
            runtime_result.environment_profile
        )

        policy = (
            runtime_result.adaptive_policy
        )

        event = (
            runtime_result.event
        )

        discovery_result = (
            runtime_result.discovery_result
        )

        # --------------------------------------------------
        # Prediction
        # --------------------------------------------------

        prediction_message = (
            PredictionMessage(

                label=prediction.label,

                class_id=prediction.class_id,

                confidence=prediction.confidence,

                inference_time_ms=(
                    prediction.inference_time_ms
                ),

                top_k=list(
                    prediction.top_k
                ),

            )
        )

        # --------------------------------------------------
        # Environment
        # --------------------------------------------------

        environment_message = (
            EnvironmentMessage(

                environment_type=(
                    profile.environment_type
                ),

                observation_count=(
                    profile.observation_count
                ),

                observation_duration_seconds=(
                    profile.observation_duration_seconds
                ),

                event_counts=dict(
                    profile.event_counts
                ),

                event_ratios=dict(
                    profile.event_ratios
                ),

                average_confidence=(
                    profile.average_confidence
                ),

                acoustic_activity=(
                    profile.acoustic_activity
                ),

                natural_score=(
                    profile.natural_score
                ),

                anthropogenic_score=(
                    profile.anthropogenic_score
                ),

                weather_score=(
                    profile.weather_score
                ),

                aquatic_score=(
                    profile.aquatic_score
                ),

                uncertainty=(
                    profile.uncertainty
                ),

            )
        )

        # --------------------------------------------------
        # Adaptive Policy
        # --------------------------------------------------

        policy_message = (
            AdaptivePolicyMessage(

                environment_type=(
                    policy.environment_type
                ),

                detection_threshold=(
                    policy.detection_threshold
                ),

                transmission_mode=(
                    policy.transmission_mode
                ),

                sampling_mode=(
                    policy.sampling_mode
                ),

                class_sensitivity=dict(
                    policy.class_sensitivity
                ),

                class_priority=dict(
                    policy.class_priority
                ),

                ignored_classes=list(
                    policy.ignored_classes
                ),

                reason=policy.reason,

            )
        )

        # --------------------------------------------------
        # Event
        # --------------------------------------------------

        event_message = (
            EventMessage(

                label=event.label,

                class_id=event.class_id,

                confidence=event.confidence,

                adjusted_confidence=(
                    event.adjusted_confidence
                ),

                detection_threshold=(
                    event.detection_threshold
                ),

                detected=event.detected,

                priority=event.priority,

                environment_type=(
                    event.environment_type
                ),

                reason=event.reason,

                inference_time_ms=(
                    event.inference_time_ms
                ),

                metadata=dict(
                    event.metadata
                ),

            )
        )

        # --------------------------------------------------
        # Unknown Discovery
        # --------------------------------------------------

        discovery = None

        if discovery_result is not None:

            if hasattr(
                discovery_result,
                "to_dict",
            ):

                discovery = (
                    discovery_result.to_dict()
                )

            elif isinstance(
                discovery_result,
                dict,
            ):

                discovery = dict(
                    discovery_result
                )

            else:

                discovery = {
                    "value":
                        str(
                            discovery_result
                        )
                }

        # --------------------------------------------------
        # Timestamp
        # --------------------------------------------------

        if timestamp is None:
            timestamp = time.time()

        # --------------------------------------------------
        # Complete Edge Message
        # --------------------------------------------------

        return EdgeMessage(

            device_id=self.device_id,

            timestamp=float(
                timestamp
            ),

            prediction=prediction_message,

            environment=environment_message,

            adaptive_policy=policy_message,

            event=event_message,

            unknown_discovery=discovery,

            location=location,

            device_status=device_status,

        )