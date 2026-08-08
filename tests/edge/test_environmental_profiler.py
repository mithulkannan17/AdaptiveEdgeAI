"""
Unit Tests for Environmental Profiling Engine
"""

import time

import pytest

from edge.profiling import EnvironmentalProfiler


class TestEnvironmentalProfiler:
    """
    Tests for EnvironmentalProfiler.
    """

    def test_empty_profile_returns_insufficient_data(self):

        profiler = EnvironmentalProfiler(
            window_seconds=300,
            minimum_observations=3
        )

        profile = profiler.profile()

        assert profile.environment_type == "InsufficientData"

        assert profile.observation_count == 0

        assert profile.average_confidence == 0.0

    def test_natural_environment(self):

        profiler = EnvironmentalProfiler(
            window_seconds=300,
            minimum_observations=3
        )

        profiler.add_event("Bird", 0.95)

        profiler.add_event("Bird", 0.90)

        profiler.add_event("Wildlife", 0.92)

        profiler.add_event("Insects", 0.88)

        profile = profiler.profile()

        assert profile.environment_type == "Natural"

        assert profile.natural_score > (
            profile.anthropogenic_score
        )

        assert profile.natural_score > (
            profile.weather_score
        )

    def test_anthropogenic_environment(self):

        profiler = EnvironmentalProfiler(
            window_seconds=300,
            minimum_observations=3
        )

        profiler.add_event("Vehicle", 0.95)

        profiler.add_event("Vehicle", 0.91)

        profiler.add_event("Chainsaw", 0.94)

        profiler.add_event("Jackhammer", 0.90)

        profile = profiler.profile()

        assert profile.environment_type == "Anthropogenic"

        assert profile.anthropogenic_score > (
            profile.natural_score
        )

    def test_weather_environment(self):

        profiler = EnvironmentalProfiler(
            window_seconds=300,
            minimum_observations=3
        )

        profiler.add_event("Thunderstorm", 0.95)

        profiler.add_event("Thunderstorm", 0.92)

        profiler.add_event("Wind", 0.88)

        profiler.add_event("Wind", 0.90)

        profile = profiler.profile()

        assert profile.environment_type == "WeatherDominant"

        assert profile.weather_score > (
            profile.natural_score
        )

    def test_aquatic_environment(self):

        profiler = EnvironmentalProfiler(
            window_seconds=300,
            minimum_observations=3
        )

        profiler.add_event("Water", 0.95)

        profiler.add_event("Water", 0.92)

        profiler.add_event("Water", 0.90)

        profile = profiler.profile()

        assert profile.environment_type == "Aquatic"

        assert profile.aquatic_score > (

            profile.natural_score

        )

    def test_event_counts(self):

        profiler = EnvironmentalProfiler(
            window_seconds=300,
            minimum_observations=1
        )

        profiler.add_event("Bird", 0.90)

        profiler.add_event("Bird", 0.80)

        profiler.add_event("Wind", 0.85)

        profile = profiler.profile()

        assert profile.event_counts["Bird"] == 2

        assert profile.event_counts["Wind"] == 1

        assert profile.observation_count == 3

    def test_event_ratios(self):

        profiler = EnvironmentalProfiler(
            window_seconds=300,
            minimum_observations=1
        )

        profiler.add_event("Bird", 0.90)

        profiler.add_event("Bird", 0.80)

        profiler.add_event("Wind", 0.85)

        profile = profiler.profile()

        assert profile.event_ratios["Bird"] == pytest.approx(
            2 / 3
        )

        assert profile.event_ratios["Wind"] == pytest.approx(
            1 / 3
        )

    def test_average_confidence(self):

        profiler = EnvironmentalProfiler(
            window_seconds=300,
            minimum_observations=1
        )

        profiler.add_event("Bird", 0.80)

        profiler.add_event("Bird", 0.90)

        profile = profiler.profile()

        assert profile.average_confidence == pytest.approx(
            0.85
        )

    def test_confidence_is_clamped(self):

        profiler = EnvironmentalProfiler(
            window_seconds=300,
            minimum_observations=1
        )

        profiler.add_event("Bird", 2.0)

        profiler.add_event("Wind", -1.0)

        profile = profiler.profile()

        assert 0.0 <= profile.average_confidence <= 1.0

    def test_expired_events_are_removed(self):

        profiler = EnvironmentalProfiler(
            window_seconds=1,
            minimum_observations=1
        )

        old_timestamp = time.monotonic() - 5

        profiler.add_event(
            "Bird",
            0.90,
            timestamp=old_timestamp
        )

        profiler.add_event(
            "Vehicle",
            0.90
        )

        profile = profiler.profile()

        assert profile.observation_count == 1

        assert profile.event_counts["Vehicle"] == 1

        assert "Bird" not in profile.event_counts

    def test_reset_clears_profile(self):

        profiler = EnvironmentalProfiler(
            window_seconds=300,
            minimum_observations=1
        )

        profiler.add_event(
            "Bird",
            0.90
        )

        assert profiler.profile().observation_count == 1

        profiler.reset()

        profile = profiler.profile()

        assert profile.observation_count == 0

        assert profile.environment_type == "InsufficientData"

    def test_profile_to_dict(self):

        profiler = EnvironmentalProfiler(
            window_seconds=300,
            minimum_observations=1
        )

        profiler.add_event(
            "Bird",
            0.90
        )

        profile = profiler.profile()

        data = profile.to_dict()

        assert isinstance(data, dict)

        assert data["environment_type"] == "Natural"

        assert data["observation_count"] == 1

        assert "event_counts" in data

        assert "event_ratios" in data

        assert "natural_score" in data

        assert "uncertainty" in data