"""
Integration tests for EdgeController.
"""

import torch

from edge.runtime import (
    EdgeController,
)

from edge.profiling import (
    EnvironmentalProfiler,
)

from edge.adaptation import (
    AdaptiveBehaviorEngine,
)

from inference.types import (
    PredictionResult,
)


class FakePredictor:

    def __init__(
        self,
        prediction,
    ):

        self.prediction = prediction

        self.last_discovery_result = None

    def predict_spectrogram(
        self,
        spectrogram,
        top_k=5,
        audio_path=None,
    ):

        return self.prediction

    def get_last_discovery_result(
        self,
    ):

        return self.last_discovery_result

    def clear_unknown_buffer(
        self,
    ):

        pass


def create_controller(
    prediction,
):

    predictor = FakePredictor(
        prediction
    )

    profiler = EnvironmentalProfiler(

        window_seconds=300,

        minimum_observations=3,

    )

    return EdgeController(

        predictor=predictor,

        profiler=profiler,

        behavior_engine=(
            AdaptiveBehaviorEngine()
        ),

    )


class TestEdgeController:

    def test_prediction_flows_through_runtime(
        self,
    ):

        prediction = PredictionResult(

            label="Bird",

            class_id=0,

            confidence=0.90,

            top_k=[
                (
                    "Bird",
                    0.90,
                )
            ],

            inference_time_ms=20.0,

        )

        controller = (
            create_controller(
                prediction
            )
        )

        # Build enough observations for profiling.

        controller.process_prediction(
            prediction
        )

        controller.process_prediction(
            prediction
        )

        result = (
            controller.process_prediction(
                prediction
            )
        )

        assert (
            result.prediction.label
            == "Bird"
        )

        assert (
            result.environment_profile
            is not None
        )

        assert (
            result.adaptive_policy
            is not None
        )

        assert (
            result.event
            is not None
        )

    def test_natural_environment_generates_natural_policy(
        self,
    ):

        prediction = PredictionResult(

            label="Bird",

            class_id=0,

            confidence=0.90,

        )

        controller = (
            create_controller(
                prediction
            )
        )

        controller.process_prediction(
            prediction
        )

        controller.process_prediction(
            PredictionResult(
                label="Wildlife",
                class_id=12,
                confidence=0.90,
            )
        )

        result = (
            controller.process_prediction(
                PredictionResult(
                    label="Insects",
                    class_id=7,
                    confidence=0.90,
                )
            )
        )

        assert (
            result.environment_profile
            .environment_type
            == "Natural"
        )

        assert (
            result.adaptive_policy
            .environment_type
            == "Natural"
        )

    def test_event_is_generated(
        self,
    ):

        prediction = PredictionResult(

            label="Chainsaw",

            class_id=1,

            confidence=0.80,

        )

        controller = (
            create_controller(
                prediction
            )
        )

        # Add enough observations.

        controller.process_prediction(
            prediction
        )

        controller.process_prediction(
            prediction
        )

        result = (
            controller.process_prediction(
                prediction
            )
        )

        assert (
            result.event.detected
            is True
        )

        assert (
            result.event.label
            == "Chainsaw"
        )

        assert (
            result.event.priority
            > 0
        )

    def test_runtime_state_serialization(
        self,
    ):

        prediction = PredictionResult(

            label="Bird",

            class_id=0,

            confidence=0.90,

        )

        controller = (
            create_controller(
                prediction
            )
        )

        controller.process_prediction(
            prediction
        )

        state = (
            controller.state()
        )

        assert isinstance(
            state,
            dict
        )

        assert (
            "prediction"
            in state
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
            "event"
            in state
        )

    def test_reset(
        self,
    ):

        prediction = PredictionResult(

            label="Bird",

            class_id=0,

            confidence=0.90,

        )

        controller = (
            create_controller(
                prediction
            )
        )

        controller.process_prediction(
            prediction
        )

        assert (
            controller.get_last_result()
            is not None
        )

        controller.reset()

        assert (
            controller.get_last_result()
            is None
        )

        profile = (
            controller.profiler.profile()
        )

        assert (
            profile.observation_count
            == 0
        )

    def test_process_spectrogram(
        self,
    ):

        prediction = PredictionResult(

            label="Water",

            class_id=11,

            confidence=0.82,

        )

        controller = (
            create_controller(
                prediction
            )
        )

        spectrogram = torch.randn(

            1,
            1,
            128,
            157,

        )

        result = (
            controller.process_spectrogram(
                spectrogram
            )
        )

        assert (
            result.prediction.label
            == "Water"
        )

        assert (
            result.event.label
            == "Water"
        )