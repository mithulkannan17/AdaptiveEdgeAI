"""
Tests for EdgeRuntimeResult → EdgeMessage serialization.
"""

from communication import (
    EdgeMessageSerializer,
)

from edge.events import Event

from edge.adaptation import AdaptivePolicy

from edge.profiling import EnvironmentProfile

from inference.types import PredictionResult

from edge.runtime import EdgeRuntimeResult


def create_runtime_result():

    prediction = PredictionResult(

        label="Chainsaw",

        class_id=1,

        confidence=0.91,

        top_k=[
            (
                "Chainsaw",
                0.91,
            ),
            (
                "Vehicle",
                0.04,
            ),
        ],

        inference_time_ms=35.2,

    )

    profile = EnvironmentProfile(

        environment_type="Natural",

        observation_count=20,

        observation_duration_seconds=300.0,

        event_counts={
            "Chainsaw": 5,
            "Bird": 15,
        },

        event_ratios={
            "Chainsaw": 0.25,
            "Bird": 0.75,
        },

        average_confidence=0.89,

        acoustic_activity=0.066,

        natural_score=0.75,

        anthropogenic_score=0.25,

        weather_score=0.0,

        aquatic_score=0.0,

        uncertainty=0.20,

    )

    policy = AdaptivePolicy(

        environment_type="Natural",

        detection_threshold=0.55,

        transmission_mode="selective",

        sampling_mode="active",

        class_sensitivity={
            "Chainsaw": 1.30,
        },

        class_priority={
            "Chainsaw": 5,
        },

        ignored_classes=(),

        reason="Natural environment.",

    )

    event = Event(

        label="Chainsaw",

        class_id=1,

        confidence=0.91,

        adjusted_confidence=1.0,

        detection_threshold=0.55,

        detected=True,

        priority=4,

        environment_type="Natural",

        reason="Event detected.",

        inference_time_ms=35.2,

    )

    return EdgeRuntimeResult(

        prediction=prediction,

        environment_profile=profile,

        adaptive_policy=policy,

        event=event,

        discovery_result=None,

    )


def test_serializer():

    runtime_result = (
        create_runtime_result()
    )

    serializer = (
        EdgeMessageSerializer(
            device_id="edge_node_001"
        )
    )

    message = serializer.serialize(

        runtime_result,

        timestamp=1234567890.0,

    )

    assert (
        message.device_id
        == "edge_node_001"
    )

    assert (
        message.timestamp
        == 1234567890.0
    )

    assert (
        message.prediction.label
        == "Chainsaw"
    )

    assert (
        message.environment.environment_type
        == "Natural"
    )

    assert (
        message.adaptive_policy
        .detection_threshold
        == 0.55
    )

    assert (
        message.event.detected
        is True
    )

    assert (
        message.event.priority
        == 4
    )


def test_serializer_to_dict():

    runtime_result = (
        create_runtime_result()
    )

    serializer = (
        EdgeMessageSerializer(
            device_id="edge_node_001"
        )
    )

    message = serializer.serialize(

        runtime_result,

        timestamp=1234567890.0,

    )

    data = message.to_dict()

    assert isinstance(
        data,
        dict,
    )

    assert (
        data["device_id"]
        == "edge_node_001"
    )

    assert (
        data["prediction"]["label"]
        == "Chainsaw"
    )

    assert (
        data["environment"]["environment_type"]
        == "Natural"
    )

    assert (
        data["event"]["detected"]
        is True
    )


def test_optional_device_information():

    runtime_result = (
        create_runtime_result()
    )

    serializer = (
        EdgeMessageSerializer(
            device_id="edge_node_001"
        )
    )

    message = serializer.serialize(

        runtime_result,

        location={
            "latitude": 12.2958,
            "longitude": 76.6394,
        },

        device_status={
            "battery_percent": 82.5,
            "temperature": 28.4,
        },

    )

    assert (
        message.location["latitude"]
        == 12.2958
    )

    assert (
        message.device_status[
            "battery_percent"
        ]
        == 82.5
    )