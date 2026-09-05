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
    DecisionMessage,
    EdgeMessage,
    EnvironmentMessage,
    EventMessage,
    PredictionMessage,
)

from communication.telemetry import (
    DeviceTelemetry,
    LocationTelemetry,
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

    # ======================================================
    # Telemetry Normalization
    # ======================================================

    @staticmethod
    def _normalize_location(
        location,
    ) -> Optional[LocationTelemetry]:
        """
        Convert location input into LocationTelemetry.

        Supports:

            LocationTelemetry
            dict
            None
        """

        if location is None:

            return None

        if isinstance(
            location,
            LocationTelemetry,
        ):

            return location

        if isinstance(
            location,
            dict,
        ):

            return LocationTelemetry(
                **location
            )

        raise TypeError(
            "location must be LocationTelemetry, "
            "dict, or None."
        )

    @staticmethod
    def _normalize_device_status(
        device_status,
    ) -> Optional[DeviceTelemetry]:
        """
        Convert device status input into DeviceTelemetry.

        Supports:

            DeviceTelemetry
            dict
            None
        """

        if device_status is None:

            return None

        if isinstance(
            device_status,
            DeviceTelemetry,
        ):

            return device_status

        if isinstance(
            device_status,
            dict,
        ):

            return DeviceTelemetry(
                **device_status
            )

        raise TypeError(
            "device_status must be DeviceTelemetry, "
            "dict, or None."
        )

    # ======================================================
    # Serialization
    # ======================================================

    def serialize(
        self,
        runtime_result,
        timestamp: Optional[float] = None,
        location=None,
        device_status=None,
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
            Optional LocationTelemetry or dictionary.

        device_status:
            Optional DeviceTelemetry or dictionary.
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
            getattr(
                runtime_result,
                "discovery_result",
                None,
            )
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
        # CADIE Decision
        # --------------------------------------------------
        #
        # CADIE is available in the production runtime.
        #
        # However, older/minimal runtime-result objects
        # used by communication tests may not contain a
        # "decision" attribute.
        #
        # getattr() keeps the communication layer backward
        # compatible without weakening the real CADIE path.
        # --------------------------------------------------

        decision_message = None

        decision = getattr(
            runtime_result,
            "decision",
            None,
        )

        if decision is not None:

            decision_message = DecisionMessage(

                risk_level=(
                    decision.risk_level
                ),

                decision_score=(
                    decision.decision_score
                ),

                recommended_action=(
                    decision.recommended_action
                ),

                requires_attention=(
                    decision.requires_attention
                ),

                confidence=(
                    decision.confidence
                ),

                reason=(
                    decision.reason
                ),

                contributing_factors=list(
                    decision.contributing_factors
                ),

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
        # Telemetry
        # --------------------------------------------------

        location_telemetry = (
            self._normalize_location(
                location
            )
        )

        device_telemetry = (
            self._normalize_device_status(
                device_status
            )
        )

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

            decision=decision_message,

            unknown_discovery=discovery,

            location=(
                location_telemetry.to_dict()
                if location_telemetry is not None
                else None
            ),

            device_status=(
                device_telemetry.to_dict()
                if device_telemetry is not None
                else None
            ),

        )