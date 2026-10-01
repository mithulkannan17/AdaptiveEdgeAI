"""
Security & RBAC Unit Tests for AuraForest
=========================================
Tests:
  1. Edge Device API Key & Token Authentication
  2. Session Token Generation & HMAC Verification
  3. User Role-Based Access Control (RBAC)
  4. Physical Sensor Boundaries Anti-Spoofing Checks
  5. Timestamp Replay & Clock Skew Validation
  6. Backend Auth Endpoints (/api/v1/auth/*)
"""

import time
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.security import (
    UserRole,
    UserProfile,
    SessionTokenManager,
    DeviceAuthenticator,
    DataIntegrityVerifier,
    authenticate_user,
    ROLE_PERMISSIONS,
    DEFAULT_MASTER_KEY,
)


@pytest.fixture
def client():
    return TestClient(app)


# ==========================================================
# 1. EDGE DEVICE AUTHENTICATION TESTS
# ==========================================================

def test_device_auth_master_key():
    """Verify master sentinel key passes authentication."""
    ok, msg = DeviceAuthenticator.verify_device_token(DEFAULT_MASTER_KEY, device_id="sentinel_001")
    assert ok is True
    assert "Authenticated" in msg


def test_device_auth_bearer_prefix():
    """Verify tokens with 'Bearer ' prefix are correctly stripped and verified."""
    ok, msg = DeviceAuthenticator.verify_device_token(f"Bearer {DEFAULT_MASTER_KEY}", device_id="sentinel_001")
    assert ok is True


def test_device_auth_invalid_key():
    """Verify unauthorized keys are rejected."""
    ok, msg = DeviceAuthenticator.verify_device_token("rogue_hacker_key_999", device_id="sentinel_001", enforce=True)
    assert ok is False
    assert "Invalid device token" in msg


def test_device_auth_missing_key_enforce():
    """Verify missing key is rejected when enforcement is active."""
    ok, msg = DeviceAuthenticator.verify_device_token(None, device_id="sentinel_001", enforce=True)
    assert ok is False
    assert "Missing required" in msg


# ==========================================================
# 2. SESSION TOKEN & HMAC VERIFICATION TESTS
# ==========================================================

def test_session_token_lifecycle():
    """Verify creating and verifying HMAC signed session tokens."""
    token = SessionTokenManager.create_token("admin", UserRole.ADMIN, expires_in_sec=3600)
    assert isinstance(token, str)
    assert "." in token

    profile = SessionTokenManager.verify_token(token)
    assert profile is not None
    assert profile.username == "admin"
    assert profile.role == UserRole.ADMIN
    assert "dispatch:alerts" in profile.permissions


def test_session_token_tampered():
    """Verify tampered session tokens fail HMAC verification."""
    token = SessionTokenManager.create_token("admin", UserRole.ADMIN, expires_in_sec=3600)
    # Modify token payload
    tampered = "eyJuYW1lIjoidGFtcGVyZWQifQ." + token.split(".")[1]
    profile = SessionTokenManager.verify_token(tampered)
    assert profile is None


def test_session_token_expired():
    """Verify expired session tokens are rejected."""
    token = SessionTokenManager.create_token("ranger", UserRole.RANGER, expires_in_sec=-10)
    profile = SessionTokenManager.verify_token(token)
    assert profile is None


# ==========================================================
# 3. USER AUTHENTICATION & RBAC TESTS
# ==========================================================

def test_authenticate_admin_user():
    """Verify admin login with valid credentials."""
    result = authenticate_user("admin", "auraadmin123")
    assert result is not None
    profile, token = result
    assert profile.role == UserRole.ADMIN
    assert "manage:system" in profile.permissions


def test_authenticate_ranger_user():
    """Verify ranger login with valid credentials."""
    result = authenticate_user("ranger", "auraranger123")
    assert result is not None
    profile, token = result
    assert profile.role == UserRole.RANGER
    assert "dispatch:alerts" in profile.permissions
    assert "manage:system" not in profile.permissions


def test_authenticate_guest_user():
    """Verify guest user has read-only permissions."""
    result = authenticate_user("guest", "guest123")
    assert result is not None
    profile, token = result
    assert profile.role == UserRole.VIEWER
    assert "view:telemetry" in profile.permissions
    assert "dispatch:alerts" not in profile.permissions


def test_authenticate_invalid_credentials():
    """Verify incorrect password returns None."""
    result = authenticate_user("admin", "wrong_password_xyz")
    assert result is None


# ==========================================================
# 4. SENSOR BOUNDS & INTEGRITY TESTS
# ==========================================================

def test_telemetry_bounds_valid():
    """Verify normal physical sensor values pass boundary validation."""
    valid_data = {
        "temperature": 26.5,
        "humidity": 65.0,
        "battery_voltage": 3.95,
        "battery_percent": 88.0,
        "light_level": 450.0,
    }
    is_valid, violations = DataIntegrityVerifier.validate_telemetry_bounds(valid_data)
    assert is_valid is True
    assert len(violations) == 0


def test_telemetry_bounds_anomalous():
    """Verify out-of-bounds sensor readings are detected."""
    anomalous_data = {
        "temperature": 150.0,     # Out of range (-40 to 85)
        "humidity": 140.0,        # Out of range (0 to 100)
        "battery_voltage": 12.0,  # Out of range (2.0 to 5.5)
    }
    is_valid, violations = DataIntegrityVerifier.validate_telemetry_bounds(anomalous_data)
    assert is_valid is False
    assert len(violations) == 3


# ==========================================================
# 5. TIMESTAMP REPLAY PROTECTION TESTS
# ==========================================================

def test_timestamp_valid():
    """Verify fresh timestamp passes replay check."""
    now = time.time()
    ok, msg = DataIntegrityVerifier.validate_timestamp_replay(now)
    assert ok is True


def test_timestamp_replay_ancient():
    """Verify timestamps older than skew limit are rejected."""
    ancient_ts = time.time() - 1000.0  # ~16 minutes ago
    ok, msg = DataIntegrityVerifier.validate_timestamp_replay(ancient_ts, max_skew_sec=300.0)
    assert ok is False
    assert "too old" in msg


def test_timestamp_future_skew():
    """Verify timestamps far in the future are rejected."""
    future_ts = time.time() + 500.0
    ok, msg = DataIntegrityVerifier.validate_timestamp_replay(future_ts)
    assert ok is False
    assert "future" in msg


# ==========================================================
# 6. FASTAPI AUTH ENDPOINTS INTEGRATION TESTS
# ==========================================================

def test_api_login_success(client):
    """Verify POST /api/v1/auth/login endpoint."""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "auraadmin123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "token" in data
    assert data["user"]["role"] == "admin"


def test_api_login_failure(client):
    """Verify failed login returns HTTP 401."""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "bad_password"},
    )
    assert response.status_code == 401


def test_api_auth_me_with_token(client):
    """Verify GET /api/v1/auth/me with valid Bearer token."""
    login_res = client.post(
        "/api/v1/auth/login",
        json={"username": "ranger", "password": "auraranger123"},
    )
    token = login_res.json()["token"]

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["authenticated"] is True
    assert data["user"]["username"] == "ranger"


def test_api_auth_roles(client):
    """Verify GET /api/v1/auth/roles returns role definitions."""
    response = client.get("/api/v1/auth/roles")
    assert response.status_code == 200
    data = response.json()
    assert "admin" in data["roles"]
    assert "ranger" in data["roles"]
    assert "viewer" in data["roles"]


def test_api_verify_key(client):
    """Verify POST /api/v1/auth/verify_key."""
    response = client.post(
        "/api/v1/auth/verify_key",
        json={"token": DEFAULT_MASTER_KEY, "device_id": "sentinel_001"},
    )
    assert response.status_code == 200
    assert response.json()["valid"] is True
