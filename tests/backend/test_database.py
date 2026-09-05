"""
Runtime database tests.

Verifies that complete edge messages, including
location and device telemetry, are persisted and
retrieved correctly.
"""

from backend.database import RuntimeDatabase


def test_runtime_database_stores_telemetry(
    tmp_path,
):
    database_path = (
        tmp_path / "runtime.db"
    )

    database = RuntimeDatabase(
        database_path=database_path
    )

    message = {

        "device_id":
            "edge_node_001",

        "timestamp":
            1755100000.0,

        "prediction": {

            "label":
                "Bird",

            "class_id":
                0,

            "confidence":
                0.94,

        },

        "environment": {

            "environment_type":
                "Natural",

            "observation_count":
                10,

        },

        "adaptive_policy": {

            "environment_type":
                "Natural",

            "detection_threshold":
                0.55,

        },

        "event": {

            "label":
                "Bird",

            "detected":
                True,

            "priority":
                1,

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

    record_id = database.insert_message(
        message
    )

    assert record_id > 0

    assert database.count() == 1

    result = database.get_latest()

    assert result is not None

    # --------------------------------------------------
    # Device
    # --------------------------------------------------

    assert (
        result["device_id"]
        == "edge_node_001"
    )

    # --------------------------------------------------
    # Location
    # --------------------------------------------------

    assert (
        result["location"]["latitude"]
        == 12.2958
    )

    assert (
        result["location"]["longitude"]
        == 76.6394
    )

    assert (
        result["location"]["altitude"]
        == 770.0
    )

    # --------------------------------------------------
    # Device telemetry
    # --------------------------------------------------

    assert (
        result["device_status"][
            "battery_percent"
        ]
        == 82.5
    )

    assert (
        result["device_status"][
            "battery_voltage"
        ]
        == 3.91
    )

    assert (
        result["device_status"][
            "temperature"
        ]
        == 28.4
    )

    assert (
        result["device_status"][
            "humidity"
        ]
        == 67.2
    )

    assert (
        result["device_status"][
            "vibration_detected"
        ]
        is False
    )


def test_runtime_database_empty_returns_none(
    tmp_path,
):
    database = RuntimeDatabase(
        database_path=tmp_path / "runtime.db"
    )

    assert database.count() == 0

    assert (
        database.get_latest()
        is None
    )