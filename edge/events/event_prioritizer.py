"""
Event Prioritizer

Assigns operational priority to detected acoustic events.
"""

from __future__ import annotations

from edge.adaptation.adaptation_policy import (
    AdaptivePolicy,
)

from edge.events.event import Event


class EventPrioritizer:
    """
    Converts a detected Event into an operationally
    prioritized event.

    Priority is derived from the AdaptivePolicy and
    adjusted confidence.
    """

    # Priority levels used by the edge system.

    LOW = 1

    MEDIUM = 2

    HIGH = 3

    CRITICAL = 4

    def prioritize(
        self,
        event: Event,
        policy: AdaptivePolicy,
    ) -> Event:
        """
        Assign operational priority to an event.

        Undetected events always receive priority 0.
        """

        if not isinstance(
            event,
            Event,
        ):

            raise TypeError(
                "event must be an Event."
            )

        if not isinstance(
            policy,
            AdaptivePolicy,
        ):

            raise TypeError(
                "policy must be an AdaptivePolicy."
            )

        # --------------------------------------------------
        # Undetected event
        # --------------------------------------------------

        if not event.detected:

            return event

        base_priority = (
            policy.priority_for(
                event.label
            )
        )

        # --------------------------------------------------
        # Critical events
        #
        # Policy priority 5 is reserved for events
        # requiring immediate attention.
        # --------------------------------------------------

        if base_priority >= 5:

            priority = self.CRITICAL

        elif base_priority >= 4:

            priority = self.HIGH

        elif base_priority >= 2:

            priority = self.MEDIUM

        else:

            priority = self.LOW

        # --------------------------------------------------
        # Metadata describing the operational priority
        # --------------------------------------------------

        metadata = dict(
            event.metadata
        )

        metadata.update({

            "policy_priority":
                base_priority,

            "operational_priority":
                priority,

        })

        return Event(

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

            priority=priority,

            environment_type=(
                event.environment_type
            ),

            reason=event.reason,

            inference_time_ms=(
                event.inference_time_ms
            ),

            metadata=metadata,

        )