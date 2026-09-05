"""
Integration tests for CADIE + EdgeController.
"""

from types import SimpleNamespace

from edge.decision import CADIE
from edge.runtime.edge_controller import (
    EdgeController,
)
from inference.types import PredictionResult


class DummyPredictor:

    def __init__(self):

        self.last_discovery = None

    def get_last_discovery_result(self):

        return self.last_discovery

    def clear_unknown_buffer(self):

        self.last_discovery = None


def create_prediction(
    label="Chainsaw",
    confidence=0.95,
):

    return PredictionResult(

        label=label,

        class_id=1,

        confidence=confidence,

        top_k=[
            (
                label,
                confidence,
            )
        ],

        inference_time_ms=20.0,

    )


def test_cadie_is_integrated_into_runtime():

    controller = EdgeController(

        predictor=DummyPredictor(),

    )

    result = controller.process_prediction(

        create_prediction(

            label="Chainsaw",

            confidence=0.95,

        ),

        device_status={

            "battery_percent":
                82.5,

        },

    )

    assert result.decision is not None

    assert result.decision.risk_level in {

        "MINIMAL",
        "LOW",
        "MEDIUM",
        "HIGH",
        "CRITICAL",

    }


def test_cadie_decision_is_serialized():

    controller = EdgeController(

        predictor=DummyPredictor(),

    )

    result = controller.process_prediction(

        create_prediction(),

        device_status={

            "battery_percent":
                82.5,

        },

    )

    data = result.to_dict()

    assert (
        "decision"
        in data
    )

    assert (
        data["decision"]
        is not None
    )

    assert (
        "risk_level"
        in data["decision"]
    )

    assert (
        "decision_score"
        in data["decision"]
    )

    assert (
        "recommended_action"
        in data["decision"]
    )


def test_cadie_receives_device_status():

    controller = EdgeController(

        predictor=DummyPredictor(),

    )

    result = controller.process_prediction(

        create_prediction(

            label="Bird",

            confidence=0.60,

        ),

        device_status={

            "battery_percent":
                15.0,

        },

    )

    assert result.decision is not None

    assert isinstance(
        result.decision.decision_score,
        float,
    )


def test_runtime_reset_clears_cadie_result():

    controller = EdgeController(

        predictor=DummyPredictor(),

    )

    controller.process_prediction(

        create_prediction(),

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


def test_custom_cadie_can_be_injected():

    cadie = CADIE()

    controller = EdgeController(

        predictor=DummyPredictor(),

        cadie=cadie,

    )

    assert (
        controller.cadie
        is cadie
    )