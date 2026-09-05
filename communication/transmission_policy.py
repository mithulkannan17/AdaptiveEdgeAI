"""
Transmission Policy

Determines whether an edge runtime result should be
transmitted to the backend.

The policy respects the transmission mode selected by
the Adaptive Behaviour Engine.
"""

from __future__ import annotations


class TransmissionPolicy:
    """
    Controls backend transmission decisions.
    """

    VALID_MODES = {
        "event_driven",
        "selective",
        "continuous",
    }

    def should_transmit(
        self,
        runtime_result,
    ) -> bool:
        """
        Determine whether a runtime result should be sent.

        Parameters
        ----------
        runtime_result:
            EdgeRuntimeResult produced by EdgeController.

        Returns
        -------
        bool
            True when the result should be transmitted.
        """

        if runtime_result is None:

            raise ValueError(
                "runtime_result cannot be None."
            )

        policy = (
            runtime_result.adaptive_policy
        )

        event = (
            runtime_result.event
        )

        mode = (
            policy.transmission_mode
        )

        # --------------------------------------------------
        # Continuous
        # --------------------------------------------------

        if mode == "continuous":

            return True

        # --------------------------------------------------
        # Event driven
        # --------------------------------------------------

        if mode == "event_driven":

            return bool(
                event.detected
            )

        # --------------------------------------------------
        # Selective
        # --------------------------------------------------

        if mode == "selective":

            if event.detected:

                return True

            # Important state-changing / high-priority
            # events should still be transmitted.
            if event.priority >= 4:

                return True

            return False

        # --------------------------------------------------
        # Unknown mode
        # --------------------------------------------------

        # Safe behaviour:
        # do not transmit when the mode is invalid.
        return False