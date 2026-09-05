"""
Tests for the dummy hardware layer.

The dummy implementations must behave exactly like the
hardware interfaces that will later be implemented by
the real ESP32-S3 sensor drivers.
"""

import numpy as np
import pytest

from hardware.dummy import (
    CHAINSAW,
    FOREST,
    create_sensor_manager,
    get_scenario,
)

from hardware.telemetry import (
    HardwareTelemetry,
)


def test_forest_scenario():

    manager = create_sensor_manager(
        FOREST
    )

    telemetry = manager.read_all()

    assert isinstance(
        telemetry,
        HardwareTelemetry,
    )

    assert (
        telemetry.location.latitude
        == FOREST.latitude
    )

    assert (
        telemetry.location.longitude
        == FOREST.longitude
    )

    assert (
        telemetry.device_status.battery_percent
        == FOREST.battery_percent
    )

    assert (
        telemetry.device_status.temperature
        == FOREST.temperature
    )

    assert (
        telemetry.device_status.humidity
        == FOREST.humidity
    )

    assert (
        telemetry.device_status.light_level
        == FOREST.light_level
    )

    assert (
        telemetry.device_status.vibration_detected
        == FOREST.vibration_detected
    )


def test_chainsaw_scenario():

    manager = create_sensor_manager(
        CHAINSAW
    )

    telemetry = manager.read_all()

    assert (
        telemetry.device_status.vibration_detected
        is True
    )

    assert (
        telemetry.device_status.battery_percent
        == CHAINSAW.battery_percent
    )


def test_microphone_returns_mono_audio():

    manager = create_sensor_manager(
        FOREST
    )

    audio = manager.read_audio(

        duration_seconds=1.0,

        sample_rate=16000,

    )

    assert isinstance(
        audio,
        np.ndarray,
    )

    assert audio.dtype == np.float32

    assert audio.ndim == 1

    assert len(audio) == 16000


def test_microphone_is_deterministic():

    manager_a = create_sensor_manager(
        FOREST
    )

    manager_b = create_sensor_manager(
        FOREST
    )

    audio_a = manager_a.read_audio(

        duration_seconds=1.0,

        sample_rate=16000,

    )

    audio_b = manager_b.read_audio(

        duration_seconds=1.0,

        sample_rate=16000,

    )

    assert np.array_equal(
        audio_a,
        audio_b,
    )


def test_all_scenarios_are_available():

    scenario_names = [

        "forest",

        "chainsaw",

        "rain",

        "low_battery",

        "human_activity",

        "vehicle",

    ]

    for name in scenario_names:

        scenario = get_scenario(
            name
        )

        manager = create_sensor_manager(
            scenario
        )

        telemetry = manager.read_all()

        assert isinstance(
            telemetry,
            HardwareTelemetry,
        )


def test_unknown_scenario_is_rejected():

    with pytest.raises(
        ValueError
    ):

        get_scenario(
            "does_not_exist"
        )


def test_audio_requires_positive_duration():

    manager = create_sensor_manager(
        FOREST
    )

    with pytest.raises(
        ValueError
    ):

        manager.read_audio(

            duration_seconds=0,

            sample_rate=16000,

        )


def test_audio_requires_positive_sample_rate():

    manager = create_sensor_manager(
        FOREST
    )

    with pytest.raises(
        ValueError
    ):

        manager.read_audio(

            duration_seconds=1.0,

            sample_rate=0,

        )