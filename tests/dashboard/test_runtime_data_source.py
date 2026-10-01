"""
Tests for dashboard.runtime_data_source.

RuntimeDataSource was refactored to poll the FastAPI backend over HTTP.
All tests use the internal helper methods directly so they are independent
of a live backend.
"""

from __future__ import annotations

from copy import deepcopy
from dashboard.runtime_data_source import RuntimeDataSource


# ==========================================================================
# Helpers
# ==========================================================================

def _make_source(api_url: str = "http://127.0.0.1:8000") -> RuntimeDataSource:
    """Return an initialised RuntimeDataSource pointing at a dummy URL."""
    return RuntimeDataSource(api_url=api_url, device_id="test_node_001")


# ==========================================================================
# Empty / offline state
# ==========================================================================

def test_runtime_source_returns_empty_state_when_database_is_empty():
    """
    When the backend is unreachable, tick() must return the offline-empty
    state with the correct structural defaults.
    """
    source = _make_source()
    # Patch _get_json to simulate an unreachable backend (all None).
    source._get_json = lambda path: None  # type: ignore[method-assign]

    state = source.tick()

    # Core fields must exist and match defaults from _build_empty_runtime_state.
    assert state["event"] is None
    assert state["events"] == []
    assert state["waveform"] == []
    assert state["telemetry"]["temperature"] is None
    assert state["cadie"]["risk_level"] == "LOW"
    # device_id falls back to the value supplied at construction time.
    assert state["device_id"] is not None


# ==========================================================================
# State construction from a full event record
# ==========================================================================

def test_runtime_source_builds_dashboard_state():
    """
    When the backend returns a valid event record, tick() must map all
    fields correctly into the dashboard state dict.
    """
    source = _make_source()

    # Simulate a full runtime record returned by /api/v1/edge/events/latest.
    event_record = {
        "device_id": "NODE-07",
        "timestamp": 1234567890.0,
        "prediction": {
            "label": "Bird",
            "class_id": 2,
            "confidence": 0.94,
            "inference_time_ms": 18.5,
        },
        "environment": {
            "environment_type": "FOREST",
        },
        "adaptive_policy": {
            "sampling_mode": "BALANCED",
        },
        "event": {
            "label": "Bird",
            "class_id": 2,
            "confidence": 0.94,
            "priority": 1,
            "detected": True,
        },
        "decision": {
            "risk_level": "LOW",
            "decision_score": 0.18,
            "recommended_action": "MONITOR",
            "requires_attention": False,
            "confidence": 0.91,
            "reason": "Normal environmental activity.",
            "contributing_factors": ["Natural sound"],
        },
        "unknown_discovery": None,
        "location": {
            "latitude": 12.3456,
            "longitude": 76.5432,
            "altitude": 742.0,
            "accuracy": 5.0,
        },
        "device_status": {
            "battery_percent": 92.0,
            "battery_voltage": 3.91,
            "temperature": 24.5,
            "humidity": 68.2,
            "light_level": 341.0,
            "vibration_detected": False,
        },
    }

    telemetry_record = {
        "device_status": {
            "battery_percent": 92.0,
            "battery_voltage": 3.91,
            "temperature": 24.5,
            "humidity": 68.2,
            "light_level": 341.0,
            "vibration_detected": False,
        },
        "location": {
            "latitude": 12.3456,
            "longitude": 76.5432,
            "altitude": 742.0,
            "accuracy": 5.0,
        },
    }

    # Patch _get_json to return controlled responses per path.
    def fake_get_json(path: str):
        if "/health" in path:
            return {"status": "ok"}
        if "/telemetry" in path:
            return telemetry_record
        if "/latest" in path:
            return event_record
        if "/events" in path:
            return [event_record]
        return None

    source._get_json = fake_get_json  # type: ignore[method-assign]

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


# ==========================================================================
# Reset
# ==========================================================================

def test_runtime_source_reset_clears_cache():
    source = _make_source()
    source._last_state = {"test": True}
    source.reset()
    assert source._last_state is None


# ==========================================================================
# Source metadata
# ==========================================================================

def test_runtime_source_is_not_simulator():
    source = _make_source()
    assert source.is_simulator() is False


def test_runtime_source_name():
    source = _make_source()
    # source_name() returns "LIVE FASTAPI" in the current implementation.
    assert isinstance(source.source_name(), str)
    assert len(source.source_name()) > 0


# ==========================================================================
# Internal helper: _extract_telemetry
# ==========================================================================

def test_extract_telemetry_returns_none_for_non_dict():
    assert RuntimeDataSource._extract_telemetry(None) is None
    assert RuntimeDataSource._extract_telemetry([]) is None


def test_extract_telemetry_returns_none_on_failure():
    assert RuntimeDataSource._extract_telemetry({"success": False}) is None


def test_extract_telemetry_returns_nested_telemetry():
    response = {"telemetry": {"temperature": 27.0}}
    result = RuntimeDataSource._extract_telemetry(response)
    assert result == {"temperature": 27.0}


# ==========================================================================
# Internal helper: _extract_latest_event
# ==========================================================================

def test_extract_latest_event_returns_none_for_empty():
    assert RuntimeDataSource._extract_latest_event(None) is None
    assert RuntimeDataSource._extract_latest_event([]) is None


def test_extract_latest_event_returns_first_item_from_list():
    records = [{"prediction": {"label": "Fire"}}, {"prediction": {"label": "Wind"}}]
    result = RuntimeDataSource._extract_latest_event(records)
    assert result == records[0]


def test_extract_latest_event_returns_record_directly():
    record = {"prediction": {"label": "Chainsaw"}, "event": {}}
    result = RuntimeDataSource._extract_latest_event(record)
    assert result == record


# ==========================================================================
# Internal helper: _extract_history
# ==========================================================================

def test_extract_history_returns_empty_for_none():
    assert RuntimeDataSource._extract_history(None) == []


def test_extract_history_returns_list_directly():
    records = [{"label": "Bird"}, {"label": "Fire"}]
    result = RuntimeDataSource._extract_history(records)
    assert result == records


def test_extract_history_extracts_events_key():
    response = {"events": [{"label": "Wind"}]}
    result = RuntimeDataSource._extract_history(response)
    assert result == [{"label": "Wind"}]


# ==========================================================================
# Internal helper: _build_telemetry
# ==========================================================================

def test_build_telemetry_returns_none_fields_when_empty():
    telemetry = RuntimeDataSource._build_telemetry(None)
    assert telemetry["temperature"] is None
    assert telemetry["battery_percent"] is None
    assert telemetry["latitude"] is None


def test_build_telemetry_extracts_device_status():
    record = {
        "device_status": {
            "temperature": 31.4,
            "humidity": 62.0,
            "battery_percent": 78.0,
        },
        "location": {
            "latitude": 10.0,
            "longitude": 77.0,
        },
    }
    telemetry = RuntimeDataSource._build_telemetry(record)
    assert telemetry["temperature"] == 31.4
    assert telemetry["humidity"] == 62.0
    assert telemetry["battery_percent"] == 78.0
    assert telemetry["latitude"] == 10.0
    assert telemetry["longitude"] == 77.0