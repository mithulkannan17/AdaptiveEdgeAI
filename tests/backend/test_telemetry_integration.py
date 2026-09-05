"""
Telemetry integration tests.

Verifies that structured telemetry can pass through
the communication serialization boundary while
remaining JSON-compatible.
"""

from communication import (
    DeviceTelemetry,
    LocationTelemetry,
    EdgeMessageSerializer,
)

from tests.backend.test_serializer import (
    create_runtime_result,
)


def test_structured_telemetry_serialization():

    runtime_result = (
        create_runtime_result()
    )

    serializer = EdgeMessageSerializer(
        device_id="edge_node_001"
    )

    location = LocationTelemetry(

        latitude=12.2958,

        longitude=76.6394,

        altitude=770.0,

        accuracy=4.5,

    )

    telemetry = DeviceTelemetry(

        battery_percent=82.5,

        battery_voltage=3.91,

        temperature=28.4,

        humidity=67.2,

        light_level=145.0,

        vibration_detected=False,

    )

    message = serializer.serialize(

        runtime_result,

        location=location,

        device_status=telemetry,

    )

    # --------------------------------------------------
    # Location
    # --------------------------------------------------

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

    # --------------------------------------------------
    # Device telemetry
    # --------------------------------------------------

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

    # --------------------------------------------------
    # Final JSON-compatible payload
    # --------------------------------------------------

    payload = message.to_dict()

    assert (
        payload["location"]["latitude"]
        == 12.2958
    )

    assert (
        payload["device_status"][
            "battery_percent"
        ]
        == 82.5
    )

    assert (
        payload["device_status"][
            "vibration_detected"
        ]
        is False
    )