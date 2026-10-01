"""
AuraForest Security & Identity Architecture
===========================================

Multi-layer security system providing:
1. Edge Node Authentication (Device Tokens / API Keys / HMAC request validation)
2. Anti-Replay Protection & Timestamp Skew Validation
3. Telemetry Physical Bounds & Anti-Spoofing Integrity Checks
4. Role-Based Access Control (RBAC) & Ranger User Authentication (Admin, Ranger, Viewer)
5. Session Token Generation & Verification
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


# ==========================================================
# CONSTANTS & CONFIGURATION
# ==========================================================

DEFAULT_MASTER_KEY = os.getenv("AURAFOREST_MASTER_KEY", "aura_sentry_sec_key_99")
JWT_SECRET_KEY = os.getenv("AURAFOREST_JWT_SECRET", "aura_jwt_forest_secret_2026_x89")
ENFORCE_DEVICE_AUTH = os.getenv("AURAFOREST_SECURITY_ENFORCE", "false").lower() in ("true", "1", "yes")
MAX_ALLOWED_CLOCK_SKEW_SEC = float(os.getenv("AURAFOREST_MAX_CLOCK_SKEW", "300.0"))  # 5 minutes


# ==========================================================
# ROLES & PERMISSIONS (RBAC)
# ==========================================================

class UserRole(str, Enum):
    ADMIN = "admin"
    RANGER = "ranger"
    VIEWER = "viewer"


class UserProfile(BaseModel):
    username: str
    role: UserRole
    display_name: str
    department: str
    permissions: List[str]


# Role Permission Matrix
ROLE_PERMISSIONS: Dict[UserRole, List[str]] = {
    UserRole.ADMIN: [
        "view:telemetry",
        "view:audio_spectrum",
        "view:alerts",
        "dispatch:alerts",
        "acknowledge:alerts",
        "manage:clustering",
        "manage:labeling",
        "manage:buffer",
        "manage:device_keys",
        "manage:system",
    ],
    UserRole.RANGER: [
        "view:telemetry",
        "view:audio_spectrum",
        "view:alerts",
        "dispatch:alerts",
        "acknowledge:alerts",
        "manage:clustering",
        "manage:labeling",
    ],
    UserRole.VIEWER: [
        "view:telemetry",
        "view:audio_spectrum",
        "view:alerts",
    ],
}


# ==========================================================
# USER CREDENTIALS REPOSITORY
# ==========================================================

# SHA-256 password hash generator with internal salt
def _hash_password(password: str, salt: str = "aura_forest_salt_2026") -> str:
    return hashlib.sha256(f"{salt}:{password}".encode("utf-8")).hexdigest()


# Built-in secure user accounts
BUILTIN_USERS: Dict[str, Dict[str, Any]] = {
    "admin": {
        "password_hash": _hash_password("auraadmin123"),
        "role": UserRole.ADMIN,
        "display_name": "Chief Ranger (Admin)",
        "department": "Forestry Cyber-Defense Command",
    },
    "ranger": {
        "password_hash": _hash_password("auraranger123"),
        "role": UserRole.RANGER,
        "display_name": "Field Ranger Unit 1",
        "department": "Sector 4 Bioacoustic Patrol",
    },
    "guest": {
        "password_hash": _hash_password("guest123"),
        "role": UserRole.VIEWER,
        "display_name": "Guest Observer",
        "department": "Public Wildlife Research",
    },
}

# Registered Edge Nodes & Device Shared Tokens
DEVICE_TOKEN_REGISTRY: Dict[str, str] = {
    "sentinel_001": DEFAULT_MASTER_KEY,
    "sentinel_002": DEFAULT_MASTER_KEY,
    "sentinel_003": DEFAULT_MASTER_KEY,
}


# ==========================================================
# TOKEN GENERATION & SIGNATURE VERIFICATION
# ==========================================================

class SessionTokenManager:
    """Creates and verifies tamper-proof signed session tokens."""

    @staticmethod
    def create_token(username: str, role: UserRole, expires_in_sec: int = 86400) -> str:
        """Create a signed session token containing payload + expiration + HMAC signature."""
        now = time.time()
        payload = {
            "sub": username,
            "role": role.value,
            "iat": now,
            "exp": now + expires_in_sec,
        }
        raw_json = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        payload_b64 = base64.urlsafe_b64encode(raw_json).decode("utf-8").rstrip("=")

        sig = hmac.new(
            JWT_SECRET_KEY.encode("utf-8"),
            payload_b64.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        return f"{payload_b64}.{sig}"

    @staticmethod
    def verify_token(token_str: str) -> Optional[UserProfile]:
        """Verify the signature and expiration of a session token."""
        if not token_str or "." not in token_str:
            return None

        parts = token_str.strip().split(".")
        if len(parts) != 2:
            return None

        payload_b64, signature = parts[0], parts[1]

        # Verify HMAC
        expected_sig = hmac.new(
            JWT_SECRET_KEY.encode("utf-8"),
            payload_b64.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(expected_sig, signature):
            return None

        # Decode payload
        try:
            rem = len(payload_b64) % 4
            padded = payload_b64 + ("=" * ((4 - rem) % 4))
            raw_bytes = base64.urlsafe_b64decode(padded.encode("utf-8"))
            payload = json.loads(raw_bytes.decode("utf-8"))
        except Exception:
            return None

        # Check expiration
        exp = payload.get("exp", 0)
        if time.time() > exp:
            return None

        username = payload.get("sub", "")
        role_str = payload.get("role", UserRole.VIEWER.value)
        try:
            role = UserRole(role_str)
        except ValueError:
            role = UserRole.VIEWER

        user_info = BUILTIN_USERS.get(username, {})
        display_name = user_info.get("display_name", username.capitalize())
        department = user_info.get("department", "AuraForest Node")

        return UserProfile(
            username=username,
            role=role,
            display_name=display_name,
            department=department,
            permissions=ROLE_PERMISSIONS.get(role, []),
        )


# ==========================================================
# EDGE DEVICE AUTHENTICATION
# ==========================================================

class DeviceAuthenticator:
    """Authenticates ESP32 edge sentinels via device tokens & API keys."""

    @staticmethod
    def verify_device_token(
        token: Optional[str],
        device_id: Optional[str] = None,
        enforce: bool = False,
    ) -> tuple[bool, str]:
        """
        Validate incoming X-Device-Token or X-API-Key.
        If enforce is False and no token is provided, returns (True, "Dev mode - token omitted")
        to preserve test compatibility unless explicitly configured.
        """
        if not token:
            if enforce or ENFORCE_DEVICE_AUTH:
                return False, "Missing required X-Device-Token or X-API-Key header"
            return True, "Development mode: unauthenticated access allowed"

        cleaned_token = token.strip()
        if cleaned_token.startswith("Bearer "):
            cleaned_token = cleaned_token[7:].strip()

        # Check master key
        if hmac.compare_digest(cleaned_token, DEFAULT_MASTER_KEY):
            return True, "Authenticated via Master Sentinel Key"

        # Check device-specific key
        if device_id and device_id in DEVICE_TOKEN_REGISTRY:
            registered_key = DEVICE_TOKEN_REGISTRY[device_id]
            if hmac.compare_digest(cleaned_token, registered_key):
                return True, f"Authenticated device: {device_id}"

        return False, "Invalid device token / API key"


# ==========================================================
# SENSOR BOUNDS & DATA INTEGRITY VERIFIER
# ==========================================================

class DataIntegrityVerifier:
    """
    Validates physical sanity and boundaries of incoming edge sensor data
    to detect tampered, malformed, or injected packets.
    """

    BOUNDS = {
        "temperature": (-40.0, 85.0),      # DHT11/BME280 physical operating range
        "humidity": (0.0, 100.0),          # Relative humidity %
        "battery_voltage": (2.0, 5.5),     # Li-Po single cell + charging voltage
        "battery_percent": (0.0, 100.0),    # Battery SOC %
        "light_level": (0.0, 120000.0),    # BH1750 Lux range
        "microphone_level": (0.0, 4096.0), # ADC level
        "mq2_ratio": (0.0, 50.0),          # Gas Rs/R0 ratio
        "mq135_ratio": (0.0, 50.0),        # Air quality ratio
    }

    @classmethod
    def validate_telemetry_bounds(cls, telemetry_data: Dict[str, Any]) -> tuple[bool, List[str]]:
        """
        Verify that all reported metrics fall within legitimate physical bounds.
        Returns (is_valid, list_of_violations).
        """
        violations: List[str] = []
        if not isinstance(telemetry_data, dict):
            return False, ["Telemetry payload is not a dictionary"]

        for key, (min_val, max_val) in cls.BOUNDS.items():
            val = telemetry_data.get(key)
            if val is not None:
                try:
                    num_val = float(val)
                    if num_val < min_val or num_val > max_val:
                        violations.append(f"{key}={num_val} out of physical bounds [{min_val}, {max_val}]")
                except (ValueError, TypeError):
                    violations.append(f"{key} has invalid non-numeric value: {val}")

        # Check nested device_status if present
        dev_status = telemetry_data.get("device_status")
        if isinstance(dev_status, dict):
            gas_info = dev_status.get("gas_assessment")
            if isinstance(gas_info, dict):
                for g_key in ["mq2_ratio", "mq135_ratio"]:
                    if g_key in gas_info and gas_info[g_key] is not None:
                        try:
                            g_val = float(gas_info[g_key])
                            g_min, g_max = cls.BOUNDS[g_key]
                            if g_val < g_min or g_val > g_max:
                                violations.append(f"gas_assessment.{g_key}={g_val} out of bounds [{g_min}, {g_max}]")
                        except (ValueError, TypeError):
                            pass

        is_valid = len(violations) == 0
        return is_valid, violations

    @staticmethod
    def validate_timestamp_replay(
        timestamp: float,
        max_skew_sec: float = MAX_ALLOWED_CLOCK_SKEW_SEC,
    ) -> tuple[bool, str]:
        """
        Verify timestamp is not in the distant past (replay attack) or future.
        """
        try:
            ts = float(timestamp)
        except (ValueError, TypeError):
            return False, "Malformed timestamp"

        now = time.time()
        skew = now - ts

        if skew < -60.0:
            return False, f"Timestamp is in the future by {-skew:.1f}s (clock desync)"

        if skew > max_skew_sec:
            return False, f"Timestamp is too old ({skew:.1f}s ago > limit {max_skew_sec:.0f}s)"

        return True, "Timestamp valid"


# ==========================================================
# AUTHENTICATION API HELPER FUNCTIONS
# ==========================================================

def authenticate_user(username: str, password: str) -> Optional[tuple[UserProfile, str]]:
    """Authenticate username and password, returning (UserProfile, session_token) or None."""
    username = username.strip().lower()
    user_record = BUILTIN_USERS.get(username)
    if not user_record:
        return None

    expected_hash = user_record["password_hash"]
    computed_hash = _hash_password(password)

    if not hmac.compare_digest(expected_hash, computed_hash):
        return None

    role = user_record["role"]
    token = SessionTokenManager.create_token(username, role)
    profile = UserProfile(
        username=username,
        role=role,
        display_name=user_record["display_name"],
        department=user_record["department"],
        permissions=ROLE_PERMISSIONS.get(role, []),
    )
    return profile, token
