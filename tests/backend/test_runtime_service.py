"""
Tests for the edge runtime communication service.
"""

from types import SimpleNamespace

from communication.runtime_service import (
    EdgeRuntimeService,
)
from communication.transmission_policy import (
    TransmissionPolicy,
)

from hardware import (
    DeviceTelemetry,
    HardwareTelemetry,
    LocationTelemetry,
)

class FakeController:
    """
    Minimal controller used to isolate the communication
    service from the actual inference pipeline.
    """

    def __init__(
        self,
        runtime_result,
    ):
        self.runtime_result = (
            runtime_result
        )

        self.process_prediction_calls = 0

        self.process_spectrogram_calls = 0

    def process_prediction(
        self,
        prediction,
    ):

        self.process_prediction_calls += 1

        return self.runtime_result

    def process_spectrogram(
        self,
        spectrogram,
        top_k=5,
        audio_path=None,
    ):

        self.process_spectrogram_calls += 1

        return self.runtime_result


class FakeClient:
    """
    Fake communication client.

    Prevents tests from making real HTTP requests.
    """

    def __init__(self):

        self.messages = []

        self.responses = []

    def send(
        self,
        message,
    ):

        self.messages.append(
            message
        )

        response = {

            "success":
                True,

            "record_id":
                len(self.messages),

        }

        self.responses.append(
            response
        )

        return response


def create_runtime_result(
    mode="selective",
    detected=True,
    priority=1,
):
    """
    Create the minimum runtime result required by
    TransmissionPolicy and EdgeMessageSerializer.
    """

    prediction = SimpleNamespace(

        label="Bird",

        class_id=0,

        confidence=0.91,

        inference_time_ms=35.2,

        top_k=[
            (
                "Bird",
                0.91,
            ),
        ],

    )

    profile = SimpleNamespace(

        environment_type="Natural",

        observation_count=10,

        observation_duration_seconds=30.0,

        event_counts={
            "Bird": 10,
        },

        event_ratios={
            "Bird": 1.0,
        },

        average_confidence=0.91,

        acoustic_activity=0.33,

        natural_score=1.0,

        anthropogenic_score=0.0,

        weather_score=0.0,

        aquatic_score=0.0,

        uncertainty=0.0,

    )

    policy = SimpleNamespace(

        environment_type="Natural",

        detection_threshold=0.55,

        transmission_mode=mode,

        sampling_mode="active",

        class_sensitivity={
            "Bird": 1.2,
        },

        class_priority={
            "Bird": priority,
        },

        ignored_classes=[],

        reason="Test policy.",

    )

    event = SimpleNamespace(

        label="Bird",

        class_id=0,

        confidence=0.91,

        adjusted_confidence=1.0,

        detection_threshold=0.55,

        detected=detected,

        priority=priority,

        environment_type="Natural",

        reason="Test event.",

        inference_time_ms=35.2,

        metadata={},

    )

    return SimpleNamespace(

        prediction=prediction,

        environment_profile=profile,

        adaptive_policy=policy,

        event=event,

        discovery_result=None,

    )


def test_detected_event_is_transmitted():

    runtime_result = create_runtime_result(

        mode="selective",

        detected=True,

        priority=1,

    )

    controller = FakeController(
        runtime_result
    )

    client = FakeClient()

    service = EdgeRuntimeService(

        controller=controller,

        device_id="edge_node_001",

        communication_client=client,

    )

    response = service.process_prediction(
        prediction=object()
    )

    assert response is not None

    assert (
        response["success"]
        is True
    )

    assert (
        controller.process_prediction_calls
        == 1
    )

    assert (
        len(client.messages)
        == 1
    )

    assert (
        service.was_last_transmitted()
        is True
    )

    assert (
        service.get_last_message()
        is not None
    )

    assert (
        service.get_last_response()
        is not None
    )


def test_undetected_selective_event_is_not_transmitted():

    runtime_result = create_runtime_result(

        mode="selective",

        detected=False,

        priority=1,

    )

    controller = FakeController(
        runtime_result
    )

    client = FakeClient()

    service = EdgeRuntimeService(

        controller=controller,

        device_id="edge_node_001",

        communication_client=client,

    )

    response = service.process_prediction(
        prediction=object()
    )

    assert response is None

    assert (
        len(client.messages)
        == 0
    )

    assert (
        service.was_last_transmitted()
        is False
    )

    assert (
        service.get_last_message()
        is None
    )

    assert (
        service.get_last_response()
        is None
    )


def test_high_priority_selective_event_is_transmitted():

    runtime_result = create_runtime_result(

        mode="selective",

        detected=False,

        priority=4,

    )

    controller = FakeController(
        runtime_result
    )

    client = FakeClient()

    service = EdgeRuntimeService(

        controller=controller,

        device_id="edge_node_001",

        communication_client=client,

    )

    response = service.process_prediction(
        prediction=object()
    )

    assert response is not None

    assert (
        len(client.messages)
        == 1
    )

    assert (
        service.was_last_transmitted()
        is True
    )


def test_event_driven_undetected_event_is_not_transmitted():

    runtime_result = create_runtime_result(

        mode="event_driven",

        detected=False,

        priority=1,

    )

    controller = FakeController(
        runtime_result
    )

    client = FakeClient()

    service = EdgeRuntimeService(

        controller=controller,

        device_id="edge_node_001",

        communication_client=client,

    )

    response = service.process_prediction(
        prediction=object()
    )

    assert response is None

    assert (
        len(client.messages)
        == 0
    )


def test_continuous_mode_is_transmitted():

    runtime_result = create_runtime_result(

        mode="continuous",

        detected=False,

        priority=0,

    )

    controller = FakeController(
        runtime_result
    )

    client = FakeClient()

    service = EdgeRuntimeService(

        controller=controller,

        device_id="edge_node_001",

        communication_client=client,

    )

    response = service.process_prediction(
        prediction=object()
    )

    assert response is not None

    assert (
        len(client.messages)
        == 1
    )


def test_telemetry_is_included_in_transmitted_message():

    runtime_result = create_runtime_result(

        mode="continuous",

        detected=True,

        priority=1,

    )

    controller = FakeController(
        runtime_result
    )

    client = FakeClient()

    service = EdgeRuntimeService(

        controller=controller,

        device_id="edge_node_001",

        communication_client=client,

    )

    location = {

        "latitude":
            12.2958,

        "longitude":
            76.6394,

        "altitude":
            770.0,

    }

    device_status = {

        "battery_percent":
            82.5,

        "battery_voltage":
            3.91,

        "temperature":
            28.4,

        "humidity":
            67.2,

        "light_level":
            145.0,

        "vibration_detected":
            False,

    }

    response = service.process_prediction(

        prediction=object(),

        location=location,

        device_status=device_status,

    )

    assert response is not None

    assert (
        len(client.messages)
        == 1
    )

    message = client.messages[0]

    assert (
        message.location["latitude"]
        == 12.2958
    )

    assert (
        message.location["longitude"]
        == 76.6394
    )

    assert (
        message.device_status[
            "battery_percent"
        ]
        == 82.5
    )

    assert (
        message.device_status[
            "temperature"
        ]
        == 28.4
    )


def test_runtime_result_is_retained_when_transmission_is_skipped():

    runtime_result = create_runtime_result(

        mode="event_driven",

        detected=False,

        priority=0,

    )

    controller = FakeController(
        runtime_result
    )

    client = FakeClient()

    service = EdgeRuntimeService(

        controller=controller,

        device_id="edge_node_001",

        communication_client=client,

    )

    service.process_prediction(
        prediction=object()
    )

    assert (
        service.get_last_runtime_result()
        is runtime_result
    )

    assert (
        service.was_last_transmitted()
        is False
    )


def test_structured_hardware_telemetry():

    runtime_result = create_runtime_result(

        mode="continuous",

        detected=True,

        priority=1,

    )

    controller = FakeController(
        runtime_result
    )

    client = FakeClient()

    service = EdgeRuntimeService(

        controller=controller,

        device_id="edge_node_001",

        communication_client=client,

    )

    telemetry = HardwareTelemetry(

        location=LocationTelemetry(

            latitude=12.2958,

            longitude=76.6394,

            altitude=770.0,

            accuracy=4.5,

        ),

        device_status=DeviceTelemetry(

            battery_percent=82.5,

            battery_voltage=3.91,

            temperature=28.4,

            humidity=67.2,

            light_level=145.0,

            vibration_detected=False,

        ),

    )

    response = service.process_prediction(

        prediction=object(),

        telemetry=telemetry,

    )

    assert response is not None

    assert (
        service.was_last_transmitted()
        is True
    )

    message = (
        service.get_last_message()
    )

    assert (
        message.location["latitude"]
        == 12.2958
    )

    assert (
        message.location["longitude"]
        == 76.6394
    )

    assert (
        message.location["altitude"]
        == 770.0
    )

    assert (
        message.location["accuracy"]
        == 4.5
    )

    assert (
        message.device_status[
            "battery_percent"
        ]
        == 82.5
    )

    assert (
        message.device_status[
            "battery_voltage"
        ]
        == 3.91
    )

    assert (
        message.device_status[
            "temperature"
        ]
        == 28.4
    )

    assert (
        message.device_status[
            "humidity"
        ]
        == 67.2
    )

    assert (
        message.device_status[
            "light_level"
        ]
        == 145.0
    )

    assert (
        message.device_status[
            "vibration_detected"
        ]
        is False
    )