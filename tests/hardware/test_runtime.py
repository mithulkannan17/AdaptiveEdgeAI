"""
Tests for the production hardware runtime adapter.

These tests verify:

    Dummy Microphone
        ↓
    PreProcessor
        ↓
    Model-ready Spectrogram
        ↓
    EdgeRuntimeService
        ↓
    HardwareTelemetry

No physical hardware is required.
"""

from types import SimpleNamespace

import pytest
import torch

from hardware.dummy import (
    FOREST,
    create_sensor_manager,
)

from hardware.runtime import (
    HardwareRuntime,
)

from hardware.telemetry import (
    HardwareTelemetry,
)

from inference.preprocessor import (
    PreProcessor,
)


# ==========================================================
# Helpers
# ==========================================================


def create_runtime_service():

    calls = {}

    def process_spectrogram(
        spectrogram,
        top_k=5,
        audio_path=None,
        telemetry=None,
    ):

        calls["spectrogram"] = spectrogram

        calls["top_k"] = top_k

        calls["audio_path"] = audio_path

        calls["telemetry"] = telemetry

        return {

            "success": True,

            "record_id": 1,

        }

    service = SimpleNamespace(

        process_spectrogram=(
            process_spectrogram
        ),

    )

    return service, calls


# ==========================================================
# Construction
# ==========================================================


def test_runtime_requires_sensor_manager():

    service, _ = (
        create_runtime_service()
    )

    with pytest.raises(
        ValueError
    ):

        HardwareRuntime(

            sensor_manager=None,

            runtime_service=service,

        )


def test_runtime_requires_service():

    manager = (
        create_sensor_manager(
            FOREST
        )
    )

    with pytest.raises(
        ValueError
    ):

        HardwareRuntime(

            sensor_manager=manager,

            runtime_service=None,

        )


def test_runtime_rejects_invalid_preprocessor():

    manager = (
        create_sensor_manager(
            FOREST
        )
    )

    service, _ = (
        create_runtime_service()
    )

    with pytest.raises(
        TypeError
    ):

        HardwareRuntime(

            sensor_manager=manager,

            runtime_service=service,

            preprocessor="invalid",

        )


# ==========================================================
# Construction With Production PreProcessor
# ==========================================================


def test_runtime_uses_production_preprocessor():

    manager = (
        create_sensor_manager(
            FOREST
        )
    )

    service, _ = (
        create_runtime_service()
    )

    preprocessor = (
        PreProcessor()
    )

    runtime = HardwareRuntime(

        sensor_manager=manager,

        runtime_service=service,

        preprocessor=preprocessor,

    )

    assert (
        runtime.preprocessor
        is preprocessor
    )

    assert (
        runtime.sample_rate
        == 16000
    )

    assert (
        runtime.duration_seconds
        == 5.0
    )


# ==========================================================
# Audio Capture
# ==========================================================


def test_capture_audio():

    manager = (
        create_sensor_manager(
            FOREST
        )
    )

    service, _ = (
        create_runtime_service()
    )

    runtime = HardwareRuntime(

        sensor_manager=manager,

        runtime_service=service,

        duration_seconds=1.0,

        sample_rate=16000,

    )

    audio = (
        runtime.capture_audio()
    )

    assert isinstance(
        audio,
        torch.Tensor,
    )

    assert audio.dtype == torch.float32

    assert audio.ndim == 1

    assert len(audio) == 16000

    assert (
        runtime.get_last_audio()
        is audio
    )


# ==========================================================
# Telemetry
# ==========================================================


def test_capture_telemetry():

    manager = (
        create_sensor_manager(
            FOREST
        )
    )

    service, _ = (
        create_runtime_service()
    )

    runtime = HardwareRuntime(

        sensor_manager=manager,

        runtime_service=service,

    )

    telemetry = (
        runtime.capture_telemetry()
    )

    assert isinstance(
        telemetry,
        HardwareTelemetry,
    )

    assert (
        telemetry.device_status
        is not None
    )

    assert (
        telemetry.location
        is not None
    )

    assert (
        telemetry.device_status.battery_percent
        == FOREST.battery_percent
    )

    assert (
        telemetry.location.latitude
        == FOREST.latitude
    )

    assert (
        runtime.get_last_telemetry()
        is telemetry
    )


# ==========================================================
# Preprocessing
# ==========================================================


def test_preprocess_audio():

    manager = (
        create_sensor_manager(
            FOREST
        )
    )

    service, _ = (
        create_runtime_service()
    )

    runtime = HardwareRuntime(

        sensor_manager=manager,

        runtime_service=service,

    )

    # 5 seconds at 16 kHz.
    audio = torch.randn(
        80000
    )

    spectrogram = (
        runtime.preprocess_audio(
            audio
        )
    )

    assert isinstance(
        spectrogram,
        torch.Tensor,
    )

    assert tuple(
        spectrogram.shape
    ) == (
        1,
        128,
        157,
    )

    assert (
        runtime.get_last_spectrogram()
        is spectrogram
    )


# ==========================================================
# Complete Runtime Cycle
# ==========================================================


def test_process_once():

    manager = (
        create_sensor_manager(
            FOREST
        )
    )

    service, calls = (
        create_runtime_service()
    )

    runtime = HardwareRuntime(

        sensor_manager=manager,

        runtime_service=service,

        sample_rate=16000,

        duration_seconds=5.0,

    )

    result = (
        runtime.process_once(
            top_k=5
        )
    )

    assert result is not None

    assert (
        result.runtime_response[
            "success"
        ]
        is True
    )

    assert (
        result.runtime_response[
            "record_id"
        ]
        == 1
    )

    assert (
        result.audio_samples
        == 80000
    )

    assert isinstance(
        result.telemetry,
        HardwareTelemetry,
    )

    assert (
        calls["telemetry"]
        is result.telemetry
    )

    assert (
        calls["top_k"]
        == 5
    )

    assert (
        result.spectrogram_shape
        == (
            1,
            128,
            157,
        )
    )

    assert isinstance(
        calls["spectrogram"],
        torch.Tensor,
    )


# ==========================================================
# Runtime State
# ==========================================================


def test_last_result_is_stored():

    manager = (
        create_sensor_manager(
            FOREST
        )
    )

    service, _ = (
        create_runtime_service()
    )

    runtime = HardwareRuntime(

        sensor_manager=manager,

        runtime_service=service,

        duration_seconds=5.0,

    )

    result = (
        runtime.process_once()
    )

    assert (
        runtime.get_last_result()
        is result
    )


def test_reset():

    manager = (
        create_sensor_manager(
            FOREST
        )
    )

    service, _ = (
        create_runtime_service()
    )

    runtime = HardwareRuntime(

        sensor_manager=manager,

        runtime_service=service,

        duration_seconds=5.0,

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
        runtime.get_last_telemetry()
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
        runtime.get_last_telemetry()
        is None
    )

    assert (
        runtime.get_last_spectrogram()
        is None
    )


# ==========================================================
# Telemetry Reaches Service
# ==========================================================


def test_telemetry_reaches_runtime_service():

    manager = (
        create_sensor_manager(
            FOREST
        )
    )

    service, calls = (
        create_runtime_service()
    )

    runtime = HardwareRuntime(

        sensor_manager=manager,

        runtime_service=service,

        duration_seconds=5.0,

    )

    runtime.process_once()

    telemetry = (
        calls["telemetry"]
    )

    assert isinstance(
        telemetry,
        HardwareTelemetry,
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
        telemetry.device_status.battery_percent
        == FOREST.battery_percent
    )