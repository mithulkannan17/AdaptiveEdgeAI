"""
Tests for runtime telemetry structures.
"""

import pytest

from communication import (
    DeviceTelemetry,
    LocationTelemetry,
)


def test_device_telemetry():

    telemetry = DeviceTelemetry(

        battery_percent=82.5,

        battery_voltage=3.91,

        temperature=27.4,

        humidity=68.2,

        light_level=145.7,

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
        == 27.4
    )

    assert (
        data["humidity"]
        == 68.2
    )

    assert (
        data["light_level"]
        == 145.7
    )

    assert (
        data["vibration_detected"]
        is False
    )


def test_device_telemetry_optional_values():

    telemetry = DeviceTelemetry()

    data = telemetry.to_dict()

    assert data == {

        "battery_percent": None,

        "battery_voltage": None,

        "temperature": None,

        "humidity": None,

        "light_level": None,

        "vibration_detected": None,

    }


def test_invalid_battery_percentage():

    with pytest.raises(
        ValueError
    ):

        DeviceTelemetry(
            battery_percent=101
        )


def test_invalid_humidity():

    with pytest.raises(
        ValueError
    ):

        DeviceTelemetry(
            humidity=101
        )


def test_invalid_battery_voltage():

    with pytest.raises(
        ValueError
    ):

        DeviceTelemetry(
            battery_voltage=-1
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


def test_invalid_latitude():

    with pytest.raises(
        ValueError
    ):

        LocationTelemetry(
            latitude=91
        )


def test_invalid_longitude():

    with pytest.raises(
        ValueError
    ):

        LocationTelemetry(
            longitude=181
        )


def test_invalid_location_accuracy():

    with pytest.raises(
        ValueError
    ):

        LocationTelemetry(
            accuracy=-1
        )