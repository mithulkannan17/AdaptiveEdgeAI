"""
Tests for dashboard.runtime_data_source.

Verifies that RuntimeDataSource correctly converts
RuntimeDatabase records into dashboard state.
"""

from __future__ import annotations

from dashboard.runtime_data_source import RuntimeDataSource


class FakeDatabase:
    """Deterministic fake runtime database."""

    def __init__(self, record=None):
        self.record = record

    def get_latest(self):
        return self.record


def test_runtime_source_returns_empty_state_when_database_is_empty():

    source = RuntimeDataSource.__new__(
        RuntimeDataSource
    )

    source.database = FakeDatabase(
        record=None
    )

    source._last_state = None

    state = source.tick()

    assert state["event"] is None
    assert state["events"] == []
    assert state["waveform"] == []

    assert state["telemetry"]["temperature"] is None

    assert state["cadie"]["risk_level"] == "LOW"

    assert state["device_id"] is None


def test_runtime_source_builds_dashboard_state():

    source = RuntimeDataSource.__new__(
        RuntimeDataSource
    )

    source.database = FakeDatabase(

        record={

            "device_id":
                "NODE-07",

            "timestamp":
                1234567890.0,

            "prediction": {

                "label":
                    "Bird",

                "class_id":
                    2,

                "confidence":
                    0.94,

                "inference_time_ms":
                    18.5,

            },

            "environment": {

                "environment_type":
                    "FOREST",

            },

            "adaptive_policy": {

                "sampling_mode":
                    "BALANCED",

            },

            "event": {

                "label":
                    "Bird",

                "class_id":
                    2,

                "confidence":
                    0.94,

                "priority":
                    1,

                "detected":
                    True,

            },

            "decision": {

                "risk_level":
                    "LOW",

                "decision_score":
                    0.18,

                "recommended_action":
                    "MONITOR",

                "requires_attention":
                    False,

                "confidence":
                    0.91,

                "reason":
                    "Normal environmental activity.",

                "contributing_factors":
                    ["Natural sound"],

            },

            "unknown_discovery":
                None,

            "location": {

                "latitude":
                    12.3456,

                "longitude":
                    76.5432,

                "altitude":
                    742.0,

                "accuracy":
                    5.0,

            },

            "device_status": {

                "battery_percent":
                    92.0,

                "battery_voltage":
                    3.91,

                "temperature":
                    24.5,

                "humidity":
                    68.2,

                "light_level":
                    341.0,

                "vibration_detected":
                    False,

            },

        }

    )

    source._last_state = None

    state = source.tick()

    assert state["device_id"] == "NODE-07"

    assert state["prediction"]["label"] == "Bird"

    assert state["telemetry"]["temperature"] == 24.5

    assert state["telemetry"]["battery_percent"] == 92.0

    assert state["telemetry"]["latitude"] == 12.3456

    assert state["telemetry"]["longitude"] == 76.5432

    assert state["event"]["label"] == "Bird"

    assert state["event"]["confidence"] == 0.94

    assert state["cadie"]["risk_level"] == "LOW"

    assert state["cadie"]["score"] == 0.18

    assert state["cadie"]["action"] == "MONITOR"

    assert len(state["events"]) == 1

    assert state["waveform"] == []


def test_runtime_source_reset_clears_cache():

    source = RuntimeDataSource.__new__(
        RuntimeDataSource
    )

    source.database = FakeDatabase(
        record=None
    )

    source._last_state = {
        "test": True
    }

    source.reset()

    assert source._last_state is None


def test_runtime_source_is_not_simulator():

    source = RuntimeDataSource.__new__(
        RuntimeDataSource
    )

    assert source.is_simulator() is False

    assert source.source_name() == "RuntimeDataSource"