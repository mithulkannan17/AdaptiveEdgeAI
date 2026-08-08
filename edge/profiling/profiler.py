"""
Environmental Profiling Engine

Infers the current environmental context from
aggregated acoustic events.
"""

from __future__ import annotations

import math
import time
from collections import Counter
from typing import Optional

from edge.profiling.environment_profile import (
    EnvironmentProfile,
)


class EnvironmentalProfiler:
    """
    Builds an environmental profile from acoustic events.

    The profiler operates over a temporal observation window
    rather than making a decision from a single prediction.
    """

    EVENT_GROUPS = {

        "natural": {

            "Bird": 1.0,
            "Wildlife": 1.0,
            "Insects": 0.8,

        },

        "anthropogenic": {

            "Chainsaw": 1.0,
            "Drill": 0.9,
            "EmergencyVehicle": 0.8,
            "Footsteps": 0.6,
            "Human": 0.7,
            "Jackhammer": 1.0,
            "Vehicle": 0.9,

        },

        "weather": {

            "Thunderstorm": 1.0,
            "Wind": 0.8,
            "Fire": 0.3,

        },

        "aquatic": {

            "Water": 1.0,

        },

    }

    def __init__(

        self,

        window_seconds: float = 300.0,

        minimum_observations: int = 10,

    ):

        self.window_seconds = window_seconds

        self.minimum_observations = (
            minimum_observations
        )

        self.events = []

        self.window_start = time.monotonic()

    def reset(self):
        """
        Reset the current profiling window.
        """

        self.events.clear()

        self.window_start = time.monotonic()

    def add_event(

        self,

        label: str,

        confidence: float,

        timestamp: Optional[float] = None,

    ):
        """
        Add a classified acoustic event.

        Parameters
        ----------
        label:
            Predicted environmental sound class.

        confidence:
            Model confidence in the prediction.

        timestamp:
            Optional monotonic timestamp.
        """

        if timestamp is None:

            timestamp = time.monotonic()

        confidence = max(

            0.0,

            min(1.0, float(confidence))

        )

        self.events.append({

            "label": label,

            "confidence": confidence,

            "timestamp": timestamp,

        })

        self._remove_expired_events(timestamp)

    def _remove_expired_events(

        self,

        current_time: float,

    ):

        cutoff = (

            current_time

            - self.window_seconds

        )

        self.events = [

            event

            for event in self.events

            if event["timestamp"] >= cutoff

        ]

    def _event_counts(self) -> Counter:

        return Counter(

            event["label"]

            for event in self.events

        )

    def _event_ratios(

        self,

        counts: Counter,

    ) -> dict:

        total = sum(counts.values())

        if total == 0:

            return {}

        return {

            label: count / total

            for label, count in counts.items()

        }

    def _average_confidence(self) -> float:

        if not self.events:

            return 0.0

        return sum(

            event["confidence"]

            for event in self.events

        ) / len(self.events)

    def _calculate_group_score(

        self,

        group: str,

        ratios: dict,

    ) -> float:

        weights = self.EVENT_GROUPS[group]

        score = 0.0

        for label, ratio in ratios.items():

            weight = weights.get(

                label,

                0.0

            )

            score += ratio * weight

        return score

    def _calculate_event_diversity(

        self,

        ratios: dict,

    ) -> float:
        """
        Calculate normalized Shannon entropy of
        observed acoustic events.

        This measures event diversity, NOT environmental
        uncertainty.
        """

        if not ratios:

            return 0.0

        entropy = 0.0

        for probability in ratios.values():

            if probability > 0:

                entropy -= (

                    probability

                    * math.log(probability)

                )

        max_entropy = math.log(

            max(len(ratios), 2)

        )

        if max_entropy == 0:

            return 0.0

        return min(

            1.0,

            entropy / max_entropy

        )

    def _calculate_environment_uncertainty(

        self,

        group_scores: dict,

    ) -> float:
        """
        Calculate uncertainty from the competition
        between environmental groups.

        High value:
            Multiple environmental categories have
            similar scores.

        Low value:
            One environmental category clearly dominates.
        """

        scores = sorted(

            group_scores.values(),

            reverse=True

        )

        if not scores:

            return 1.0

        highest = scores[0]

        second_highest = (

            scores[1]

            if len(scores) > 1

            else 0.0

        )

        total = sum(scores)

        if total <= 0:

            return 1.0

        # Normalize the separation between the
        # strongest and second strongest groups.
        margin = (

            highest - second_highest

        ) / highest if highest > 0 else 0.0

        uncertainty = 1.0 - margin

        return max(

            0.0,

            min(1.0, uncertainty)

        )

    def _classify_environment(

        self,

        natural_score: float,

        anthropogenic_score: float,

        weather_score: float,

        aquatic_score: float,

        uncertainty: float,

    ) -> str:

        if len(self.events) < self.minimum_observations:

            return "InsufficientData"

        scores = {

            "Natural": natural_score,

            "Anthropogenic": anthropogenic_score,

            "WeatherDominant": weather_score,

            "Aquatic": aquatic_score,

        }

        environment, highest_score = max(

            scores.items(),

            key=lambda item: item[1]

        )

        if highest_score < 0.25:

            return "Unknown"

        # Only classify as mixed when environmental
        # group scores are genuinely competing.
        if uncertainty > 0.75:

            return "Mixed"

        return environment

    def profile(self) -> EnvironmentProfile:
        """
        Generate the current environmental profile.
        """

        counts = self._event_counts()

        ratios = self._event_ratios(

            counts

        )

        average_confidence = (

            self._average_confidence()

        )

        natural_score = (

            self._calculate_group_score(

                "natural",

                ratios

            )

        )

        anthropogenic_score = (

            self._calculate_group_score(

                "anthropogenic",

                ratios

            )

        )

        weather_score = (

            self._calculate_group_score(

                "weather",

                ratios

            )

        )

        aquatic_score = (

            self._calculate_group_score(

                "aquatic",

                ratios

            )

        )

        group_scores = {

            "natural": natural_score,

            "anthropogenic": anthropogenic_score,

            "weather": weather_score,

            "aquatic": aquatic_score,

        }

        environment_uncertainty = (

            self._calculate_environment_uncertainty(

                group_scores

            )

        )

        event_diversity = (

            self._calculate_event_diversity(

                ratios

            )

        )

        now = time.monotonic()

        observation_duration = min(

            self.window_seconds,

            max(

                0.0,

                now - self.window_start

            )

        )

        acoustic_activity = 0.0

        if observation_duration > 0:

            acoustic_activity = (

                len(self.events)

                / observation_duration

            )

        environment_type = (

            self._classify_environment(

                natural_score,

                anthropogenic_score,

                weather_score,

                aquatic_score,

                environment_uncertainty,

            )

        )

        return EnvironmentProfile(

            environment_type=environment_type,

            observation_count=len(self.events),

            observation_duration_seconds=(

                observation_duration

            ),

            event_counts=dict(counts),

            event_ratios=ratios,

            average_confidence=average_confidence,

            acoustic_activity=acoustic_activity,

            natural_score=natural_score,

            anthropogenic_score=anthropogenic_score,

            weather_score=weather_score,

            aquatic_score=aquatic_score,

            uncertainty=event_diversity,

        )