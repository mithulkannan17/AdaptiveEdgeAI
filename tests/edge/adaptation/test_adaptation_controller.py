"""
Tests for Adaptive Runtime Controller.
"""

from edge.adaptation import (
    AdaptiveRuntimeController,
)

from edge.profiling.profiler import (
    EnvironmentalProfiler,
)


class TestAdaptiveRuntimeController:

    def create_controller(self):

        profiler = EnvironmentalProfiler(

            window_seconds=300,

            minimum_observations=3,

        )

        return AdaptiveRuntimeController(
            profiler=profiler
        )

    # ======================================================
    # Natural Environment
    # ======================================================

    def test_natural_environment_flows_into_policy(
        self,
    ):

        controller = (
            self.create_controller()
        )

        controller.add_event(
            "Bird",
            0.95,
        )

        controller.add_event(
            "Bird",
            0.90,
        )

        controller.add_event(
            "Wildlife",
            0.92,
        )

        controller.add_event(
            "Insects",
            0.88,
        )

        profile = (
            controller.get_profile()
        )

        policy = (
            controller.get_policy()
        )

        assert (
            profile.environment_type
            == "Natural"
        )

        assert (
            policy.environment_type
            == "Natural"
        )

        assert (
            policy.sensitivity_for(
                "Bird"
            )
            > 1.0
        )

        assert (
            policy.sensitivity_for(
                "Wildlife"
            )
            > 1.0
        )

    # ======================================================
    # Anthropogenic Environment
    # ======================================================

    def test_anthropogenic_environment_flows_into_policy(
        self,
    ):

        controller = (
            self.create_controller()
        )

        controller.add_event(
            "Vehicle",
            0.95,
        )

        controller.add_event(
            "Vehicle",
            0.91,
        )

        controller.add_event(
            "Chainsaw",
            0.94,
        )

        controller.add_event(
            "Jackhammer",
            0.90,
        )

        profile = (
            controller.get_profile()
        )

        policy = (
            controller.get_policy()
        )

        assert (
            profile.environment_type
            == "Anthropogenic"
        )

        assert (
            policy.environment_type
            == "Anthropogenic"
        )

        assert (
            policy.sensitivity_for(
                "Vehicle"
            )
            > 1.0
        )

        assert (
            policy.sensitivity_for(
                "Chainsaw"
            )
            > 1.0
        )

    # ======================================================
    # Weather Environment
    # ======================================================

    def test_weather_environment_flows_into_policy(
        self,
    ):

        controller = (
            self.create_controller()
        )

        controller.add_event(
            "Thunderstorm",
            0.95,
        )

        controller.add_event(
            "Thunderstorm",
            0.92,
        )

        controller.add_event(
            "Wind",
            0.88,
        )

        controller.add_event(
            "Wind",
            0.90,
        )

        profile = (
            controller.get_profile()
        )

        policy = (
            controller.get_policy()
        )

        assert (
            profile.environment_type
            == "WeatherDominant"
        )

        assert (
            policy.environment_type
            == "WeatherDominant"
        )

        assert (
            policy.transmission_mode
            == "event_driven"
        )

    # ======================================================
    # Aquatic Environment
    # ======================================================

    def test_aquatic_environment_flows_into_policy(
        self,
    ):

        controller = (
            self.create_controller()
        )

        controller.add_event(
            "Water",
            0.95,
        )

        controller.add_event(
            "Water",
            0.92,
        )

        controller.add_event(
            "Wildlife",
            0.90,
        )

        profile = (
            controller.get_profile()
        )

        policy = (
            controller.get_policy()
        )

        assert (
            profile.environment_type
            == "Aquatic"
        )

        assert (
            policy.environment_type
            == "Aquatic"
        )

    # ======================================================
    # Insufficient Data
    # ======================================================

    def test_initial_state_is_safe(
        self,
    ):

        controller = (
            self.create_controller()
        )

        profile = (
            controller.get_profile()
        )

        policy = (
            controller.get_policy()
        )

        assert (
            profile.environment_type
            == "InsufficientData"
        )

        assert (
            policy.environment_type
            == "InsufficientData"
        )

    # ======================================================
    # Reset
    # ======================================================

    def test_reset_clears_environment(
        self,
    ):

        controller = (
            self.create_controller()
        )

        controller.add_event(
            "Bird",
            0.95,
        )

        controller.add_event(
            "Bird",
            0.90,
        )

        controller.add_event(
            "Wildlife",
            0.92,
        )

        controller.reset()

        profile = (
            controller.get_profile()
        )

        assert (
            profile.observation_count
            == 0
        )

        assert (
            profile.environment_type
            == "InsufficientData"
        )

    # ======================================================
    # State Serialization
    # ======================================================

    def test_state_serialization(
        self,
    ):

        controller = (
            self.create_controller()
        )

        controller.add_event(
            "Bird",
            0.95,
        )

        state = (
            controller.state()
        )

        assert isinstance(
            state,
            dict
        )

        assert (
            "environment_profile"
            in state
        )

        assert (
            "adaptive_policy"
            in state
        )

        assert (
            state[
                "environment_profile"
            ][
                "environment_type"
            ]
            == "InsufficientData"
        )