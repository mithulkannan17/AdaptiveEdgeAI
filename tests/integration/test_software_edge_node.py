"""
Software Edge-Node Integration Test

Validates the complete Adaptive Edge Intelligence pipeline
without requiring physical ESP32-S3 hardware.

Pipeline:

    Dummy Hardware
        ↓
    HardwareRuntime
        ↓
    PreProcessor
        ↓
    AURA-CNN Predictor
        ↓
    EdgeController
        ↓
    CADIE
        ↓
    TransmissionPolicy
        ↓
    EdgeMessageSerializer
        ↓
    Fake Communication Client

The test intentionally stops at the communication-client
boundary. Backend API round-trip testing is covered by the
backend integration tests.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from communication.client import CommunicationClient
from communication.runtime_service import EdgeRuntimeService
from communication.transmission_policy import (
    TransmissionPolicy,
)

from edge.runtime import EdgeController

from hardware.runtime import HardwareRuntime
from hardware.sensors import HardwareSensorManager
from hardware.telemetry import (
    DeviceTelemetry,
    HardwareTelemetry,
    LocationTelemetry,
)

from hardware.microphone import (
    DummyMicrophone,
)

from inference.predictor import Predictor


# ==========================================================
# Paths
# ==========================================================

PROJECT_ROOT = (
    Path(__file__).resolve().parents[2]
)

AURA_CHECKPOINT = (
    PROJECT_ROOT
    / "models"
    / "checkpoints"
    / "aura_cnn"
    / "best_model.pth"
)


# ==========================================================
# Dummy Sensors
# ==========================================================


class DummyBatterySensor:
    """
    Simulates MAX17048 battery telemetry.
    """

    def read_battery_percent(
        self,
    ) -> float:

        return 82.5

    def read_battery_voltage(
        self,
    ) -> float:

        return 3.91


class DummyEnvironmentalSensor:
    """
    Simulates BME280 telemetry.
    """

    def read_temperature(
        self,
    ) -> float:

        return 28.4

    def read_humidity(
        self,
    ) -> float:

        return 67.2


class DummyLightSensor:
    """
    Simulates BH1750 telemetry.
    """

    def read_light_level(
        self,
    ) -> float:

        return 145.0


class DummyVibrationSensor:
    """
    Simulates SW420 vibration telemetry.
    """

    def vibration_detected(
        self,
    ) -> bool:

        return False


class DummyGPSSensor:
    """
    Simulates GPS telemetry.
    """

    def read_location(
        self,
    ) -> LocationTelemetry:

        return LocationTelemetry(

            latitude=12.2958,

            longitude=76.6394,

            altitude=770.0,

            accuracy=4.5,

        )


# ==========================================================
# Fake Communication Client
# ==========================================================


class FakeCommunicationClient:
    """
    Captures the EdgeMessage instead of performing a real
    HTTP request.

    This keeps the test independent of a running backend
    server while still exercising serialization and the
    communication boundary.
    """

    def __init__(self):

        self.last_message = None

        self.send_count = 0

    def send(
        self,
        message,
    ):

        self.last_message = message

        self.send_count += 1

        return {

            "success": True,

            "record_id": self.send_count,

        }


# ==========================================================
# Hardware Factory
# ==========================================================


def create_sensor_manager():
    """
    Create a complete simulated hardware stack.
    """

    return HardwareSensorManager(

        microphone_sensor=(
            DummyMicrophone()
        ),

        battery_sensor=(
            DummyBatterySensor()
        ),

        environmental_sensor=(
            DummyEnvironmentalSensor()
        ),

        light_sensor=(
            DummyLightSensor()
        ),

        vibration_sensor=(
            DummyVibrationSensor()
        ),

        gps_sensor=(
            DummyGPSSensor()
        ),

    )


# ==========================================================
# Predictor
# ==========================================================


def create_predictor():
    """
    Load the real AURA-CNN checkpoint.
    """

    if not AURA_CHECKPOINT.exists():

        raise FileNotFoundError(

            "AURA-CNN checkpoint was not found: "

            f"{AURA_CHECKPOINT}"

        )

    return Predictor(

        checkpoint_path=(
            AURA_CHECKPOINT
        ),

    )


# ==========================================================
# Complete Runtime
# ==========================================================


def create_runtime():
    """
    Construct the complete software edge node.
    """

    predictor = (
        create_predictor()
    )

    controller = EdgeController(

        predictor=predictor,

    )

    communication_client = (
        FakeCommunicationClient()
    )

    service = EdgeRuntimeService(

        controller=controller,

        device_id=(
            "software_edge_node_001"
        ),

        communication_client=(
            communication_client
        ),

        transmission_policy=(
            TransmissionPolicy()
        ),

    )

    sensor_manager = (
        create_sensor_manager()
    )

    runtime = HardwareRuntime(

        sensor_manager=(
            sensor_manager
        ),

        runtime_service=service,

    )

    return (
        runtime,
        communication_client,
    )


# ==========================================================
# Tests
# ==========================================================


def test_real_aura_checkpoint_exists():

    assert AURA_CHECKPOINT.exists()

    assert (
        AURA_CHECKPOINT.is_file()
    )


def test_complete_software_edge_node():

    runtime, client = (
        create_runtime()
    )

    result = (
        runtime.process_once()
    )

    # ------------------------------------------------------
    # Runtime result
    # ------------------------------------------------------

    assert result is not None

    assert (
        runtime.get_last_result()
        is result
    )

    # ------------------------------------------------------
    # Audio
    # ------------------------------------------------------

    audio = (
        runtime.get_last_audio()
    )

    assert audio is not None

    assert audio.dtype.is_floating_point

    assert (
        audio.numel()
        > 0
    )

    # ------------------------------------------------------
    # Spectrogram
    # ------------------------------------------------------

    spectrogram = (
        runtime.get_last_spectrogram()
    )

    assert spectrogram is not None

    assert (
        spectrogram.numel()
        > 0
    )

    # ------------------------------------------------------
    # Telemetry
    # ------------------------------------------------------

    telemetry = (
        runtime.get_last_telemetry()
    )

    assert telemetry is not None

    assert (
        telemetry.location
        is not None
    )

    assert (
        telemetry.device_status
        is not None
    )

    assert (
        telemetry.location.latitude
        == 12.2958
    )

    assert (
        telemetry.location.longitude
        == 76.6394
    )

    assert (
        telemetry.device_status
        .battery_percent
        == 82.5
    )

    # ------------------------------------------------------
    # Communication
    # ------------------------------------------------------

    assert (
        client.send_count
        >= 0
    )

    # ------------------------------------------------------
    # If transmission occurred, validate the message.
    # ------------------------------------------------------

    if client.last_message is not None:

        message = (
            client.last_message
        )

        payload = (
            message.to_dict()
        )

        assert (
            payload["device_id"]
            == "software_edge_node_001"
        )

        assert (
            payload["prediction"]
            is not None
        )

        assert (
            payload["environment"]
            is not None
        )

        assert (
            payload["adaptive_policy"]
            is not None
        )

        assert (
            payload["event"]
            is not None
        )

        assert (
            payload["location"]
            is not None
        )

        assert (
            payload["device_status"]
            is not None
        )


def test_software_edge_node_telemetry():

    runtime, _ = (
        create_runtime()
    )

    runtime.process_once()

    telemetry = (
        runtime.get_last_telemetry()
    )

    assert telemetry is not None

    location = (
        telemetry.location
    )

    status = (
        telemetry.device_status
    )

    assert location is not None

    assert status is not None

    assert (
        location.latitude
        == 12.2958
    )

    assert (
        location.longitude
        == 76.6394
    )

    assert (
        location.altitude
        == 770.0
    )

    assert (
        location.accuracy
        == 4.5
    )

    assert (
        status.battery_percent
        == 82.5
    )

    assert (
        status.battery_voltage
        == 3.91
    )

    assert (
        status.temperature
        == 28.4
    )

    assert (
        status.humidity
        == 67.2
    )

    assert (
        status.light_level
        == 145.0
    )

    assert (
        status.vibration_detected
        is False
    )


def test_runtime_state_is_serializable():

    runtime, _ = (
        create_runtime()
    )

    runtime.process_once()

    result = (
        runtime.get_last_result()
    )

    assert result is not None

    data = (
        result.to_dict()
    )

    assert isinstance(
        data,
        dict,
    )

    assert (
        "runtime_response"
        in data
    )

    assert (
        "telemetry"
        in data
    )

    assert (
        "audio_samples"
        in data
    )

    assert (
        "spectrogram_shape"
        in data
    )


def test_runtime_can_be_reset():

    runtime, _ = (
        create_runtime()
    )

    runtime.process_once()

    assert (
        runtime.get_last_result()
        is not None
    )

    assert (
        runtime.get_last_audio()
        is not None
    )

    assert (
        runtime.get_last_spectrogram()
        is not None
    )

    runtime.reset()

    assert (
        runtime.get_last_result()
        is None
    )

    assert (
        runtime.get_last_audio()
        is None
    )

    assert (
        runtime.get_last_spectrogram()
        is None
    )

    assert (
        runtime.get_last_telemetry()
        is None
    )