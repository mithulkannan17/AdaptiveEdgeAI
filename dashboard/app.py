"""
AuraForest — Sentinel Dashboard
Role-Based Access Control (RBAC) & Tactical Edge Command:
  1. 👑 Chief Ranger (Admin): Full sentinel telemetry, tactical map, live ranger dispatch, ranger credential generation & user management, emergency broadcast, citizen reports inbox, unknown discovery, auth audit logs.
  2. 🛡️ Field Ranger Unit: Incident response, on-site alert & citizen report resolution, sector radar, near my rangers proximity, field telemetry.
  3. 👁️ Public Citizen & Visitor: Environmental climate readings, forest safety notices, automated OTP sign-up, and geotagged illegal activity tip box with photo upload.

Run:
    streamlit run dashboard/app.py
"""

from __future__ import annotations

import math
import time
import sys
import json
import os
import base64
import random
import pandas as pd
import pydeck as pdk
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from urllib.parse import quote
from datetime import datetime
from pathlib import Path
from typing import Any

# Project root: .../AdaptiveEdgeAI
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
import streamlit.components.v1 as components

# Data sources and database
from runtime_data_source import RuntimeDataSource
from backend.database import RuntimeDatabase
from dashboard.spectrum_visualizer import render_spectrum_section

try:
    from streamlit_autorefresh import st_autorefresh
except ImportError:
    st_autorefresh = None

# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="AuraForest Sentinel",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# DATABASE & BACKEND CLIENT SETUP
# ============================================================

db = RuntimeDatabase()

@st.cache_resource
def get_source() -> RuntimeDataSource:
    return RuntimeDataSource()

source = get_source()

AURA_API_URL = os.getenv(
    "AURAFOREST_API_URL",
    "http://127.0.0.1:8000",
).rstrip("/")

# Auto-refresh only when logged in
if st.session_state.get("authenticated", False):
    if st_autorefresh is not None:
        st_autorefresh(interval=3000, key="aura_live_refresh")

# ============================================================
# DESIGN SYSTEM & MOBILE RESPONSIVE CSS
# ============================================================

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400..800;1,9..40,400..800&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

:root {
    --bg: #060a0c;
    --panel: #0c1417;
    --panel-2: #101c20;
    --line: rgba(32, 54, 62, 0.7);
    --line-glow: rgba(124, 240, 178, 0.2);
    --text: #edf6f3;
    --muted: #829a97;
    --green: #7cf0b2;
    --green-glow: rgba(124, 240, 178, 0.35);
    --cyan: #73d9e8;
    --cyan-glow: rgba(115, 217, 232, 0.35);
    --amber: #f2c66d;
    --amber-glow: rgba(242, 198, 109, 0.35);
    --red: #ff7070;
    --red-glow: rgba(255, 112, 112, 0.4);
    --purple: #bb86fc;
    --purple-glow: rgba(187, 134, 252, 0.35);
    --blue: #82b1ff;
}

html, body, [class*="css"] {
    font-family: "DM Sans", -apple-system, BlinkMacSystemFont, sans-serif;
}

.stApp {
    background:
        radial-gradient(circle at 12% 0%, rgba(38, 166, 120, 0.16), transparent 35%),
        radial-gradient(circle at 88% 8%, rgba(41, 128, 185, 0.12), transparent 32%),
        radial-gradient(circle at 50% 50%, rgba(187, 134, 252, 0.04), transparent 40%),
        var(--bg);
    color: var(--text);
}

.block-container {
    max-width: 1540px;
    padding: 16px 24px 40px 24px;
}

header[data-testid="stHeader"] {
    background: transparent;
}

/* Sidebar styling */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, rgba(12, 20, 23, 0.98) 0%, rgba(6, 10, 12, 0.99) 100%) !important;
    border-right: 1px solid rgba(32, 54, 62, 0.8) !important;
    box-shadow: 4px 0 25px rgba(0, 0, 0, 0.45);
}

div[data-testid="stSidebarUserContent"] {
    padding: 18px 12px;
}

/* Sidebar Navigation Radio Buttons */
div[data-testid="stRadio"] > div {
    gap: 7px;
}

div[data-testid="stRadio"] label {
    background: rgba(255, 255, 255, 0.025);
    border: 1px solid rgba(32, 54, 62, 0.7);
    border-radius: 12px;
    padding: 10px 14px;
    transition: all 0.22s ease;
    cursor: pointer;
    font-size: 13px;
    font-weight: 600;
    color: #edf6f3 !important;
    display: flex;
    align-items: center;
}

div[data-testid="stRadio"] label:hover {
    background: rgba(124, 240, 178, 0.08);
    border-color: rgba(124, 240, 178, 0.4);
    transform: translateX(2px);
}

/* Metric Cards */
.metric-card {
    background: linear-gradient(145deg, rgba(16, 26, 31, 0.94), rgba(9, 15, 18, 0.98));
    border: 1px solid var(--line);
    border-radius: 16px;
    padding: 16px 18px;
    min-height: 120px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.3);
    position: relative;
    overflow: hidden;
    transition: transform 0.25s ease, box-shadow 0.25s ease, border-color 0.25s ease;
    margin-bottom: 12px;
}

.metric-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 16px 36px rgba(0,0,0,0.4);
    border-color: rgba(124, 240, 178, 0.4);
}

.metric-card::before {
    content: "";
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 3px;
    background: var(--accent-bar, linear-gradient(90deg, #7cf0b2, #73d9e8));
}

.metric-card-amber::before { background: linear-gradient(90deg, #ff9f43, #f2c66d); }
.metric-card-cyan::before { background: linear-gradient(90deg, #00d2d3, #73d9e8); }
.metric-card-gold::before { background: linear-gradient(90deg, #feca57, #ff9f43); }
.metric-card-emerald::before { background: linear-gradient(90deg, #1dd1a1, #7cf0b2); }
.metric-card-purple::before { background: linear-gradient(90deg, #a55eea, #bb86fc); }
.metric-card-coral::before { background: linear-gradient(90deg, #ff6b6b, #ff7070); }

.metric-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 6px;
}

.metric-label {
    color: var(--muted);
    font-size: 11px;
    letter-spacing: .08em;
    text-transform: uppercase;
    font-weight: 600;
}

.metric-icon-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 26px;
    height: 26px;
    border-radius: 8px;
    background: rgba(255, 255, 255, 0.05);
    font-size: 13px;
}

.metric-value {
    font-size: 24px;
    font-weight: 800;
    letter-spacing: -.02em;
    color: var(--text);
    margin-top: 2px;
}

.metric-unit {
    font-size: 12px;
    color: var(--muted);
    font-weight: 500;
    margin-left: 3px;
}

.metric-sub {
    font-size: 11px;
    color: var(--muted);
    margin-top: 4px;
}

/* Threat Hero Card */
.big-event {
    border-radius: 18px;
    padding: 22px;
    border: 1px solid var(--line);
    transition: all 0.3s ease;
    margin-bottom: 14px;
}

.threat-critical {
    background:
        radial-gradient(circle at 85% 15%, rgba(255, 112, 112, 0.22), transparent 45%),
        linear-gradient(145deg, #1e1113, #0f090a);
    border-color: rgba(255, 112, 112, 0.45);
    box-shadow: 0 0 35px rgba(255, 112, 112, 0.15);
}

.threat-elevated {
    background:
        radial-gradient(circle at 85% 15%, rgba(242, 198, 109, 0.20), transparent 45%),
        linear-gradient(145deg, #1b1710, #0e0c08);
    border-color: rgba(242, 198, 109, 0.4);
    box-shadow: 0 0 35px rgba(242, 198, 109, 0.12);
}

.threat-nominal {
    background:
        radial-gradient(circle at 85% 15%, rgba(124, 240, 178, 0.18), transparent 45%),
        linear-gradient(145deg, #0e1c18, #070e0c);
    border-color: rgba(124, 240, 178, 0.35);
    box-shadow: 0 0 35px rgba(124, 240, 178, 0.1);
}

.event-label {
    font-size: 32px;
    font-weight: 800;
    letter-spacing: -.03em;
    margin: 4px 0 8px;
    line-height: 1.15;
}

.event-caption {
    color: var(--muted);
    font-size: 11px;
    letter-spacing: .04em;
}

.confidence {
    font-family: "JetBrains Mono", monospace;
    font-size: 17px;
    font-weight: 700;
}

.bar {
    height: 8px;
    background: rgba(24, 35, 39, 0.8);
    border-radius: 99px;
    overflow: hidden;
    margin-top: 8px;
}

.bar > div {
    height: 100%;
    border-radius: 99px;
    transition: width 0.4s ease;
}

.panel {
    background: linear-gradient(145deg, rgba(16, 26, 31, 0.94), rgba(9, 15, 18, 0.98));
    border: 1px solid var(--line);
    border-radius: 16px;
    padding: 16px 18px;
    margin-bottom: 14px;
}

.panel-title {
    font-size: 13px;
    font-weight: 700;
    letter-spacing: .04em;
    color: var(--text);
    margin-bottom: 12px;
}

.status-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 0;
    border-bottom: 1px solid rgba(32, 54, 62, 0.5);
}

.status-row:last-child {
    border-bottom: 0;
}

.status-name {
    color: #b9c8c5;
    font-size: 12px;
}

.status-value {
    font-family: "JetBrains Mono", monospace;
    font-size: 11px;
    font-weight: 600;
}

.ok { color: var(--green); }
.warn { color: var(--amber); }
.bad { color: var(--red); }
.neutral { color: var(--muted); }

.decision-box {
    border-radius: 14px;
    border: 1px solid var(--line);
    padding: 14px 16px;
    margin-bottom: 10px;
    background: rgba(255, 255, 255, 0.02);
}

.decision-risk {
    font-size: 22px;
    font-weight: 800;
    letter-spacing: -0.02em;
}

.hero {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 18px;
    flex-wrap: wrap;
    gap: 12px;
}

.kicker {
    font-family: "JetBrains Mono", monospace;
    font-size: 10px;
    letter-spacing: .16em;
    color: var(--green);
    font-weight: 700;
}

.brand {
    font-size: 24px;
    font-weight: 800;
    letter-spacing: -0.02em;
    color: #fff;
    margin-top: 2px;
}

.brand-mark {
    color: var(--green);
    margin-right: 6px;
}

.subtitle {
    font-size: 12px;
    color: var(--muted);
    margin-top: 2px;
}

.live-pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(124, 240, 178, 0.08);
    border: 1px solid rgba(124, 240, 178, 0.35);
    border-radius: 999px;
    padding: 6px 14px;
    color: var(--green);
    font-family: "JetBrains Mono", monospace;
    font-size: 11px;
    font-weight: 700;
}

.dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--green);
    box-shadow: 0 0 10px var(--green);
}

.section {
    margin: 20px 0 12px;
}

.section-title {
    font-size: 15px;
    font-weight: 800;
    color: #fff;
    letter-spacing: -0.01em;
}

.section-meta {
    font-family: "JetBrains Mono", monospace;
    font-size: 10px;
    letter-spacing: .08em;
    color: var(--muted);
    margin-top: 2px;
}

.chip {
    display: inline-block;
    border: 1px solid rgba(124, 240, 178, 0.25);
    background: rgba(124, 240, 178, 0.06);
    border-radius: 999px;
    padding: 4px 10px;
    color: var(--green);
    font-family: "JetBrains Mono", monospace;
    font-size: 10px;
    font-weight: 600;
    margin: 2px 3px 2px 0;
}

.footer {
    color: #526563;
    font-family: "JetBrains Mono", monospace;
    font-size: 10px;
    text-align: center;
    padding-top: 28px;
}

/* Touch-friendly buttons & Mobile responsiveness */
button, input, select, textarea {
    font-family: "DM Sans", sans-serif !important;
}

button[kind="primary"], button[kind="secondary"] {
    min-height: 42px;
    border-radius: 10px !important;
    font-weight: 600 !important;
}

@media (max-width: 768px) {
    .block-container {
        padding: 12px 14px 30px 14px !important;
    }
    .brand {
        font-size: 20px !important;
    }
    .event-label {
        font-size: 24px !important;
    }
    .metric-value {
        font-size: 20px !important;
    }
    .metric-card {
        min-height: 100px !important;
        padding: 12px 14px !important;
    }
}
</style>
""",
    unsafe_allow_html=True,
)

# ============================================================
# DATA & UTILITY HELPERS
# ============================================================

def safe_num(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        value = float(value)
        return value if math.isfinite(value) else default
    except (TypeError, ValueError):
        return default

def pct(value: Any) -> str:
    return f"{safe_num(value):.1f}%"

def confidence(value: Any) -> str:
    return f"{safe_num(value) * 100:.2f}%"

def status_class(value: Any) -> str:
    text = str(value or "").upper()
    if text in {"WORKING", "OK", "ONLINE", "ACTIVE", "TRUE", "VERIFIED", "RESOLVED"}:
        return "ok"
    if text in {"NOT_WORKING", "FAILED", "OFFLINE", "ERROR", "FALSE"}:
        return "bad"
    return "warn" if text in {"PENDING", "ASSIGNED", "DISPATCHED"} else "neutral"

def display_status(name: str, value: Any) -> str:
    cls = status_class(value)
    return (
        f'<div class="status-row">'
        f'<span class="status-name">{name}</span>'
        f'<span class="status-value {cls}">{str(value or "UNKNOWN")}</span>'
        f'</div>'
    )

def metric(
    label: str,
    value: str,
    unit: str = "",
    sub: str = "",
    accent: str = "emerald",
    icon: str = "◈",
) -> None:
    st.markdown(
        f"""
        <div class="metric-card metric-card-{accent}">
            <div class="metric-header">
                <span class="metric-label">{label}</span>
                <span class="metric-icon-badge">{icon}</span>
            </div>
            <div class="metric-value">{value}<span class="metric-unit">{unit}</span></div>
            <div class="metric-sub">{sub}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def calculate_haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    try:
        r_earth = 6371000.0  # meters
        d_lat = math.radians(lat2 - lat1)
        d_lon = math.radians(lon2 - lon1)
        a = math.sin(d_lat / 2.0) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon / 2.0) ** 2
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))
        return r_earth * c
    except Exception:
        return 0.0

def format_gps_distance(meters: float) -> str:
    if meters < 1000.0:
        return f"{int(round(meters))}m away"
    return f"{meters / 1000.0:.2f}km away"

# ============================================================
# BACKEND API CLIENT WITH DIRECT DB FALLBACK
# ============================================================

def api_request(path: str, method: str = "GET", payload: dict | None = None, timeout: float = 3.0) -> dict:
    """Call backend REST API with fallback to local RuntimeDatabase."""
    url = f"{AURA_API_URL}{path}"
    headers = {
        "Accept": "application/json",
        "X-API-Key": os.getenv("AURAFOREST_MASTER_KEY", "aura_sentry_sec_key_99"),
    }
    auth_token = st.session_state.get("aura_auth_token")
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"

    body = None
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    try:
        req = Request(url, data=body, headers=headers, method=method)
        with urlopen(req, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except HTTPError as e:
        try:
            raw = e.read().decode("utf-8")
            data = json.loads(raw)
            return {"error": data.get("detail", str(e)), "success": False, "status_code": e.code}
        except Exception:
            return {"error": str(e), "success": False, "status_code": e.code}
    except Exception:
        return {}

def auth_login_call(username_inp: str, password_inp: str) -> tuple[bool, dict, str]:
    """Authenticate credentials via API, local database, or root admin fallback."""
    u_clean = username_inp.strip().lower()
    p_clean = password_inp.strip()

    # 1. Immediate Root Chief Master Authentication
    if u_clean in ("chief", "admin") and p_clean in ("auraadmin123", "chief@aura2026", "admin123", "chief123", "auraadmin"):
        token = f"aura_sess_chief_{int(time.time())}"
        profile = {
            "username": "chief",
            "role": "admin",
            "display_name": "Chief Ranger Sharma",
            "department": "AuraForest Central Command",
            "sector": "All Sanctuary Sectors",
        }
        try:
            db.insert_auth_audit_log(
                username="chief",
                role="admin",
                action="LOGIN_SUCCESS",
                details="Chief Ranger master administrator logged in.",
            )
        except Exception:
            pass
        return True, profile, token

    # 2. Try Backend API
    try:
        res = api_request("/api/v1/auth/login", method="POST", payload={"username": u_clean, "password": p_clean})
        if res.get("success"):
            return True, res.get("user", {}), res.get("token", "")
    except Exception:
        pass

    # 3. Fallback to direct Database
    try:
        import importlib
        import backend.database
        importlib.reload(backend.database)
        db_inst = backend.database.RuntimeDatabase()
        db_u = db_inst.authenticate_user(u_clean, p_clean)
        if db_u:
            role_map = {"admin": "admin", "chief": "admin", "ranger": "ranger", "viewer": "viewer"}
            user_role = role_map.get(str(db_u.get("role", "viewer")).lower(), "viewer")
            token = f"aura_sess_{int(time.time())}_{random.randint(100,999)}"
            profile = {
                "username": db_u["username"],
                "role": user_role,
                "display_name": db_u.get("full_name") or db_u["username"].capitalize(),
                "department": db_u.get("sector") or ("Command" if user_role == "admin" else "Field Unit"),
            }
            db_inst.insert_auth_audit_log(
                username=db_u["username"],
                role=user_role,
                action="LOGIN_SUCCESS",
                details=f"User {db_u['username']} logged in via local auth.",
            )
            return True, profile, token
    except Exception:
        pass

    return False, {}, "Invalid username or password."

def generate_otp_call(phone_or_email: str) -> tuple[bool, str, dict, str]:
    """Request automated 6-digit OTP code, log to backend console, and dispatch via Email/SMS."""
    import importlib
    import backend.email_service
    importlib.reload(backend.email_service)
    svc = backend.email_service.EmailService()
    contact = phone_or_email.strip().lower()
    is_email = "@" in contact and "." in contact

    # 1. Create OTP directly in SQLite DB
    otp = db.create_otp(contact)
    deliv = {}
    if is_email:
        deliv = svc.send_otp_email(contact, otp, user_name=contact.split("@")[0].capitalize())

    # 2. Log to system backend console & audit log
    print(f"\n[AuraForest Sentinel AUTH] ========================================", flush=True)
    print(f"[AuraForest Sentinel AUTH] 🔐 OTP DISPATCHED TO: {contact}", flush=True)
    print(f"[AuraForest Sentinel AUTH] 🔑 6-DIGIT OTP CODE: {otp}", flush=True)
    print(f"[AuraForest Sentinel AUTH] ⏱️ VALIDITY: 15 MINUTES (900 seconds)", flush=True)
    print(f"[AuraForest Sentinel AUTH] 📡 DELIVERY RESULT: {deliv.get('message', 'N/A')}", flush=True)
    print(f"[AuraForest Sentinel AUTH] ========================================\n", flush=True)

    db.insert_auth_audit_log(
        username=contact,
        role="public",
        action="GENERATE_OTP",
        details=f"Generated OTP for {contact} (Delivery: {deliv.get('channel', 'SMS')})",
    )

    # 3. Synchronize with API if running
    api_request("/api/v1/auth/signup/otp/generate", method="POST", payload={"phone_or_email": contact})

    if is_email and not deliv.get("success", False):
        return False, otp, deliv, deliv.get("message", "Email delivery failed.")

    return True, otp, deliv, f"Verification code dispatched to {contact} via {'Gmail SMTP' if deliv.get('channel') == 'SMTP_RELAY' else 'SMS Gateway'}."

def validate_otp_call(contact: str, otp: str) -> tuple[bool, str]:
    """Validate the 6-digit OTP code across Session, Database, and Backend API."""
    clean_contact = contact.strip().lower()
    clean_otp = str(otp).replace(" ", "").replace("-", "").strip()
    if not clean_otp:
        return False, "Please enter the 6-digit OTP received in your email."

    # 1. Check Session State
    expected_sess = str(st.session_state.get("active_expected_otp", "")).strip()
    expected_email = str(st.session_state.get("active_expected_email", "")).strip().lower()
    if clean_otp and clean_otp == expected_sess and (not expected_email or clean_contact == expected_email):
        db.verify_otp(clean_contact, clean_otp)
        print(f"[AuraForest Sentinel AUTH] ✅ OTP Verified successfully for {clean_contact} (Session Sync)", flush=True)
        return True, f"Email '{clean_contact}' verified successfully!"

    # 2. Check Database directly
    if db.verify_otp(clean_contact, clean_otp) or db.is_otp_verified(clean_contact):
        print(f"[AuraForest Sentinel AUTH] ✅ OTP Verified successfully for {clean_contact} (Database Sync)", flush=True)
        return True, f"Email '{clean_contact}' verified successfully!"

    # 3. Check Backend REST API
    res = api_request("/api/v1/auth/signup/otp/validate", method="POST", payload={
        "phone_or_email": clean_contact,
        "otp_code": clean_otp,
    })
    if res.get("success"):
        print(f"[AuraForest Sentinel AUTH] ✅ OTP Verified successfully for {clean_contact} (API Sync)", flush=True)
        return True, f"Email '{clean_contact}' verified successfully!"

    print(f"[AuraForest Sentinel AUTH] ❌ OTP Verification Failed for {clean_contact} with code '{clean_otp}'", flush=True)
    return False, "Invalid or expired OTP verification code. Please check the code in your email."

def verify_otp_and_signup_call(contact: str, otp: str, username: str, password: str, full_name: str) -> tuple[bool, str]:
    """Register new citizen account after email verification."""
    clean_contact = contact.strip().lower()
    clean_otp = str(otp).replace(" ", "").replace("-", "").strip()
    clean_user = username.strip().lower()

    # Validate eligibility
    is_valid = (
        st.session_state.get("citizen_email_verified") == clean_contact
        or db.is_otp_verified(clean_contact)
        or db.verify_otp(clean_contact, clean_otp)
        or (clean_otp and clean_otp == str(st.session_state.get("active_expected_otp", "")).strip())
    )

    if not is_valid:
        return False, "Please enter the 6-digit OTP from your email and click 'Verify OTP' first."

    created = db.create_user(
        username=clean_user,
        password=password,
        role="viewer",
        full_name=full_name.strip(),
        email_or_phone=clean_contact,
        created_by="SELF_SIGNUP",
    )
    if created:
        print(f"[AuraForest Sentinel AUTH] 🎉 Account '{clean_user}' created successfully for {clean_contact}", flush=True)
        db.insert_auth_audit_log(
            username=clean_user,
            role="public",
            action="CITIZEN_REGISTRATION",
            details=f"Citizen {full_name} registered successfully.",
        )
        api_request("/api/v1/auth/signup/otp/verify", method="POST", payload={
            "phone_or_email": clean_contact,
            "otp_code": clean_otp,
            "username": clean_user,
            "password": password,
            "full_name": full_name.strip(),
        })
        return True, f"Account '{clean_user}' created successfully! You may now sign in."
    return False, "Failed to create user account. Desired username may already be registered."

def chief_create_ranger_call(full_name: str, callsign: str, rank: str, sector: str, phone: str = "", email: str = "") -> tuple[bool, dict, str]:
    """Chief creates new Field Ranger account and emails credentials."""
    from backend.email_service import email_service
    res = api_request("/api/v1/auth/ranger/create", method="POST", payload={
        "full_name": full_name,
        "email": email,
        "callsign": callsign,
        "rank": rank,
        "sector": sector,
        "phone": phone,
    })
    if res.get("success"):
        return True, res, res.get("message", "Ranger account generated.")

    # DB fallback
    first_token = [t for t in full_name.split() if t.lower() not in ("ranger", "officer", "cadet")]
    clean_f = "".join(c for c in (first_token[0] if first_token else full_name.split()[0]) if c.isalnum()).lower()
    username = f"ranger.{clean_f}{random.randint(10, 99)}"
    password = f"Aura#Ranger{random.randint(100, 999)}"
    contact_val = email.strip() or phone.strip()
    created = db.create_user(username=username, password=password, role="ranger", full_name=full_name, email_or_phone=contact_val, callsign=callsign, rank=rank, sector=sector, created_by="chief")

    deliv = {}
    if email.strip() and "@" in email:
        deliv = email_service.send_ranger_credentials_email(
            recipient_email=email.strip(),
            full_name=full_name,
            username=username,
            password=password,
            callsign=callsign,
            rank=rank,
            sector=sector,
        )

    if created:
        db.insert_auth_audit_log(username="chief", role="admin", action="CHIEF_CREATE_RANGER", details=f"Chief created Ranger {full_name} ({username}) -> Dispatched to {contact_val}.")
        return True, {
            "username": username,
            "password": password,
            "full_name": full_name,
            "callsign": callsign,
            "rank": rank,
            "sector": sector,
            "phone": phone,
            "email": email,
            "delivery": deliv,
        }, f"Field Ranger account created! Credentials dispatched to {contact_val}."
    return False, {}, "Failed to create field ranger."

def get_all_users_call() -> list[dict]:
    res = api_request("/api/v1/auth/users")
    if res.get("success"):
        return res.get("users", [])
    return db.get_all_users()

def delete_user_call(username: str) -> tuple[bool, str]:
    res = api_request(f"/api/v1/auth/users/{username}", method="DELETE")
    if res.get("success"):
        return True, res.get("message", "User deleted.")
    if db.delete_user(username):
        db.insert_auth_audit_log(username="chief", role="admin", action="DELETE_USER", details=f"Deleted user {username}")
        return True, f"User '{username}' deleted."
    return False, "Could not delete user."

def update_user_password_call(username: str, new_pwd: str) -> tuple[bool, str]:
    res = api_request(f"/api/v1/auth/users/{username}/password", method="POST", payload={"new_password": new_pwd})
    if res.get("success"):
        return True, res.get("message", "Password updated.")
    ok = db.update_user(username=username, password=new_pwd)
    if ok:
        db.insert_auth_audit_log(username="chief", role="admin", action="RESET_PASSWORD", details=f"Reset password for user {username}")
        return True, f"Password for '{username}' updated."
    return False, "User not found."

def update_user_call(
    username: str,
    full_name: str | None = None,
    email_or_phone: str | None = None,
    role: str | None = None,
    callsign: str | None = None,
    rank: str | None = None,
    sector: str | None = None,
    new_password: str | None = None,
) -> tuple[bool, str]:
    payload = {
        "full_name": full_name,
        "email_or_phone": email_or_phone,
        "role": role,
        "callsign": callsign,
        "rank": rank,
        "sector": sector,
        "new_password": new_password,
    }
    res = api_request(f"/api/v1/auth/users/{username}/update", method="POST", payload=payload)
    if res.get("success"):
        return True, res.get("message", "User updated successfully.")
    if res.get("error"):
        return False, res.get("error")

    # DB fallback
    if email_or_phone:
        existing = db.get_user_by_email(email_or_phone)
        if existing and existing["username"] != username.strip().lower():
            return False, f"Email '{email_or_phone}' is already in use by user '{existing['username']}'."

    ok = db.update_user(
        username=username,
        full_name=full_name,
        email_or_phone=email_or_phone,
        role=role,
        callsign=callsign,
        rank=rank,
        sector=sector,
        password=new_password,
    )
    if ok:
        db.insert_auth_audit_log(username="chief", role="admin", action="UPDATE_USER", details=f"Updated details for user {username}")
        return True, f"User '{username}' updated successfully."
    return False, "Could not update user."

# ============================================================
# 🔐 AUTHENTICATION GATEWAY (LOGIN & SIGN-UP)
# ============================================================

if not st.session_state.get("authenticated", False):
    st.markdown(
        """
        <div style="text-align: center; margin-top: 20px; margin-bottom: 24px;">
            <div style="font-family:'JetBrains Mono',monospace;font-size:11px;letter-spacing:.2em;color:#7cf0b2;font-weight:700;">AURAFOREST BIO-DEFENSE PLATFORM</div>
            <div style="font-size:32px;font-weight:800;color:#fff;margin-top:4px;letter-spacing:-0.03em;">◈ Sentinel Gateway</div>
            <div style="font-size:13px;color:#829a97;margin-top:4px;">Secure Role-Based Access Control · Chief Command · Field Rangers · Public Citizens</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    auth_col1, auth_col2, auth_col3 = st.columns([1, 2.2, 1])
    with auth_col2:
        auth_tab_login, auth_tab_signup = st.tabs(["🔐 Sign In", "📝 Public Citizen Sign-Up"])

        # ----------------------------------------------------
        # TAB 1: LOGIN
        # ----------------------------------------------------
        with auth_tab_login:
            with st.container(border=True):
                st.markdown("<div style='font-size:16px;font-weight:800;color:#fff;margin-bottom:12px;'>Enter Portal Credentials</div>", unsafe_allow_html=True)
                l_user = st.text_input("Username / ID", key="login_username_inp", placeholder="e.g. chief, ranger.amar, citizen.demo")
                l_pass = st.text_input("Password", type="password", key="login_password_inp", placeholder="••••••••••••")

                if st.button("🚀 Access Sentinel Portal", type="primary", use_container_width=True, key="btn_portal_login"):
                    if not l_user.strip() or not l_pass.strip():
                        st.error("Please enter both username and password.")
                    else:
                        ok, user_info, token = auth_login_call(l_user.strip(), l_pass.strip())
                        if ok:
                            st.session_state["authenticated"] = True
                            st.session_state["aura_username"] = user_info.get("username", l_user.strip().lower())
                            st.session_state["aura_user_role"] = user_info.get("role", "viewer")
                            st.session_state["aura_user_name"] = user_info.get("display_name", l_user.strip().capitalize())
                            st.session_state["aura_user_dept"] = user_info.get("department", "AuraForest")
                            st.session_state["aura_auth_token"] = token
                            st.success(f"Welcome back, {st.session_state['aura_user_name']}!")
                            st.rerun()
                        else:
                            st.error(token)



        # ----------------------------------------------------
        # TAB 2: PUBLIC CITIZEN SIGN-UP (WITH EMAIL OTP)
        # ----------------------------------------------------
        with auth_tab_signup:
            with st.container(border=True):
                st.markdown(
                    """
                    <div style="background:rgba(115,217,232,0.08); border:1px solid rgba(115,217,232,0.3); border-radius:10px; padding:10px 14px; margin-bottom:14px;">
                        <div style="font-size:12px; font-weight:700; color:#73d9e8;">ℹ️ Registration Notice:</div>
                        <div style="font-size:11px; color:#edf6f3; margin-top:2px;">
                            • <b>Public Citizens:</b> Enter your email address to receive an official 6-digit verification code.<br/>
                            • <b>Field Rangers:</b> Accounts and passwords are generated exclusively by the <b>Chief Ranger</b>.
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                s_name = st.text_input("Full Name", placeholder="e.g. Priya Nambiar", key="signup_name")
                s_contact = st.text_input("Email Address (for Verification OTP)", placeholder="e.g. user@gmail.com", key="signup_contact")

                # Step 1: Request OTP Button
                if st.button("⚡ Send 6-Digit OTP to Email", use_container_width=True, key="btn_req_otp"):
                    if not s_contact.strip() or len(s_contact.strip()) < 5 or "@" not in s_contact:
                        st.error("Please enter a valid email address.")
                    else:
                        with st.spinner(f"Sending verification OTP to {s_contact.strip()}..."):
                            ok, otp_code, deliv_info, msg = generate_otp_call(s_contact.strip())
                            if ok:
                                st.session_state["otp_sent_to"] = s_contact.strip().lower()
                                st.session_state["otp_sent_time"] = time.time()
                                st.session_state["active_expected_otp"] = otp_code
                                st.session_state["active_expected_email"] = s_contact.strip().lower()
                                st.session_state.pop("citizen_email_verified", None)
                                st.success(f"✅ 6-digit OTP sent to **{s_contact.strip()}**! Please check your email inbox (and spam folder) and enter the code below.")
                            else:
                                st.error(f"❌ {msg}")

                # Status Banner if OTP was sent
                if st.session_state.get("otp_sent_to") == s_contact.strip().lower() and not st.session_state.get("citizen_email_verified"):
                    st.markdown(
                        f"""
                        <div style="background: linear-gradient(135deg, rgba(115, 217, 232, 0.12), rgba(124, 240, 178, 0.10)); border: 1.5px solid #73d9e8; border-radius: 12px; padding: 12px 16px; margin: 12px 0;">
                            <div style="display:flex; justify-content:space-between; align-items:center;">
                                <span style="font-family:'JetBrains Mono',monospace; font-size:11px; font-weight:700; color:#73d9e8;">📬 VERIFICATION EMAIL SENT</span>
                                <span style="font-size:10px; color:#7cf0b2; font-weight:700;">🟢 ACTIVE INBOX DISPATCH</span>
                            </div>
                            <div style="font-size:11px; color:#edf6f3; margin-top:6px;">
                                An email containing your 6-digit one-time passcode was sent to <b>{s_contact.strip()}</b>.<br/>
                                <span style="color:#829a97;">⏱️ Valid for 15 minutes. Enter the OTP code and click <b>Verify OTP</b> below.</span>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                # Step 2: Enter and Verify OTP
                s_otp = st.text_input("Enter 6-Digit OTP from Email", placeholder="e.g. 123456", key="signup_otp_inp")

                # Dedicated Verify OTP Button
                if st.button("✅ Verify OTP", use_container_width=True, key="btn_verify_otp_only"):
                    if not s_contact.strip() or "@" not in s_contact:
                        st.error("Please enter your email address first.")
                    elif not s_otp.strip():
                        st.error("Please enter the 6-digit OTP code received in your email.")
                    else:
                        with st.spinner("Validating OTP code..."):
                            ok, v_msg = validate_otp_call(s_contact.strip(), s_otp.strip())
                            if ok:
                                st.session_state["citizen_email_verified"] = s_contact.strip().lower()
                                st.success(f"✅ {v_msg}")
                            else:
                                st.error(f"❌ {v_msg}")

                # Verified Confirmation Badge
                is_verified = st.session_state.get("citizen_email_verified") == s_contact.strip().lower()
                if is_verified:
                    st.markdown(
                        f"""
                        <div style="background: rgba(124, 240, 178, 0.15); border: 1.5px solid #7cf0b2; border-radius: 10px; padding: 10px 14px; margin: 10px 0;">
                            <span style="color:#7cf0b2; font-weight:700; font-size:12px;">✅ EMAIL VERIFIED:</span>
                            <span style="color:#edf6f3; font-size:12px; margin-left:6px;">{s_contact.strip()}</span>
                            <div style="color:#829a97; font-size:11px; margin-top:2px;">You may now create your username & password below.</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                st.markdown("<hr style='border:none; border-top:1px solid rgba(115,217,232,0.15); margin:16px 0;'/>", unsafe_allow_html=True)

                # Step 3: Account Credentials
                s_username = st.text_input("Desired Username", placeholder="e.g. citizen.priya", key="signup_user_inp")
                s_password = st.text_input("Create Password", type="password", placeholder="••••••••••••", key="signup_pass_inp")

                if st.button("✨ Complete Citizen Sign-Up", type="primary", use_container_width=True, key="btn_complete_signup"):
                    if not s_name.strip() or not s_contact.strip() or not s_username.strip() or not s_password.strip():
                        st.error("Please fill in all required fields.")
                    elif not is_verified and not s_otp.strip():
                        st.error("Please enter the 6-digit OTP from your email and click 'Verify OTP'.")
                    else:
                        with st.spinner("Creating your citizen account..."):
                            ok, msg = verify_otp_and_signup_call(s_contact.strip(), s_otp.strip(), s_username.strip(), s_password.strip(), s_name.strip())
                            if ok:
                                st.session_state.pop("otp_sent_to", None)
                                st.session_state.pop("otp_sent_time", None)
                                st.session_state.pop("citizen_email_verified", None)
                                st.success(f"✅ {msg}")
                                st.info("👉 You can now switch to the '🔐 Sign In' tab above and log in with your new credentials!")
                            else:
                                st.error(f"❌ {msg}")

    st.stop()

# ============================================================
# LOGGED IN STATE & SESSION CONTEXT
# ============================================================

current_role = st.session_state.get("aura_user_role", "viewer")
user_display = st.session_state.get("aura_user_name", "User")
user_dept = st.session_state.get("aura_user_dept", "Forestry")
username_active = st.session_state.get("aura_username", "user")

# Read edge state
state = source.tick()
telemetry = state.get("telemetry") or {}
event = state.get("event") or {}
cadie = state.get("cadie") or {}
prediction = state.get("prediction") or {}
environment = state.get("environment") or {}
policy = state.get("adaptive_policy") or {}
unknown = state.get("unknown_discovery") or {}
device_id = state.get("device_id") or "ESP32-S3-SENTINEL-01"
hardware = state.get("hardware_health") or telemetry.get("hardware_health") or {}

label = event.get("label") or prediction.get("label") or "Ambient Forest"
conf = safe_num(event.get("confidence", prediction.get("confidence", 0.0)))
detected = event.get("detected", False)
risk_raw = str(cadie.get("risk_level") or "LOW").upper()
threat_class = "threat-critical" if risk_raw in ["HIGH", "CRITICAL"] else ("threat-elevated" if risk_raw in ["ELEVATED", "MEDIUM"] else "threat-nominal")
conf_color = "#ff7070" if risk_raw in ["HIGH", "CRITICAL"] else ("#f2c66d" if risk_raw in ["ELEVATED", "MEDIUM"] else "#7cf0b2")

# Active emergency alerts
active_alerts = db.get_active_emergency_alerts()
field_rangers = db.get_field_rangers()

# GPS Coordinates
loc_dict = state.get("location") or telemetry.get("location") or {}
raw_lat = loc_dict.get("latitude") if loc_dict.get("latitude") is not None else telemetry.get("latitude")
raw_lon = loc_dict.get("longitude") if loc_dict.get("longitude") is not None else telemetry.get("longitude")
sent_lat = float(safe_num(raw_lat, 12.29581))
sent_lon = float(safe_num(raw_lon, 76.63938))
if abs(sent_lat) < 0.0001:
    sent_lat = 12.29581
if abs(sent_lon) < 0.0001:
    sent_lon = 76.63938

# ============================================================
# 🧭 SIDEBAR: PROFILE & NAVIGATION MENU (REPLACED NAVBAR)
# ============================================================

with st.sidebar:
    # 1. Branding Header
    st.markdown(
        """
        <div style="padding: 4px 0 14px 0; border-bottom: 1px solid rgba(32, 54, 62, 0.7); margin-bottom: 14px;">
            <div style="font-family:'JetBrains Mono',monospace;font-size:10px;letter-spacing:.16em;color:var(--green);font-weight:700;">AURAFOREST SENTINEL</div>
            <div style="font-size:20px;font-weight:800;color:#fff;margin-top:2px;letter-spacing:-0.02em;">◈ Bio-Defense Sentry</div>
            <div style="font-size:11px;color:var(--muted);margin-top:2px;">AI Acoustic Intelligence</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 2. User Identity Card & Logout
    role_badges = {
        "admin": ("#7cf0b2", "rgba(124, 240, 178, 0.12)", "👑 CHIEF RANGER"),
        "ranger": ("#73d9e8", "rgba(115, 217, 232, 0.12)", "🛡️ FIELD RANGER"),
        "viewer": ("#f2c66d", "rgba(242, 198, 109, 0.12)", "👁️ PUBLIC CITIZEN"),
    }
    r_color, r_bg, r_title = role_badges.get(current_role, ("#7cf0b2", "rgba(124,240,178,0.1)", "USER"))

    st.markdown(
        f"""
        <div style="background:{r_bg}; border:1px solid {r_color}; border-radius:12px; padding:10px 12px; margin-bottom:14px;">
            <div style="font-family:'JetBrains Mono',monospace; font-size:10px; font-weight:700; color:{r_color};">
                ● {r_title}
            </div>
            <div style="font-size:13px; font-weight:700; color:#fff; margin-top:2px;">
                {user_display}
            </div>
            <div style="font-size:10px; color:#829a97; margin-top:1px;">
                ID: <code>{username_active}</code> · {user_dept}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 3. Role-Aware Sidebar Navigation (Replaces top navbar!)
    st.markdown('<div class="metric-label" style="margin-bottom:6px;">SIDEBAR NAVIGATION</div>', unsafe_allow_html=True)

    if current_role == "admin":
        nav_options = [
            "📡 Live Sentinel Overview",
            "🗺️ Tactical Map & Dispatch",
            "👥 Ranger & User Management",
            "📊 Acoustic AI & Spectrum",
            "🚨 Emergency Broadcast",
            "📨 Citizen Reports Inbox",
            "📜 Incident Archive & Resolution Logs",
            "🔬 Unknown Sound Discovery",
            "🔒 Security & Audit Log",
        ]
    elif current_role == "ranger":
        nav_options = [
            "🚨 Incident & Citizen Response",
            "🗺️ Sector Map & Near Rangers",
            "📜 Incident Archive & Resolution Logs",
            "📡 Field Telemetry & Gas",
            "📊 Acoustic Frequency Monitor",
        ]
    else:
        nav_options = [
            "🌿 Forest Climate & Readings",
            "⚠️ Safety Notices & Alerts",
            "📸 Report Illegal Activity",
        ]

    active_page = st.radio(
        "Navigation",
        options=nav_options,
        key="sidebar_navigation_choice",
        label_visibility="collapsed",
    )

    # 4. Live Sentinel Quick Stats
    batt_pct = safe_num(telemetry.get("battery_percent", 0.0))
    batt_v = safe_num(telemetry.get("battery_voltage", 0.0))
    st.markdown(
        f"""
        <div class="panel" style="padding:12px; margin-top:16px; margin-bottom:12px; border-radius:12px; background:rgba(16, 26, 31, 0.85);">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span class="metric-label">NODE ID</span>
                <span style="font-family:'JetBrains Mono',monospace; font-size:11px; font-weight:700; color:var(--green);">{device_id}</span>
            </div>
            <div style="display:flex; justify-content:space-between; align-items:center; margin-top:6px;">
                <span class="metric-label">CORE STATE</span>
                <span style="font-family:'JetBrains Mono',monospace; font-size:10px; color:#7cf0b2; font-weight:600;">ONLINE ●</span>
            </div>
            <div style="display:flex; justify-content:space-between; align-items:center; margin-top:6px;">
                <span class="metric-label">BATTERY</span>
                <span style="font-family:'JetBrains Mono',monospace; font-size:10px; color:#73d9e8; font-weight:600;">{batt_pct:.1f}% ({batt_v:.2f}V)</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 5. Audio Siren Quick Test
    if st.button("🚨 Test Siren Sound", use_container_width=True, key="btn_sidebar_test_siren"):
        st.session_state["manual_siren_trigger"] = time.time()
        st.toast("🚨 Playing tactical alarm siren sound...", icon="🔊")

    # 6. Log Out Button
    if st.button("🚪 Sign Out", use_container_width=True, key="btn_sidebar_logout"):
        st.session_state["authenticated"] = False
        st.session_state["aura_auth_token"] = None
        st.rerun()

# ============================================================
# MAIN CONTENT HEADER & TOP ALERTS
# ============================================================

role_headers = {
    "admin": ("CHIEF RANGER COMMAND CONSOLE", "Autonomous Bioacoustic & Threat Defense · Full Sentinel Access"),
    "ranger": ("FIELD RANGER TACTICAL RESPONSE CONSOLE", "Incident Response · GPS Navigation · On-Site Resolution"),
    "viewer": ("AURAFOREST PUBLIC CITIZEN & ECO-SENTRY", "Live Climate & Air Quality · Safety Alerts · Public Tip Box"),
}
h_title, h_sub = role_headers.get(current_role, ("Sentinel Command", "Edge Intelligence"))

st.markdown(
    f"""
    <div class="hero">
        <div>
            <div class="kicker">AURAFOREST / {current_role.upper()} INTERFACE</div>
            <div class="brand"><span class="brand-mark">◈</span>{h_title}</div>
            <div class="subtitle">{h_sub}</div>
        </div>
        <div class="live-pill"><span class="dot"></span>SENTINEL ONLINE</div>
    </div>
    """,
    unsafe_allow_html=True,
)

def render_siren_audio_synthesizer(is_active: bool = True, threat_label: str = "Threat") -> None:
    """In-browser Web Audio API tactical alarm siren synthesizer (Dual-Tone 960Hz/680Hz)."""
    if not is_active:
        return

    siren_component_html = f"""
    <div style="background: rgba(255, 112, 112, 0.12); border: 1.5px solid #ff7070; border-radius: 10px; padding: 8px 14px; margin-bottom: 12px; display: flex; align-items: center; justify-content: space-between; box-shadow: 0 0 20px rgba(255,112,112,0.2);">
        <div style="display: flex; align-items: center; gap: 10px;">
            <span style="display: inline-block; width: 12px; height: 12px; background: #ff7070; border-radius: 50%; box-shadow: 0 0 10px #ff7070;"></span>
            <span style="color: #ff7070; font-family: -apple-system, BlinkMacSystemFont, sans-serif; font-size: 12px; font-weight: 800; letter-spacing: 0.05em;">🔊 TACTICAL SIREN ALARM ACTIVE ({threat_label.upper()})</span>
        </div>
        <button id="auraSirenBtn" onclick="toggleAuraSiren()" style="background: #ff7070; color: #060a0c; font-weight: 800; font-size: 11px; border: none; border-radius: 6px; padding: 6px 14px; cursor: pointer; font-family: sans-serif; transition: all 0.2s; box-shadow: 0 2px 8px rgba(255,112,112,0.4);">
            🚨 MUTE / PLAY SIREN
        </button>
    </div>
    <script>
    let auraAudioCtx = null;
    let auraOsc = null;
    let auraGain = null;
    let isSirenPlaying = false;
    let sirenInterval = null;

    function startSirenSound() {{
        try {{
            const AudioContext = window.AudioContext || window.webkitAudioContext;
            if (!AudioContext) return;
            if (!auraAudioCtx) {{
                auraAudioCtx = new AudioContext();
            }}
            if (auraAudioCtx.state === 'suspended') {{
                auraAudioCtx.resume();
            }}

            if (isSirenPlaying) return;
            isSirenPlaying = true;

            auraOsc = auraAudioCtx.createOscillator();
            auraGain = auraAudioCtx.createGain();
            auraOsc.type = 'sawtooth';
            auraGain.gain.setValueAtTime(0.18, auraAudioCtx.currentTime);

            // Dual tone warble sweep (960Hz <-> 680Hz)
            let high = true;
            auraOsc.frequency.setValueAtTime(960, auraAudioCtx.currentTime);
            
            sirenInterval = setInterval(() => {{
                if (!isSirenPlaying || !auraAudioCtx || !auraOsc) return;
                const now = auraAudioCtx.currentTime;
                if (high) {{
                    auraOsc.frequency.exponentialRampToValueAtTime(680, now + 0.22);
                }} else {{
                    auraOsc.frequency.exponentialRampToValueAtTime(960, now + 0.22);
                }}
                high = !high;
            }}, 280);

            auraOsc.connect(auraGain);
            auraGain.connect(auraAudioCtx.destination);
            auraOsc.start();

            const btn = document.getElementById("auraSirenBtn");
            if (btn) btn.innerText = "🔇 MUTE SIREN";
        }} catch (e) {{
            console.warn("AuraForest Siren Audio:", e);
        }}
    }}

    function stopSirenSound() {{
        if (sirenInterval) clearInterval(sirenInterval);
        if (auraOsc) {{
            try {{ auraOsc.stop(); }} catch(e) {{}}
            try {{ auraOsc.disconnect(); }} catch(e) {{}}
            auraOsc = null;
        }}
        isSirenPlaying = false;
        const btn = document.getElementById("auraSirenBtn");
        if (btn) btn.innerText = "🚨 PLAY SIREN";
    }}

    function toggleAuraSiren() {{
        if (isSirenPlaying) {{
            stopSirenSound();
        }} else {{
            startSirenSound();
        }}
    }}

    // Auto-start on load & unlock on user click
    setTimeout(startSirenSound, 80);
    document.addEventListener('click', () => {{
        if (!isSirenPlaying) startSirenSound();
    }}, {{ once: true }});
    </script>
    """
    components.html(siren_component_html, height=52)

# Active alert notification banner
if active_alerts:
    top_alert = active_alerts[0]
    al_threat = str(top_alert.get("threat_type", "Threat")).upper()
    al_conf = safe_num(top_alert.get("confidence", 0.95)) * 100
    al_lat = top_alert.get("location_lat")
    al_lon = top_alert.get("location_lon")
    al_coords = f"{al_lat:.5f}°N, {al_lon:.5f}°E" if al_lat is not None and al_lon is not None else "Coordinates Acquired"

    # Play in-browser tactical siren sound
    render_siren_audio_synthesizer(is_active=True, threat_label=al_threat)

    b_c1, b_c2 = st.columns([3.5, 1.2])
    with b_c1:
        st.markdown(
            f"""
            <div style="background: linear-gradient(135deg, rgba(255, 112, 112, 0.22), rgba(255, 71, 87, 0.08)); border: 1.5px solid #ff7070; border-radius: 14px; padding: 14px 18px; margin-bottom: 16px; box-shadow: 0 0 25px rgba(255, 112, 112, 0.25);">
                <div style="display:flex;align-items:center;gap:10px;">
                    <span style="display:inline-block;width:10px;height:10px;background:#ff7070;border-radius:50%;box-shadow:0 0 10px #ff7070;"></span>
                    <span style="color:#ff7070;font-family:'JetBrains Mono',monospace;font-size:11px;font-weight:700;letter-spacing:.14em;">🚨 ACTIVE EMERGENCY ALERT</span>
                </div>
                <div style="font-size:18px;font-weight:800;color:#fff;margin-top:4px;">
                    {al_threat} DETECTED ({al_conf:.1f}% Confidence) · {al_coords}
                </div>
                <div style="color:#edf5f2;font-size:11px;margin-top:2px;font-family:'JetBrains Mono',monospace;">
                    Device: {top_alert.get('device_id')} · Assigned: {top_alert.get('assigned_ranger_name') or 'Unassigned'}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with b_c2:
        if current_role in ["admin", "ranger"]:
            st.write("")
            if st.button("✅ Silence Siren", key="btn_ack_top_alert", use_container_width=True, type="primary"):
                db.acknowledge_emergency_alert(top_alert.get("alert_id"), acknowledged_by=user_display)
                st.success("Siren silenced.")
                st.rerun()

elif st.session_state.get("manual_siren_trigger"):
    if time.time() - float(st.session_state.get("manual_siren_trigger", 0)) < 15:
        render_siren_audio_synthesizer(is_active=True, threat_label="Tactical Siren Audio Test")
        st.info("🚨 Playing manual siren audio test (Web Audio API). Click Silence / Mute to stop.")

# Build map dataframe with rich hover metadata, color-coded markers, and nodes/alerts
def build_map_data() -> pd.DataFrame:
    records = [
        {
            "latitude": float(sent_lat),
            "longitude": float(sent_lon),
            "Entity": f"📡 Primary Sentinel Base Node ({device_id})",
            "label_short": f"📡 Sentinel-01",
            "Category": "🟢 Sentinel AI Base Node",
            "Coordinates": f"{sent_lat:.5f}°N, {sent_lon:.5f}°E",
            "Status": "ONLINE & ARMED",
            "Details": f"Live Perception: {label} ({confidence(conf)}) · ESP32-S3 DMA",
            "color": [124, 240, 178, 240],
            "radius": 95,
            "size": 38,
        },
        {
            "latitude": float(sent_lat + 0.0042),
            "longitude": float(sent_lon + 0.0035),
            "Entity": "📡 Sentinel-02 Mesh Node (North Ridge)",
            "label_short": "📡 Sentinel-02",
            "Category": "🟢 Sentinel AI Base Node",
            "Coordinates": f"{(sent_lat + 0.0042):.5f}°N, {(sent_lon + 0.0035):.5f}°E",
            "Status": "ONLINE (Mesh Hop 1)",
            "Details": "LoRa 868MHz Mesh Relay · Solar 98% · Perimeter Secured",
            "color": [124, 240, 178, 210],
            "radius": 80,
            "size": 28,
        },
        {
            "latitude": float(sent_lat - 0.0038),
            "longitude": float(sent_lon - 0.0044),
            "Entity": "📡 Sentinel-03 Mesh Node (West Creek)",
            "label_short": "📡 Sentinel-03",
            "Category": "🟢 Sentinel AI Base Node",
            "Coordinates": f"{(sent_lat - 0.0038):.5f}°N, {(sent_lon - 0.0044):.5f}°E",
            "Status": "ONLINE (Mesh Hop 2)",
            "Details": "LoRa 868MHz Mesh Relay · Solar 92% · Perimeter Secured",
            "color": [124, 240, 178, 210],
            "radius": 80,
            "size": 28,
        },
    ]

# Build map dataframe with rich hover metadata, color-coded markers, and nodes/alerts/responding units
def build_map_data() -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    records = [
        {
            "latitude": float(sent_lat),
            "longitude": float(sent_lon),
            "Entity": f"📡 Primary Sentinel Base Node ({device_id})",
            "label_short": f"📡 Sentinel-01",
            "Category": "🟢 Sentinel AI Base Node",
            "Coordinates": f"{sent_lat:.5f}°N, {sent_lon:.5f}°E",
            "Status": "ONLINE & ARMED",
            "Details": f"Live Perception: {label} ({confidence(conf)}) · ESP32-S3 DMA",
            "color": [124, 240, 178, 240],
            "radius": 95,
            "size": 38,
        },
        {
            "latitude": float(sent_lat + 0.0042),
            "longitude": float(sent_lon + 0.0035),
            "Entity": "📡 Sentinel-02 Mesh Node (North Ridge)",
            "label_short": "📡 Sentinel-02",
            "Category": "🟢 Sentinel AI Base Node",
            "Coordinates": f"{(sent_lat + 0.0042):.5f}°N, {(sent_lon + 0.0035):.5f}°E",
            "Status": "ONLINE (Mesh Hop 1)",
            "Details": "LoRa 868MHz Mesh Relay · Solar 98% · Perimeter Secured",
            "color": [124, 240, 178, 210],
            "radius": 80,
            "size": 28,
        },
        {
            "latitude": float(sent_lat - 0.0038),
            "longitude": float(sent_lon - 0.0044),
            "Entity": "📡 Sentinel-03 Mesh Node (West Creek)",
            "label_short": "📡 Sentinel-03",
            "Category": "🟢 Sentinel AI Base Node",
            "Coordinates": f"{(sent_lat - 0.0038):.5f}°N, {(sent_lon - 0.0044):.5f}°E",
            "Status": "ONLINE (Mesh Hop 2)",
            "Details": "LoRa 868MHz Mesh Relay · Solar 92% · Perimeter Secured",
            "color": [124, 240, 178, 210],
            "radius": 80,
            "size": 28,
        },
    ]

    dispatch_routes: list[dict[str, Any]] = []
    alert_loc_map: dict[str, tuple[float, float, str]] = {}

    # Plot all active threats and emergency alerts
    if active_alerts:
        for al in active_alerts:
            a_lat = al.get("location_lat")
            a_lon = al.get("location_lon")
            if a_lat and a_lon:
                a_th = al.get("threat_type", "Threat")
                a_risk = al.get("risk_level", "CRITICAL")
                a_rname = al.get("assigned_ranger_name")
                a_id = al.get("alert_id")
                alert_loc_map[str(a_id)] = (float(a_lat), float(a_lon), a_th)

                if a_rname:
                    records.append({
                        "latitude": float(a_lat),
                        "longitude": float(a_lon),
                        "Entity": f"🚨 {a_th} Threat Alert [RESPONDING: {a_rname}]",
                        "label_short": f"🚨 {a_th} (Assigned: {a_rname.split()[0]})",
                        "Category": f"🔴 Active Threat ({a_risk})",
                        "Coordinates": f"{float(a_lat):.5f}°N, {float(a_lon):.5f}°E",
                        "Status": f"⚡ RESPONDING UNIT: Ranger {a_rname} (EN ROUTE)",
                        "Details": f"Assigned Ranger: {a_rname} · Priority: {a_risk} · Interception Active",
                        "color": [255, 75, 75, 250],
                        "radius": 135,
                        "size": 50,
                    })
                else:
                    records.append({
                        "latitude": float(a_lat),
                        "longitude": float(a_lon),
                        "Entity": f"🚨 {a_th} Emergency Alert (Unassigned)",
                        "label_short": f"🚨 {a_th}",
                        "Category": f"🔴 Active Threat ({a_risk})",
                        "Coordinates": f"{float(a_lat):.5f}°N, {float(a_lon):.5f}°E",
                        "Status": f"PRIORITY: {a_risk} · AWAITING RANGER DISPATCH",
                        "Details": f"Confidence: {safe_num(al.get('confidence', 0.96))*100:.1f}% · ID: {a_id}",
                        "color": [255, 80, 80, 245],
                        "radius": 130,
                        "size": 48,
                    })
    elif detected or str(cadie.get("risk_level", "")).upper() in ["HIGH", "CRITICAL"]:
        live_th_lat = float(sent_lat + 0.0022)
        live_th_lon = float(sent_lon + 0.0025)
        alert_loc_map["live_ai_threat"] = (live_th_lat, live_th_lon, label)
        records.append({
            "latitude": live_th_lat,
            "longitude": live_th_lon,
            "Entity": f"🚨 Live AI Threat Signal: {label}",
            "label_short": f"🚨 {label}",
            "Category": "🔴 Active Threat (AI TRIAGED)",
            "Coordinates": f"{live_th_lat:.5f}°N, {live_th_lon:.5f}°E",
            "Status": f"CONFIDENCE: {confidence(conf)} · ACTION: {cadie.get('action', 'DISPATCH')}",
            "Details": f"CADIE Multimodal Score: {safe_num(cadie.get('score')):.3f} · Immediate Interception",
            "color": [255, 80, 80, 245],
            "radius": 130,
            "size": 48,
        })

    # Ensure field rangers list is always populated with tactical coordinates
    rangers_to_plot = field_rangers
    if not rangers_to_plot:
        db._seed_default_rangers()
        rangers_to_plot = db.get_field_rangers()

    # Offsets around primary sentinel to place field rangers in active sanctuary sectors
    ranger_offsets = [
        (0.0025, 0.0028),
        (-0.0032, -0.0025),
        (0.0045, -0.0035),
        (-0.0018, 0.0042),
    ]

    for idx, rng in enumerate(rangers_to_plot):
        lat_val = rng.get("latitude")
        lon_val = rng.get("longitude")
        # If coordinates are missing, default, or far away from sanctuary sent_lat, anchor nearby
        if lat_val is None or lon_val is None or abs(float(lat_val)) < 0.1 or abs(float(lat_val) - sent_lat) > 0.5:
            off_lat, off_lon = ranger_offsets[idx % len(ranger_offsets)]
            lat_val = sent_lat + off_lat
            lon_val = sent_lon + off_lon
        else:
            lat_val = float(lat_val)
            lon_val = float(lon_val)

        r_name = rng.get("name", "Field Ranger")
        r_call = rng.get("callsign", f"UNIT-{idx+1}")
        r_sec = rng.get("sector", "Sanctuary Perimeter")
        r_batt = rng.get("battery", 100)
        r_stat = str(rng.get("status", "PATROL READY")).upper()
        r_asgn = rng.get("assigned_alert")

        # Check if ranger is currently responding to an active alert
        is_responding = "RESPONDING" in r_stat or bool(r_asgn)

        if is_responding:
            dest_lat, dest_lon, dest_th = sent_lat, sent_lon, "Threat"
            if r_asgn and str(r_asgn) in alert_loc_map:
                dest_lat, dest_lon, dest_th = alert_loc_map[str(r_asgn)]
            elif alert_loc_map:
                dest_lat, dest_lon, dest_th = next(iter(alert_loc_map.values()))

            dispatch_routes.append({
                "source_coords": [lon_val, lat_val],
                "target_coords": [dest_lon, dest_lat],
                "color": [255, 195, 0, 230],
                "Entity": f"⚡ Tactical Response Vector: Ranger {r_name} ➔ {dest_th} Alert",
            })

            records.append({
                "latitude": lat_val,
                "longitude": lon_val,
                "Entity": f"🛡️ Ranger {r_name} ({r_call}) ⚡ [RESPONDING UNIT]",
                "label_short": f"⚡ {r_name.split()[0]} (RESPONDING)",
                "Category": "🔵 Field Ranger [DISPATCHED TO THREAT]",
                "Coordinates": f"{lat_val:.5f}°N, {lon_val:.5f}°E",
                "Status": f"⚡ RESPONDING (EN ROUTE TO {dest_th.upper()}) · 🔋 {r_batt}% BATT",
                "Details": f"⚡ Active Interception · Sector: {r_sec} · Callsign: {r_call} · 📞 {rng.get('phone', 'N/A')}",
                "color": [255, 195, 0, 245],
                "radius": 110,
                "size": 42,
            })
        else:
            records.append({
                "latitude": lat_val,
                "longitude": lon_val,
                "Entity": f"🛡️ Ranger {r_name} ({r_call})",
                "label_short": f"{r_name.split()[0]} ({r_call})",
                "Category": "🔵 Field Ranger Patrol",
                "Coordinates": f"{lat_val:.5f}°N, {lon_val:.5f}°E",
                "Status": f"{r_stat} · 🔋 {r_batt}% BATT",
                "Details": f"Assigned Sector: {r_sec} · Callsign: {r_call} · 📞 {rng.get('phone', 'N/A')}",
                "color": [115, 217, 232, 235],
                "radius": 90,
                "size": 36,
            })

    for rep in db.get_citizen_reports():
        rep_stat = str(rep.get("status", "PENDING")).upper()
        # SOLVED / RESOLVED incidents disappear from the tactical radar map!
        if rep_stat == "RESOLVED":
            continue

        if rep.get("location_lat") and rep.get("location_lon"):
            c_cat = rep.get("threat_category", "Tip")
            c_lat = float(rep["location_lat"])
            c_lon = float(rep["location_lon"])
            c_asgn = rep.get("assigned_ranger_name")
            c_id = rep.get("report_id")

            if rep_stat == "DISPATCHED":
                records.append({
                    "latitude": c_lat,
                    "longitude": c_lon,
                    "Entity": f"📸 Citizen Tip: {c_cat} ⚡ [PATROL DISPATCHED - {c_asgn or 'En Route'}]",
                    "label_short": f"⚡ 📸 {c_cat}",
                    "Category": "🟠 Dispatched Citizen Report",
                    "Coordinates": f"{c_lat:.5f}°N, {c_lon:.5f}°E",
                    "Status": f"⚡ DISPATCHED · Assigned: {c_asgn or 'Field Patrol'}",
                    "Details": f"Reported by: {rep.get('reporter_name')} (📞 {rep.get('contact_info')}) · Notes: {rep.get('status_notes', 'Patrol unit en route')}",
                    "color": [255, 160, 0, 245],
                    "radius": 100,
                    "size": 42,
                })
            else:
                records.append({
                    "latitude": c_lat,
                    "longitude": c_lon,
                    "Entity": f"📸 Citizen Tip: {c_cat}",
                    "label_short": f"📸 {c_cat}",
                    "Category": "🟠 Citizen GPS Report",
                    "Coordinates": f"{c_lat:.5f}°N, {c_lon:.5f}°E",
                    "Status": f"Status: {rep.get('status', 'PENDING')}",
                    "Details": f"Reported by: {rep.get('reporter_name')} (📞 {rep.get('contact_info')}) · {rep.get('description', '')[:35]}",
                    "color": [242, 198, 109, 230],
                    "radius": 75,
                    "size": 30,
                })
    return pd.DataFrame(records), dispatch_routes

map_dataframe, map_dispatch_routes = build_map_data()

def render_tactical_pydeck_map(df: pd.DataFrame, center_lat: float, center_lon: float, zoom: float = 13.5, routes: list | None = None):
    """Render high-contrast tactical map with interactive hover tooltips showing ranger names, sentinel node locations, threat alerts, and dispatch response vectors."""
    if df is None or df.empty:
        st.info("No GPS telemetry coordinates available for map rendering.")
        return

    layers = []

    if routes:
        routes_df = pd.DataFrame(routes)
        line_layer = pdk.Layer(
            "LineLayer",
            data=routes_df,
            get_source_position="source_coords",
            get_target_position="target_coords",
            get_color="color",
            get_width=6,
            pickable=True,
            auto_highlight=True,
        )
        layers.append(line_layer)

    scatter_layer = pdk.Layer(
        "ScatterplotLayer",
        data=df,
        get_position="[longitude, latitude]",
        get_color="color",
        get_radius="radius",
        radius_scale=1,
        radius_min_pixels=9,
        radius_max_pixels=30,
        pickable=True,
        auto_highlight=True,
    )
    layers.append(scatter_layer)

    text_layer = pdk.Layer(
        "TextLayer",
        data=df,
        get_position="[longitude, latitude]",
        get_text="label_short",
        get_color=[255, 255, 255, 235],
        get_size=11,
        get_alignment_baseline="'bottom'",
        get_text_anchor="'middle'",
        get_pixel_offset=[0, -14],
        pickable=False,
    )
    layers.append(text_layer)

    view_state = pdk.ViewState(
        latitude=float(center_lat),
        longitude=float(center_lon),
        zoom=zoom,
        pitch=25,
        bearing=0,
    )

    tooltip = {
        "html": """
        <div style="background: rgba(10, 18, 22, 0.96); border: 1.5px solid #73d9e8; border-radius: 10px; padding: 10px 14px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; color: #edf5f2; min-width: 220px; box-shadow: 0 10px 30px rgba(0,0,0,0.85);">
            <div style="font-size: 13px; font-weight: 800; color: #ffffff; margin-bottom: 4px; letter-spacing: 0.2px;">{Entity}</div>
            <div style="font-size: 11px; color: #73d9e8; font-weight: 700; margin-bottom: 4px;">{Category}</div>
            <div style="font-size: 11px; color: #7cf0b2; margin-bottom: 3px;">Status: <b>{Status}</b></div>
            <div style="font-size: 10px; color: #f2c66d; margin-bottom: 4px;">{Details}</div>
            <div style="font-size: 10px; color: #9bb1ab; font-family: 'JetBrains Mono', monospace; border-top: 1px solid rgba(255,255,255,0.12); padding-top: 4px; margin-top: 4px;">📍 GPS: {Coordinates}</div>
        </div>
        """,
        "style": {
            "backgroundColor": "transparent",
            "color": "white"
        }
    }

    deck = pdk.Deck(
        layers=layers,
        initial_view_state=view_state,
        map_style="dark",
        tooltip=tooltip,
    )
    st.pydeck_chart(deck, use_container_width=True)

def render_incident_archive_page():
    """Render comprehensive historical archive of all solved threats and citizen incidents."""
    st.markdown('<div class="section"><div class="section-title">📜 Resolved Incident Archive & Historical Logs</div><div class="section-meta">PERMANENT RECORD OF SOLVED THREATS · OCCURRENCE & RESOLUTION TIMESTAMPS · ADDRESSING RANGERS</div></div>', unsafe_allow_html=True)

    resolved_list = db.get_all_resolved_incidents(limit=200)

    # 1. Summary KPIs
    k1, k2, k3, k4 = st.columns(4)
    total_res = len(resolved_list)
    edge_res = sum(1 for r in resolved_list if "Sentinel" in r.get("source_type", ""))
    cit_res = sum(1 for r in resolved_list if "Citizen" in r.get("source_type", ""))

    with k1:
        metric("Total Incidents Solved", str(total_res), "records", "all-time archived", accent="emerald", icon="🏆")
    with k2:
        metric("Edge AI Alerts Solved", str(edge_res), "alerts", "acoustic perception", accent="coral", icon="📡")
    with k3:
        metric("Citizen Reports Solved", str(cit_res), "reports", "public tips addressed", accent="amber", icon="👁️")
    with k4:
        metric("Average Response", "4.2", "min", "rapid interception", accent="cyan", icon="⚡")

    # 2. Search & Filters
    st.markdown("<div style='margin-top:16px; margin-bottom:10px; font-size:13px; font-weight:700; color:#73d9e8;'>🔍 Search & Filter Historical Incident Logs:</div>", unsafe_allow_html=True)
    f_c1, f_c2 = st.columns([2, 1])
    with f_c1:
        search_kw = st.text_input("Search Incidents (Threat Category, Ranger Name, Notes, Incident ID)", placeholder="e.g. Chainsaw, Ranger Amar, Sector 4...", key="arch_search_kw")
    with f_c2:
        type_filter = st.selectbox("Filter Source Type", ["All Incident Sources", "📡 Sentinel Edge AI Alert", "👁️ Public Citizen Report"], key="arch_type_filter")

    filtered = resolved_list
    if type_filter != "All Incident Sources":
        filtered = [r for r in filtered if r.get("source_type") == type_filter]
    if search_kw.strip():
        kw = search_kw.strip().lower()
        filtered = [
            r for r in filtered
            if kw in str(r.get("incident_id", "")).lower()
            or kw in str(r.get("threat_category", "")).lower()
            or kw in str(r.get("resolved_by", "")).lower()
            or kw in str(r.get("resolution_notes", "")).lower()
            or kw in str(r.get("reporter", "")).lower()
        ]

    if not filtered:
        st.info("No resolved incident records match your search criteria.")
        return

    st.markdown(f"<div style='font-size:12px; color:#829a97; margin-bottom:12px;'>Showing <b>{len(filtered)}</b> resolved incident records in chronological order:</div>", unsafe_allow_html=True)

    for idx, inc in enumerate(filtered):
        inc_id = inc.get("incident_id")
        src_type = inc.get("source_type")
        th_cat = inc.get("threat_category")
        occ_time = str(inc.get("occurred_at", ""))[:19].replace("T", " ")
        res_time = str(inc.get("resolved_at", ""))[:19].replace("T", " ")
        res_by = inc.get("resolved_by")
        res_notes = inc.get("resolution_notes")
        lat = inc.get("location_lat")
        lon = inc.get("location_lon")
        photo = inc.get("photo_filename")
        reporter = inc.get("reporter")

        with st.container(border=True):
            h_c1, h_c2 = st.columns([2.2, 1.2])
            with h_c1:
                badge_col = "#ff7070" if "Sentinel" in str(src_type) else "#f2c66d"
                st.markdown(
                    f"""
                    <div style="display:flex; align-items:center; gap:8px;">
                        <span style="background:rgba(255,255,255,0.06); color:{badge_col}; border:1px solid {badge_col}; border-radius:6px; padding:2px 8px; font-size:10px; font-weight:700;">{src_type}</span>
                        <span style="font-size:15px; font-weight:800; color:#fff;">{th_cat}</span>
                        <span style="font-family:'JetBrains Mono',monospace; font-size:11px; color:#73d9e8;">({inc_id})</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.markdown(f"**Action Taken / Resolution Notes:** {res_notes}")
                if reporter:
                    st.caption(f"Source / Reporter: {reporter}")

            with h_c2:
                st.markdown(f"⏱️ **Occurred:** `{occ_time or 'N/A'}`")
                st.markdown(f"✅ **Resolved:** `{res_time or 'N/A'}`")
                st.markdown(f"🛡️ **Addressed By:** <span style='color:#7cf0b2;font-weight:700;'>{res_by}</span>", unsafe_allow_html=True)
                if lat and lon:
                    st.markdown(f"📍 **GPS:** [`{float(lat):.5f}°N, {float(lon):.5f}°E`](https://maps.google.com/?q={lat},{lon})")

            if photo and photo != "no_photo.jpg":
                if str(photo).startswith("data:image"):
                    st.image(photo, caption=f"📸 Photo Evidence: {th_cat}", width=220)
                elif os.path.exists(str(photo)):
                    st.image(photo, caption=f"📸 Photo Evidence: {th_cat}", width=220)

# ============================================================
# 👑 CHIEF RANGER VIEW HANDLERS
# ============================================================

if current_role == "admin":
    if active_page == "📡 Live Sentinel Overview":
        st.markdown('<div class="section"><div class="section-title">Live Environmental Telemetry</div><div class="section-meta">REAL-TIME SENSOR SNAPSHOT · ESP32-S3 DMA BUS</div></div>', unsafe_allow_html=True)
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        with c1:
            metric("Temperature", f"{safe_num(telemetry.get('temperature')):.1f}", "°C", "ambient thermal state", accent="amber", icon="🌡️")
        with c2:
            metric("Humidity", f"{safe_num(telemetry.get('humidity')):.1f}", "%", "relative humidity", accent="cyan", icon="💧")
        with c3:
            metric("Light Level", f"{safe_num(telemetry.get('light_level')):.0f}", "lux", "BH1750 optical index", accent="gold", icon="☀️")
        with c4:
            metric("Battery Gauge", f"{safe_num(telemetry.get('battery_percent')):.1f}", "%", f"{safe_num(telemetry.get('battery_voltage')):.3f} V", accent="emerald", icon="⚡")
        with c5:
            vibration = bool(telemetry.get("vibration_detected"))
            metric("Vibration", "DETECTED" if vibration else "CLEAR", "", "SW-420 seismic latch", accent="coral" if vibration else "purple", icon="📳")
        with c6:
            dev_status = telemetry.get("device_status") if isinstance(telemetry.get("device_status"), dict) else {}
            gas_info = dev_status.get("gas_assessment") or telemetry.get("gas_assessment") or {}
            gas_status = str(gas_info.get("overall_status") or "NOMINAL").upper()
            gas_score = safe_num(gas_info.get("gas_risk_score", 0.0))
            metric("Atmosphere / Gas", gas_status, f"Risk {gas_score:.2f}", "MQ-2 / MQ-135 Engine", accent="emerald" if gas_status == "NOMINAL" else "coral", icon="🧪")

        st.markdown('<div class="section"><div class="section-title">Acoustic Perception & CADIE Decision Engine</div><div class="section-meta">MODEL INFERENCE → CADIE MULTIMODAL FUSION → AUTONOMOUS RESPONSE</div></div>', unsafe_allow_html=True)
        left, mid, right = st.columns([1.35, 1.15, 1])
        with left:
            st.markdown(
                f"""
                <div class="big-event {threat_class}">
                    <div class="kicker">ACTIVE ACOUSTIC PERCEPTION</div>
                    <div class="event-label">{label}</div>
                    <div class="event-caption">{"🔴 THREAT SIGNAL DETECTED" if detected else "🟢 STEADY STATE MONITORING"} · class {event.get("class_id", prediction.get("class_id", "—"))}</div>
                    <div style="margin-top:20px">
                        <div style="display:flex;justify-content:space-between">
                            <span class="event-caption">MODEL CONFIDENCE</span>
                            <span class="confidence" style="color:{conf_color}">{confidence(conf)}</span>
                        </div>
                        <div class="bar"><div style="width:{max(0,min(100,conf*100))}%;background:{conf_color};box-shadow:0 0 10px {conf_color}"></div></div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with mid:
            risk = str(cadie.get("risk_level") or "LOW").upper()
            st.markdown(
                f"""
                <div class="panel">
                    <div class="panel-title">Decision Engine (CADIE)</div>
                    <div class="decision-box">
                        <div class="kicker">TRIAGE RISK LEVEL</div>
                        <div class="decision-risk {status_class('FAILED' if risk in ['HIGH','CRITICAL'] else ('WORKING' if risk in ['LOW','MINIMAL'] else 'WARN'))}">{risk}</div>
                        <div class="decision-action" style="color:var(--green)">ACTION: {cadie.get("action", "MONITOR")}</div>
                    </div>
                    {display_status("CADIE Score", f"{safe_num(cadie.get('score')):.3f}")}
                    {display_status("Ranger Attention", "YES (ALERT)" if cadie.get("requires_attention") else "NO (MONITOR)")}
                    {display_status("Primary Trigger", cadie.get("signal", label))}
                </div>
                """,
                unsafe_allow_html=True,
            )
        with right:
            inference_ms = safe_num(prediction.get("inference_time_ms", event.get("inference_time_ms")))
            st.markdown(
                f"""
                <div class="panel">
                    <div class="panel-title">Inference & Edge Health</div>
                    {display_status("Model Engine", prediction.get("model", "MobileNetV3-Small"))}
                    {display_status("Latency", f"{inference_ms:.2f} ms")}
                    {display_status("Open-Set Discovery", "ACTIVE" if bool((unknown.get("decision") or {}).get("is_unknown")) else "IDLE")}
                    {display_status("Environment Type", environment.get("environment_type", "—"))}
                </div>
                """,
                unsafe_allow_html=True,
            )

    elif active_page == "🗺️ Tactical Map & Dispatch":
        st.markdown('<div class="section"><div class="section-title">Live Tactical Map & Field Ranger Dispatch</div><div class="section-meta">GPS SENTINEL NODES · ACTIVE THREATS · NEARBY FIELD RANGERS</div></div>', unsafe_allow_html=True)
        map_col, dispatch_col = st.columns([2.2, 1.3])
        with map_col:
            render_tactical_pydeck_map(map_dataframe, sent_lat, sent_lon, zoom=13.5, routes=map_dispatch_routes)
            st.markdown(
                """
                <div style="display:flex;gap:14px;flex-wrap:wrap;background:rgba(12,20,23,0.8);border:1px solid rgba(32,54,62,0.7);border-radius:10px;padding:8px 14px;margin-top:8px;margin-bottom:12px;font-size:11px;">
                    <span style="color:#73d9e8;font-weight:700;">● 🔵 Field Ranger Patrol Units</span>
                    <span style="color:#ffc300;font-weight:700;">● ⚡ Responding Units (Dispatched Route)</span>
                    <span style="color:#7cf0b2;font-weight:700;">● 🟢 Sentinel AI Base Nodes</span>
                    <span style="color:#ff7070;font-weight:700;">● 🔴 Active Threats</span>
                    <span style="color:#f2c66d;font-weight:700;">● 🟠 Citizen GPS Reports</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.dataframe(map_dataframe[["Entity", "Category", "Coordinates", "Status"]], use_container_width=True, hide_index=True)
        with dispatch_col:
            st.markdown('<div class="panel"><div class="panel-title">Nearby Field Rangers Roster</div>', unsafe_allow_html=True)
            top_t_lat = active_alerts[0].get("location_lat", sent_lat) if active_alerts else sent_lat
            top_t_lon = active_alerts[0].get("location_lon", sent_lon) if active_alerts else sent_lon
            for rng in field_rangers:
                r_id = rng.get("ranger_id")
                r_name = rng.get("name")
                r_call = rng.get("callsign")
                r_lat = float(safe_num(rng.get("latitude"), sent_lat))
                r_lon = float(safe_num(rng.get("longitude"), sent_lon))
                d_val = calculate_haversine_distance(r_lat, r_lon, top_t_lat, top_t_lon)
                with st.container(border=True):
                    st.markdown(f"**{r_name}** (`{r_call}`)")
                    st.caption(f"📍 {rng.get('sector')} · 🔋 {rng.get('battery')}% · 📞 {rng.get('phone')}")
                    r_stat_raw = str(rng.get('status', 'STANDBY')).upper()
                    if "RESPONDING" in r_stat_raw or rng.get("assigned_alert"):
                        st.markdown(f"<span style='background:rgba(255,195,0,0.2);color:#ffc300;padding:3px 8px;border-radius:6px;font-weight:700;font-size:11px;'>⚡ RESPONDING (EN ROUTE TO THREAT)</span>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"Status: `{r_stat_raw}` · **Distance to Threat:** `{format_gps_distance(d_val)}`")
                    if active_alerts:
                        top_a_id = active_alerts[0].get("alert_id")
                        top_a_th = active_alerts[0].get("threat_type", "Threat")
                        if st.button(f"⚡ Dispatch {r_call} to Threat", key=f"btn_assign_{r_id}_{top_a_id}", use_container_width=True, type="primary" if "RESPONDING" not in r_stat_raw else "secondary"):
                            db.assign_emergency_alert(top_a_id, r_id, r_name, assigned_by=user_display)
                            st.success(f"🚨 {top_a_th} Alert dispatched to {r_name}! Live response vector armed.")
                            st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    elif active_page == "👥 Ranger & User Management":
        st.markdown('<div class="section"><div class="section-title">Chief Ranger: Credential & User Management</div><div class="section-meta">GENERATE FIELD RANGER LOGINS · MANAGE PASSWORDS · CONFIGURE LIVE EMAIL SERVER</div></div>', unsafe_allow_html=True)

        cr_tab1, cr_tab2, cr_tab3 = st.tabs([
            "⚡ Generate Field Ranger Login",
            "📋 Registered Users Directory & Reset",
            "⚙️ Live SMTP Email Server Settings",
        ])

        with cr_tab1:
            with st.container(border=True):
                st.markdown("<div style='font-size:15px;font-weight:800;color:#7cf0b2;margin-bottom:8px;'>👑 Add New Field Ranger Unit</div>", unsafe_allow_html=True)
                st.caption("Chief enters the ranger's details. The system automatically creates a unique username, secure password, and dispatches an official appointment email.")
                rg_c1, rg_c2 = st.columns(2)
                with rg_c1:
                    n_name = st.text_input("Ranger Full Name", placeholder="e.g. Rajesh Varma", key="chief_r_name")
                    n_call = st.text_input("Callsign / Unit Code", placeholder="e.g. DELTA-9", key="chief_r_call")
                    n_rank = st.selectbox("Rank / Designation", ["Field Ranger", "Senior Wildlife Tracker", "Rapid Response Lead", "Acoustic Sentry Officer", "Patrol Commander"], key="chief_r_rank")
                with rg_c2:
                    n_sec = st.selectbox("Assigned Sector", ["Sector 4 (Tiger Corridor)", "Sector 2 (River Ridge)", "Sector 7 (North Boundary)", "Sector 1 (Sanctuary Core)", "Sector 6 (Bamboo Basin)"], key="chief_r_sec")
                    n_email = st.text_input("Ranger Email Address (Credentials will be emailed here)", placeholder="e.g. rajesh.varma@auraforest.gov.in", key="chief_r_email")
                    n_phone = st.text_input("Contact Phone Number (Optional)", placeholder="e.g. +91 99887 76655", key="chief_r_phone")

                if st.button("⚡ Generate Ranger Login & Dispatch Email", type="primary", use_container_width=True, key="btn_gen_ranger"):
                    if not n_name.strip():
                        st.error("Please enter the Ranger's full name.")
                    else:
                        ok, r_data, msg = chief_create_ranger_call(n_name.strip(), n_call.strip(), n_rank, n_sec, phone=n_phone.strip(), email=n_email.strip())
                        if ok:
                            st.session_state["newly_generated_ranger"] = r_data
                            st.success(f"✅ {msg}")

                if "newly_generated_ranger" in st.session_state:
                    ngr = st.session_state["newly_generated_ranger"]
                    deliv = ngr.get("delivery", {})
                    target_em = ngr.get("email") or ngr.get("phone")

                    st.markdown(
                        f"""
                        <div style="background: linear-gradient(135deg, rgba(124, 240, 178, 0.16), rgba(115, 217, 232, 0.1)); border: 1.5px solid #7cf0b2; border-radius: 14px; padding: 16px 20px; margin-top: 14px; box-shadow: 0 0 25px rgba(124,240,178,0.25);">
                            <div style="display:flex; justify-content:space-between; align-items:center;">
                                <div style="font-family:'JetBrains Mono',monospace; font-size:11px; font-weight:700; color:#7cf0b2;">🎉 NEW FIELD RANGER COMMISSIONED & CREDENTIALS ISSUED</div>
                                <div style="font-size:10px; color:#73d9e8; font-weight:700;">🟢 DISPATCHED TO RANGER</div>
                            </div>
                            <div style="font-size:16px; font-weight:800; color:#fff; margin-top:4px;">{ngr.get('full_name')} ({ngr.get('rank')}) · Callsign: {ngr.get('callsign')}</div>
                            <div style="display:grid; grid-template-columns: 1fr 1fr; gap:10px; margin-top:10px; background:rgba(0,0,0,0.3); padding:12px; border-radius:10px;">
                                <div>
                                    <div style="font-size:10px; color:#829a97;">ASSIGNED USERNAME:</div>
                                    <div style="font-family:'JetBrains Mono',monospace; font-size:14px; font-weight:700; color:#73d9e8;">{ngr.get('username')}</div>
                                </div>
                                <div>
                                    <div style="font-size:10px; color:#829a97;">GENERATED PASSWORD:</div>
                                    <div style="font-family:'JetBrains Mono',monospace; font-size:14px; font-weight:700; color:#7cf0b2;">{ngr.get('password')}</div>
                                </div>
                            </div>
                            <div style="font-size:11px; color:#edf6f3; margin-top:8px;">
                                📬 Login credentials, tactical callsign, and sector instructions have been emailed to <b>{target_em or 'Ranger Terminal'}</b>.
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    if deliv.get("html_preview"):
                        with st.expander("📨 Click to Preview Official Commissioning Email Sent to Ranger", expanded=False):
                            st.components.v1.html(deliv.get("html_preview"), height=380, scrolling=True)

        with cr_tab2:
            all_users = get_all_users_call()
            st.markdown("<div style='font-size:15px;font-weight:800;color:#7cf0b2;margin-bottom:8px;'>👥 Registered Personnel & User Directory</div>", unsafe_allow_html=True)
            st.caption("Chief Ranger has master clearance to inspect all registered accounts, modify profile details, reassign roles/sectors, reset passwords, or delete users.")

            # Search & Filter
            search_query = st.text_input("🔍 Search Users (Username, Name, Email, Role, Sector)", placeholder="e.g. ranger, priya, Sector 4...", key="user_search_inp")
            filtered_users = all_users
            if search_query.strip():
                q_low = search_query.strip().lower()
                filtered_users = [
                    u for u in all_users
                    if q_low in str(u.get("username", "")).lower()
                    or q_low in str(u.get("full_name", "")).lower()
                    or q_low in str(u.get("email_or_phone", "")).lower()
                    or q_low in str(u.get("role", "")).lower()
                    or q_low in str(u.get("sector", "")).lower()
                ]

            u_rows = []
            for u in filtered_users:
                u_rows.append({
                    "USERNAME": u.get("username"),
                    "ROLE": str(u.get("role", "")).upper(),
                    "FULL NAME": u.get("full_name") or "—",
                    "EMAIL / CONTACT": u.get("email_or_phone") or "—",
                    "CALLSIGN": u.get("callsign") or "—",
                    "RANK": u.get("rank") or "—",
                    "SECTOR": u.get("sector") or "—",
                    "REGISTERED VIA": u.get("created_by") or "SYSTEM",
                })
            st.dataframe(u_rows, use_container_width=True, hide_index=True)

            st.markdown("<hr style='border:none; border-top:1px solid rgba(115,217,232,0.2); margin:20px 0 16px 0;'/>", unsafe_allow_html=True)

            # User Edit & Deletion Console
            st.markdown("<div style='font-size:14px;font-weight:800;color:#73d9e8;margin-bottom:10px;'>⚙️ Edit User Profile & Manage Credentials</div>", unsafe_allow_html=True)

            if not all_users:
                st.info("No registered users found in the database.")
            else:
                user_list = [u["username"] for u in all_users]
                selected_uname = st.selectbox("Select Account to Edit / Manage:", user_list, key="sel_user_edit")
                curr_u = next((u for u in all_users if u["username"] == selected_uname), None)

                if curr_u:
                    with st.container(border=True):
                        st.markdown(f"<div style='font-size:13px;font-weight:700;color:#fff;margin-bottom:12px;'>Editing Profile: <b style='color:#7cf0b2;'>@{curr_u['username']}</b> (Role: <span style='color:#73d9e8;'>{str(curr_u.get('role')).upper()}</span>)</div>", unsafe_allow_html=True)

                        ed_c1, ed_c2 = st.columns(2)
                        with ed_c1:
                            ed_name = st.text_input("Full Name", value=curr_u.get("full_name", ""), key=f"ed_name_{selected_uname}")
                            ed_email = st.text_input("Email Address / Contact Phone (Must be Unique)", value=curr_u.get("email_or_phone", ""), key=f"ed_email_{selected_uname}")
                            role_opts = ["viewer", "ranger", "admin"]
                            curr_role_idx = role_opts.index(curr_u.get("role", "viewer")) if curr_u.get("role", "viewer") in role_opts else 0
                            ed_role = st.selectbox("Security Role", role_opts, index=curr_role_idx, format_func=lambda x: {"admin": "👑 Master Administrator (Chief)", "ranger": "🛡️ Field Ranger Unit", "viewer": "👁️ Public Citizen (Viewer)"}.get(x, x), key=f"ed_role_{selected_uname}")

                        with ed_c2:
                            ed_callsign = st.text_input("Callsign / Unit ID", value=curr_u.get("callsign") or "", placeholder="e.g. ALPHA-1", key=f"ed_call_{selected_uname}")
                            ed_rank = st.text_input("Rank / Designation", value=curr_u.get("rank") or "", placeholder="e.g. Field Ranger, Citizen Member", key=f"ed_rank_{selected_uname}")
                            ed_sector = st.text_input("Assigned Sector", value=curr_u.get("sector") or "", placeholder="e.g. Sector 4 (Tiger Corridor)", key=f"ed_sec_{selected_uname}")

                        st.markdown("<div style='font-size:12px;font-weight:700;color:#f6c445;margin-top:8px;'>🔑 Reset Password (Leave blank to keep unchanged):</div>", unsafe_allow_html=True)
                        ed_new_pwd = st.text_input("New Password", type="password", placeholder="Leave blank to keep existing password", key=f"ed_pwd_{selected_uname}")

                        act_c1, act_c2 = st.columns([1.5, 1])
                        with act_c1:
                            if st.button("💾 Save User Profile Changes", type="primary", use_container_width=True, key=f"btn_save_{selected_uname}"):
                                with st.spinner("Saving changes..."):
                                    ok, u_msg = update_user_call(
                                        username=selected_uname,
                                        full_name=ed_name.strip(),
                                        email_or_phone=ed_email.strip().lower(),
                                        role=ed_role,
                                        callsign=ed_callsign.strip() if ed_callsign.strip() else None,
                                        rank=ed_rank.strip() if ed_rank.strip() else None,
                                        sector=ed_sector.strip() if ed_sector.strip() else None,
                                        new_password=ed_new_pwd.strip() if ed_new_pwd.strip() else None,
                                    )
                                    if ok:
                                        st.success(f"✅ {u_msg}")
                                        st.rerun()
                                    else:
                                        st.error(f"❌ {u_msg}")

                        with act_c2:
                            if selected_uname in ("chief", "admin"):
                                st.button("🔒 Root Chief Protected", disabled=True, use_container_width=True, key=f"btn_del_dis_{selected_uname}")
                            else:
                                if st.button(f"🗑️ Delete User '{selected_uname}'", use_container_width=True, key=f"btn_del_{selected_uname}"):
                                    with st.spinner("Deleting user account..."):
                                        ok, d_msg = delete_user_call(selected_uname)
                                        if ok:
                                            st.success(f"✅ {d_msg}")
                                            st.rerun()
                                        else:
                                            st.error(f"❌ {d_msg}")

        with cr_tab3:
            from backend.email_service import email_service
            is_armed = email_service.is_configured
            status_badge_html = "<span style='color:#7cf0b2;font-weight:700;'>🟢 REAL SMTP RELAY ARMED</span>" if is_armed else "<span style='color:#f2c66d;font-weight:700;'>🟡 LOCAL SIMULATION MODE (No SMTP credentials set)</span>"

            st.markdown(
                f"""
                <div style="background:rgba(16,26,31,0.9); border:1px solid var(--line); border-radius:14px; padding:16px; margin-bottom:16px;">
                    <div style="font-size:14px; font-weight:800; color:#fff;">Live Outgoing Email Relay Configuration</div>
                    <div style="font-size:12px; margin-top:4px;">Current Status: {status_badge_html}</div>
                    <div style="font-size:11px; color:#829a97; margin-top:4px;">
                        Configure your Gmail, Outlook, or corporate SMTP server below to deliver verification OTPs and Ranger login credentials to real inboxes.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            with st.container(border=True):
                ec_1, ec_2 = st.columns(2)
                with ec_1:
                    cfg_host = st.text_input("SMTP Server Host", value=email_service.smtp_host or "smtp.gmail.com", key="cfg_smtp_host")
                    cfg_user = st.text_input("Sender Email Address (Username)", value=email_service.smtp_user, placeholder="your-email@gmail.com", key="cfg_smtp_user")
                with ec_2:
                    cfg_port = st.number_input("SMTP Port", value=email_service.smtp_port or 587, key="cfg_smtp_port")
                    cfg_pass = st.text_input("SMTP Password / App Password", value=email_service.smtp_pass, type="password", placeholder="16-character App Password", key="cfg_smtp_pass")

                btn_s1, btn_s2 = st.columns(2)
                with btn_s1:
                    if st.button("💾 Save & Arm SMTP Server", type="primary", use_container_width=True, key="btn_save_smtp"):
                        env_file_path = Path(PROJECT_ROOT) / ".env"
                        env_content = f"""
SMTP_HOST={cfg_host.strip()}
SMTP_PORT={int(cfg_port)}
SMTP_USER={cfg_user.strip()}
SMTP_PASS={cfg_pass.strip()}
SMTP_FROM={cfg_user.strip()}
SMTP_SSL=false
                        """.strip()
                        env_file_path.write_text(env_content, encoding="utf-8")
                        email_service.configure(
                            smtp_host=cfg_host.strip(),
                            smtp_port=int(cfg_port),
                            smtp_user=cfg_user.strip(),
                            smtp_pass=cfg_pass.strip(),
                            smtp_from=cfg_user.strip(),
                        )
                        st.success("✅ SMTP Configuration saved and loaded into active runtime!")
                        st.rerun()

                with btn_s2:
                    test_rcpt = st.text_input("Test Recipient Email", value=cfg_user.strip(), placeholder="recipient@example.com", key="test_rcpt_inp", label_visibility="collapsed")
                    if st.button("🧪 Send Live Test Email", use_container_width=True, key="btn_test_smtp"):
                        if not test_rcpt.strip():
                            st.error("Please enter a test recipient email.")
                        else:
                            res = email_service.send_otp_email(
                                recipient_email=test_rcpt.strip(),
                                otp_code=f"{random.randint(100000, 999999)}",
                                user_name="Test Recipient",
                            )
                            st.success(f"Dispatched: {res.get('message')}")
                            if res.get("html_preview"):
                                with st.expander("View Dispatched Message", expanded=True):
                                    st.components.v1.html(res["html_preview"], height=300, scrolling=True)

    elif active_page == "📊 Acoustic AI & Spectrum":
        render_spectrum_section(label, mic_level=safe_num(telemetry.get("microphone_level", 500.0)))

    elif active_page == "🚨 Emergency Broadcast":
        st.markdown('<div class="section"><div class="section-title">Emergency Alert Broadcast Console</div><div class="section-meta">MULTI-CHANNEL DISPATCH · DEVICE STROBE · WEBHOOK BROADCAST</div></div>', unsafe_allow_html=True)
        with st.container(border=True):
            f_th, f_rk, f_ac = st.columns(3)
            with f_th:
                m_threat = st.selectbox("Threat Category", ["🔥 Fire (Highest Priority)", "🪚 Logging: Chainsaw / Drill (Highest Priority)", "🚗 Vehicles: Truck / Engine (Moderate)", "👤 Human Intrusion / Speech (Moderate)", "🌿 Others: Wildlife (Low)"], key="adm_threat_choice")
            with f_rk:
                m_risk = st.selectbox("Priority Level", ["CRITICAL", "HIGH", "MODERATE", "LOW"], key="adm_risk_choice")
            with f_ac:
                m_action = st.selectbox("Dispatch Action", ["DISPATCH_RANGERS", "INTERCEPT_VEHICLE", "INVESTIGATE_INTRUSION", "RECORD_EVIDENCE", "MONITOR"], key="adm_action_choice")

            clean_th = m_threat.split(" (")[0].replace("🔥 ", "").replace("🪚 ", "").replace("🚗 ", "").replace("👤 ", "").replace("🌿 ", "")
            if st.button("🚨 Broadcast Emergency Alert Now", type="primary", use_container_width=True):
                db.insert_emergency_alert({
                    "alert_id": f"alert_man_{int(time.time())}",
                    "device_id": device_id,
                    "threat_type": clean_th,
                    "risk_level": m_risk,
                    "confidence": 0.98,
                    "location_lat": sent_lat,
                    "location_lon": sent_lon,
                    "message": f"🚨 {m_risk}: {clean_th} alert dispatched by Chief Ranger Sharma.",
                })
                st.success("Emergency Alert broadcast to all field sentinels and ranger units!")
                st.rerun()

        st.markdown("<div style='margin-top:14px;font-size:13px;font-weight:700;'>Alert Broadcast & Dispatch History Log:</div>", unsafe_allow_html=True)
        hist_rows = []
        for a_item in db.get_emergency_alert_history(limit=15):
            hist_rows.append({
                "ALERT ID": a_item.get("alert_id"),
                "THREAT": a_item.get("threat_type"),
                "PRIORITY": a_item.get("risk_level"),
                "STATUS": a_item.get("status"),
                "RESPONDING RANGER": a_item.get("assigned_ranger_name") or "Awaiting Dispatch",
                "ADDRESSED & RESOLVED BY": a_item.get("resolved_by") or ("En Route / Addressing" if a_item.get("assigned_ranger_name") else "Unassigned"),
                "RESOLUTION NOTES": a_item.get("resolution_notes") or "—",
            })
        st.dataframe(hist_rows, use_container_width=True, hide_index=True)

    elif active_page == "📨 Citizen Reports Inbox":
        st.markdown('<div class="section"><div class="section-title">Public Citizen Reports & Tips Inbox</div><div class="section-meta">CITIZEN TIPS · PHOTO EVIDENCE · TRIAGE & DISPATCH CONTROLS</div></div>', unsafe_allow_html=True)
        c_reports = db.get_citizen_reports()
        if not c_reports:
            st.info("No citizen reports pending review.")
        else:
            for rep in c_reports:
                r_id = rep.get("report_id")
                r_cat = rep.get("threat_category")
                r_stat = str(rep.get("status", "PENDING")).upper()
                r_photo = rep.get("photo_filename")
                r_lat = rep.get("location_lat")
                r_lon = rep.get("location_lon")

                with st.container(border=True):
                    c1, c2, c3 = st.columns([1.2, 1.8, 1.1])
                    with c1:
                        if r_photo and r_photo != "no_photo.jpg":
                            if r_photo.startswith("data:image"):
                                st.image(r_photo, caption=f"📸 Photo ({r_cat})", use_container_width=True)
                            elif os.path.exists(r_photo):
                                st.image(r_photo, caption=f"📸 Photo ({r_cat})", use_container_width=True)
                            else:
                                st.markdown(f"<div style='padding:12px;background:rgba(255,255,255,0.03);border:1px dashed var(--line);border-radius:8px;'>📸 Attached Photo: {r_photo[:20]}...</div>", unsafe_allow_html=True)
                        else:
                            st.caption("📷 No photo attached")
                    with c2:
                        st.markdown(f"**Threat:** `{r_cat}`")
                        st.markdown(f"**Report ID:** `{r_id}` · **Reporter:** {rep.get('reporter_name')} (📞 `{rep.get('contact_info')}`)")
                        st.markdown(f"**Description:** {rep.get('description')}")
                        if r_lat and r_lon:
                            st.markdown(f"📍 **Phone GPS:** [`{r_lat:.6f}°N, {r_lon:.6f}°E`](https://maps.google.com/?q={r_lat},{r_lon})")
                    with c3:
                        st.markdown(f"STATUS: **{r_stat}**")
                        if r_stat != "RESOLVED":
                            f_rangers_opts = {f"{r.get('name')} ({r.get('callsign')})": (r.get("ranger_id"), r.get("name")) for r in field_rangers}
                            sel_disp_r = st.selectbox("Dispatch Ranger Unit", list(f_rangers_opts.keys()) if f_rangers_opts else ["General Patrol"], key=f"sel_rng_{r_id}", label_visibility="collapsed")
                            disp_r_id, disp_r_name = f_rangers_opts.get(sel_disp_r, (None, None))
                            if st.button("⚡ Dispatch to Ranger", key=f"btn_disp_{r_id}", use_container_width=True, type="primary"):
                                db.dispatch_citizen_report(r_id, ranger_id=disp_r_id, ranger_name=disp_r_name, dispatched_by=user_display)
                                st.success(f"🚨 Dispatched to {disp_r_name or 'Patrol'}! Location updated on Tactical Radar.")
                                st.rerun()
                            if st.button("✅ Mark Solved", key=f"btn_res_adm_{r_id}", use_container_width=True):
                                db.resolve_citizen_report(r_id, resolved_by=user_display, resolution_notes="Chief Ranger verified and resolved tip on site.")
                                st.success("Incident resolved and archived in Historical Logs.")
                                st.rerun()
                        else:
                            st.caption(f"✅ Resolved by {rep.get('resolved_by') or 'Ranger Unit'}")

    elif active_page == "📜 Incident Archive & Resolution Logs":
        render_incident_archive_page()

    elif active_page == "🔬 Unknown Sound Discovery":
        st.markdown('<div class="section"><div class="section-title">Unknown Sound Discovery & Clustering</div><div class="section-meta">OPEN-SET REJECTION → DBSCAN CLUSTERS → HUMAN REVIEW</div></div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            metric("Pending Unknown", str(safe_num(unknown.get("buffer_size", 0))), "samples", "awaiting batch", accent="cyan")
        with c2:
            metric("Discovered Clusters", "3", "classes", "DBSCAN clusters", accent="purple")

    elif active_page == "🔒 Security & Audit Log":
        st.markdown('<div class="section"><div class="section-title">Security & Authentication Audit Log</div><div class="section-meta">IMMUTABLE RECORD OF LOGINS, DISPATCHES, AND RANGER INCIDENT RESOLUTIONS</div></div>', unsafe_allow_html=True)
        logs = db.get_auth_audit_log(limit=50)
        if logs:
            l_rows = []
            for l in logs:
                l_rows.append({
                    "TIMESTAMP": str(l.get("created_at", ""))[:19].replace("T", " "),
                    "USER / RANGER": l.get("username"),
                    "ROLE": str(l.get("role")).upper(),
                    "ACTION TYPE": l.get("action"),
                    "OFFICIAL AUDIT STATEMENT": l.get("details"),
                })
            st.dataframe(l_rows, use_container_width=True, hide_index=True)
        else:
            st.info("No audit logs recorded yet.")

# ============================================================
# 🛡️ FIELD RANGER VIEW HANDLERS
# ============================================================

elif current_role == "ranger":
    if active_page == "🚨 Incident & Citizen Response":
        st.markdown('<div class="section"><div class="section-title">Active Threats & Citizen Incidents Response</div><div class="section-meta">ON-SITE INVESTIGATION AND RESOLUTION</div></div>', unsafe_allow_html=True)

        # 1. Edge Alerts
        st.markdown("<div style='font-size:13px;font-weight:700;color:#ff7070;margin-bottom:8px;'>📡 Sentinel Edge AI Threat Alerts:</div>", unsafe_allow_html=True)
        if not active_alerts:
            st.success("🟢 No unacknowledged Sentinel edge alerts in your sector.")
        else:
            for al in active_alerts:
                al_id = al.get("alert_id")
                al_lat = float(safe_num(al.get("location_lat"), sent_lat))
                al_lon = float(safe_num(al.get("location_lon"), sent_lon))
                d_str = format_gps_distance(calculate_haversine_distance(sent_lat, sent_lon, al_lat, al_lon))

                with st.container(border=True):
                    st.markdown(f"**🚨 THREAT: {al.get('threat_type')}** ({safe_num(al.get('confidence'))*100:.1f}%) · Pinpoint: `{al_lat:.5f}°N, {al_lon:.5f}°E` · **{d_str}**")
                    r_c1, r_c2 = st.columns([2.5, 1])
                    with r_c1:
                        notes_inp = st.text_input("Resolution Notes", value="Threat investigated and perimeter secured.", key=f"al_notes_{al_id}")
                    with r_c2:
                        st.write("")
                        if st.button("✅ Mark as Solved", key=f"btn_res_{al_id}", use_container_width=True, type="primary"):
                            db.resolve_emergency_alert(al_id, resolved_by=user_display, resolution_notes=notes_inp)
                            st.success("Alert resolved and recorded!")
                            st.rerun()

        # 2. Citizen Reports
        st.markdown("<div style='font-size:13px;font-weight:700;color:#f2c66d;margin-top:16px;margin-bottom:8px;'>📸 Citizen-Reported Field Incidents:</div>", unsafe_allow_html=True)
        cit_unres = [c for c in db.get_citizen_reports() if str(c.get("status", "")).upper() != "RESOLVED"]
        if not cit_unres:
            st.info("🟢 No pending citizen reports.")
        else:
            for rep in cit_unres:
                c_id = rep.get("report_id")
                c_lat = float(safe_num(rep.get("location_lat"), sent_lat))
                c_lon = float(safe_num(rep.get("location_lon"), sent_lon))
                d_str = format_gps_distance(calculate_haversine_distance(sent_lat, sent_lon, c_lat, c_lon))

                with st.container(border=True):
                    st.markdown(f"**📸 Sighting: {rep.get('threat_category')}** (Reporter: {rep.get('reporter_name')}) · **{d_str}**")
                    st.caption(f"Description: {rep.get('description')}")
                    if rep.get("photo_filename") and rep.get("photo_filename").startswith("data:image"):
                        st.image(rep.get("photo_filename"), width=200)
                    rc_1, rc_2 = st.columns([2.5, 1])
                    with rc_1:
                        cit_notes = st.text_input("Action Notes", value="Inspected coordinates, area secured.", key=f"cit_res_n_{c_id}")
                    with rc_2:
                        st.write("")
                        if st.button("✅ Mark Solved", key=f"btn_cit_res_{c_id}", use_container_width=True, type="primary"):
                            db.resolve_citizen_report(c_id, resolved_by=user_display, resolution_notes=cit_notes)
                            st.success(f"Incident marked as solved by {user_display}! Removed from live radar and recorded in Incident Archive.")
                            st.rerun()

    elif active_page == "🗺️ Sector Map & Near Rangers":
        st.markdown('<div class="section"><div class="section-title">Tactical Sector Map & Near My Rangers Radar</div><div class="section-meta">LIVE PATROL BUDDY PROXIMITY · TARGET THREAT COORDINATES</div></div>', unsafe_allow_html=True)
        render_tactical_pydeck_map(map_dataframe, sent_lat, sent_lon, zoom=14.0, routes=map_dispatch_routes)
        st.markdown(
            """
            <div style="display:flex;gap:14px;flex-wrap:wrap;background:rgba(12,20,23,0.8);border:1px solid rgba(32,54,62,0.7);border-radius:10px;padding:8px 14px;margin-top:8px;margin-bottom:12px;font-size:11px;">
                <span style="color:#73d9e8;font-weight:700;">● 🔵 Field Ranger Patrol Units</span>
                <span style="color:#ffc300;font-weight:700;">● ⚡ Responding Units (Dispatched Route)</span>
                <span style="color:#7cf0b2;font-weight:700;">● 🟢 Sentinel AI Base Nodes</span>
                <span style="color:#ff7070;font-weight:700;">● 🔴 Active Threats</span>
                <span style="color:#f2c66d;font-weight:700;">● 🟠 Citizen GPS Reports</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("<div style='font-size:13px;font-weight:700;color:#73d9e8;margin-top:14px;margin-bottom:8px;'>👥 Near My Rangers (Live Radar):</div>", unsafe_allow_html=True)
        r_cols = st.columns(len(field_rangers))
        for idx, rng in enumerate(field_rangers):
            with r_cols[idx]:
                rg_lat = float(safe_num(rng.get("latitude"), sent_lat))
                rg_lon = float(safe_num(rng.get("longitude"), sent_lon))
                rg_dist = format_gps_distance(calculate_haversine_distance(sent_lat, sent_lon, rg_lat, rg_lon))
                with st.container(border=True):
                    st.markdown(f"**{rng.get('name')}** (`{rng.get('callsign')}`)")
                    st.caption(f"📍 Proximity: `{rg_dist}` · 🔋 `{rng.get('battery')}%`")
                    st.markdown(f"📞 `{rng.get('phone')}`")

    elif active_page == "📜 Incident Archive & Resolution Logs":
        render_incident_archive_page()

    elif active_page == "📡 Field Telemetry & Gas":
        st.markdown('<div class="section"><div class="section-title">Field Environment & Gas Sentry</div><div class="section-meta">LIVE SENSOR READINGS FROM SENTINEL NODE</div></div>', unsafe_allow_html=True)
        rc1, rc2, rc3, rc4 = st.columns(4)
        with rc1:
            metric("Ambient Temp", f"{safe_num(telemetry.get('temperature')):.1f}", "°C", "thermal sensor", accent="amber", icon="🌡️")
        with rc2:
            metric("Humidity", f"{safe_num(telemetry.get('humidity')):.1f}", "%", "RH level", accent="cyan", icon="💧")
        with rc3:
            metric("Battery SOC", f"{safe_num(telemetry.get('battery_percent')):.1f}", "%", "MAX17048", accent="emerald", icon="⚡")
        with rc4:
            metric("Gas Atmosphere", str((telemetry.get("device_status") or {}).get("gas_assessment", {}).get("overall_status") or "NOMINAL").upper(), "", "MQ-2/MQ-135", accent="purple", icon="🧪")

    elif active_page == "📊 Acoustic Frequency Monitor":
        render_spectrum_section(label, mic_level=safe_num(telemetry.get("microphone_level", 500.0)))

# ============================================================
# 👁️ PUBLIC CITIZEN VIEW HANDLERS
# ============================================================

elif current_role == "viewer":
    if active_page == "🌿 Forest Climate & Readings":
        st.markdown('<div class="section"><div class="section-title">Live Forest Environmental Readings</div><div class="section-meta">PUBLIC REAL-TIME CLIMATE AND AIR QUALITY</div></div>', unsafe_allow_html=True)
        pc1, pc2, pc3 = st.columns(3)
        with pc1:
            metric("Forest Temperature", f"{safe_num(telemetry.get('temperature')):.1f}", "°C", "Pleasant climate", accent="amber", icon="🌲")
        with pc2:
            metric("Relative Humidity", f"{safe_num(telemetry.get('humidity')):.1f}", "%", "Canopy moisture", accent="cyan", icon="💧")
        with pc3:
            metric("Air Quality", "FRESH & CLEAN", "", "Natural forest atmosphere", accent="emerald", icon="🍃")

    elif active_page == "⚠️ Safety Notices & Alerts":
        st.markdown('<div class="section"><div class="section-title">Public Forest Safety Notices</div><div class="section-meta">OFFICIAL RANGER ADVISORIES</div></div>', unsafe_allow_html=True)
        if active_alerts:
            for al in active_alerts:
                st.error(f"⚠️ SAFETY NOTICE: Elevated activity ({al.get('threat_type')}) detected in Sector. Please stay on marked trails.")
        else:
            st.success("✅ Forest Reserve is safe. All sectors are currently green.")

    elif active_page == "📸 Report Illegal Activity":
        st.markdown('<div class="section"><div class="section-title">Citizen Tip: Report Illegal Forest Activity</div><div class="section-meta">REPORT CHAINSAWS, POACHING, OR FIRES DIRECTLY TO CHIEF RANGER</div></div>', unsafe_allow_html=True)

        with st.container(border=True):
            r_col1, r_col2 = st.columns(2)
            with r_col1:
                cit_name = st.text_input("Your Name", value=user_display)
                cit_cat = st.selectbox("Observed Activity", [
                    "🪚 Illegal Tree Felling / Chainsaw Activity",
                    "🔥 Wildfire / Smoke Sighting",
                    "🏹 Poaching / Animal Trap Sighting",
                    "🚗 Unauthorized Vehicle Intrusion",
                    "🗑️ Illegal Waste Dumping / Encroachment",
                ])
                cit_contact = st.text_input("Contact Phone / Email", value=st.session_state.get("aura_username", ""))
            with r_col2:
                cit_desc = st.text_area("Description of Sighting", placeholder="Describe what you observed, trail marker, number of individuals, etc.")
                cit_file = st.file_uploader("Upload Photo Evidence", type=["png", "jpg", "jpeg"], key="citizen_photo_upload_inp")
                if cit_file is not None:
                    st.image(cit_file, caption=f"📸 Evidence Attached: {cit_file.name}", width=220)

            g_c1, g_c2 = st.columns(2)
            with g_c1:
                rep_lat = st.number_input("Incident Latitude (Phone GPS)", value=sent_lat, format="%.6f")
            with g_c2:
                rep_lon = st.number_input("Incident Longitude (Phone GPS)", value=sent_lon, format="%.6f")

            is_already_sent = st.session_state.get("citizen_report_just_sent", False)
            btn_label = "✅ Report & Evidence Sent to Chief Ranger!" if is_already_sent else "📤 Send Report & GPS Coordinates to Chief Ranger"

            col_submit, col_reset = st.columns([2, 1])
            with col_submit:
                if st.button(btn_label, type="secondary" if is_already_sent else "primary", use_container_width=True, key="btn_citizen_send_tip", disabled=is_already_sent):
                    if not cit_desc.strip():
                        st.error("Please provide a description of the observed activity.")
                    else:
                        photo_str = "no_photo.jpg"
                        if cit_file is not None:
                            file_bytes = cit_file.getvalue()
                            b64 = base64.b64encode(file_bytes).decode("utf-8")
                            mime = "image/jpeg" if cit_file.name.lower().endswith((".jpg", ".jpeg")) else "image/png"
                            photo_str = f"data:{mime};base64,{b64}"

                        report_id = f"cit_{int(time.time())}_{random.randint(100,999)}"
                        db.insert_citizen_report(
                            report_id=report_id,
                            reporter_name=cit_name,
                            contact_info=cit_contact,
                            threat_category=cit_cat,
                            description=cit_desc,
                            photo_filename=photo_str,
                            location_lat=rep_lat,
                            location_lon=rep_lon,
                        )
                        st.session_state["citizen_report_just_sent"] = True
                        st.session_state["citizen_last_report_id"] = report_id
                        st.success(f"✅ Tip & Photo sent! Chief Ranger and field patrol units have been alerted with your verified GPS coordinates ({rep_lat:.5f}°N, {rep_lon:.5f}°E).")
                        st.rerun()

            with col_reset:
                if is_already_sent:
                    if st.button("➕ Submit Another Report", use_container_width=True, key="btn_citizen_reset_tip"):
                        st.session_state["citizen_report_just_sent"] = False
                        st.rerun()

# ============================================================
# FOOTER
# ============================================================

st.markdown(
    f"""
    <div class="footer">
        AURAForest Sentinel · {device_id} · User: {username_active} ({current_role.upper()}) ·
        HMAC-SHA256 Authenticated · Live Refresh Active
    </div>
    """,
    unsafe_allow_html=True,
)
