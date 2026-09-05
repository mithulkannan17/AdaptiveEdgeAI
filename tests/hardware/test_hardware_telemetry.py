"""
Tests for hardware telemetry structures.
"""

from hardware import (
    DeviceTelemetry,
    HardwareTelemetry,
    LocationTelemetry,
)


def test_location_telemetry():

    location = LocationTelemetry(

        latitude=12.2958,

        longitude=76.6394,

        altitude=770.0,

        accuracy=4.5,

    )

    data = location.to_dict()

    assert (
        data["latitude"]
        == 12.2958
    )

    assert (
        data["longitude"]
        == 76.6394
    )

    assert (
        data["altitude"]
        == 770.0
    )

    assert (
        data["accuracy"]
        == 4.5
    )


def test_device_telemetry():

    telemetry = DeviceTelemetry(

        battery_percent=82.5,

        battery_voltage=3.91,

        temperature=28.4,

        humidity=67.2,

        light_level=145.0,

        vibration_detected=False,

    )

    data = telemetry.to_dict()

    assert (
        data["battery_percent"]
        == 82.5
    )

    assert (
        data["battery_voltage"]
        == 3.91
    )

    assert (
        data["temperature"]
        == 28.4
    )

    assert (
        data["humidity"]
        == 67.2
    )

    assert (
        data["light_level"]
        == 145.0
    )

    assert (
        data["vibration_detected"]
        is False
    )


def test_optional_telemetry():

    telemetry = DeviceTelemetry()

    data = telemetry.to_dict()

    assert (
        data["battery_percent"]
        is None
    )

    assert (
        data["temperature"]
        is None
    )

    assert (
        data["vibration_detected"]
        is None
    )


def test_complete_hardware_telemetry():

    telemetry = HardwareTelemetry(

        location=LocationTelemetry(

            latitude=12.2958,

            longitude=76.6394,

        ),

        device_status=DeviceTelemetry(

            battery_percent=82.5,

            temperature=28.4,

        ),

    )

    data = telemetry.to_dict()

    assert (
        data["location"]["latitude"]
        == 12.2958
    )

    assert (
        data["location"]["longitude"]
        == 76.6394
    )

    assert (
        data["device_status"]["battery_percent"]
        == 82.5
    )

    assert (
        data["device_status"]["temperature"]
        == 28.4
    )


def test_empty_hardware_telemetry():

    telemetry = HardwareTelemetry()

    data = telemetry.to_dict()

    assert (
        data["location"]
        is None
    )

    assert (
        data["device_status"]
        is None
    )