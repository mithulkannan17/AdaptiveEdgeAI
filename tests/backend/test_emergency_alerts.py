"""
Unit tests for backend/alert_dispatcher.py and emergency alert endpoints.
"""

from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from backend.database import RuntimeDatabase
from backend.alert_dispatcher import EmergencyAlertDispatcher
from backend.main import app


@pytest.fixture
def temp_db(tmp_path: Path):
    db_file = tmp_path / "test_alerts.db"
    return RuntimeDatabase(database_path=db_file)


def test_alert_dispatcher_trigger_logic():
    dispatcher = EmergencyAlertDispatcher()

    # Critical threat should trigger
    should_trigger = dispatcher.should_trigger_emergency(
        prediction={"label": "Chainsaw", "confidence": 0.92},
        cadie_decision={"risk_level": "CRITICAL", "requires_attention": True},
    )
    assert should_trigger is True

    # Low-risk quiet ambient should not trigger
    should_not_trigger = dispatcher.should_trigger_emergency(
        prediction={"label": "Birdsong", "confidence": 0.40},
        cadie_decision={"risk_level": "LOW", "requires_attention": False},
    )
    assert should_not_trigger is False


def test_alert_creation_and_db_persistence(temp_db: RuntimeDatabase):
    dispatcher = EmergencyAlertDispatcher(database=temp_db)

    payload = dispatcher.create_alert_payload(
        device_id="sentinel_test_01",
        threat_type="Forest Fire",
        confidence=0.96,
        risk_level="CRITICAL",
        location={"latitude": 12.2958, "longitude": 76.6394},
        decision={"risk_level": "CRITICAL", "recommended_action": "DISPATCH_RANGERS"},
        contributing_factors=["Gas anomaly 2.1x", "Crackle acoustic 96%"],
    )

    assert "alert_id" in payload
    assert "🚨 LOCAL EMERGENCY ALERT" in payload["message"]

    dispatched = dispatcher.dispatch_alert(payload)
    assert dispatched["status"] == "DISPATCHED"

    # Query active alerts from DB
    active = temp_db.get_active_emergency_alerts()
    assert len(active) == 1
    assert active[0]["threat_type"] == "Forest Fire"
    assert active[0]["status"] == "DISPATCHED"

    # Acknowledge alert
    ack_ok = temp_db.acknowledge_emergency_alert(payload["alert_id"], acknowledged_by="Ranger Team Alpha")
    assert ack_ok is True

    # Active should now be empty
    assert len(temp_db.get_active_emergency_alerts()) == 0

    # History should contain acknowledged alert
    hist = temp_db.get_emergency_alert_history()
    assert len(hist) == 1
    assert hist[0]["status"] == "ACKNOWLEDGED"
    assert hist[0]["acknowledged_by"] == "Ranger Team Alpha"


def test_emergency_alert_api_endpoints():
    client = TestClient(app)

    # 1. Dispatch manual alert
    dispatch_resp = client.post(
        "/api/v1/edge/alerts/dispatch",
        json={
            "device_id": "sentinel_api_test",
            "threat_type": "Gunshot",
            "confidence": 0.99,
            "risk_level": "CRITICAL",
            "latitude": 12.30,
            "longitude": 76.65,
            "action": "DISPATCH_RANGERS",
            "contributing_factors": ["Acoustic blast 99%"],
        },
    )
    assert dispatch_resp.status_code == 200
    data = dispatch_resp.json()
    assert data["success"] is True
    alert_id = data["alert"]["alert_id"]

    # 2. Get active alerts
    active_resp = client.get("/api/v1/edge/alerts/active")
    assert active_resp.status_code == 200
    active_data = active_resp.json()
    assert any(a["alert_id"] == alert_id for a in active_data["alerts"])

    # 3. Acknowledge alert
    ack_resp = client.post(
        f"/api/v1/edge/alerts/{alert_id}/acknowledge",
        json={"acknowledged_by": "Ranger HQ Test"},
    )
    assert ack_resp.status_code == 200
    assert ack_resp.json()["status"] == "ACKNOWLEDGED"

    # 4. Get history
    hist_resp = client.get("/api/v1/edge/alerts/history")
    assert hist_resp.status_code == 200
    assert any(a["alert_id"] == alert_id for a in hist_resp.json()["alerts"])
