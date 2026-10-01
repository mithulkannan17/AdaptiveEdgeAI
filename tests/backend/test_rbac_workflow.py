"""
Tests for RBAC workflows, alert resolution, ranger dispatch, citizen reporting, and audit logs.
"""

import importlib
from fastapi.testclient import TestClient
from backend.database import RuntimeDatabase


def create_test_client(tmp_path, monkeypatch):
    database_path = tmp_path / "runtime_rbac.db"
    database = RuntimeDatabase(database_path)
    module = importlib.import_module("backend.main")
    monkeypatch.setattr(module, "database", database)
    return TestClient(module.app), database


def test_field_rangers_list(tmp_path, monkeypatch):
    client, db = create_test_client(tmp_path, monkeypatch)
    response = client.get("/api/v1/edge/rangers")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    rangers = data["rangers"]
    assert len(rangers) >= 3
    assert any("Amar" in r["name"] for r in rangers)


def test_alert_assign_and_resolve_workflow(tmp_path, monkeypatch):
    client, db = create_test_client(tmp_path, monkeypatch)

    # Insert a mock alert using dictionary format
    alert_id = db.insert_emergency_alert({
        "alert_id": "alert_test_001",
        "device_id": "edge_node_001",
        "threat_type": "Chainsaw",
        "risk_level": "CRITICAL",
        "confidence": 0.94,
        "location_lat": 12.2958,
        "location_lon": 76.6394,
        "message": "🚨 CRITICAL: Chainsaw logging activity detected in Sector 4.",
    })

    # 1. Chief Ranger assigns alert to field ranger unit
    assign_resp = client.post(
        f"/api/v1/edge/alerts/{alert_id}/assign",
        json={"ranger_id": "ranger_01", "ranger_name": "Ranger Amar Singh"},
    )
    assert assign_resp.status_code == 200
    assert assign_resp.json()["success"] is True
    assert assign_resp.json()["status"] == "ASSIGNED"

    # Verify assignment in DB history
    history = db.get_emergency_alert_history(limit=5)
    assert history[0]["assigned_ranger_id"] == "ranger_01"
    assert history[0]["assigned_ranger_name"] == "Ranger Amar Singh"

    # 2. Field ranger marks as solved / resolved
    resolve_resp = client.post(
        f"/api/v1/edge/alerts/{alert_id}/resolve",
        json={
            "resolved_by": "Ranger Amar Singh",
            "resolution_notes": "Suspect apprehended and chainsaw confiscated. Area secured.",
        },
    )
    assert resolve_resp.status_code == 200
    assert resolve_resp.json()["success"] is True
    assert resolve_resp.json()["status"] == "RESOLVED"

    # Verify resolution in DB history
    updated_alerts = db.get_emergency_alert_history(limit=5)
    assert updated_alerts[0]["resolved_by"] == "Ranger Amar Singh"
    assert "confiscated" in updated_alerts[0]["resolution_notes"]


def test_citizen_report_submission_and_review(tmp_path, monkeypatch):
    client, db = create_test_client(tmp_path, monkeypatch)

    # Citizen submits report
    payload = {
        "reporter_name": "Jane Citizen",
        "contact_info": "jane@example.com",
        "threat_category": "Illegal Tree Felling",
        "description": "Observed 3 individuals cutting sandalwood trees near the north creek.",
        "location_lat": 12.2990,
        "location_lon": 76.6410,
        "photo_filename": "evidence.jpg",
    }
    submit_resp = client.post("/api/v1/public/report", json=payload)
    assert submit_resp.status_code == 200
    assert submit_resp.json()["success"] is True
    report_id = submit_resp.json()["report_id"]

    # Chief Ranger reviews reports
    reports_resp = client.get("/api/v1/public/reports")
    assert reports_resp.status_code == 200
    reports = reports_resp.json()["reports"]
    assert len(reports) == 1
    assert reports[0]["reporter_name"] == "Jane Citizen"

    # Chief updates report status
    status_resp = client.post(
        f"/api/v1/public/reports/{report_id}/status",
        json={"status": "DISPATCHED", "notes": "Dispatched Ranger Deepa to inspect creek."},
    )
    assert status_resp.status_code == 200

    # Verify updated report
    updated_reports = client.get("/api/v1/public/reports").json()["reports"]
    assert updated_reports[0]["status"] == "DISPATCHED"
    # Field Ranger resolves citizen report on site
    resolve_resp = client.post(
        f"/api/v1/public/reports/{report_id}/resolve",
        json={"resolved_by": "Ranger Amar Singh", "resolution_notes": "Suspects intercepted and handed to authorities."},
    )
    assert resolve_resp.status_code == 200
    assert resolve_resp.json()["status"] == "RESOLVED"
    assert resolve_resp.json()["resolved_by"] == "Ranger Amar Singh"


def test_ranger_live_gps_streaming(tmp_path, monkeypatch):
    client, db = create_test_client(tmp_path, monkeypatch)

    # Ranger device streams live GPS fix
    loc_payload = {
        "latitude": 12.2995,
        "longitude": 76.6435,
        "battery": 91,
        "status": "RESPONDING",
    }
    resp = client.post("/api/v1/edge/rangers/ranger_01/location", json=loc_payload)
    assert resp.status_code == 200
    assert resp.json()["success"] is True

    # Verify updated location
    rangers_resp = client.get("/api/v1/edge/rangers")
    rangers = rangers_resp.json()["rangers"]
    ranger_01 = next(r for r in rangers if r["ranger_id"] == "ranger_01")
    assert abs(ranger_01["latitude"] - 12.2995) < 0.0001
    assert abs(ranger_01["longitude"] - 76.6435) < 0.0001
    assert ranger_01["battery"] == 91
    assert ranger_01["status"] == "RESPONDING"


def test_auth_audit_log(tmp_path, monkeypatch):
    client, db = create_test_client(tmp_path, monkeypatch)

    # Insert an audit log entry
    db.insert_auth_audit_log(
        username="admin_chief",
        role="admin",
        action="LOGIN_CHIEF_RANGER",
        details="Chief Ranger logged into operations console.",
    )

    resp = client.get("/api/v1/auth/audit_log")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    logs = data["audit_logs"]
    assert len(logs) >= 1
    assert logs[0]["action"] == "LOGIN_CHIEF_RANGER"


def test_chief_generates_field_ranger_and_ranger_logs_in(tmp_path, monkeypatch):
    client, db = create_test_client(tmp_path, monkeypatch)

    # 1. Chief creates ranger account
    payload = {
        "full_name": "Ranger Rajesh Varma",
        "callsign": "DELTA-9",
        "rank": "Senior Wildlife Tracker",
        "sector": "Sector 6 (Bamboo Basin)",
        "phone": "+91 99887 76655",
    }
    create_resp = client.post("/api/v1/auth/ranger/create", json=payload)
    assert create_resp.status_code == 200
    res_data = create_resp.json()
    assert res_data["success"] is True
    generated_user = res_data["username"]
    generated_pwd = res_data["password"]
    assert generated_user.startswith("ranger.rajesh")
    assert generated_pwd.startswith("Aura#Ranger")

    # 2. Ranger logs in using generated credentials
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"username": generated_user, "password": generated_pwd},
    )
    assert login_resp.status_code == 200
    login_data = login_resp.json()
    assert login_data["success"] is True
    assert login_data["user"]["role"] == "ranger"
    assert login_data["user"]["display_name"] == "Ranger Rajesh Varma"


def test_citizen_automated_otp_and_signup_flow(tmp_path, monkeypatch):
    client, db = create_test_client(tmp_path, monkeypatch)

    contact = "+91 91234 56789"

    # 1. Citizen requests OTP
    otp_resp = client.post("/api/v1/auth/signup/otp/generate", json={"phone_or_email": contact})
    assert otp_resp.status_code == 200
    otp_data = otp_resp.json()
    assert otp_data["success"] is True
    generated_otp = otp_data["otp"]
    assert len(generated_otp) == 6

    # 2. Citizen verifies OTP and creates account
    verify_payload = {
        "phone_or_email": contact,
        "otp_code": generated_otp,
        "username": "citizen.priya",
        "password": "priyapassword123",
        "full_name": "Priya Nambiar",
    }
    reg_resp = client.post("/api/v1/auth/signup/otp/verify", json=verify_payload)
    assert reg_resp.status_code == 200
    assert reg_resp.json()["success"] is True

    # 3. Citizen logs in
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"username": "citizen.priya", "password": "priyapassword123"},
    )
    assert login_resp.status_code == 200
    assert login_resp.json()["success"] is True
    assert login_resp.json()["user"]["role"] == "viewer"
    assert login_resp.json()["user"]["display_name"] == "Priya Nambiar"


def test_chief_user_management_suite(tmp_path, monkeypatch):
    client, db = create_test_client(tmp_path, monkeypatch)

    # 1. Chief logs in with default master credentials
    chief_login = client.post(
        "/api/v1/auth/login",
        json={"username": "chief", "password": "auraadmin123"},
    )
    assert chief_login.status_code == 200
    assert chief_login.json()["user"]["role"] == "admin"

    # 2. Chief views all registered users
    users_resp = client.get("/api/v1/auth/users")
    assert users_resp.status_code == 200
    users = users_resp.json()["users"]
    assert len(users) >= 4

    # 3. Chief updates a user's password
    update_resp = client.post(
        "/api/v1/auth/users/ranger.amar/password",
        json={"new_password": "NewAmarPassword999"},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["success"] is True

    # Ranger logs in with new password
    ranger_login = client.post(
        "/api/v1/auth/login",
        json={"username": "ranger.amar", "password": "NewAmarPassword999"},
    )
    assert ranger_login.status_code == 200

    # 4. Chief deletes user
    del_resp = client.delete("/api/v1/auth/users/citizen.demo")
    assert del_resp.status_code == 200
    assert del_resp.json()["success"] is True

