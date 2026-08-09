"""
Tests for Adaptive Behaviour Engine.
"""

from edge.adaptation import (
    AdaptiveBehaviorEngine,
)

from edge.profiling.environment_profile import (
    EnvironmentProfile,
)


def make_profile(
    environment_type,
    observation_count=10,
    uncertainty=0.10,
):

    return EnvironmentProfile(

        environment_type=environment_type,

        observation_count=observation_count,

        observation_duration_seconds=300.0,

        event_counts={},

        event_ratios={},

        average_confidence=0.90,

        acoustic_activity=0.50,

        natural_score=0.0,

        anthropogenic_score=0.0,

        weather_score=0.0,

        aquatic_score=0.0,

        uncertainty=uncertainty,

    )


class TestAdaptiveBehaviorEngine:

    def test_natural_policy(self):

        engine = (
            AdaptiveBehaviorEngine()
        )

        policy = engine.generate_policy(
            make_profile("Natural")
        )

        assert (
            policy.environment_type
            == "Natural"
        )

        assert (
            policy.detection_threshold
            == 0.55
        )

        assert (
            policy.sensitivity_for("Bird")
            > 1.0
        )

        assert (
            policy.sensitivity_for("Wildlife")
            > 1.0
        )

        assert (
            policy.priority_for("Chainsaw")
            == 5
        )

    def test_anthropogenic_policy(self):

        engine = (
            AdaptiveBehaviorEngine()
        )

        policy = engine.generate_policy(
            make_profile("Anthropogenic")
        )

        assert (
            policy.environment_type
            == "Anthropogenic"
        )

        assert (
            policy.sensitivity_for(
                "EmergencyVehicle"
            )
            == 1.30
        )

        assert (
            policy.sensitivity_for(
                "Vehicle"
            )
            > 1.0
        )

    def test_weather_policy(self):

        engine = (
            AdaptiveBehaviorEngine()
        )

        policy = engine.generate_policy(
            make_profile(
                "WeatherDominant"
            )
        )

        assert (
            policy.transmission_mode
            == "event_driven"
        )

        assert (
            policy.sensitivity_for("Wind")
            < 1.0
        )

        assert (
            policy.sensitivity_for(
                "Chainsaw"
            )
            > 1.0
        )

    def test_aquatic_policy(self):

        engine = (
            AdaptiveBehaviorEngine()
        )

        policy = engine.generate_policy(
            make_profile("Aquatic")
        )

        assert (
            policy.sensitivity_for("Water")
            < 1.0
        )

        assert (
            policy.sensitivity_for(
                "Wildlife"
            )
            > 1.0
        )

    def test_mixed_policy(self):

        engine = (
            AdaptiveBehaviorEngine()
        )

        policy = engine.generate_policy(
            make_profile("Mixed")
        )

        assert (
            policy.detection_threshold
            == 0.50
        )

        assert (
            policy.sampling_mode
            == "active"
        )

    def test_unknown_environment(self):

        engine = (
            AdaptiveBehaviorEngine()
        )

        policy = engine.generate_policy(
            make_profile("Unknown")
        )

        assert (
            policy.detection_threshold
            == 0.50
        )

        assert (
            policy.sampling_mode
            == "active"
        )

    def test_insufficient_observations(self):

        engine = (
            AdaptiveBehaviorEngine()
        )

        policy = engine.generate_policy(

            make_profile(

                "Natural",

                observation_count=0,

            )

        )

        assert (
            policy.environment_type
            == "Natural"
        )

        assert (
            policy.detection_threshold
            == 0.50
        )

    def test_high_uncertainty(self):

        engine = (
            AdaptiveBehaviorEngine()
        )

        policy = engine.generate_policy(

            make_profile(

                "Natural",

                uncertainty=0.80,

            )

        )

        assert (
            policy.detection_threshold
            == 0.50
        )

    def test_sensitivity_default(self):

        engine = (
            AdaptiveBehaviorEngine()
        )

        policy = engine.generate_policy(
            make_profile("Natural")
        )

        assert (
            policy.sensitivity_for(
                "NonExistingClass"
            )
            == 1.0
        )

    def test_priority_default(self):

        engine = (
            AdaptiveBehaviorEngine()
        )

        policy = engine.generate_policy(
            make_profile("Natural")
        )

        assert (
            policy.priority_for(
                "NonExistingClass"
            )
            == 1
        )

    def test_serialization(self):

        engine = (
            AdaptiveBehaviorEngine()
        )

        policy = engine.generate_policy(
            make_profile("Natural")
        )

        data = policy.to_dict()

        assert isinstance(
            data,
            dict
        )

        assert (
            data["environment_type"]
            == "Natural"
        )

        assert (
            "detection_threshold"
            in data
        )

        assert (
            "class_sensitivity"
            in data
        )

        assert (
            "class_priority"
            in data
        )

        assert (
            "ignored_classes"
            in data
        )

        assert (
            "reason"
            in data
        )