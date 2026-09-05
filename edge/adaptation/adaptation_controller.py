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
    """

    def __init__(
        self,
        profiler: EnvironmentalProfiler | None = None,
        behavior_engine: AdaptiveBehaviorEngine | None = None,
    ):
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
    # Add Event
    # ======================================================

    def add_event(
        self,
        label: str,
        confidence: float,
        timestamp: float | None = None,
    ) -> AdaptivePolicy:
        """
        Add an acoustic event and update the adaptive state.
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
        Recalculate the environment profile and adaptive
        policy.
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
    # Profile
    # ======================================================

    def get_profile(
        self,
    ) -> EnvironmentProfile:
        """
        Return the current environmental profile.
        """

        if self._profile is None:
            self.update()

        return self._profile

    # ======================================================
    # Policy
    # ======================================================

    def get_policy(
        self,
    ) -> AdaptivePolicy:
        """
        Return the current adaptive policy.
        """

        if self._policy is None:
            self.update()

        return self._policy

    # ======================================================
    # Reset
    # ======================================================

    def reset(self) -> None:
        """
        Reset the profiling window and cached state.
        """

        self.profiler.reset()

        self._profile = None

        self._policy = None

    # ======================================================
    # State
    # ======================================================

    def state(self) -> dict:
        """
        Return the complete adaptive runtime state.
        """

        profile = self.get_profile()

        policy = self.get_policy()

        return {
            "environment_profile":
                profile.to_dict(),

            "adaptive_policy":
                policy.to_dict(),
        }


# ==========================================================
# Backward-compatible alias
# ==========================================================

AdaptationController = AdaptiveRuntimeController