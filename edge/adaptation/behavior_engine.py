"""
Adaptive Behaviour Engine

Converts an environmental profile into an
adaptive runtime policy. Supports day/night adaptive
thresholding using BH1750 ambient light telemetry
and temporal context.
"""

from __future__ import annotations

from typing import Optional

from edge.adaptation.adaptation_policy import (
    AdaptivePolicy,
)

from edge.profiling.environment_profile import (
    EnvironmentProfile,
)


class AdaptiveBehaviorEngine:
    """
    Selects edge behaviour according to the current
    environmental profile and diurnal/nocturnal cycle.

    The engine does not directly control hardware.

    It produces an AdaptivePolicy that can later be
    consumed by the edge controller.
    """

    # ======================================================
    # Default Configuration
    # ======================================================

    DEFAULT_SENSITIVITY = 1.0

    DEFAULT_NIGHT_LUX_THRESHOLD = 15.0

    BASE_PRIORITY = {

        "Fire": 5,           # High (Highest priority)

        "Chainsaw": 5,       # High / Logging (Highest priority)

        "Drill": 5,          # High / Logging (Highest priority)

        "Jackhammer": 5,     # High / Logging (Highest priority)

        "Gunshot": 5,        # High (Highest priority)

        "Vehicle": 3,        # Moderate (Need to be addressed)

        "EmergencyVehicle": 3, # Moderate (Need to be addressed)

        "Human": 3,          # Moderate (Need to be addressed)

        "Footsteps": 3,      # Moderate (Need to be addressed)

        "Wildlife": 2,       # Low

        "Thunderstorm": 2,   # Low

        "Bird": 1,           # Low

        "Insects": 1,        # Low

        "Water": 1,          # Low

        "Wind": 1,           # Low

    }

    # ======================================================
    # Dynamic Threshold Mathematical Formula:
    # Threshold_effective = (Base * Noise * Context) / Multiplier
    # ======================================================

    @staticmethod
    def calculate_adaptive_threshold(
        base_threshold: float = 0.50,
        noise_factor: float = 1.0,
        context_factor: float = 1.0,
        threat_multiplier: float = 1.0,
    ) -> float:
        """
        Formal AuraForest Adaptive Threshold Formula:
        Threshold_effective = (Base * Noise * Context) / Threat_Multiplier

        Parameters
        ----------
        base_threshold:
            Nominal baseline confidence threshold (default 0.50).
        noise_factor:
            Acoustic noise floor multiplier (1.0 Natural, 1.30 Weather/Wind).
        context_factor:
            Diurnal context factor (1.00 Day, 0.82 Night via BH1750 < 15 lx).
        threat_multiplier:
            Class sensitivity multiplier (e.g. 1.45 for Chainsaw, 1.45 for Gunshot).
        """
        if threat_multiplier <= 0:
            threat_multiplier = 1.0
        return max(
            0.05,
            min(
                0.95,
                float((base_threshold * noise_factor * context_factor) / threat_multiplier),
            ),
        )

    # ======================================================
    # Constructor
    # ======================================================

    def __init__(
        self,
        minimum_threshold: float = 0.40,
        maximum_threshold: float = 0.80,
        uncertainty_threshold: float = 0.60,
        night_lux_threshold: float = 15.0,
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

        night_lux_threshold:
            BH1750 ambient light level in Lux below which
            the environment is categorized as Night.
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

        self.night_lux_threshold = (
            float(night_lux_threshold)
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
    # Day / Night Determination
    # ======================================================

    def determine_day_night(
        self,
        device_status: Optional[dict] = None,
        timestamp: Optional[float] = None,
    ) -> tuple[bool, str, Optional[float]]:
        """
        Determine whether current conditions are Diurnal (Day)
        or Nocturnal (Night).

        Parameters
        ----------
        device_status:
            Optional hardware telemetry dictionary containing
            'light_level', 'light_lux', or 'is_night'.

        timestamp:
            Optional epoch timestamp.

        Returns
        -------
        tuple[bool, str, Optional[float]]
            (is_night, reason_text, light_lux)
        """

        if device_status:
            # 1. Explicit boolean flag if already computed
            if "is_night" in device_status:
                is_night = bool(device_status["is_night"])
                lux_val = device_status.get("light_level", device_status.get("light_lux"))
                return is_night, "reported by hardware telemetry flag", float(lux_val) if lux_val is not None else None

            # 2. BH1750 ambient light reading (optical lux)
            light_val = device_status.get("light_level")
            if light_val is None:
                light_val = device_status.get("light_lux")

            if light_val is not None:
                try:
                    lux = float(light_val)
                    if lux < self.night_lux_threshold:
                        return True, f"BH1750 ambient light {lux:.1f} lx < {self.night_lux_threshold:.1f} lx (Night)", lux
                    else:
                        return False, f"BH1750 ambient light {lux:.1f} lx >= {self.night_lux_threshold:.1f} lx (Day)", lux
                except (TypeError, ValueError):
                    pass

            # 3. Explicit clock hour if present
            if "hour" in device_status:
                try:
                    hour = int(device_status["hour"])
                    is_night = (hour < 6 or hour >= 18)
                    return is_night, f"telemetry clock {hour:02d}:00", None
                except (TypeError, ValueError):
                    pass

        # 4. Optional timestamp fallback
        if timestamp is not None:
            try:
                import datetime
                dt = datetime.datetime.fromtimestamp(float(timestamp), tz=datetime.timezone.utc)
                is_night = (dt.hour < 6 or dt.hour >= 18)
                return is_night, f"GPS/UTC timestamp {dt.hour:02d}:00", None
            except Exception:
                pass

        # Default fallback to daytime baseline
        return False, "default diurnal baseline", None

    # ======================================================
    # Natural Environment
    # ======================================================

    def _natural_policy(
        self,
        profile: EnvironmentProfile,
        is_night: bool = False,
        lux: Optional[float] = None,
    ) -> AdaptivePolicy:
        """
        Policy for predominantly natural environments with
        day/night adaptive thresholding.
        """

        sensitivity = (
            self._base_sensitivity()
        )

        priority = (
            self._base_priorities()
        )

        priority.update({

            "Fire": 5,

            "Chainsaw": 5,

            "Drill": 5,

            "Gunshot": 5,

            "Vehicle": 3,

            "Human": 3,

            "Wildlife": 2,

        })

        if is_night:
            # Nocturnal canopy: quieter acoustic floor, human/logging events
            # are strongly anomalous -> lower threshold (higher vigilance).
            threshold = self._clamp(0.45)

            sensitivity.update({

                "Bird": 0.90,

                "Wildlife": 1.20,

                "Insects": 1.20,

                "Chainsaw": 1.45,

                "Fire": 1.35,

                "Gunshot": 1.45,

                "Drill": 1.40,

                "Human": 1.35,

                "Vehicle": 1.30,

            })

            lux_info = f" (BH1750: {lux:.1f} lx)" if lux is not None else ""
            reason = (
                f"Natural environment (Night regime){lux_info}: "
                f"nocturnal acoustic floor lowers detection threshold to {threshold:.2f}; "
                "illicit logging and poaching threats receive heightened sensitivity."
            )
            regime = "NIGHT"

        else:
            # Diurnal canopy: standard daytime threshold to reject daytime noise
            threshold = self._clamp(0.55)

            sensitivity.update({

                "Bird": 1.20,

                "Wildlife": 1.25,

                "Insects": 1.15,

                "Chainsaw": 1.30,

                "Fire": 1.30,

                "Human": 1.25,

                "Footsteps": 1.20,

            })

            lux_info = f" (BH1750: {lux:.1f} lx)" if lux is not None else ""
            reason = (
                f"Natural acoustic environment (Day regime){lux_info}: "
                "wildlife sensitivity is increased while "
                "potentially critical anthropogenic events "
                "remain highly prioritized."
            )
            regime = "DAY"

        return AdaptivePolicy(

            environment_type=(
                profile.environment_type
            ),

            detection_threshold=threshold,

            transmission_mode="selective",

            sampling_mode="active",

            class_sensitivity=sensitivity,

            class_priority=priority,

            ignored_classes=(),

            reason=reason,

            regime=regime,

            is_night=is_night,

        )

    # ======================================================
    # Anthropogenic Environment
    # ======================================================

    def _anthropogenic_policy(
        self,
        profile: EnvironmentProfile,
        is_night: bool = False,
        lux: Optional[float] = None,
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

        priority.update({

            "Fire": 5,

            "Chainsaw": 5,

            "Drill": 5,

            "Jackhammer": 5,

            "EmergencyVehicle": 3,

            "Human": 3,

            "Vehicle": 3,

        })

        if is_night:
            threshold = self._clamp(0.48)

            sensitivity.update({

                "Human": 1.35,

                "Vehicle": 1.30,

                "EmergencyVehicle": 1.30,

                "Chainsaw": 1.40,

                "Drill": 1.30,

                "Jackhammer": 1.30,

                "Gunshot": 1.45,

            })

            lux_info = f" (BH1750: {lux:.1f} lx)" if lux is not None else ""
            reason = (
                f"Anthropogenic environment (Night regime){lux_info}: "
                f"mechanical activity after dark triggers sensitive threshold {threshold:.2f}."
            )
            regime = "NIGHT"

        else:
            threshold = self._clamp(0.60)

            sensitivity.update({

                "Human": 1.20,

                "Vehicle": 1.20,

                "EmergencyVehicle": 1.30,

                "Chainsaw": 1.25,

                "Drill": 1.15,

                "Jackhammer": 1.15,

            })

            lux_info = f" (BH1750: {lux:.1f} lx)" if lux is not None else ""
            reason = (
                f"Anthropogenic acoustic environment (Day regime){lux_info}: "
                "human activity, vehicles and mechanical "
                "events receive increased sensitivity."
            )
            regime = "DAY"

        return AdaptivePolicy(

            environment_type=(
                profile.environment_type
            ),

            detection_threshold=threshold,

            transmission_mode="selective",

            sampling_mode="active",

            class_sensitivity=sensitivity,

            class_priority=priority,

            ignored_classes=(),

            reason=reason,

            regime=regime,

            is_night=is_night,

        )

    # ======================================================
    # Weather Environment
    # ======================================================

    def _weather_policy(
        self,
        profile: EnvironmentProfile,
        is_night: bool = False,
        lux: Optional[float] = None,
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

        if is_night:
            threshold = self._clamp(0.52)

            sensitivity.update({

                "Thunderstorm": 0.80,

                "Wind": 0.60,

                "Bird": 0.85,

                "Wildlife": 1.10,

                "Fire": 1.35,

                "Chainsaw": 1.40,

                "Gunshot": 1.45,

            })

            lux_info = f" (BH1750: {lux:.1f} lx)" if lux is not None else ""
            reason = (
                f"Weather-dominant environment (Night regime){lux_info}: "
                f"threshold adapted to {threshold:.2f} for nocturnal weather conditions."
            )
            regime = "NIGHT"

        else:
            threshold = self._clamp(0.65)

            sensitivity.update({

                "Thunderstorm": 0.80,

                "Wind": 0.60,

                "Bird": 1.10,

                "Wildlife": 1.10,

                "Fire": 1.30,

                "Chainsaw": 1.30,

            })

            lux_info = f" (BH1750: {lux:.1f} lx)" if lux is not None else ""
            reason = (
                f"Weather-dominant environment (Day regime){lux_info}: "
                "persistent weather sounds are treated "
                "as background while potentially important "
                "events remain sensitive."
            )
            regime = "DAY"

        return AdaptivePolicy(

            environment_type=(
                profile.environment_type
            ),

            detection_threshold=threshold,

            transmission_mode="event_driven",

            sampling_mode="adaptive",

            class_sensitivity=sensitivity,

            class_priority=priority,

            ignored_classes=(),

            reason=reason,

            regime=regime,

            is_night=is_night,

        )

    # ======================================================
    # Aquatic Environment
    # ======================================================

    def _aquatic_policy(
        self,
        profile: EnvironmentProfile,
        is_night: bool = False,
        lux: Optional[float] = None,
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

        if is_night:
            threshold = self._clamp(0.46)

            sensitivity.update({

                "Water": 0.70,

                "Wildlife": 1.20,

                "Bird": 0.90,

                "Human": 1.25,

                "Vehicle": 1.25,

                "Chainsaw": 1.40,

            })

            lux_info = f" (BH1750: {lux:.1f} lx)" if lux is not None else ""
            reason = (
                f"Aquatic environment (Night regime){lux_info}: "
                f"threshold adapted to {threshold:.2f}."
            )
            regime = "NIGHT"

        else:
            threshold = self._clamp(0.55)

            sensitivity.update({

                "Water": 0.70,

                "Wildlife": 1.20,

                "Bird": 1.15,

                "Human": 1.10,

                "Vehicle": 1.10,

            })

            lux_info = f" (BH1750: {lux:.1f} lx)" if lux is not None else ""
            reason = (
                f"Aquatic environment (Day regime){lux_info}: "
                "persistent water sounds are down-weighted while biological "
                "and human activity remains observable."
            )
            regime = "DAY"

        return AdaptivePolicy(

            environment_type=(
                profile.environment_type
            ),

            detection_threshold=threshold,

            transmission_mode="selective",

            sampling_mode="adaptive",

            class_sensitivity=sensitivity,

            class_priority=priority,

            ignored_classes=(),

            reason=reason,

            regime=regime,

            is_night=is_night,

        )

    # ======================================================
    # Mixed Environment
    # ======================================================

    def _mixed_policy(
        self,
        profile: EnvironmentProfile,
        is_night: bool = False,
        lux: Optional[float] = None,
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

        threshold = self._clamp(0.42 if is_night else 0.50)
        regime = "NIGHT" if is_night else "DAY"
        lux_info = f" (BH1750: {lux:.1f} lx)" if lux is not None else ""

        return AdaptivePolicy(

            environment_type=(
                profile.environment_type
            ),

            detection_threshold=threshold,

            transmission_mode="selective",

            sampling_mode="active",

            class_sensitivity=sensitivity,

            class_priority=priority,

            ignored_classes=(),

            reason=(
                f"Mixed acoustic environment ({regime} regime){lux_info}: "
                f"adaptive threshold set to {threshold:.2f}."
            ),

            regime=regime,

            is_night=is_night,

        )

    # ======================================================
    # Unknown / Insufficient Environment
    # ======================================================

    def _unknown_policy(
        self,
        profile: EnvironmentProfile,
        is_night: bool = False,
        lux: Optional[float] = None,
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

        threshold = self._clamp(0.42 if is_night else 0.50)
        regime = "NIGHT" if is_night else "DAY"
        lux_info = f" (BH1750: {lux:.1f} lx)" if lux is not None else ""

        return AdaptivePolicy(

            environment_type=(
                profile.environment_type
            ),

            detection_threshold=threshold,

            transmission_mode="selective",

            sampling_mode="active",

            class_sensitivity=sensitivity,

            class_priority=priority,

            ignored_classes=(),

            reason=(
                f"Environmental context uncertain ({regime} regime){lux_info}: "
                f"adaptive fallback threshold {threshold:.2f} applied."
            ),

            regime=regime,

            is_night=is_night,

        )

    # ======================================================
    # Public API
    # ======================================================

    def generate_policy(
        self,
        profile: EnvironmentProfile,
        device_status: Optional[dict] = None,
        timestamp: Optional[float] = None,
    ) -> AdaptivePolicy:
        """
        Generate an adaptive policy from an EnvironmentProfile
        and optional day/night device telemetry.

        Parameters
        ----------
        profile:
            EnvironmentProfile.

        device_status:
            Optional hardware telemetry containing BH1750 light_level
            or light_lux.

        timestamp:
            Optional epoch timestamp.
        """

        if not isinstance(
            profile,
            EnvironmentProfile,
        ):

            raise TypeError(
                "profile must be an EnvironmentProfile."
            )

        # --------------------------------------------------
        # Determine Day / Night regime
        # --------------------------------------------------

        is_night, _, lux = self.determine_day_night(
            device_status=device_status,
            timestamp=timestamp,
        )

        # --------------------------------------------------
        # No observations
        # --------------------------------------------------

        if profile.observation_count <= 0:

            return self._unknown_policy(
                profile,
                is_night=is_night,
                lux=lux,
            )

        # --------------------------------------------------
        # High uncertainty
        # --------------------------------------------------

        if (
            profile.uncertainty
            >= self.uncertainty_threshold
        ):

            return self._unknown_policy(
                profile,
                is_night=is_night,
                lux=lux,
            )

        # --------------------------------------------------
        # Environment classification
        # --------------------------------------------------

        environment = (
            profile.environment_type
        )

        if environment == "Natural":

            return self._natural_policy(
                profile,
                is_night=is_night,
                lux=lux,
            )

        if environment == "Anthropogenic":

            return self._anthropogenic_policy(
                profile,
                is_night=is_night,
                lux=lux,
            )

        if environment == "WeatherDominant":

            return self._weather_policy(
                profile,
                is_night=is_night,
                lux=lux,
            )

        if environment == "Aquatic":

            return self._aquatic_policy(
                profile,
                is_night=is_night,
                lux=lux,
            )

        if environment == "Mixed":

            return self._mixed_policy(
                profile,
                is_night=is_night,
                lux=lux,
            )

        return self._unknown_policy(
            profile,
            is_night=is_night,
            lux=lux,
        )
