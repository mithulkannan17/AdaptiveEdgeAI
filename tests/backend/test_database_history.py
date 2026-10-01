"""
Unit & integration tests for RuntimeDatabase telemetry history, gas history,
experiment logging, and database statistics.
"""

from pathlib import Path
import tempfile
import time
import pytest
from fastapi.testclient import TestClient

from backend.database import RuntimeDatabase
from backend.main import app


@pytest.fixture
def temp_db(tmp_path):
    db_path = tmp_path / "test_runtime.db"
    db = RuntimeDatabase(database_path=db_path)
    return db


class TestDatabaseHistoryAndExperiments:

    def test_telemetry_history_insertion_and_query(self, temp_db: RuntimeDatabase):
        ts = time.time()
        dev_status = {
            "temperature": 24.5,
            "humidity": 68.2,
            "light_level": 450.0,
            "battery_percent": 88.0,
            "battery_voltage": 4.12,
            "vibration_detected": False,
            "mq2_raw": 320.0,
            "mq2_adc_voltage": 0.25,
            "mq135_raw": 290.0,
            "mq135_adc_voltage": 0.22,
            "gas_assessment": {
                "gas_risk_score": 0.15,
                "overall_status": "NOMINAL",
            },
        }

        # Insert multiple historical records
        for i in range(5):
            temp_db.insert_telemetry_history(
                device_id="esp32_test_node",
                timestamp=ts + i * 10,
                device_status=dev_status,
                location={"latitude": 12.2958, "longitude": 76.6394},
                hardware_health={"wifi": "OK"},
            )

        history = temp_db.get_telemetry_history(device_id="esp32_test_node", limit=10)
        assert len(history) == 5
        assert history[0]["device_id"] == "esp32_test_node"
        assert history[0]["temperature"] == 24.5
        assert history[0]["mq2_raw"] == 320.0
        assert history[0]["gas_status"] == "NOMINAL"

        # Gas history query
        gas_hist = temp_db.get_gas_history(device_id="esp32_test_node")
        assert len(gas_hist) == 5
        assert gas_hist[0]["mq2_raw"] == 320.0
        assert gas_hist[0]["gas_risk_score"] == 0.15

    def test_experiment_logging(self, temp_db: RuntimeDatabase):
        summary = {"total_trials": 100, "accuracy": 0.95}
        details = [{"trial": 1, "passed": True}]
        config = {"snr_db": 10.0}

        row_id = temp_db.insert_experiment_log(
            experiment_name="unit_test_experiment",
            summary=summary,
            details=details,
            config=config,
        )
        assert row_id > 0

        latest = temp_db.get_latest_experiment("unit_test_experiment")
        assert latest is not None
        assert latest["experiment_name"] == "unit_test_experiment"
        assert latest["summary"]["accuracy"] == 0.95

        all_exp = temp_db.get_all_experiments()
        assert len(all_exp) >= 1

    def test_database_stats(self, temp_db: RuntimeDatabase):
        temp_db.insert_telemetry_history(
            device_id="node_01",
            timestamp=time.time(),
            device_status={"temperature": 20.0},
        )
        temp_db.insert_experiment_log(
            experiment_name="stats_test",
            summary={"ok": True},
            details=[],
        )

        stats = temp_db.get_database_stats()
        assert stats["total_telemetry_history_records"] >= 1
        assert stats["total_experiment_logs"] >= 1
        assert "file_size_kb" in stats


class TestDatabaseAPIEndpoints:

    def test_telemetry_and_history_api(self):
        client = TestClient(app)
        dev_id = "test_device_api_99"

        # 1. Post telemetry
        post_resp = client.post(
            "/api/v1/edge/telemetry",
            json={
                "device_id": dev_id,
                "timestamp": time.time(),
                "device_status": {
                    "temperature": 26.0,
                    "humidity": 60.0,
                    "mq2_raw": 300.0,
                    "mq135_raw": 280.0,
                },
                "location": {"latitude": 12.0, "longitude": 76.0},
            },
        )
        assert post_resp.status_code == 200

        # 2. Get telemetry history
        hist_resp = client.get(f"/api/v1/edge/devices/{dev_id}/telemetry/history")
        assert hist_resp.status_code == 200
        data = hist_resp.json()
        assert data["success"] is True
        assert data["count"] >= 1

        # 3. Get gas history
        gas_resp = client.get(f"/api/v1/edge/devices/{dev_id}/gas/history")
        assert gas_resp.status_code == 200
        gas_data = gas_resp.json()
        assert gas_data["success"] is True
        assert len(gas_data["gas_history"]) >= 1

        # 4. Get database stats
        stats_resp = client.get("/api/v1/edge/database/stats")
        assert stats_resp.status_code == 200
        assert stats_resp.json()["success"] is True
