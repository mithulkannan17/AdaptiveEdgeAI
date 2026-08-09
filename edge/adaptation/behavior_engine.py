"""
Adaptive Behaviour Engine

Converts an environmental profile into an
adaptive runtime policy.
"""

from __future__ import annotations

from edge.adaptation.adaptation_policy import (
    AdaptivePolicy,
)

from edge.profiling.environment_profile import (
    EnvironmentProfile,
)


class AdaptiveBehaviorEngine:
    """
    Selects edge behaviour according to the current
    environmental profile.

    The engine does not directly control hardware.

    It produces an AdaptivePolicy that can later be
    consumed by the edge controller.
    """

    # ======================================================
    # Default Configuration
    # ======================================================

    DEFAULT_SENSITIVITY = 1.0

    BASE_PRIORITY = {

        "Bird": 1,

        "Chainsaw": 5,

        "Drill": 4,

        "EmergencyVehicle": 5,

        "Fire": 5,

        "Footsteps": 2,

        "Human": 3,

        "Insects": 1,

        "Jackhammer": 4,

        "Thunderstorm": 2,

        "Vehicle": 3,

        "Water": 1,

        "Wildlife": 4,

        "Wind": 1,

    }

    # ======================================================
    # Constructor
    # ======================================================

    def __init__(
        self,
        minimum_threshold: float = 0.40,
        maximum_threshold: float = 0.80,
        uncertainty_threshold: float = 0.60,
    ):
        """
        Parameters
        ----------
        minimum_threshold:
            Lowest allowed detection threshold.

        maximum_threshold:
            Highest allowed detection threshold.

        uncertainty_threshold:
            Profiles with uncertainty at or above this
            value receive conservative behaviour.
        """

        if not (
            0.0
            <= minimum_threshold
            <= 1.0
        ):

            raise ValueError(
                "minimum_threshold must be between 0 and 1."
            )

        if not (
            0.0
            <= maximum_threshold
            <= 1.0
        ):

            raise ValueError(
                "maximum_threshold must be between 0 and 1."
            )

        if minimum_threshold > maximum_threshold:

            raise ValueError(
                "minimum_threshold cannot exceed "
                "maximum_threshold."
            )

        if not (
            0.0
            <= uncertainty_threshold
            <= 1.0
        ):

            raise ValueError(
                "uncertainty_threshold must be between 0 and 1."
            )

        self.minimum_threshold = (
            minimum_threshold
        )

        self.maximum_threshold = (
            maximum_threshold
        )

        self.uncertainty_threshold = (
            uncertainty_threshold
        )

    # ======================================================
    # Utility
    # ======================================================

    def _clamp(
        self,
        value: float,
    ) -> float:
        """
        Clamp a detection threshold to the configured
        safe range.
        """

        return max(

            self.minimum_threshold,

            min(
                self.maximum_threshold,
                value,
            ),

        )

    def _base_sensitivity(
        self,
    ) -> dict:

        return {

            label:
                self.DEFAULT_SENSITIVITY

            for label
            in self.BASE_PRIORITY

        }

    def _base_priorities(
        self,
    ) -> dict:

        return dict(
            self.BASE_PRIORITY
        )

    # ======================================================
    # Natural Environment
    # ======================================================

    def _natural_policy(
        self,
        profile: EnvironmentProfile,
    ) -> AdaptivePolicy:
        """
        Policy for predominantly natural environments.
        """

        sensitivity = (
            self._base_sensitivity()
        )

        priority = (
            self._base_priorities()
        )

        sensitivity.update({

            "Bird": 1.20,

            "Wildlife": 1.25,

            "Insects": 1.15,

            "Chainsaw": 1.30,

            "Fire": 1.30,

        })

        priority.update({

            "Chainsaw": 5,

            "Fire": 5,

            "Wildlife": 4,

        })

        return AdaptivePolicy(

            environment_type=(
                profile.environment_type
            ),

            detection_threshold=(
                self._clamp(0.55)
            ),

            transmission_mode="selective",

            sampling_mode="active",

            class_sensitivity=sensitivity,

            class_priority=priority,

            ignored_classes=(),

            reason=(
                "Natural acoustic environment: "
                "wildlife sensitivity is increased while "
                "potentially critical anthropogenic events "
                "remain highly prioritized."
            ),

        )

    # ======================================================
    # Anthropogenic Environment
    # ======================================================

    def _anthropogenic_policy(
        self,
        profile: EnvironmentProfile,
    ) -> AdaptivePolicy:
        """
        Policy for predominantly anthropogenic environments.
        """

        sensitivity = (
            self._base_sensitivity()
        )

        priority = (
            self._base_priorities()
        )

        sensitivity.update({

            "Human": 1.20,

            "Vehicle": 1.20,

            "EmergencyVehicle": 1.30,

            "Chainsaw": 1.25,

            "Drill": 1.15,

            "Jackhammer": 1.15,

        })

        priority.update({

            "EmergencyVehicle": 5,

            "Chainsaw": 5,

            "Human": 3,

            "Vehicle": 3,

        })

        return AdaptivePolicy(

            environment_type=(
                profile.environment_type
            ),

            detection_threshold=(
                self._clamp(0.60)
            ),

            transmission_mode="selective",

            sampling_mode="active",

            class_sensitivity=sensitivity,

            class_priority=priority,

            ignored_classes=(),

            reason=(
                "Anthropogenic acoustic environment: "
                "human activity, vehicles and mechanical "
                "events receive increased sensitivity."
            ),

        )

    # ======================================================
    # Weather Environment
    # ======================================================

    def _weather_policy(
        self,
        profile: EnvironmentProfile,
    ) -> AdaptivePolicy:
        """
        Policy for weather-dominant environments.
        """

        sensitivity = (
            self._base_sensitivity()
        )

        priority = (
            self._base_priorities()
        )

        sensitivity.update({

            "Thunderstorm": 0.80,

            "Wind": 0.60,

            "Bird": 1.10,

            "Wildlife": 1.10,

            "Fire": 1.30,

            "Chainsaw": 1.30,

        })

        return AdaptivePolicy(

            environment_type=(
                profile.environment_type
            ),

            detection_threshold=(
                self._clamp(0.65)
            ),

            transmission_mode="event_driven",

            sampling_mode="adaptive",

            class_sensitivity=sensitivity,

            class_priority=priority,

            ignored_classes=(),

            reason=(
                "Weather-dominant environment: "
                "persistent weather sounds are treated "
                "as background while potentially important "
                "events remain sensitive."
            ),

        )

    # ======================================================
    # Aquatic Environment
    # ======================================================

    def _aquatic_policy(
        self,
        profile: EnvironmentProfile,
    ) -> AdaptivePolicy:
        """
        Policy for aquatic environments.
        """

        sensitivity = (
            self._base_sensitivity()
        )

        priority = (
            self._base_priorities()
        )

        sensitivity.update({

            "Water": 0.70,

            "Wildlife": 1.20,

            "Bird": 1.15,

            "Human": 1.10,

            "Vehicle": 1.10,

        })

        return AdaptivePolicy(

            environment_type=(
                profile.environment_type
            ),

            detection_threshold=(
                self._clamp(0.55)
            ),

            transmission_mode="selective",

            sampling_mode="adaptive",

            class_sensitivity=sensitivity,

            class_priority=priority,

            ignored_classes=(),

            reason=(
                "Aquatic environment: persistent water "
                "sounds are down-weighted while biological "
                "and human activity remains observable."
            ),

        )

    # ======================================================
    # Mixed Environment
    # ======================================================

    def _mixed_policy(
        self,
        profile: EnvironmentProfile,
    ) -> AdaptivePolicy:
        """
        Conservative policy for mixed environments.
        """

        sensitivity = (
            self._base_sensitivity()
        )

        priority = (
            self._base_priorities()
        )

        return AdaptivePolicy(

            environment_type=(
                profile.environment_type
            ),

            detection_threshold=(
                self._clamp(0.50)
            ),

            transmission_mode="selective",

            sampling_mode="active",

            class_sensitivity=sensitivity,

            class_priority=priority,

            ignored_classes=(),

            reason=(
                "Mixed acoustic environment: conservative "
                "adaptive behaviour is used because no "
                "single environmental context dominates."
            ),

        )

    # ======================================================
    # Unknown / Insufficient Environment
    # ======================================================

    def _unknown_policy(
        self,
        profile: EnvironmentProfile,
    ) -> AdaptivePolicy:
        """
        Safe default policy when the environment is unknown,
        insufficient, or highly uncertain.
        """

        sensitivity = (
            self._base_sensitivity()
        )

        priority = (
            self._base_priorities()
        )

        return AdaptivePolicy(

            environment_type=(
                profile.environment_type
            ),

            detection_threshold=(
                self._clamp(0.50)
            ),

            transmission_mode="selective",

            sampling_mode="active",

            class_sensitivity=sensitivity,

            class_priority=priority,

            ignored_classes=(),

            reason=(
                "Environmental context is unavailable "
                "or uncertain; conservative default "
                "behaviour is applied."
            ),

        )

    # ======================================================
    # Public API
    # ======================================================

    def generate_policy(
        self,
        profile: EnvironmentProfile,
    ) -> AdaptivePolicy:
        """
        Generate an adaptive policy from an
        EnvironmentProfile.
        """

        if not isinstance(
            profile,
            EnvironmentProfile,
        ):

            raise TypeError(
                "profile must be an EnvironmentProfile."
            )

        # --------------------------------------------------
        # No observations
        # --------------------------------------------------

        if profile.observation_count <= 0:

            return self._unknown_policy(
                profile
            )

        # --------------------------------------------------
        # High uncertainty
        # --------------------------------------------------

        if (
            profile.uncertainty
            >= self.uncertainty_threshold
        ):

            return self._unknown_policy(
                profile
            )

        # --------------------------------------------------
        # Environment classification
        # --------------------------------------------------

        environment = (
            profile.environment_type
        )

        if environment == "Natural":

            return self._natural_policy(
                profile
            )

        if environment == "Anthropogenic":

            return self._anthropogenic_policy(
                profile
            )

        if environment == "WeatherDominant":

            return self._weather_policy(
                profile
            )

        if environment == "Aquatic":

            return self._aquatic_policy(
                profile
            )

        if environment == "Mixed":

            return self._mixed_policy(
                profile
            )

        return self._unknown_policy(
            profile
        )