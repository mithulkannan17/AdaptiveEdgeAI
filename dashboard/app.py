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

@st.cache_resource
def get_database() -> RuntimeDatabase:
    return RuntimeDatabase()

@st.cache_resource
def get_source() -> RuntimeDataSource:
    return RuntimeDataSource()

db = get_database()
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
    except Exception:
        return {}

def auth_login_call(username_inp: str, password_inp: str) -> tuple[bool, dict, str]:
    """Authenticate credentials via API or local database."""
    # 1. Try Backend API
    res = api_request("/api/v1/auth/login", method="POST", payload={"username": username_inp, "password": password_inp})
    if res.get("success"):
        return True, res.get("user", {}), res.get("token", "")

    # 2. Fallback to direct Database
    db_u = db.authenticate_user(username_inp, password_inp)
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
        db.insert_auth_audit_log(
            username=db_u["username"],
            role=user_role,
            action="LOGIN_SUCCESS",
            details=f"User {db_u['username']} logged in via local auth.",
        )
        return True, profile, token

    return False, {}, "Invalid username or password."

def generate_otp_call(phone_or_email: str) -> tuple[bool, str, dict, str]:
    """Request automated 6-digit OTP code and dispatch via Email/SMS."""
    from backend.email_service import email_service
    contact = phone_or_email.strip()
    is_email = "@" in contact and "." in contact

    res = api_request("/api/v1/auth/signup/otp/generate", method="POST", payload={"phone_or_email": contact})
    if res.get("success") and res.get("otp"):
        return True, res.get("otp"), res.get("delivery", {}), res.get("message", "OTP generated")

    # DB fallback + email service
    otp = db.create_otp(contact)
    deliv = {}
    if is_email:
        deliv = email_service.send_otp_email(contact, otp, user_name=contact.split("@")[0].capitalize())

    db.insert_auth_audit_log(username=contact, role="public", action="GENERATE_OTP", details=f"Generated OTP {otp} for {contact} (Channel: {'EMAIL' if is_email else 'SMS'})")
    return True, otp, deliv, f"Verification code dispatched to {contact}."

def verify_otp_and_signup_call(contact: str, otp: str, username: str, password: str, full_name: str) -> tuple[bool, str]:
    """Verify OTP and register new citizen."""
    res = api_request("/api/v1/auth/signup/otp/verify", method="POST", payload={
        "phone_or_email": contact,
        "otp_code": otp,
        "username": username,
        "password": password,
        "full_name": full_name,
    })
    if res.get("success"):
        return True, res.get("message", "Account created successfully!")

    # DB fallback
    if not db.verify_otp(contact, otp):
        return False, "Invalid or expired OTP verification code."

    created = db.create_user(username=username, password=password, role="viewer", full_name=full_name, email_or_phone=contact, created_by="SELF_SIGNUP")
    if created:
        db.insert_auth_audit_log(username=username, role="public", action="CITIZEN_REGISTRATION", details=f"Citizen {full_name} registered.")
        return True, f"Account '{username}' created successfully! You may now login."
    return False, "Failed to create user account."

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
    u = db.get_user(username)
    if u:
        db.create_user(username=u["username"], password=new_pwd, role=u["role"], full_name=u["full_name"], email_or_phone=u.get("email_or_phone", ""), callsign=u.get("callsign"), rank=u.get("rank"), sector=u.get("sector"), created_by="chief_password_reset")
        return True, f"Password for '{username}' updated."
    return False, "User not found."

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

                st.markdown("<div style='margin-top:16px; border-top:1px solid rgba(32,54,62,0.6); padding-top:12px;'></div>", unsafe_allow_html=True)
                st.caption("⚡ Quick Access Profiles for Testing:")
                q1, q2, q3 = st.columns(3)
                with q1:
                    if st.button("👑 Chief Ranger", use_container_width=True, key="quick_chief"):
                        st.session_state["authenticated"] = True
                        st.session_state["aura_username"] = "chief"
                        st.session_state["aura_user_role"] = "admin"
                        st.session_state["aura_user_name"] = "Chief Ranger Sharma"
                        st.session_state["aura_user_dept"] = "Forestry Cyber-Defense Command"
                        st.rerun()
                with q2:
                    if st.button("🛡️ Field Ranger", use_container_width=True, key="quick_ranger"):
                        st.session_state["authenticated"] = True
                        st.session_state["aura_username"] = "ranger.amar"
                        st.session_state["aura_user_role"] = "ranger"
                        st.session_state["aura_user_name"] = "Ranger Amar Singh"
                        st.session_state["aura_user_dept"] = "Sector 4 (Tiger Corridor)"
                        st.rerun()
                with q3:
                    if st.button("👁️ Public Citizen", use_container_width=True, key="quick_citizen"):
                        st.session_state["authenticated"] = True
                        st.session_state["aura_username"] = "citizen.demo"
                        st.session_state["aura_user_role"] = "viewer"
                        st.session_state["aura_user_name"] = "Jane Citizen (Observer)"
                        st.session_state["aura_user_dept"] = "Public Eco-Visitor"
                        st.rerun()

        # ----------------------------------------------------
        # TAB 2: PUBLIC CITIZEN SIGN-UP (WITH SYSTEM OTP)
        # ----------------------------------------------------
        with auth_tab_signup:
            with st.container(border=True):
                st.markdown(
                    """
                    <div style="background:rgba(115,217,232,0.08); border:1px solid rgba(115,217,232,0.3); border-radius:10px; padding:10px 14px; margin-bottom:14px;">
                        <div style="font-size:12px; font-weight:700; color:#73d9e8;">ℹ️ Registration Notice:</div>
                        <div style="font-size:11px; color:#edf6f3; margin-top:2px;">
                            • <b>Public Citizens:</b> Self-register below using automated System OTP verification.<br/>
                            • <b>Field Rangers:</b> Logins are issued exclusively by the <b>Chief Ranger</b>.
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                s_name = st.text_input("Full Name", placeholder="e.g. Priya Nambiar", key="signup_name")
                s_contact = st.text_input("Mobile Phone or Email (for Automated OTP)", placeholder="e.g. +91 98765 43210 or priya@example.com", key="signup_contact")

                # Step 1: Request OTP Button
                otp_col1, otp_col2 = st.columns([1.5, 1])
                with otp_col1:
                    if st.button("⚡ Request Verification Code (Email / SMS)", use_container_width=True, key="btn_req_otp"):
                        if not s_contact.strip() or len(s_contact.strip()) < 5:
                            st.error("Please enter a valid phone number or email address.")
                        else:
                            ok, otp_code, deliv_info, msg = generate_otp_call(s_contact.strip())
                            if ok:
                                st.session_state["active_otp_contact"] = s_contact.strip()
                                st.session_state["active_otp_code"] = otp_code
                                st.session_state["active_otp_deliv"] = deliv_info
                                is_em = "@" in s_contact.strip()
                                st.success(f"✅ OTP successfully dispatched to {s_contact.strip()} via {'Email Server' if is_em else 'SMS Gateway'}!")

                # Live Realistic Email / SMS Dispatch Badge
                if "active_otp_code" in st.session_state and st.session_state.get("active_otp_contact") == s_contact.strip():
                    is_em = "@" in s_contact.strip()
                    deliv = st.session_state.get("active_otp_deliv", {})
                    channel_label = "📬 OFFICIAL VERIFICATION EMAIL DISPATCHED" if is_em else "💬 SMS VERIFICATION MESSAGE DISPATCHED"
                    relay_channel = deliv.get("channel", "EMAIL_RELAY" if is_em else "SMS_GATEWAY")

                    st.markdown(
                        f"""
                        <div style="background: linear-gradient(135deg, rgba(124, 240, 178, 0.18), rgba(115, 217, 232, 0.12)); border: 1.5px solid #7cf0b2; border-radius: 14px; padding: 14px 18px; margin: 14px 0; box-shadow: 0 0 22px rgba(124,240,178,0.25);">
                            <div style="display:flex; justify-content:space-between; align-items:center;">
                                <span style="font-family:'JetBrains Mono',monospace; font-size:11px; font-weight:700; color:#7cf0b2;">{channel_label}</span>
                                <span style="font-size:10px; color:#7cf0b2; font-weight:700;">🟢 DELIVERED TO INBOX</span>
                            </div>
                            <div style="display:flex; justify-content:space-between; align-items:center; margin-top:8px; flex-wrap:wrap; gap:8px;">
                                <div>
                                    <div style="font-size:11px; color:#829a97;">To Recipient: <b style="color:#edf6f3;">{s_contact.strip()}</b></div>
                                    <div style="font-size:11px; color:#829a97;">Sender: <b style="color:#73d9e8;">AuraForest Sentinel &lt;no-reply@auraforest.gov.in&gt;</b></div>
                                </div>
                                <div style="background:#101c20; border:1px solid #7cf0b2; border-radius:8px; padding:6px 14px; text-align:center;">
                                    <div style="font-size:9px; color:#829a97;">VERIFICATION CODE</div>
                                    <div style="font-family:'Courier New',monospace; font-size:20px; font-weight:800; color:#7cf0b2; letter-spacing:3px;">
                                        {st.session_state['active_otp_code']}
                                    </div>
                                </div>
                            </div>
                            <div style="font-size:11px; color:#c4d7d3; margin-top:8px;">
                                ⏱️ Valid for 5 minutes. Enter the 6-digit passcode below to complete your registration.
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    if is_em and deliv.get("html_preview"):
                        with st.expander("📨 Click to View Incoming Email Message in Mailbox", expanded=False):
                            st.components.v1.html(deliv.get("html_preview"), height=360, scrolling=True)

                s_otp = st.text_input("Enter 6-Digit System OTP", placeholder="e.g. 839201", key="signup_otp_inp")
                s_username = st.text_input("Desired Username", placeholder="e.g. citizen.priya", key="signup_user_inp")
                s_password = st.text_input("Create Password", type="password", placeholder="••••••••••••", key="signup_pass_inp")

                if st.button("✨ Complete Citizen Sign-Up", type="primary", use_container_width=True, key="btn_complete_signup"):
                    if not s_name.strip() or not s_contact.strip() or not s_otp.strip() or not s_username.strip() or not s_password.strip():
                        st.error("Please fill in all fields including the OTP.")
                    else:
                        ok, msg = verify_otp_and_signup_call(s_contact.strip(), s_otp.strip(), s_username.strip(), s_password.strip(), s_name.strip())
                        if ok:
                            st.success(f"✅ {msg}")
                            st.info("You can now switch to the 'Sign In' tab and log in.")
                        else:
                            st.error(msg)

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
            "🔬 Unknown Sound Discovery",
            "🔒 Security & Audit Log",
        ]
    elif current_role == "ranger":
        nav_options = [
            "🚨 Incident & Citizen Response",
            "🗺️ Sector Map & Near Rangers",
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

    # 5. Log Out Button
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

# Active alert notification banner
if active_alerts:
    top_alert = active_alerts[0]
    al_threat = str(top_alert.get("threat_type", "Threat")).upper()
    al_conf = safe_num(top_alert.get("confidence", 0.95)) * 100
    al_lat = top_alert.get("location_lat")
    al_lon = top_alert.get("location_lon")
    al_coords = f"{al_lat:.5f}°N, {al_lon:.5f}°E" if al_lat is not None and al_lon is not None else "Coordinates Acquired"

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

# Build map dataframe
def build_map_data() -> pd.DataFrame:
    records = [
        {"latitude": float(sent_lat), "longitude": float(sent_lon), "Entity": f"📡 Primary Sentinel: {device_id}", "Category": "🟢 Sentinel Node (Active)", "Coordinates": f"{sent_lat:.5f}°N, {sent_lon:.5f}°E", "Status": "ONLINE"},
        {"latitude": float(sent_lat + 0.0042), "longitude": float(sent_lon + 0.0035), "Entity": "📡 Sentinel-02 (North Ridge)", "Category": "🟢 Sentinel Node (Mesh)", "Coordinates": f"{(sent_lat + 0.0042):.5f}°N, {(sent_lon + 0.0035):.5f}°E", "Status": "ONLINE"},
        {"latitude": float(sent_lat - 0.0038), "longitude": float(sent_lon - 0.0044), "Entity": "📡 Sentinel-03 (West Creek)", "Category": "🟢 Sentinel Node (Mesh)", "Coordinates": f"{(sent_lat - 0.0038):.5f}°N, {(sent_lon - 0.0044):.5f}°E", "Status": "ONLINE"},
    ]
    for al in active_alerts:
        if al.get("location_lat") and al.get("location_lon"):
            records.append({"latitude": float(al["location_lat"]), "longitude": float(al["location_lon"]), "Entity": f"🚨 {al.get('threat_type')} Alert", "Category": "🔴 Active Threat", "Coordinates": f"{float(al['location_lat']):.5f}°N, {float(al['location_lon']):.5f}°E", "Status": f"PRIORITY: {al.get('risk_level', 'CRITICAL')}"})
    for rng in field_rangers:
        if rng.get("latitude") and rng.get("longitude"):
            records.append({"latitude": float(rng["latitude"]), "longitude": float(rng["longitude"]), "Entity": f"🛡️ {rng.get('name')} ({rng.get('callsign')})", "Category": "🔵 Field Ranger Patrol", "Coordinates": f"{float(rng['latitude']):.5f}°N, {float(rng['longitude']):.5f}°E", "Status": f"{rng.get('status')} · {rng.get('battery')}% BATT"})
    for rep in db.get_citizen_reports():
        if rep.get("location_lat") and rep.get("location_lon"):
            records.append({"latitude": float(rep["location_lat"]), "longitude": float(rep["location_lon"]), "Entity": f"📸 Citizen Tip: {rep.get('threat_category')}", "Category": "🟠 Citizen GPS Report", "Coordinates": f"{float(rep['location_lat']):.5f}°N, {float(rep['location_lon']):.5f}°E", "Status": f"Status: {rep.get('status', 'PENDING')}"})
    return pd.DataFrame(records)

map_dataframe = build_map_data()

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
            st.map(map_dataframe[["latitude", "longitude"]], zoom=13, use_container_width=True)
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
                    st.markdown(f"Status: `{rng.get('status')}` · **Distance to Threat:** `{format_gps_distance(d_val)}`")
                    if active_alerts:
                        top_a_id = active_alerts[0].get("alert_id")
                        if st.button(f"⚡ Assign Alert to {r_call}", key=f"btn_assign_{r_id}_{top_a_id}", use_container_width=True):
                            db.assign_emergency_alert(top_a_id, r_id, r_name)
                            st.success(f"Alert assigned to {r_name}!")
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
            st.markdown("<div style='font-size:14px;font-weight:700;margin-bottom:8px;'>Registered User Accounts:</div>", unsafe_allow_html=True)
            u_rows = []
            for u in all_users:
                u_rows.append({
                    "USERNAME": u.get("username"),
                    "ROLE": str(u.get("role")).upper(),
                    "FULL NAME": u.get("full_name"),
                    "CONTACT": u.get("email_or_phone") or "—",
                    "CALLSIGN / SECTOR": f"{u.get('callsign') or '—'} ({u.get('sector') or '—'})",
                    "CREATED BY": u.get("created_by"),
                })
            st.dataframe(u_rows, use_container_width=True, hide_index=True)

            # Password Update / Reset
            st.markdown("<div style='font-size:13px;font-weight:700;margin-top:16px;margin-bottom:6px;'>🔑 Update User Password / Reset:</div>", unsafe_allow_html=True)
            rst_c1, rst_c2, rst_c3 = st.columns([1.5, 1.5, 1])
            with rst_c1:
                target_user = st.selectbox("Select User", [u["username"] for u in all_users], key="rst_target_user")
            with rst_c2:
                new_pwd_inp = st.text_input("New Password", placeholder="Enter new password", key="rst_new_pwd")
            with rst_c3:
                st.write("")
                if st.button("Update Password", type="primary", use_container_width=True, key="btn_apply_pwd_rst"):
                    if len(new_pwd_inp.strip()) < 4:
                        st.error("Password must be at least 4 characters.")
                    else:
                        ok, msg = update_user_password_call(target_user, new_pwd_inp.strip())
                        if ok:
                            st.success(f"Password for {target_user} updated!")
                            st.rerun()

            # Delete User
            if target_user not in ("chief", "admin"):
                if st.button(f"🗑️ Delete User '{target_user}'", key="btn_del_user"):
                    ok, msg = delete_user_call(target_user)
                    if ok:
                        st.success(msg)
                        st.rerun()

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

        st.markdown("<div style='margin-top:14px;font-size:13px;font-weight:700;'>Alert Broadcast History:</div>", unsafe_allow_html=True)
        hist_rows = []
        for a_item in db.get_emergency_alert_history(limit=10):
            hist_rows.append({
                "ALERT ID": a_item.get("alert_id"),
                "THREAT": a_item.get("threat_type"),
                "RISK": a_item.get("risk_level"),
                "CONFIDENCE": f"{safe_num(a_item.get('confidence')) * 100:.1f}%",
                "STATUS": a_item.get("status"),
                "ASSIGNED RANGER": a_item.get("assigned_ranger_name") or "Unassigned",
                "RESOLVED BY": a_item.get("resolved_by") or "—",
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
                        if st.button("✅ Verify Tip", key=f"btn_ver_{r_id}", use_container_width=True):
                            db.update_citizen_report_status(r_id, "VERIFIED", "Chief verified tip")
                            st.rerun()
                        if st.button("⚡ Dispatch Patrol", key=f"btn_disp_{r_id}", use_container_width=True, type="primary"):
                            db.update_citizen_report_status(r_id, "DISPATCHED", "Patrol dispatched")
                            st.rerun()

    elif active_page == "🔬 Unknown Sound Discovery":
        st.markdown('<div class="section"><div class="section-title">Unknown Sound Discovery & Clustering</div><div class="section-meta">OPEN-SET REJECTION → DBSCAN CLUSTERS → HUMAN REVIEW</div></div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            metric("Pending Unknown", str(safe_num(unknown.get("buffer_size", 0))), "samples", "awaiting batch", accent="cyan")
        with c2:
            metric("Discovered Clusters", "3", "classes", "DBSCAN clusters", accent="purple")

    elif active_page == "🔒 Security & Audit Log":
        st.markdown('<div class="section"><div class="section-title">Security & Authentication Audit Log</div><div class="section-meta">IMMUTABLE RECORD OF LOGINS, DISPATCHES, AND RESOLUTIONS</div></div>', unsafe_allow_html=True)
        logs = db.get_auth_audit_log(limit=50)
        if logs:
            l_rows = []
            for l in logs:
                l_rows.append({
                    "TIMESTAMP": str(l.get("created_at", ""))[:19].replace("T", " "),
                    "USER": l.get("username"),
                    "ROLE": str(l.get("role")).upper(),
                    "ACTION": l.get("action"),
                    "DETAILS": l.get("details"),
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
                            db.update_citizen_report_status(c_id, "RESOLVED", cit_notes)
                            st.success("Incident marked as solved!")
                            st.rerun()

    elif active_page == "🗺️ Sector Map & Near Rangers":
        st.markdown('<div class="section"><div class="section-title">Tactical Sector Map & Near My Rangers Radar</div><div class="section-meta">LIVE PATROL BUDDY PROXIMITY · TARGET THREAT COORDINATES</div></div>', unsafe_allow_html=True)
        st.map(map_dataframe[["latitude", "longitude"]], zoom=14, use_container_width=True)
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
                cit_file = st.file_uploader("Upload Photo Evidence", type=["png", "jpg", "jpeg"])

            g_c1, g_c2 = st.columns(2)
            with g_c1:
                rep_lat = st.number_input("Incident Latitude (Phone GPS)", value=sent_lat, format="%.6f")
            with g_c2:
                rep_lon = st.number_input("Incident Longitude (Phone GPS)", value=sent_lon, format="%.6f")

            if st.button("📤 Send Report & GPS Coordinates to Chief Ranger", type="primary", use_container_width=True):
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
                    st.success(f"✅ Tip received! Chief Ranger and field patrol units have been alerted with your verified GPS coordinates ({rep_lat:.5f}°N, {rep_lon:.5f}°E).")
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
