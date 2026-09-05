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


def test_telemetry_survives_api_round_trip(
    tmp_path,
    monkeypatch,
):

    client = create_client(
        tmp_path,
        monkeypatch,
    )

    payload = {

        "device_id":
            "edge_node_telemetry_001",

        "timestamp":
            1755100000.0,

        "prediction": {

            "label":
                "Bird",

            "class_id":
                0,

            "confidence":
                0.94,

            "inference_time_ms":
                42.1,

            "top_k": [

                {
                    "label":
                        "Bird",

                    "confidence":
                        0.94,

                },

            ],

        },

        "environment": {

            "environment_type":
                "Natural",

            "observation_count":
                10,

            "observation_duration_seconds":
                120.0,

            "event_counts":
                {
                    "Bird": 10,
                },

            "event_ratios":
                {
                    "Bird": 1.0,
                },

            "average_confidence":
                0.94,

            "acoustic_activity":
                0.083,

            "natural_score":
                1.0,

            "anthropogenic_score":
                0.0,

            "weather_score":
                0.0,

            "aquatic_score":
                0.0,

            "uncertainty":
                0.0,

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
                    "Bird": 1.20,
                },

            "class_priority":
                {
                    "Bird": 1,
                },

            "ignored_classes":
                [],

            "reason":
                "Natural acoustic environment.",

        },

        "event": {

            "label":
                "Bird",

            "class_id":
                0,

            "confidence":
                0.94,

            "adjusted_confidence":
                1.0,

            "detection_threshold":
                0.55,

            "detected":
                True,

            "priority":
                1,

            "environment_type":
                "Natural",

            "reason":
                "Event detected.",

            "inference_time_ms":
                42.1,

            "metadata":
                {},

        },

        "unknown_discovery":
            None,

        "location": {

            "latitude":
                12.2958,

            "longitude":
                76.6394,

            "altitude":
                770.0,

            "accuracy":
                4.5,

        },

        "device_status": {

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

        },

    }

    # --------------------------------------------------
    # Send through FastAPI
    # --------------------------------------------------

    response = client.post(

        "/api/v1/edge/events",

        json=payload,

    )

    assert response.status_code == 200

    response_data = response.json()

    assert (
        response_data["success"]
        is True
    )

    assert (
        response_data["record_id"]
        == 1
    )

    # --------------------------------------------------
    # Retrieve through FastAPI
    # --------------------------------------------------

    latest = client.get(
        "/api/v1/edge/events/latest"
    )

    assert latest.status_code == 200

    data = latest.json()

    # --------------------------------------------------
    # Device
    # --------------------------------------------------

    assert (
        data["device_id"]
        == "edge_node_telemetry_001"
    )

    # --------------------------------------------------
    # Location
    # --------------------------------------------------

    assert (
        data["location"]["latitude"]
        == 12.2958
    )

    assert (
        data["location"]["longitude"]
        == 76.6394
    )

    assert (
        data["location"]["altitude"]
        == 770.0
    )

    assert (
        data["location"]["accuracy"]
        == 4.5
    )

    # --------------------------------------------------
    # Device telemetry
    # --------------------------------------------------

    assert (
        data["device_status"]["battery_percent"]
        == 82.5
    )

    assert (
        data["device_status"]["battery_voltage"]
        == 3.91
    )

    assert (
        data["device_status"]["temperature"]
        == 28.4
    )

    assert (
        data["device_status"]["humidity"]
        == 67.2
    )

    assert (
        data["device_status"]["light_level"]
        == 145.0
    )

    assert (
        data["device_status"]["vibration_detected"]
        is False
    )