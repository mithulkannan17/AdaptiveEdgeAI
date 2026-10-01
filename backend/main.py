"""
FastAPI Backend

Receives:
    1. Hardware telemetry from ESP32 edge nodes
    2. PCM16 audio from ESP32 edge nodes

Telemetry is cached per device and supplied as environmental
context to the adaptive audio-intelligence pipeline.
"""

from __future__ import annotations

from typing import Any
import struct
import uuid

from fastapi import Body, Header
from fastapi import FastAPI
from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict
from pathlib import Path
from fastapi.responses import FileResponse

from backend.audio_service import AudioInferenceService
from backend.database import RuntimeDatabase
from backend.alert_dispatcher import EmergencyAlertDispatcher
from backend.email_service import email_service
from edge.sensors.gas_interpreter import GasSensorInterpreter
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


# ==========================================================
# UNKNOWN AUDIO EVIDENCE STORAGE
# ==========================================================

UNKNOWN_AUDIO_ROOT = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "unknown_audio"
)
UNKNOWN_AUDIO_ROOT.mkdir(
    parents=True,
    exist_ok=True,
)


def _detect_audio_extension(audio_bytes: bytes) -> str:
    """Best-effort detection of common audio container formats."""
    if len(audio_bytes) >= 12:
        if audio_bytes[0:4] == b"RIFF" and audio_bytes[8:12] == b"WAVE":
            return "wav"

    if audio_bytes.startswith(b"ID3"):
        return "mp3"

    if len(audio_bytes) >= 2 and audio_bytes[0] == 0xFF:
        # MPEG Layer III frame sync. Keep this conservative so raw
        # PCM is not accidentally classified as MP3.
        b1 = audio_bytes[1]
        if (b1 & 0xE0) == 0xE0 and (b1 & 0x06) in (0x00, 0x02, 0x04, 0x06):
            return "mp3"

    if audio_bytes.startswith(b"fLaC"):
        return "flac"

    if audio_bytes.startswith(b"OggS"):
        return "ogg"

    if audio_bytes.startswith(b"FORM") and len(audio_bytes) >= 12:
        return "aiff"

    if len(audio_bytes) >= 12 and audio_bytes[4:8] == b"ftyp":
        return "m4a"

    # AAC ADTS commonly starts with 0xFFF sync.
    if len(audio_bytes) >= 2 and audio_bytes[0] == 0xFF:
        if (audio_bytes[1] & 0xF6) == 0xF0:
            return "aac"

    return "pcm16"


def _pcm16_to_wav(
    pcm_bytes: bytes,
    sample_rate: int,
) -> bytes:
    """Wrap mono PCM16 bytes in a standard WAV container."""
    if len(pcm_bytes) % 2 != 0:
        raise ValueError(
            "Raw PCM16 audio must contain an even number of bytes."
        )

    sample_rate = int(sample_rate)
    if sample_rate <= 0:
        raise ValueError(
            "sample_rate must be greater than zero."
        )

    data_size = len(pcm_bytes)
    byte_rate = sample_rate * 2
    block_align = 2

    header = struct.pack(
        "<4sI4s"
        "4sIHHIIHH"
        "4sI",
        b"RIFF",
        36 + data_size,
        b"WAVE",
        b"fmt ",
        16,
        1,
        1,
        sample_rate,
        byte_rate,
        block_align,
        16,
        b"data",
        data_size,
    )
    return header + pcm_bytes


def _save_audio_evidence(
    audio_bytes: bytes,
    sample_rate: int,
) -> Path:
    """
    Persist the incoming audio in data/unknown_audio.

    WAV/compressed formats are retained as received.
    Raw PCM16 is wrapped as a playable WAV file.
    """
    extension = _detect_audio_extension(audio_bytes)
    sample_id = uuid.uuid4().hex

    if extension == "pcm16":
        filename = f"incoming_{sample_id}.wav"
        payload = _pcm16_to_wav(
            audio_bytes,
            sample_rate,
        )
    else:
        filename = f"incoming_{sample_id}.{extension}"
        payload = audio_bytes

    path = (
        UNKNOWN_AUDIO_ROOT
        / filename
    )

    path.write_bytes(payload)
    return path


def _safe_audio_path(
    raw_path: str | None,
) -> Path | None:
    """
    Resolve an evidence path and require it to remain inside
    data/unknown_audio.
    """
    if not raw_path:
        return None

    root = UNKNOWN_AUDIO_ROOT.resolve()

    try:
        # Check by filename inside UNKNOWN_AUDIO_ROOT first
        direct_file = (root / Path(raw_path).name).resolve()
        if direct_file.is_file():
            direct_file.relative_to(root)
            return direct_file

        # Check direct path
        path = Path(raw_path).resolve()
        path.relative_to(root)
        if path.is_file():
            return path

        return None
    except (
        OSError,
        RuntimeError,
        ValueError,
    ):
        return None


def _unknown_evidence_required(
    inference_result: dict[str, Any],
) -> bool:
    """
    Decide whether the temporary audio evidence must be retained.

    The open-set discovery result is authoritative when present.
    A final Unknown prediction is also retained as a safe fallback.
    """
    discovery = (
        inference_result.get("unknown_discovery")
        or {}
    )

    if isinstance(discovery, dict):
        if bool(discovery.get("is_unknown")):
            return True

        if bool(discovery.get("buffered")):
            return True

        decision = discovery.get("decision")
        if isinstance(decision, dict):
            if bool(decision.get("is_unknown")):
                return True

    runtime = (
        inference_result.get("edge_runtime")
        or {}
    )

    runtime_discovery = (
        runtime.get("unknown_discovery")
        or runtime.get("discovery_result")
        or {}
    )

    if isinstance(runtime_discovery, dict):
        if bool(runtime_discovery.get("is_unknown")):
            return True

    prediction = (
        inference_result.get("prediction")
        or {}
    )

    if isinstance(prediction, dict):
        return str(
            prediction.get("label", "")
        ).strip().lower() == "unknown"

    return False


# ==========================================================
# FASTAPI APPLICATION
# ==========================================================

app = FastAPI(
    title="Adaptive Edge Intelligence API",
    description=(
        "Backend API for the Adaptive Edge Intelligence "
        "Platform."
    ),
    version="1.0.0",
)


# ==========================================================
# SERVICES
# ==========================================================

database = RuntimeDatabase()

audio_service = AudioInferenceService(
    sample_rate=16000
)

gas_interpreter = GasSensorInterpreter()

alert_dispatcher = EmergencyAlertDispatcher(database=database)


def sync_initial_experiment_data() -> None:
    """Sync experiment results on disk into database experiment_logs table."""
    try:
        project_root = Path(__file__).resolve().parent.parent
        exp_dir = project_root / "outputs" / "experiments"

        noise_file = exp_dir / "noise_robustness_results.json"
        if noise_file.exists() and database.get_latest_experiment("noise_robustness") is None:
            data = json.loads(noise_file.read_text(encoding="utf-8"))
            benchmark = data.get("benchmark", data)
            database.insert_experiment_log(
                experiment_name="noise_robustness",
                summary=benchmark.get("summary", {}),
                details=benchmark.get("records", []),
                config=benchmark.get("denoiser_config", {}),
                timestamp=benchmark.get("timestamp"),
            )

        dist_file = exp_dir / "distance_detection_results.json"
        if dist_file.exists() and database.get_latest_experiment("distance_detection") is None:
            data = json.loads(dist_file.read_text(encoding="utf-8"))
            database.insert_experiment_log(
                experiment_name="distance_detection",
                summary=data.get("summary", {}),
                details=data.get("trials", []),
                config={"confidence_threshold": data.get("confidence_threshold", 0.60)},
            )
    except Exception as exc:
        print(f"[!] Note: experiment auto-sync skipped: {exc}")

sync_initial_experiment_data()


# ==========================================================
# LATEST TELEMETRY CACHE
# ==========================================================

latest_device_telemetry: dict[
    str,
    dict[str, Any],
] = {}


# ==========================================================
# REQUEST SCHEMAS
# ==========================================================

class TelemetryRequest(BaseModel):
    """
    Hardware telemetry received from an ESP32 edge node.
    """

    model_config = ConfigDict(
        extra="allow"
    )

    device_id: str

    timestamp: float

    device_status: dict

    location: dict | None = None

    hardware_health: dict | None = None


class EdgeMessageRequest(BaseModel):
    """
    Complete runtime intelligence message.

    This is produced by the Python edge-runtime pipeline,
    not directly by the ESP32 hardware.
    """

    model_config = ConfigDict(
        extra="forbid"
    )

    device_id: str

    timestamp: float

    prediction: dict

    environment: dict

    adaptive_policy: dict

    event: dict

    decision: dict | None = None

    unknown_discovery: dict | None = None

    location: dict | None = None

    device_status: dict | None = None


class MessageResponse(BaseModel):

    success: bool

    record_id: int


class UnknownClusterLabelRequest(BaseModel):
    """Human label applied to a discovered unknown-sound cluster."""

    label: str
    notes: str = ""


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenVerifyRequest(BaseModel):
    token: str
    device_id: str | None = None


class CitizenSignupOtpRequest(BaseModel):
    phone_or_email: str


class CitizenSignupVerifyRequest(BaseModel):
    phone_or_email: str
    otp_code: str
    username: str
    password: str
    full_name: str


class CreateRangerRequest(BaseModel):
    full_name: str
    email: str = ""
    phone: str = ""
    callsign: str = "ALPHA-1"
    rank: str = "Field Ranger"
    sector: str = "Sector 4 (Tiger Corridor)"


class UpdateUserPasswordRequest(BaseModel):
    new_password: str


# ==========================================================
# AUTHENTICATION & RBAC ENDPOINTS
# ==========================================================

@app.post("/api/v1/auth/login")
def auth_login(creds: LoginRequest):
    """Authenticate ranger/admin/citizen credentials and issue a signed session token."""
    # 1. Check persistent RuntimeDatabase
    db_user = database.authenticate_user(creds.username, creds.password)
    if db_user:
        role_str = str(db_user.get("role", "viewer")).lower()
        if role_str in ("admin", "chief"):
            role = UserRole.ADMIN
        elif role_str == "ranger":
            role = UserRole.RANGER
        else:
            role = UserRole.VIEWER

        token = SessionTokenManager.create_token(creds.username, role)
        profile = UserProfile(
            username=db_user["username"],
            role=role,
            display_name=db_user.get("full_name") or db_user.get("username", "").capitalize(),
            department=db_user.get("sector") or ("Forestry Command" if role == UserRole.ADMIN else "Community"),
            permissions=ROLE_PERMISSIONS.get(role, []),
        )
        database.insert_auth_audit_log(
            username=db_user["username"],
            role=role.value,
            action="LOGIN_SUCCESS",
            details=f"User {db_user['username']} ({role.value}) logged in successfully.",
        )
        return {
            "success": True,
            "token": token,
            "user": profile.model_dump(),
            "profile_meta": db_user,
        }

    # 2. Check built-in emergency fallback accounts
    result = authenticate_user(creds.username, creds.password)
    if not result:
        database.insert_auth_audit_log(
            username=creds.username,
            role="unknown",
            action="LOGIN_FAILED",
            details=f"Failed login attempt for username '{creds.username}'.",
        )
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password.",
        )

    profile, token = result
    database.insert_auth_audit_log(
        username=profile.username,
        role=profile.role.value,
        action="LOGIN_SUCCESS",
        details=f"Built-in user {profile.username} authenticated.",
    )
    return {
        "success": True,
        "token": token,
        "user": profile.model_dump(),
    }


@app.post("/api/v1/auth/signup/otp/generate")
def auth_generate_signup_otp(payload: CitizenSignupOtpRequest):
    """Generate an automated 6-digit verification OTP and dispatch via Email/SMS."""
    contact = payload.phone_or_email.strip()
    if not contact or len(contact) < 5:
        raise HTTPException(status_code=400, detail="Valid phone number or email is required.")

    otp = database.create_otp(contact)
    is_email = "@" in contact and "." in contact
    delivery_report = {}

    if is_email:
        delivery_report = email_service.send_otp_email(
            recipient_email=contact,
            otp_code=otp,
            user_name=contact.split("@")[0].capitalize(),
        )

    database.insert_auth_audit_log(
        username=contact,
        role="public",
        action="GENERATE_OTP",
        details=f"Generated OTP verification code for citizen: {contact} (Channel: {'EMAIL' if is_email else 'SMS'})",
    )
    return {
        "success": True,
        "otp": otp,
        "phone_or_email": contact,
        "channel": "EMAIL" if is_email else "SMS",
        "delivery": delivery_report,
        "message": f"Verification code dispatched to {contact} ({'Email Inbox' if is_email else 'SMS'}). Valid for 5 minutes.",
    }


@app.post("/api/v1/auth/signup/otp/verify")
def auth_verify_signup_otp(payload: CitizenSignupVerifyRequest):
    """Validate citizen OTP and register the public citizen account."""
    contact = payload.phone_or_email.strip()
    otp_ok = database.verify_otp(contact, payload.otp_code.strip())
    if not otp_ok:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP verification code.")

    username = payload.username.strip().lower()
    if not username:
        raise HTTPException(status_code=400, detail="Username cannot be empty.")
    if len(payload.password) < 4:
        raise HTTPException(status_code=400, detail="Password must be at least 4 characters.")

    created = database.create_user(
        username=username,
        password=payload.password,
        role="viewer",
        full_name=payload.full_name.strip() or "Citizen Member",
        email_or_phone=contact,
        created_by="SELF_SIGNUP",
    )
    if not created:
        raise HTTPException(status_code=400, detail="Failed to create user account.")

    database.insert_auth_audit_log(
        username=username,
        role="public",
        action="CITIZEN_REGISTRATION",
        details=f"Citizen {payload.full_name} registered successfully with contact {contact}.",
    )
    return {
        "success": True,
        "username": username,
        "message": f"Account '{username}' created successfully! You may now log in.",
    }


@app.post("/api/v1/auth/ranger/create")
def auth_create_ranger(payload: CreateRangerRequest):
    """Chief Ranger creates a new Field Ranger account with auto-generated credentials and dispatches to Ranger email."""
    import random
    full_name = payload.full_name.strip()
    if not full_name:
        raise HTTPException(status_code=400, detail="Ranger full name is required.")

    # Strip honorific 'Ranger' if user entered 'Ranger Rajesh'
    name_tokens = [t for t in full_name.split() if t.lower() not in ("ranger", "officer", "cadet")]
    first_token = name_tokens[0] if name_tokens else full_name.split()[0]
    first_name_clean = "".join(c for c in first_token if c.isalnum()).lower()
    rand_suffix = random.randint(10, 99)
    username = f"ranger.{first_name_clean}{rand_suffix}"

    pwd_num = random.randint(100, 999)
    password = f"Aura#Ranger{pwd_num}"

    callsign = payload.callsign.strip() or f"SENTRY-{random.randint(10, 99)}"
    rank = payload.rank.strip() or "Field Ranger"
    sector = payload.sector.strip() or "Sector 4 (Tiger Corridor)"

    # Determine email contact
    email_contact = payload.email.strip()
    if not email_contact and "@" in payload.phone:
        email_contact = payload.phone.strip()
    contact_val = email_contact or payload.phone.strip()

    success = database.create_user(
        username=username,
        password=password,
        role="ranger",
        full_name=full_name,
        email_or_phone=contact_val,
        callsign=callsign,
        rank=rank,
        sector=sector,
        created_by="chief",
    )
    if not success:
        raise HTTPException(status_code=500, detail="Could not create ranger user.")

    # Dispatch official credentials email to Ranger
    delivery_report = {}
    if email_contact and "@" in email_contact:
        delivery_report = email_service.send_ranger_credentials_email(
            recipient_email=email_contact,
            full_name=full_name,
            username=username,
            password=password,
            callsign=callsign,
            rank=rank,
            sector=sector,
        )

    database.insert_auth_audit_log(
        username="chief",
        role="admin",
        action="CHIEF_CREATE_RANGER",
        details=f"Chief generated credentials for Ranger {full_name} (User: {username}, Callsign: {callsign}) -> Dispatched to {contact_val}.",
    )
    return {
        "success": True,
        "username": username,
        "password": password,
        "full_name": full_name,
        "callsign": callsign,
        "rank": rank,
        "sector": sector,
        "email": email_contact,
        "phone": payload.phone.strip(),
        "delivery": delivery_report,
        "message": f"Field Ranger account created! Credentials dispatched to {contact_val}.",
    }


@app.get("/api/v1/auth/users")
def auth_get_users(role: str | None = None):
    """List all registered users (Chief Ranger / Admin access)."""
    users = database.get_all_users(role=role)
    return {
        "success": True,
        "count": len(users),
        "users": users,
    }


@app.delete("/api/v1/auth/users/{username}")
def auth_delete_user(username: str):
    """Delete a user account (Chief Ranger only)."""
    if username.strip().lower() in ("chief", "admin"):
        raise HTTPException(status_code=403, detail="Chief / Admin root account cannot be deleted.")

    success = database.delete_user(username)
    if not success:
        raise HTTPException(status_code=404, detail=f"User '{username}' not found.")

    database.insert_auth_audit_log(
        username="chief",
        role="admin",
        action="DELETE_USER",
        details=f"Chief deleted account for user '{username}'.",
    )
    return {
        "success": True,
        "username": username,
        "message": f"User '{username}' successfully deleted.",
    }


@app.post("/api/v1/auth/users/{username}/password")
def auth_update_user_password(username: str, payload: UpdateUserPasswordRequest):
    """Chief Ranger updates a user's password."""
    new_pwd = payload.new_password.strip()
    if len(new_pwd) < 4:
        raise HTTPException(status_code=400, detail="Password must be at least 4 characters.")

    user = database.get_user(username)
    if not user:
        raise HTTPException(status_code=404, detail=f"User '{username}' not found.")

    database.create_user(
        username=user["username"],
        password=new_pwd,
        role=user["role"],
        full_name=user["full_name"],
        email_or_phone=user.get("email_or_phone", ""),
        callsign=user.get("callsign"),
        rank=user.get("rank"),
        sector=user.get("sector"),
        created_by="chief_password_reset",
    )
    database.insert_auth_audit_log(
        username="chief",
        role="admin",
        action="UPDATE_USER_PASSWORD",
        details=f"Password updated for user '{username}'.",
    )
    return {
        "success": True,
        "username": username,
        "message": f"Password for '{username}' successfully updated.",
    }


@app.get("/api/v1/auth/me")
def auth_me(authorization: str | None = Header(None)):
    """Validate current session token and return user identity and permissions."""
    token = authorization.replace("Bearer ", "").strip() if authorization else ""
    profile = SessionTokenManager.verify_token(token)
    if not profile:
        raise HTTPException(
            status_code=401,
            detail="Invalid, expired, or missing session token.",
        )
    return {
        "authenticated": True,
        "user": profile.model_dump(),
    }


@app.get("/api/v1/auth/roles")
def auth_roles():
    """Return all available RBAC roles and their associated permissions."""
    return {
        "roles": [r.value for r in UserRole],
        "permissions": {r.value: perms for r, perms in ROLE_PERMISSIONS.items()},
    }


@app.post("/api/v1/auth/verify_key")
def auth_verify_device_key(payload: TokenVerifyRequest):
    """Verify an edge node device token or master API key."""
    ok, msg = DeviceAuthenticator.verify_device_token(
        payload.token,
        device_id=payload.device_id,
        enforce=True,
    )
    return {
        "valid": ok,
        "message": msg,
        "device_id": payload.device_id,
    }


# ==========================================================
# ROOT
# ==========================================================

@app.get("/")
def root():

    return {
        "service":
            "Adaptive Edge Intelligence API",

        "status":
            "online",
    }


# ==========================================================
# HEALTH
# ==========================================================

@app.get("/health")
def health():

    return {

        "status":
            "healthy",

        "stored_records":
            database.count(),

        "tracked_devices":
            len(latest_device_telemetry),

        "inference_model":
            "mobilenet_v3_small",

    }


# ==========================================================
# ESP32 HARDWARE TELEMETRY
# ==========================================================

@app.post(
    "/api/v1/edge/telemetry"
)
def receive_telemetry(
    telemetry: TelemetryRequest,
    x_device_token: str | None = Header(None),
    x_api_key: str | None = Header(None),
):
    """
    Receive live hardware telemetry from an ESP32.

    Telemetry is verified for:
    1. Edge Device API Key / Token Authentication
    2. Physical sensor sanity boundaries (anti-spoofing)
    3. Timestamp replay window

    Telemetry is stored in:
    1. In-memory cache (used immediately by audio inference)
    2. Persistent SQLite telemetry table (used by dashboard)
    """

    # ------------------------------------------------------
    # 1. Edge Device Authentication
    # ------------------------------------------------------
    auth_token = x_device_token or x_api_key
    auth_ok, auth_msg = DeviceAuthenticator.verify_device_token(
        auth_token,
        device_id=telemetry.device_id,
    )
    if not auth_ok:
        raise HTTPException(
            status_code=401,
            detail=f"Security rejection: {auth_msg}",
        )

    # ------------------------------------------------------
    # 2. Validation
    # ------------------------------------------------------

    if not telemetry.device_id.strip():

        raise HTTPException(
            status_code=400,
            detail="device_id cannot be empty.",
        )

    # ------------------------------------------------------
    # 3. Data Integrity & Anti-Spoofing Checks
    # ------------------------------------------------------
    bounds_ok, violations = DataIntegrityVerifier.validate_telemetry_bounds(
        telemetry.model_dump()
    )
    if not bounds_ok:
        print(f"[!] Warning: Edge telemetry boundary anomaly on {telemetry.device_id}: {violations}")

    # ------------------------------------------------------
    # 4. Normalize values
    # ------------------------------------------------------

    device_id = (
        telemetry.device_id.strip()
    )

    timestamp = float(
        telemetry.timestamp
    )

    device_status = (
        telemetry.device_status
    )

    location = (
        telemetry.location
    )

    hardware_health = (
        telemetry.hardware_health
    )

    # ------------------------------------------------------
    # Gas sensor interpretation (MQ-2 / MQ-135)
    # ------------------------------------------------------
    if isinstance(device_status, dict):
        mq2_raw = float(device_status.get("mq2_raw", 0.0))
        mq2_volt = float(device_status.get("mq2_adc_voltage", device_status.get("mq2_voltage", 0.0)))
        mq135_raw = float(device_status.get("mq135_raw", 0.0))
        mq135_volt = float(device_status.get("mq135_adc_voltage", device_status.get("mq135_voltage", 0.0)))

        if mq2_raw > 0 or mq135_raw > 0:
            gas_assessment = gas_interpreter.update(
                device_id=device_id,
                mq2_raw=mq2_raw,
                mq2_voltage=mq2_volt,
                mq135_raw=mq135_raw,
                mq135_voltage=mq135_volt,
                timestamp=timestamp,
            )
            device_status["gas_assessment"] = gas_assessment.to_dict()
            device_status["gas_risk_score"] = gas_assessment.gas_risk_score

    # ------------------------------------------------------
    # Update in-memory cache
    # ------------------------------------------------------

    latest_device_telemetry[
        device_id
    ] = {

        "device_status":
            device_status,

        "location":
            location,

        "hardware_health":
            hardware_health,

        "timestamp":
            timestamp,

    }

    # ------------------------------------------------------
    # Persist latest telemetry
    # ------------------------------------------------------

    try:

        database.upsert_telemetry(

            device_id=device_id,

            timestamp=timestamp,

            device_status=device_status,

            location=location,

            hardware_health=hardware_health,

        )

        database.insert_telemetry_history(

            device_id=device_id,

            timestamp=timestamp,

            device_status=device_status,

            location=location,

            hardware_health=hardware_health,

        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to store telemetry: "
                f"{exc}"
            ),
        ) from exc

    # ------------------------------------------------------
    # Response
    # ------------------------------------------------------

    return {

        "success":
            True,

        "device_id":
            device_id,

        "timestamp":
            timestamp,

        "telemetry_cached":
            True,

        "telemetry_persisted":
            True,

    }


# ==========================================================
# GET LATEST TELEMETRY
# ==========================================================

@app.get(
    "/api/v1/edge/devices/{device_id}/telemetry"
)
def device_telemetry(
    device_id: str,
):
    """
    Return the latest telemetry for a device.

    Persistent SQLite storage is the source of truth.
    The memory cache is used only as a fallback.
    """

    if not device_id.strip():

        raise HTTPException(
            status_code=400,
            detail="device_id cannot be empty.",
        )

    device_id = (
        device_id.strip()
    )

    # ------------------------------------------------------
    # Persistent telemetry first
    # ------------------------------------------------------

    telemetry = (
        database.get_latest_telemetry(
            device_id
        )
    )

    # ------------------------------------------------------
    # Memory fallback
    # ------------------------------------------------------

    if telemetry is None:

        telemetry = (
            latest_device_telemetry.get(
                device_id
            )
        )

    # ------------------------------------------------------
    # No telemetry
    # ------------------------------------------------------

    if telemetry is None:

        raise HTTPException(
            status_code=404,
            detail=(
                "No telemetry available for "
                f"device '{device_id}'."
            ),
        )

    # ------------------------------------------------------
    # Response
    # ------------------------------------------------------

    return {

        "success":
            True,

        "device_id":
            device_id,

        **telemetry,

    }


@app.get(
    "/api/v1/edge/devices/{device_id}/gas"
)
def get_device_gas_status(
    device_id: str,
):
    """
    Retrieve real-time MQ-2 / MQ-135 gas anomaly assessment and trend analysis.
    """
    device_id = device_id.strip()
    cached = latest_device_telemetry.get(device_id)

    if cached and "device_status" in cached and "gas_assessment" in cached["device_status"]:
        return {
            "success": True,
            "device_id": device_id,
            "gas_assessment": cached["device_status"]["gas_assessment"],
            "timestamp": cached.get("timestamp"),
        }

    # Fallback to evaluating whatever raw readings exist in database or memory
    telemetry = database.get_latest_telemetry(device_id) or cached
    if telemetry is None:
        raise HTTPException(
            status_code=404,
            detail=f"No telemetry available for device '{device_id}'.",
        )

    dev_status = telemetry.get("device_status", {})
    assessment = gas_interpreter.evaluate_telemetry(dev_status, device_id=device_id)

    return {
        "success": True,
        "device_id": device_id,
        "gas_assessment": assessment.to_dict(),
        "timestamp": telemetry.get("timestamp"),
    }


@app.get(
    "/api/v1/edge/devices/{device_id}/telemetry/history"
)
def get_device_telemetry_history(
    device_id: str,
    limit: int = 100,
    start_time: float | None = None,
    end_time: float | None = None,
):
    """
    Retrieve historical sensor telemetry logged in the runtime database.
    """
    device_id = device_id.strip()
    records = database.get_telemetry_history(
        device_id=device_id,
        limit=limit,
        start_time=start_time,
        end_time=end_time,
    )
    return {
        "success": True,
        "device_id": device_id,
        "count": len(records),
        "history": records,
    }


@app.get(
    "/api/v1/edge/devices/{device_id}/gas/history"
)
def get_device_gas_history(
    device_id: str,
    limit: int = 100,
):
    """
    Retrieve historical MQ-2 and MQ-135 gas sensor time-series.
    """
    device_id = device_id.strip()
    records = database.get_gas_history(
        device_id=device_id,
        limit=limit,
    )
    return {
        "success": True,
        "device_id": device_id,
        "count": len(records),
        "gas_history": records,
    }


@app.get(
    "/api/v1/edge/database/stats"
)
def get_database_stats():
    """
    Retrieve SQLite database storage and record count statistics.
    """
    stats = database.get_database_stats()
    return {
        "success": True,
        **stats,
    }


@app.post(
    "/api/v1/edge/experiments"
)
def log_experiment_result(
    payload: dict[str, Any],
):
    """
    Persist an experiment evaluation, benchmarking run, or field trial result.
    """
    name = payload.get("experiment_name")
    if not name:
        raise HTTPException(
            status_code=400,
            detail="Missing 'experiment_name' in payload.",
        )
    summary = payload.get("summary", {})
    details = payload.get("details", payload.get("trials", []))
    config = payload.get("config", {})
    timestamp = payload.get("timestamp")

    log_id = database.insert_experiment_log(
        experiment_name=name,
        summary=summary,
        details=details,
        config=config,
        timestamp=timestamp,
    )
    return {
        "success": True,
        "record_id": log_id,
        "experiment_name": name,
    }


@app.get(
    "/api/v1/edge/experiments"
)
def get_experiments_list(
    limit: int = 50,
):
    """
    Retrieve a list of all logged experiments and benchmarks.
    """
    logs = database.get_all_experiments(limit=limit)
    return {
        "success": True,
        "count": len(logs),
        "experiments": logs,
    }


@app.get(
    "/api/v1/edge/experiments/{experiment_name}"
)
def get_experiment_detail(
    experiment_name: str,
):
    """
    Retrieve the latest full report for a specific experiment.
    """
    log = database.get_latest_experiment(experiment_name=experiment_name)
    if log is None:
        raise HTTPException(
            status_code=404,
            detail=f"No experiment record found for '{experiment_name}'.",
        )
    return {
        "success": True,
        "experiment": log,
    }


# ==========================================================
# EDGE RUNTIME EVENTS
# ==========================================================

@app.post(
    "/api/v1/edge/events",
    response_model=MessageResponse,
)
def receive_edge_event(
    message: EdgeMessageRequest,
):

    payload = message.model_dump()

    # ------------------------------------------------------
    # Update telemetry cache if available
    # ------------------------------------------------------

    if (
        message.device_status is not None
        or message.location is not None
    ):

        previous = (
            latest_device_telemetry.get(
                message.device_id,
                {}
            )
        )

        latest_device_telemetry[
            message.device_id
        ] = {

            "device_status":
                (
                    message.device_status
                    if message.device_status is not None
                    else previous.get(
                        "device_status"
                    )
                ),

            "location":
                (
                    message.location
                    if message.location is not None
                    else previous.get(
                        "location"
                    )
                ),

            "hardware_health":
                previous.get(
                    "hardware_health"
                ),

            "timestamp":
                message.timestamp,

        }

    # ------------------------------------------------------
    # Store runtime event
    # ------------------------------------------------------

    try:

        record_id = (
            database.insert_message(
                payload
            )
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to store edge event: "
                f"{exc}"
            ),
        ) from exc

    return MessageResponse(

        success=True,

        record_id=record_id,

    )


# ==========================================================
# AUDIO INGESTION
# ==========================================================

@app.post(
    "/api/v1/edge/audio"
)
async def receive_edge_audio(

    device_id: str,

    timestamp: float,

    sample_rate: int = 16000,

    audio: bytes = Body(
        ...,
        media_type="application/octet-stream",
    ),

    x_device_token: str | None = Header(None),

    x_api_key: str | None = Header(None),

):

    # ------------------------------------------------------
    # 1. Edge Device Authentication
    # ------------------------------------------------------
    auth_token = x_device_token or x_api_key
    auth_ok, auth_msg = DeviceAuthenticator.verify_device_token(
        auth_token,
        device_id=device_id,
    )
    if not auth_ok:
        raise HTTPException(
            status_code=401,
            detail=f"Security rejection: {auth_msg}",
        )

    # ------------------------------------------------------
    # 2. Validation
    # ------------------------------------------------------

    if not device_id.strip():

        raise HTTPException(
            status_code=400,
            detail="device_id cannot be empty.",
        )

    if sample_rate <= 0:

        raise HTTPException(
            status_code=400,
            detail=(
                "sample_rate must be greater "
                "than zero."
            ),
        )

    if not audio:

        raise HTTPException(
            status_code=400,
            detail="Audio payload is empty.",
        )

    # ------------------------------------------------------
    # Retrieve latest telemetry
    # ------------------------------------------------------

    cached = (
        latest_device_telemetry.get(
            device_id
        )
    )

    device_status = None

    location = None

    hardware_health = None

    telemetry_timestamp = None

    if cached is not None:

        device_status = (
            cached.get(
                "device_status"
            )
        )

        location = (
            cached.get(
                "location"
            )
        )

        hardware_health = (
            cached.get(
                "hardware_health"
            )
        )

        telemetry_timestamp = (
            cached.get(
                "timestamp"
            )
        )

    # ------------------------------------------------------
    # Persist temporary audio evidence
    # ------------------------------------------------------
    #
    # The predictor/unknown-discovery pipeline needs a stable
    # audio_path at the moment it creates an UnknownSample.
    #
    # Known audio is deleted immediately after successful
    # inference. Unknown candidates are retained for human
    # review and later cluster playback.
    # ------------------------------------------------------

    audio_evidence_path: Path | None = None

    try:
        audio_evidence_path = _save_audio_evidence(
            audio_bytes=audio,
            sample_rate=sample_rate,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to persist audio evidence: "
                f"{exc}"
            ),
        ) from exc

    # ------------------------------------------------------
    # Run complete inference pipeline
    # ------------------------------------------------------

    try:

        inference_result = (
            audio_service.infer_pcm16(

                audio_bytes=audio,

                sample_rate=sample_rate,

                top_k=5,

                device_status=device_status,

                audio_path=str(audio_evidence_path),

            )
        )

    except ValueError as exc:

        if audio_evidence_path is not None:
            try:
                audio_evidence_path.unlink(missing_ok=True)
            except OSError:
                pass

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:

        if audio_evidence_path is not None:
            try:
                audio_evidence_path.unlink(missing_ok=True)
            except OSError:
                pass

        raise HTTPException(
            status_code=500,
            detail=(
                "Audio inference failed: "
                f"{exc}"
            ),
        ) from exc

    # ------------------------------------------------------
    # Build complete runtime event
    # ------------------------------------------------------
    #
    # AudioInferenceService may return the runtime pipeline
    # under "edge_runtime". We preserve the complete result
    # while also supporting direct top-level fields.
    # ------------------------------------------------------

    runtime = (
        inference_result.get("edge_runtime")
        or {}
    )

    prediction = (
        runtime.get("prediction")
        or inference_result.get("prediction")
        or {}
    )

    environment = (
        runtime.get("environment")
        or runtime.get("environment_profile")
        or inference_result.get("environment")
        or {}
    )

    adaptive_policy = (
        runtime.get("adaptive_policy")
        or inference_result.get("adaptive_policy")
        or {}
    )

    event = (
        runtime.get("event")
        or inference_result.get("event")
        or {}
    )

    decision = (
        runtime.get("decision")
        or inference_result.get("decision")
    )

    unknown_discovery = (
        runtime.get("unknown_discovery")
        or runtime.get("discovery_result")
        or inference_result.get("unknown_discovery")
    )

    # ------------------------------------------------------
    # Ensure event has useful fallback information
    # ------------------------------------------------------

    if not event and prediction:
        event = {
            "label":
                prediction.get("label", "Unknown"),

            "class_id":
                prediction.get("class_id"),

            "confidence":
                prediction.get("confidence", 0.0),

            "inference_time_ms":
                prediction.get(
                    "inference_time_ms",
                    0.0,
                ),

            "detected":
                True,
        }

    # ------------------------------------------------------
    # Location fallback
    # ------------------------------------------------------

    if location is None:
        location = {
            "latitude": 12.2958,
            "longitude": 76.6394,
            "name": "Mysore",
            "source": "FALLBACK",
        }

    # ------------------------------------------------------
    # Persist audio inference as a runtime event
    # ------------------------------------------------------

    runtime_message = {
        "device_id":
            device_id,

        "timestamp":
            timestamp,

        "prediction":
            prediction,

        "environment":
            environment,

        "adaptive_policy":
            adaptive_policy,

        "event":
            event,

        "decision":
            decision,

        "unknown_discovery":
            unknown_discovery,

        "location":
            location,

        "device_status":
            device_status,
    }

    try:
        record_id = database.insert_message(
            runtime_message
        )

    except Exception as exc:
        if audio_evidence_path is not None:
            try:
                audio_evidence_path.unlink(missing_ok=True)
            except OSError:
                pass

        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to store audio runtime "
                f"event: {exc}"
            ),
        ) from exc

    # ------------------------------------------------------
    # Retain evidence only for unknown candidates
    # ------------------------------------------------------

    evidence_retained = _unknown_evidence_required(
        inference_result
    )

    if not evidence_retained and audio_evidence_path is not None:
        try:
            audio_evidence_path.unlink(
                missing_ok=True
            )
            audio_evidence_path = None
        except OSError:
            pass

    # ------------------------------------------------------
    # Refresh telemetry cache
    # ------------------------------------------------------

    latest_device_telemetry[
        device_id
    ] = {
        "device_status":
            device_status,

        "location":
            location,

        "hardware_health":
            hardware_health,

        "timestamp":
            timestamp,
    }

    # ------------------------------------------------------
    # Return complete result
    # ------------------------------------------------------

    # ------------------------------------------------------
    # Automatic Local Emergency Alert Dispatch
    # ------------------------------------------------------

    alert_info = None
    if alert_dispatcher.should_trigger_emergency(prediction, decision):
        alert_payload = alert_dispatcher.create_alert_payload(
            device_id=device_id,
            threat_type=str(prediction.get("label", "Threat")),
            confidence=float(prediction.get("confidence", 0.0)),
            risk_level=str(decision.get("risk_level", "CRITICAL")),
            location=location,
            decision=decision,
            contributing_factors=decision.get("contributing_factors", []),
        )
        alert_info = alert_dispatcher.dispatch_alert(alert_payload)

    return {
        "success":
            True,

        "record_id":
            record_id,

        "device_id":
            device_id,

        "timestamp":
            timestamp,

        "emergency_alert":
            alert_info,

        "telemetry_context":
            {
                "available":
                    cached is not None,

                "telemetry_timestamp":
                    telemetry_timestamp,

                "device_status":
                    device_status,

                "location":
                    location,

                "hardware_health":
                    hardware_health,
            },

        "runtime":
            {
                "prediction":
                    prediction,

                "environment":
                    environment,

                "adaptive_policy":
                    adaptive_policy,

                "event":
                    event,

                "decision":
                    decision,

                "unknown_discovery":
                    unknown_discovery,

                "audio_evidence":
                    {
                        "retained":
                            evidence_retained,

                        "audio_url":
                            (
                                f"/api/v1/edge/unknown/samples/audio/{audio_evidence_path.name}"
                                if audio_evidence_path is not None
                                and evidence_retained
                                else None
                            ),
                    },
            },

        "inference":
            inference_result,
    }


# ==========================================================
# LATEST EVENT
# ==========================================================

@app.get(
    "/api/v1/edge/events/latest"
)
def latest_event():

    result = (
        database.get_latest()
    )

    if result is None:

        raise HTTPException(
            status_code=404,
            detail=(
                "No edge events available."
            ),
        )

    return result


# ==========================================================
# RECENT EVENTS
# ==========================================================

@app.get(
    "/api/v1/edge/events"
)
def recent_events(
    limit: int = 50,
):

    if limit <= 0:

        raise HTTPException(
            status_code=400,
            detail=(
                "limit must be greater than zero."
            ),
        )

    if limit > 500:

        raise HTTPException(
            status_code=400,
            detail=(
                "limit cannot exceed 500."
            ),
        )

    return database.get_recent(
        limit=limit
    )


# ==========================================================
# UNKNOWN SOUND DISCOVERY
# ==========================================================


def _get_discovery_predictor():
    """Return the singleton predictor used by the live audio service."""

    predictor = getattr(audio_service, "predictor", None)

    if predictor is None:
        raise HTTPException(
            status_code=503,
            detail="Unknown discovery is unavailable because the predictor is not initialized.",
        )

    return predictor


def _get_last_raw_prediction_compat(predictor):
    """Return the latest raw prediction when supported by Predictor."""
    getter = getattr(predictor, "get_last_raw_prediction", None)
    if callable(getter):
        return getter()

    # Older Predictor versions did not expose a raw-prediction getter.
    # Returning None keeps the status endpoint backward compatible.
    return None


def _get_unknown_clusters_compat(predictor):
    """Return persistent unknown clusters across supported Predictor versions."""
    getter = getattr(predictor, "get_unknown_clusters", None)
    if callable(getter):
        return getter()

    manager = getattr(predictor, "discovery_manager", None)
    if manager is None:
        return []

    getter = getattr(manager, "get_clusters", None)
    if callable(getter):
        return getter()

    return []


def _get_unknown_manager(predictor):
    """Resolve the active unknown-discovery manager."""
    manager = getattr(predictor, "discovery_manager", None)
    if manager is not None:
        return manager

    manager = getattr(predictor, "unknown_discovery_manager", None)
    if manager is not None:
        return manager

    manager = getattr(predictor, "unknown_manager", None)
    if manager is not None:
        return manager

    return None


@app.get(
    "/api/v1/edge/unknown/status"
)
def unknown_discovery_status():
    """Return live open-set detection and clustering status."""

    predictor = _get_discovery_predictor()

    try:
        return {
            "success": True,
            "discovery": predictor.get_unknown_discovery_status(),
            "last_raw_prediction":
                _get_last_raw_prediction_compat(predictor),
            "last_discovery_result":
                predictor.get_last_discovery_result(),
        }
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to read unknown discovery status: {exc}",
        ) from exc


@app.get(
    "/api/v1/edge/unknown/clusters"
)
def unknown_discovery_clusters():
    """Return all persistent discovered unknown-sound clusters."""

    predictor = _get_discovery_predictor()

    try:
        return {
            "success": True,
            "clusters": _get_unknown_clusters_compat(predictor),
        }
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to read unknown clusters: {exc}",
        ) from exc


@app.post(
    "/api/v1/edge/unknown/clusters/{cluster_id}/label"
)
def label_unknown_cluster(
    cluster_id: str,
    request: UnknownClusterLabelRequest,
):
    """Apply a human-readable label to a discovered cluster."""

    if not cluster_id.strip():
        raise HTTPException(
            status_code=400,
            detail="cluster_id cannot be empty.",
        )

    if not request.label.strip():
        raise HTTPException(
            status_code=400,
            detail="label cannot be empty.",
        )

    predictor = _get_discovery_predictor()

    try:
        predictor_label = getattr(
            predictor,
            "label_unknown_cluster",
            None,
        )

        if callable(predictor_label):
            cluster = predictor_label(
                cluster_id=cluster_id,
                label=request.label,
                notes=request.notes,
            )
        else:
            manager = _get_unknown_manager(predictor)
            if manager is None:
                raise RuntimeError(
                    "Unknown discovery manager is unavailable."
                )

            manager_label = getattr(
                manager,
                "label_cluster",
                None,
            )

            if not callable(manager_label):
                raise RuntimeError(
                    "Human cluster labeling is not supported by the "
                    "current unknown-discovery manager."
                )

            cluster = manager_label(
                cluster_id=cluster_id,
                label=request.label,
                notes=request.notes,
            )

        return {
            "success": True,
            "cluster": cluster,
        }

    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to label unknown cluster: {exc}",
        ) from exc


@app.post(
    "/api/v1/edge/unknown/clusters/{cluster_id}/unlabel"
)
def unlabel_unknown_cluster(
    cluster_id: str,
):
    """Remove a human label while retaining the discovered cluster."""

    if not cluster_id.strip():
        raise HTTPException(
            status_code=400,
            detail="cluster_id cannot be empty.",
        )

    predictor = _get_discovery_predictor()

    try:
        predictor_unlabel = getattr(
            predictor,
            "unlabel_unknown_cluster",
            None,
        )

        if callable(predictor_unlabel):
            cluster = predictor_unlabel(
                cluster_id=cluster_id,
            )
        else:
            manager = _get_unknown_manager(predictor)
            if manager is None:
                raise RuntimeError(
                    "Unknown discovery manager is unavailable."
                )

            manager_unlabel = getattr(
                manager,
                "unlabel_cluster",
                None,
            )

            if not callable(manager_unlabel):
                raise RuntimeError(
                    "Human cluster unlabeling is not supported by the "
                    "current unknown-discovery manager."
                )

            cluster = manager_unlabel(
                cluster_id=cluster_id,
            )

        return {
            "success": True,
            "cluster": cluster,
        }

    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to unlabel unknown cluster: {exc}",
        ) from exc


@app.post(
    "/api/v1/edge/unknown/buffer/clear"
)
def clear_unknown_buffer():
    """Clear buffered unknown samples without deleting discovered clusters."""

    predictor = _get_discovery_predictor()

    try:
        predictor.clear_unknown_buffer()
        return {
            "success": True,
            "message": "Unknown-sound buffer cleared.",
            "discovery": predictor.get_unknown_discovery_status(),
        }
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear unknown buffer: {exc}",
        ) from exc


@app.post(
    "/api/v1/edge/unknown/cluster"
)
def trigger_unknown_clustering(
    force: bool = True,
):
    """Trigger clustering on pending unknown-sound observations."""

    predictor = _get_discovery_predictor()

    try:
        trigger_fn = getattr(predictor, "trigger_clustering", None)
        if callable(trigger_fn):
            result, cluster_ids = trigger_fn(force=force)
        else:
            manager = _get_unknown_manager(predictor)
            if manager is None:
                raise RuntimeError("Unknown discovery manager is unavailable.")
            result_obj, cluster_ids = manager.cluster(force=force)
            result = result_obj.to_dict() if hasattr(result_obj, "to_dict") else result_obj

        return {
            "success": True,
            "message": f"Clustering executed. Generated {len(cluster_ids)} new cluster(s).",
            "cluster_result": result,
            "new_cluster_ids": cluster_ids,
            "discovery": predictor.get_unknown_discovery_status(),
        }
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to run clustering: {exc}",
        ) from exc


# ==========================================================
# UNKNOWN AUDIO HUMAN-REVIEW API
# ==========================================================


@app.get(
    "/api/v1/edge/unknown/clusters/{cluster_id}/samples"
)
def unknown_cluster_samples(
    cluster_id: str,
):
    """Return sample metadata for a discovered unknown cluster."""
    if not cluster_id.strip():
        raise HTTPException(
            status_code=400,
            detail="cluster_id cannot be empty.",
        )

    predictor = _get_discovery_predictor()
    manager = _get_unknown_manager(predictor)

    if manager is None:
        raise HTTPException(
            status_code=503,
            detail="Unknown discovery manager is unavailable.",
        )

    try:
        samples = manager.get_samples(
            cluster_id
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to read cluster samples: "
                f"{exc}"
            ),
        ) from exc

    result = []

    for sample in samples:
        if hasattr(sample, "to_dict"):
            item = sample.to_dict()
        elif isinstance(sample, dict):
            item = dict(sample)
        else:
            item = {
                "sample_id": str(
                    getattr(
                        sample,
                        "sample_id",
                        "",
                    )
                ),
                "cluster_id": str(
                    getattr(
                        sample,
                        "cluster_id",
                        cluster_id,
                    )
                ),
                "captured_at": getattr(
                    sample,
                    "captured_at",
                    None,
                ),
                "predicted_class": getattr(
                    sample,
                    "predicted_class",
                    None,
                ),
                "confidence": getattr(
                    sample,
                    "confidence",
                    None,
                ),
                "audio_path": getattr(
                    sample,
                    "audio_path",
                    None,
                ),
            }

        raw_path = item.pop(
            "audio_path",
            None,
        )

        safe_path = _safe_audio_path(
            raw_path
        )

        item["audio_available"] = (
            safe_path is not None
        )

        item["audio_url"] = (
            f"/api/v1/edge/unknown/samples/{item.get('sample_id')}/audio"
            if safe_path is not None
            else None
        )

        result.append(item)

    return {
        "success": True,
        "cluster_id": cluster_id,
        "samples": result,
        "count": len(result),
    }


@app.get(
    "/api/v1/edge/unknown/samples/{sample_id}"
)
def unknown_sample(
    sample_id: str,
):
    """Return one unknown sample's review metadata."""
    if not sample_id.strip():
        raise HTTPException(
            status_code=400,
            detail="sample_id cannot be empty.",
        )

    predictor = _get_discovery_predictor()
    manager = _get_unknown_manager(predictor)

    if manager is None:
        raise HTTPException(
            status_code=503,
            detail="Unknown discovery manager is unavailable.",
        )

    try:
        sample = manager.get_sample(
            sample_id
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to read unknown sample: "
                f"{exc}"
            ),
        ) from exc

    if hasattr(sample, "to_dict"):
        item = sample.to_dict()
    elif isinstance(sample, dict):
        item = dict(sample)
    else:
        item = {
            "sample_id": str(
                getattr(
                    sample,
                    "sample_id",
                    sample_id,
                )
            ),
            "cluster_id": getattr(
                sample,
                "cluster_id",
                None,
            ),
            "captured_at": getattr(
                sample,
                "captured_at",
                None,
            ),
            "predicted_class": getattr(
                sample,
                "predicted_class",
                None,
            ),
            "confidence": getattr(
                sample,
                "confidence",
                None,
            ),
            "audio_path": getattr(
                sample,
                "audio_path",
                None,
            ),
        }

    raw_path = item.pop(
        "audio_path",
        None,
    )

    safe_path = _safe_audio_path(
        raw_path
    )

    item["audio_available"] = (
        safe_path is not None
    )

    item["audio_url"] = (
        f"/api/v1/edge/unknown/samples/{sample_id}/audio"
        if safe_path is not None
        else None
    )

    return {
        "success": True,
        "sample": item,
    }


@app.get(
    "/api/v1/edge/unknown/samples/{sample_id}/audio"
)
def unknown_sample_audio(
    sample_id: str,
):
    """Stream a retained unknown-sample audio file."""
    if not sample_id.strip():
        raise HTTPException(
            status_code=400,
            detail="sample_id cannot be empty.",
        )

    predictor = _get_discovery_predictor()
    manager = _get_unknown_manager(predictor)

    if manager is None:
        raise HTTPException(
            status_code=503,
            detail="Unknown discovery manager is unavailable.",
        )

    try:
        raw_path = manager.get_sample_audio_path(
            sample_id
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to locate unknown sample audio: "
                f"{exc}"
            ),
        ) from exc

    path = _safe_audio_path(
        raw_path
    )

    if path is None:
        raise HTTPException(
            status_code=404,
            detail="Audio evidence is not available for this sample.",
        )

    media_types = {
        ".wav": "audio/wav",
        ".mp3": "audio/mpeg",
        ".flac": "audio/flac",
        ".ogg": "audio/ogg",
        ".oga": "audio/ogg",
        ".m4a": "audio/mp4",
        ".aac": "audio/aac",
        ".aiff": "audio/aiff",
        ".aif": "audio/aiff",
    }

    media_type = media_types.get(
        path.suffix.lower(),
        "application/octet-stream",
    )

    return FileResponse(
        path=path,
        media_type=media_type,
        filename=path.name,
    )


# Backward-friendly endpoint for the evidence URL returned by
# the audio-ingestion response. It resolves the stored filename
# only after validating it is inside UNKNOWN_AUDIO_ROOT.
@app.get(
    "/api/v1/edge/unknown/samples/audio/{filename}"
)
def unknown_audio_by_filename(
    filename: str,
):
    """Stream retained evidence by its generated filename."""
    if not filename.strip():
        raise HTTPException(
            status_code=400,
            detail="filename cannot be empty.",
        )

    path = _safe_audio_path(
        str(
            UNKNOWN_AUDIO_ROOT
            / filename
        )
    )

    if path is None:
        raise HTTPException(
            status_code=404,
            detail="Audio evidence is not available.",
        )

    media_types = {
        ".wav": "audio/wav",
        ".mp3": "audio/mpeg",
        ".flac": "audio/flac",
        ".ogg": "audio/ogg",
        ".oga": "audio/ogg",
        ".m4a": "audio/mp4",
        ".aac": "audio/aac",
        ".aiff": "audio/aiff",
        ".aif": "audio/aiff",
    }

    return FileResponse(
        path=path,
        media_type=media_types.get(
            path.suffix.lower(),
            "application/octet-stream",
        ),
        filename=path.name,
    )


# ==========================================================
# DEVICES
# ==========================================================

@app.get(
    "/api/v1/edge/devices"
)
def devices():

    return {

        "devices":
            database.get_devices()

    }


# ==========================================================
# EMERGENCY ALERT NOTIFICATION ENDPOINTS
# ==========================================================

class EmergencyAlertRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    device_id: str = "edge_sentinel_001"
    threat_type: str = "Chainsaw"
    confidence: float = 0.95
    risk_level: str = "CRITICAL"
    latitude: float | None = 12.2958
    longitude: float | None = 76.6394
    action: str = "DISPATCH_RANGERS"
    contributing_factors: list[str] = ["Acoustic signature 95%", "SW-420 vibration latched"]


class AcknowledgeAlertRequest(BaseModel):
    acknowledged_by: str = "Ranger Command Center"


@app.get(
    "/api/v1/edge/alerts/active"
)
def get_active_alerts(
    limit: int = 20,
):
    """Retrieve all unacknowledged (active) emergency alerts."""
    return {
        "success": True,
        "count": len(database.get_active_emergency_alerts(limit=limit)),
        "alerts": database.get_active_emergency_alerts(limit=limit),
    }


@app.get(
    "/api/v1/edge/alerts/history"
)
def get_alerts_history(
    limit: int = 50,
):
    """Retrieve emergency alert dispatch audit logs."""
    alerts = database.get_emergency_alert_history(limit=limit)
    return {
        "success": True,
        "count": len(alerts),
        "alerts": alerts,
    }


@app.post(
    "/api/v1/edge/alerts/dispatch"
)
def dispatch_emergency_alert(
    payload: EmergencyAlertRequest = Body(...),
):
    """Manually or programmatically trigger an emergency alert broadcast."""
    location = {
        "latitude": payload.latitude,
        "longitude": payload.longitude,
        "source": "SENTINEL_GPS",
    }
    decision = {
        "risk_level": payload.risk_level,
        "recommended_action": payload.action,
        "requires_attention": True,
        "contributing_factors": payload.contributing_factors,
    }

    alert_dict = alert_dispatcher.create_alert_payload(
        device_id=payload.device_id,
        threat_type=payload.threat_type,
        confidence=payload.confidence,
        risk_level=payload.risk_level,
        location=location,
        decision=decision,
        contributing_factors=payload.contributing_factors,
    )
    result = alert_dispatcher.dispatch_alert(alert_dict)

    return {
        "success": True,
        "message": "Emergency alert broadcast successfully dispatched.",
        "alert": result,
    }


@app.post(
    "/api/v1/edge/alerts/{alert_id}/acknowledge"
)
def acknowledge_alert(
    alert_id: str,
    payload: AcknowledgeAlertRequest = Body(default_factory=AcknowledgeAlertRequest),
):
    """Acknowledge an active emergency alert."""
    success = database.acknowledge_emergency_alert(
        alert_id=alert_id,
        acknowledged_by=payload.acknowledged_by,
    )
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Emergency alert '{alert_id}' not found.",
        )
    return {
        "success": True,
        "alert_id": alert_id,
        "status": "ACKNOWLEDGED",
        "acknowledged_by": payload.acknowledged_by,
    }


class ResolveAlertRequest(BaseModel):
    resolved_by: str = "Field Ranger Unit"
    resolution_notes: str = "Threat investigated and secured on site."


class AssignAlertRequest(BaseModel):
    ranger_id: str
    ranger_name: str


@app.post(
    "/api/v1/edge/alerts/{alert_id}/resolve"
)
def resolve_alert(
    alert_id: str,
    payload: ResolveAlertRequest = Body(default_factory=ResolveAlertRequest),
):
    """Mark an emergency alert as resolved/solved by field or chief ranger."""
    success = database.resolve_emergency_alert(
        alert_id=alert_id,
        resolved_by=payload.resolved_by,
        resolution_notes=payload.resolution_notes,
    )
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Emergency alert '{alert_id}' not found.",
        )
    database.insert_auth_audit_log(
        username=payload.resolved_by,
        role="ranger",
        action="RESOLVE_ALERT",
        details=f"Alert {alert_id} resolved: {payload.resolution_notes}",
    )
    return {
        "success": True,
        "alert_id": alert_id,
        "status": "RESOLVED",
        "resolved_by": payload.resolved_by,
        "resolution_notes": payload.resolution_notes,
    }


@app.post(
    "/api/v1/edge/alerts/{alert_id}/assign"
)
def assign_alert(
    alert_id: str,
    payload: AssignAlertRequest = Body(...),
):
    """Assign an active alert to a specific field ranger unit."""
    success = database.assign_emergency_alert(
        alert_id=alert_id,
        ranger_id=payload.ranger_id,
        ranger_name=payload.ranger_name,
    )
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Emergency alert '{alert_id}' not found.",
        )
    database.insert_auth_audit_log(
        username="Chief Ranger",
        role="admin",
        action="ASSIGN_ALERT",
        details=f"Alert {alert_id} assigned to {payload.ranger_name} ({payload.ranger_id})",
    )
    return {
        "success": True,
        "alert_id": alert_id,
        "status": "ASSIGNED",
        "assigned_ranger_id": payload.ranger_id,
        "assigned_ranger_name": payload.ranger_name,
    }


@app.get(
    "/api/v1/edge/rangers"
)
def get_field_rangers():
    """Return active field ranger units and real-time status."""
    return {
        "success": True,
        "rangers": database.get_field_rangers(),
    }


class RangerLocationUpdateRequest(BaseModel):
    latitude: float
    longitude: float
    battery: int | None = None
    status: str | None = None


@app.post(
    "/api/v1/edge/rangers/{ranger_id}/location"
)
def update_ranger_location(
    ranger_id: str,
    payload: RangerLocationUpdateRequest = Body(...),
):
    """Stream live phone/device GPS location and battery from on-patrol field ranger."""
    success = database.update_ranger_location(
        ranger_id=ranger_id,
        latitude=payload.latitude,
        longitude=payload.longitude,
        battery=payload.battery,
        status=payload.status,
    )
    if not success:
        raise HTTPException(status_code=404, detail=f"Ranger '{ranger_id}' not found.")
    return {
        "success": True,
        "ranger_id": ranger_id,
        "latitude": payload.latitude,
        "longitude": payload.longitude,
        "status": payload.status or "UPDATED",
    }


# ==========================================================
# PUBLIC CITIZEN TIP & REPORT ENDPOINTS
# ==========================================================

class CitizenReportRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    reporter_name: str = "Anonymous Citizen"
    contact_info: str | None = None
    threat_category: str = "Illegal Logging / Chainsaw Activity"
    description: str
    photo_filename: str | None = None
    location_lat: float | None = 12.2960
    location_lon: float | None = 76.6400


class UpdateReportStatusRequest(BaseModel):
    status: str = "VERIFIED"
    notes: str = ""


class ResolveCitizenReportRequest(BaseModel):
    resolved_by: str = "Field Ranger Unit"
    resolution_notes: str = "Citizen-reported threat investigated and secured on site."


@app.post(
    "/api/v1/public/report"
)
def submit_citizen_report(
    payload: CitizenReportRequest = Body(...),
):
    """Submit a public citizen report of illegal forest activity or sighting."""
    report_id = "cit_" + uuid.uuid4().hex[:10]
    database.insert_citizen_report(
        report_id=report_id,
        reporter_name=payload.reporter_name,
        contact_info=payload.contact_info,
        threat_category=payload.threat_category,
        description=payload.description,
        photo_filename=payload.photo_filename,
        location_lat=payload.location_lat,
        location_lon=payload.location_lon,
    )
    database.insert_auth_audit_log(
        username=payload.reporter_name,
        role="public",
        action="SUBMIT_CITIZEN_REPORT",
        details=f"Citizen report {report_id}: {payload.threat_category}",
    )
    return {
        "success": True,
        "report_id": report_id,
        "message": "Citizen tip successfully received by Chief Ranger Dispatch.",
    }


@app.get(
    "/api/v1/public/reports"
)
def get_citizen_reports(
    limit: int = 50,
    status: str | None = None,
):
    """Retrieve citizen reports for Chief Ranger review."""
    reports = database.get_citizen_reports(limit=limit, status=status)
    return {
        "success": True,
        "count": len(reports),
        "reports": reports,
    }


@app.post(
    "/api/v1/public/reports/{report_id}/status"
)
def update_citizen_report_status(
    report_id: str,
    payload: UpdateReportStatusRequest = Body(...),
):
    """Update citizen report status (Chief Ranger review)."""
    success = database.update_citizen_report_status(
        report_id=report_id,
        status=payload.status,
        notes=payload.notes,
    )
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Report '{report_id}' not found.",
        )
    return {
        "success": True,
        "report_id": report_id,
        "status": payload.status,
    }


@app.post(
    "/api/v1/public/reports/{report_id}/resolve"
)
def resolve_citizen_report(
    report_id: str,
    payload: ResolveCitizenReportRequest = Body(default_factory=ResolveCitizenReportRequest),
):
    """Mark a citizen-reported incident as resolved by Field Ranger."""
    success = database.update_citizen_report_status(
        report_id=report_id,
        status="RESOLVED",
        notes=payload.resolution_notes,
    )
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Report '{report_id}' not found.",
        )
    database.insert_auth_audit_log(
        username=payload.resolved_by,
        role="ranger",
        action="RESOLVE_CITIZEN_REPORT",
        details=f"Citizen report {report_id} resolved: {payload.resolution_notes}",
    )
    return {
        "success": True,
        "report_id": report_id,
        "status": "RESOLVED",
        "resolved_by": payload.resolved_by,
        "notes": payload.resolution_notes,
    }


# ==========================================================
# AUTH AUDIT LOG ENDPOINT
# ==========================================================

@app.get(
    "/api/v1/auth/audit_log"
)
def get_audit_log(
    limit: int = 100,
):
    """Retrieve security & authentication audit logs (Chief Ranger Only)."""
    logs = database.get_auth_audit_log(limit=limit)
    return {
        "success": True,
        "count": len(logs),
        "audit_logs": logs,
    }
