"""
Adaptive Runtime Controller

Connects the EnvironmentalProfiler with the
AdaptiveBehaviorEngine.

The controller maintains the current environmental
profile and the corresponding adaptive runtime policy.
"""

from __future__ import annotations

from edge.adaptation.adaptation_policy import (
    AdaptivePolicy,
)

from edge.adaptation.behavior_engine import (
    AdaptiveBehaviorEngine,
)

from edge.profiling.environment_profile import (
    EnvironmentProfile,
)

from edge.profiling.profiler import (
    EnvironmentalProfiler,
)


class AdaptiveRuntimeController:
    """
    Coordinates environmental profiling and adaptive
    behaviour generation.

    Flow
    ----
    Acoustic event
        ↓
    EnvironmentalProfiler
        ↓
    EnvironmentProfile
        ↓
    AdaptiveBehaviorEngine
        ↓
    AdaptivePolicy

    This class does not perform model inference and does
    not directly control hardware.
    """

    def __init__(
        self,
        profiler: EnvironmentalProfiler | None = None,
        behavior_engine: AdaptiveBehaviorEngine | None = None,
    ):
        """
        Parameters
        ----------
        profiler:
            Existing environmental profiler.

        behavior_engine:
            Existing adaptive behaviour engine.

        If omitted, default instances are created.
        """

        self.profiler = (

            profiler

            if profiler is not None

            else EnvironmentalProfiler()

        )

        self.behavior_engine = (

            behavior_engine

            if behavior_engine is not None

            else AdaptiveBehaviorEngine()

        )

        self._profile: EnvironmentProfile | None = None

        self._policy: AdaptivePolicy | None = None

    # ======================================================
    # Add Acoustic Event
    # ======================================================

    def add_event(
        self,
        label: str,
        confidence: float,
        timestamp: float | None = None,
    ) -> AdaptivePolicy:
        """
        Add an acoustic event and immediately update
        the environmental profile and adaptive policy.

        Returns
        -------
        AdaptivePolicy
            Current adaptive policy.
        """

        self.profiler.add_event(

            label=label,

            confidence=confidence,

            timestamp=timestamp,

        )

        return self.update()

    # ======================================================
    # Update
    # ======================================================

    def update(self) -> AdaptivePolicy:
        """
        Generate a fresh EnvironmentProfile and
        AdaptivePolicy from the current observation window.
        """

        self._profile = (
            self.profiler.profile()
        )

        self._policy = (
            self.behavior_engine.generate_policy(
                self._profile
            )
        )

        return self._policy

    # ======================================================
    # Current Profile
    # ======================================================

    def get_profile(
        self,
    ) -> EnvironmentProfile:
        """
        Return the current environment profile.

        If no profile has been generated yet, one is
        generated automatically.
        """

        if self._profile is None:

            self.update()

        return self._profile

    # ======================================================
    # Current Policy
    # ======================================================

    def get_policy(
        self,
    ) -> AdaptivePolicy:
        """
        Return the current adaptive policy.

        If no policy has been generated yet, one is
        generated automatically.
        """

        if self._policy is None:

            self.update()

        return self._policy

    # ======================================================
    # Reset
    # ======================================================

    def reset(self) -> None:
        """
        Clear the profiling window and reset the cached
        profile and policy.
        """

        self.profiler.reset()

        self._profile = None

        self._policy = None

    # ======================================================
    # Serialization
    # ======================================================

    def state(self) -> dict:
        """
        Return the complete current adaptive state.
        """

        profile = self.get_profile()

        policy = self.get_policy()

        return {

            "environment_profile":
                profile.to_dict(),

            "adaptive_policy":
                policy.to_dict(),

        }