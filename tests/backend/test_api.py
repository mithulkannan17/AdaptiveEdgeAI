"""
Tests for the FastAPI runtime backend.
"""

import importlib

from fastapi.testclient import TestClient

from backend.database import RuntimeDatabase


def create_client(
    tmp_path,
    monkeypatch,
):

    database_path = (
        tmp_path
        / "runtime.db"
    )

    database = RuntimeDatabase(
        database_path
    )

    module = importlib.import_module(
        "backend.main"
    )

    monkeypatch.setattr(
        module,
        "database",
        database,
    )

    return TestClient(
        module.app
    )


def sample_message():

    return {

        "device_id":
            "edge_node_001",

        "timestamp":
            1234567890.0,

        "prediction": {

            "label":
                "Chainsaw",

            "class_id":
                1,

            "confidence":
                0.91,

            "inference_time_ms":
                35.2,

            "top_k": [

                {
                    "label":
                        "Chainsaw",

                    "confidence":
                        0.91,

                },

                {
                    "label":
                        "Vehicle",

                    "confidence":
                        0.04,

                },

            ],

        },

        "environment": {

            "environment_type":
                "Natural",

            "observation_count":
                20,

            "observation_duration_seconds":
                300.0,

            "event_counts":
                {
                    "Chainsaw": 5,
                    "Bird": 15,
                },

            "event_ratios":
                {
                    "Chainsaw": 0.25,
                    "Bird": 0.75,
                },

            "average_confidence":
                0.89,

            "acoustic_activity":
                0.066,

            "natural_score":
                0.75,

            "anthropogenic_score":
                0.25,

            "weather_score":
                0.0,

            "aquatic_score":
                0.0,

            "uncertainty":
                0.20,

        },

        "adaptive_policy": {

            "environment_type":
                "Natural",

            "detection_threshold":
                0.55,

            "transmission_mode":
                "selective",

            "sampling_mode":
                "active",

            "class_sensitivity":
                {
                    "Chainsaw": 1.30,
                },

            "class_priority":
                {
                    "Chainsaw": 5,
                },

            "ignored_classes":
                [],

            "reason":
                "Natural environment.",

        },

        "event": {

            "label":
                "Chainsaw",

            "class_id":
                1,

            "confidence":
                0.91,

            "adjusted_confidence":
                1.0,

            "detection_threshold":
                0.55,

            "detected":
                True,

            "priority":
                4,

            "environment_type":
                "Natural",

            "reason":
                "Event detected.",

            "inference_time_ms":
                35.2,

            "metadata":
                {},

        },

        "unknown_discovery":
            None,

        "location":
            None,

        "device_status":
            None,

    }


def test_health(
    tmp_path,
    monkeypatch,
):

    client = create_client(
        tmp_path,
        monkeypatch,
    )

    response = client.get(
        "/health"
    )

    assert response.status_code == 200

    data = response.json()

    assert (
        data["status"]
        == "healthy"
    )

    assert (
        data["stored_records"]
        == 0
    )


def test_receive_edge_event(
    tmp_path,
    monkeypatch,
):

    client = create_client(
        tmp_path,
        monkeypatch,
    )

    response = client.post(

        "/api/v1/edge/events",

        json=sample_message(),

    )

    assert response.status_code == 200

    data = response.json()

    assert (
        data["success"]
        is True
    )

    assert (
        data["record_id"]
        == 1
    )


def test_latest_event(
    tmp_path,
    monkeypatch,
):

    client = create_client(
        tmp_path,
        monkeypatch,
    )

    message = sample_message()

    client.post(

        "/api/v1/edge/events",

        json=message,

    )

    response = client.get(
        "/api/v1/edge/events/latest"
    )

    assert response.status_code == 200

    data = response.json()

    assert (
        data["device_id"]
        == "edge_node_001"
    )

    assert (
        data["prediction"]["label"]
        == "Chainsaw"
    )

    assert (
        data["event"]["detected"]
        is True
    )


def test_latest_event_when_empty(
    tmp_path,
    monkeypatch,
):

    client = create_client(
        tmp_path,
        monkeypatch,
    )

    response = client.get(
        "/api/v1/edge/events/latest"
    )

    assert response.status_code == 404


def test_invalid_message_is_rejected(
    tmp_path,
    monkeypatch,
):

    client = create_client(
        tmp_path,
        monkeypatch,
    )

    response = client.post(

        "/api/v1/edge/events",

        json={
            "device_id":
                "edge_node_001",
        },

    )

    assert response.status_code == 422