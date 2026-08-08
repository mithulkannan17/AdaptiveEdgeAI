"""
Environmental Profile

Data structure representing the current acoustic environment.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict


@dataclass
class EnvironmentProfile:
    """
    Represents the acoustic characteristics of an environment.
    """

    environment_type: str

    observation_count: int

    observation_duration_seconds: float

    event_counts: Dict[str, int] = field(
        default_factory=dict
    )

    event_ratios: Dict[str, float] = field(
        default_factory=dict
    )

    average_confidence: float = 0.0

    acoustic_activity: float = 0.0

    natural_score: float = 0.0

    anthropogenic_score: float = 0.0

    weather_score: float = 0.0

    aquatic_score: float = 0.0

    uncertainty: float = 1.0

    def to_dict(self) -> dict:
        """
        Convert the environment profile to a dictionary.
        """

        return {

            "environment_type":
                self.environment_type,

            "observation_count":
                self.observation_count,

            "observation_duration_seconds":
                self.observation_duration_seconds,

            "event_counts":
                dict(self.event_counts),

            "event_ratios":
                dict(self.event_ratios),

            "average_confidence":
                self.average_confidence,

            "acoustic_activity":
                self.acoustic_activity,

            "natural_score":
                self.natural_score,

            "anthropogenic_score":
                self.anthropogenic_score,

            "weather_score":
                self.weather_score,

            "aquatic_score":
                self.aquatic_score,

            "uncertainty":
                self.uncertainty,

        }