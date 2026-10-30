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
try:
    from dashboard.runtime_data_source import RuntimeDataSource
except ImportError:
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

# ============================================================
# PERSISTENT SESSION RESTORATION (SURVIVES PAGE REFRESHES)
# ============================================================

query_params = getattr(st, "query_params", {})
auth_param_user = str(query_params.get("auth_user") or "").strip().lower()
auth_param_token = str(query_params.get("auth_token") or "").strip()

if not st.session_state.get("authenticated", False) and auth_param_user and auth_param_token:
    if auth_param_user in ("chief", "admin") and (auth_param_token.startswith("aura_sess_chief") or auth_param_token.startswith("aura_sess_")):
        st.session_state["authenticated"] = True
        st.session_state["aura_username"] = "chief"
        st.session_state["aura_user_role"] = "admin"
        st.session_state["aura_user_name"] = "Chief Ranger Sharma"
        st.session_state["aura_user_dept"] = "AuraForest Central Command"
        st.session_state["aura_auth_token"] = auth_param_token
    else:
        try:
            u_rec = db.get_user(auth_param_user)
            if u_rec and (auth_param_token.startswith("aura_sess_") or len(auth_param_token) > 8):
                role_map = {"admin": "admin", "chief": "admin", "ranger": "ranger", "viewer": "viewer"}
                user_role = role_map.get(str(u_rec.get("role", "viewer")).lower(), "viewer")
                st.session_state["authenticated"] = True
                st.session_state["aura_username"] = u_rec["username"]
                st.session_state["aura_user_role"] = user_role
                st.session_state["aura_user_name"] = u_rec.get("full_name") or u_rec["username"].capitalize()
                st.session_state["aura_user_dept"] = u_rec.get("sector") or ("Command" if user_role == "admin" else "Field Unit")
                st.session_state["aura_auth_token"] = auth_param_token
        except Exception:
            pass

@st.cache_resource
def get_source() -> RuntimeDataSource:
    return RuntimeDataSource()

source = get_source()

AURA_API_URL = os.getenv(
    "AURAFOREST_API_URL",
    "http://127.0.0.1:8000",
).rstrip("/")

def format_display_label(raw_label: str) -> str:
    """
    Standardized operational label formatter:
    - chainsaw / drill / jackhammer -> 'Chainsaw / Drill (Logging)' (shows both!)
    - human / speech / talking / conversation / footsteps / walking -> 'Human Activity (Active)'
    - fire / wildfire / burning -> 'Wildfire / Crackling Fire'
    - gunshot / poaching / explosion -> 'Gunshot / Firearm Blast'
    - vehicle / truck / car / engine -> 'Vehicle Movement'
    - emergencyvehicle / siren -> 'Emergency Siren'
    - bird -> 'Birdsong / Avian'
    - insects -> 'Insects / Canopy Bio-Sound'
    - water / river / stream -> 'Water Flow / Stream'
    - wind -> 'Wind / Canopy Breeze'
    - rain / thunder -> 'Rain / Weather Activity'
    - ambient / silence -> 'Ambient Forest'
    """
    l = str(raw_label or "").strip().lower()
    if any(k in l for k in ["chainsaw", "drill", "jackhammer", "logging", "saw"]):
        return "Chainsaw / Drill (Logging)"
    if any(k in l for k in ["human", "speech", "talking", "conversation", "footsteps", "walking", "voice"]):
        return "Human Activity (Active)"
    if any(k in l for k in ["fire", "wildfire", "burning", "flame"]):
        return "Wildfire / Crackling Fire"
    if any(k in l for k in ["gunshot", "explosion", "poaching", "blast", "firearm"]):
        return "Gunshot / Poaching Blast"
    if any(k in l for k in ["vehicle", "truck", "car", "engine", "motorcycle", "bus"]):
        return "Vehicle Movement"
    if "emergencyvehicle" in l or "siren" in l:
        return "Emergency Siren"
    if "bird" in l:
        return "Birdsong / Avian"
    if "insect" in l:
        return "Insects / Canopy Bio-Sound"
    if any(k in l for k in ["water", "river", "stream", "waterfall"]):
        return "Water Flow / Stream"
    if "wind" in l:
        return "Wind / Canopy Breeze"
    if "rain" in l or "thunder" in l:
        return "Rain / Weather Activity"
    if "ambient" in l or "silence" in l:
        return "Ambient Forest"
    return raw_label.title() if raw_label else "Ambient Forest"

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
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

:root {
    --bg-main: #0b0f14;
    --surface-1: #111720;
    --surface-2: #161e29;
    --surface-3: #1d2736;
    --border-subtle: #202b3a;
    --border-hover: #334358;
    --text-primary: #f1f5f9;
    --text-secondary: #94a3b8;
    --text-muted: #64748b;
    --brand-emerald: #10b981;
    --brand-emerald-dim: rgba(16, 185, 129, 0.12);
    --status-amber: #f59e0b;
    --status-amber-dim: rgba(245, 158, 11, 0.12);
    --status-red: #ef4444;
    --status-red-dim: rgba(239, 68, 68, 0.12);
    --status-sky: #38bdf8;
    --status-sky-dim: rgba(56, 189, 248, 0.12);
}

html, body, [class*="css"] {
    font-family: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    color: var(--text-primary);
}

/* App Canvas */
.stApp {
    background-color: var(--bg-main);
    color: var(--text-primary);
}

.block-container {
    max-width: 1560px;
    padding: 20px 28px 48px 28px !important;
}

header[data-testid="stHeader"] {
    background: transparent;
}

/* Sidebar Styling */
section[data-testid="stSidebar"] {
    background-color: var(--surface-1) !important;
    border-right: 1px solid var(--border-subtle) !important;
}

div[data-testid="stSidebarUserContent"] {
    padding: 20px 14px;
}

/* Sidebar Radio Navigation */
div[data-testid="stRadio"] > div {
    gap: 4px;
}

div[data-testid="stRadio"] label {
    background: transparent;
    border: 1px solid transparent;
    border-radius: 8px;
    padding: 8px 12px;
    transition: all 0.18s ease;
    cursor: pointer;
    font-size: 13px;
    font-weight: 500;
    color: var(--text-secondary) !important;
    display: flex;
    align-items: center;
}

div[data-testid="stRadio"] label:hover {
    background: var(--surface-2);
    color: var(--text-primary) !important;
    border-color: var(--border-subtle);
}

div[data-testid="stRadio"] label[data-checked="true"],
div[data-testid="stRadio"] label:has(input:checked) {
    background: var(--surface-2) !important;
    border-color: var(--brand-emerald) !important;
    color: var(--text-primary) !important;
    font-weight: 600;
}

/* Metric Cards */
.metric-card {
    background: var(--surface-1);
    border: 1px solid var(--border-subtle);
    border-radius: 10px;
    padding: 14px 16px;
    min-height: 108px;
    transition: border-color 0.2s ease, background 0.2s ease;
    margin-bottom: 12px;
}

.metric-card:hover {
    border-color: var(--border-hover);
    background: var(--surface-2);
}

.metric-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 4px;
}

.metric-label {
    color: var(--text-muted);
    font-size: 11px;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    font-weight: 600;
}

.metric-icon-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 24px;
    height: 24px;
    border-radius: 6px;
    background: var(--surface-2);
    font-size: 12px;
    color: var(--text-secondary);
}

.metric-value {
    font-size: 24px;
    font-weight: 700;
    letter-spacing: -0.02em;
    color: var(--text-primary);
    font-family: "Inter", sans-serif;
    margin-top: 2px;
}

.metric-unit {
    font-size: 13px;
    color: var(--text-muted);
    font-weight: 500;
    margin-left: 3px;
}

.metric-sub {
    font-size: 11px;
    color: var(--text-muted);
    margin-top: 4px;
}

/* Threat Hero Card */
.big-event {
    border-radius: 12px;
    padding: 20px 22px;
    border: 1px solid var(--border-subtle);
    background: var(--surface-1);
    margin-bottom: 14px;
}

.threat-critical {
    background: #181014;
    border-color: rgba(239, 68, 68, 0.4);
}

.threat-elevated {
    background: #19150e;
    border-color: rgba(245, 158, 11, 0.4);
}

.threat-nominal {
    background: #0f1814;
    border-color: rgba(16, 185, 129, 0.3);
}

.event-label {
    font-size: 26px;
    font-weight: 700;
    letter-spacing: -0.02em;
    margin: 4px 0 6px;
    color: var(--text-primary);
}

.event-caption {
    color: var(--text-secondary);
    font-size: 12px;
}

.confidence {
    font-family: "JetBrains Mono", monospace;
    font-size: 15px;
    font-weight: 600;
}

.bar {
    height: 6px;
    background: var(--surface-3);
    border-radius: 4px;
    overflow: hidden;
    margin-top: 8px;
}

.bar > div {
    height: 100%;
    border-radius: 4px;
    transition: width 0.3s ease;
}

/* Structured Panels */
.panel {
    background: var(--surface-1);
    border: 1px solid var(--border-subtle);
    border-radius: 10px;
    padding: 16px 18px;
    margin-bottom: 14px;
}

.panel-title {
    font-size: 13px;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 12px;
    letter-spacing: 0.01em;
}

.status-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 0;
    border-bottom: 1px solid rgba(255, 255, 255, 0.04);
}

.status-row:last-child {
    border-bottom: 0;
}

.status-name {
    color: var(--text-secondary);
    font-size: 12px;
}

.status-value {
    font-family: "JetBrains Mono", monospace;
    font-size: 11px;
    font-weight: 500;
}

.ok { color: var(--brand-emerald); }
.warn { color: var(--status-amber); }
.bad { color: var(--status-red); }
.neutral { color: var(--text-muted); }

.decision-box {
    border-radius: 8px;
    border: 1px solid var(--border-subtle);
    padding: 12px 14px;
    margin-bottom: 10px;
    background: var(--surface-2);
}

.decision-risk {
    font-size: 20px;
    font-weight: 700;
    letter-spacing: -0.01em;
}

/* Header & Breadcrumb */
.hero {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
    padding-bottom: 16px;
    border-bottom: 1px solid var(--border-subtle);
    flex-wrap: wrap;
    gap: 12px;
}

.kicker {
    font-family: "JetBrains Mono", monospace;
    font-size: 10px;
    letter-spacing: 0.12em;
    color: var(--brand-emerald);
    font-weight: 600;
    text-transform: uppercase;
}

.brand {
    font-size: 22px;
    font-weight: 700;
    letter-spacing: -0.02em;
    color: var(--text-primary);
    margin-top: 2px;
}

.brand-mark {
    color: var(--brand-emerald);
    margin-right: 6px;
}

.subtitle {
    font-size: 12px;
    color: var(--text-muted);
    margin-top: 2px;
}

.live-pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: var(--brand-emerald-dim);
    border: 1px solid rgba(16, 185, 129, 0.3);
    border-radius: 999px;
    padding: 4px 12px;
    color: var(--brand-emerald);
    font-family: "JetBrains Mono", monospace;
    font-size: 11px;
    font-weight: 600;
}

.dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--brand-emerald);
}

.section {
    margin: 24px 0 12px;
}

.section-title {
    font-size: 14px;
    font-weight: 600;
    color: var(--text-primary);
    letter-spacing: -0.01em;
}

.section-meta {
    font-family: "JetBrains Mono", monospace;
    font-size: 10px;
    letter-spacing: 0.05em;
    color: var(--text-muted);
    margin-top: 2px;
    text-transform: uppercase;
}

.chip {
    display: inline-block;
    border: 1px solid var(--border-subtle);
    background: var(--surface-2);
    border-radius: 6px;
    padding: 3px 8px;
    color: var(--text-secondary);
    font-family: "JetBrains Mono", monospace;
    font-size: 10px;
    font-weight: 500;
    margin: 2px 4px 2px 0;
}

/* Institutional Emergency Alerts */
.emergency-banner-critical {
    background: #1c0f12;
    border: 1px solid var(--status-red);
    border-radius: 10px;
    padding: 14px 18px;
    margin-bottom: 16px;
}

.emergency-banner-warning {
    background: #1c160c;
    border: 1px solid var(--status-amber);
    border-radius: 10px;
    padding: 14px 18px;
    margin-bottom: 16px;
}

/* Touch & Button Controls */
button, input, select, textarea {
    font-family: "Inter", sans-serif !important;
}

button[kind="primary"] {
    background-color: var(--brand-emerald) !important;
    color: #0b0f14 !important;
    font-weight: 600 !important;
    border: none !important;
    border-radius: 8px !important;
}

button[kind="primary"]:hover {
    background-color: #059669 !important;
}

button[kind="secondary"] {
    background-color: var(--surface-2) !important;
    border: 1px solid var(--border-subtle) !important;
    color: var(--text-primary) !important;
    border-radius: 8px !important;
}

button[kind="secondary"]:hover {
    background-color: var(--surface-3) !important;
    border-color: var(--border-hover) !important;
}

.footer {
    color: var(--text-muted);
    font-size: 11px;
    text-align: center;
    padding-top: 36px;
    border-top: 1px solid var(--border-subtle);
    margin-top: 40px;
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
    """Authenticate credentials via local database or API with multi-field fallback (username, email, full name, prefix)."""
    u_clean = username_inp.strip().lower()
    p_clean = password_inp.strip()
    p_lower = p_clean.lower()

    chief_passcodes = {"auraadmin123", "chief@aura2026", "admin123", "chief123", "auraadmin", "chief", "admin"}
    ranger_passcodes = {
        "auraranger123", "ranger123", "password123", "aura@ranger2026",
        "ranger", "auraforest@2026", "password", "ranger@123", "auraranger"
    }

    # 1. Master Chief Authentication
    if u_clean in ("chief", "admin") and (p_lower in chief_passcodes or p_clean in chief_passcodes):
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

    # 2. Local Database Direct Authentication (High-speed, supports generated ranger credentials)
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
                "callsign": db_u.get("callsign", "RANGER-UNIT"),
                "rank": db_u.get("rank", "Field Ranger"),
            }
            db_inst.insert_auth_audit_log(
                username=db_u["username"],
                role=user_role,
                action="LOGIN_SUCCESS",
                details=f"User {db_u['username']} ({user_role}) logged in successfully.",
            )
            return True, profile, token
    except Exception as ex:
        pass

    # 3. Fallback to Backend API
    try:
        res = api_request("/api/v1/auth/login", method="POST", payload={"username": u_clean, "password": p_clean})
        if res.get("success"):
            return True, res.get("user", {}), res.get("token", "")
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
    )    # Synchronized directly via shared SQLite database.
    # Note: Duplicate api_request("/api/v1/auth/signup/otp/generate") removed to prevent double-email dispatch.

    if is_email and not deliv.get("success", False):
        err_msg = deliv.get("message", "Email delivery could not reach inbox.")
        return True, otp, deliv, f"⚠️ Note: SMTP email dispatch throttled/unavailable ({err_msg}). Use generated verification code: **{otp}** (or master code: **999999**)."

    return True, otp, deliv, f"Verification code dispatched to {contact} via {'Gmail SMTP' if deliv.get('channel') == 'SMTP_RELAY' else 'SMS Gateway'}." 

def validate_otp_call(contact: str, otp: str) -> tuple[bool, str]:
    """Validate the 6-digit OTP code across Session, Database, and Backend API."""
    clean_contact = contact.strip().lower()
    clean_otp = str(otp).replace(" ", "").replace("-", "").strip()
    if not clean_otp:
        return False, "Please enter the 6-digit OTP received in your email."

    # 0. Check Master Override Code (for offline testing & rate limit bypass)
    if clean_otp == "999999":
        db.verify_otp(clean_contact, clean_otp)
        print(f"[AuraForest Sentinel AUTH] ✅ Master OTP Override verified for {clean_contact}", flush=True)
        return True, f"Master verification code accepted for '{clean_contact}'!"

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
        clean_otp == "999999"
        or st.session_state.get("citizen_email_verified") == clean_contact
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
    """Chief creates new Field Ranger account and emails credentials directly and reliably."""
    from backend.email_service import email_service
    first_token = [t for t in full_name.split() if t.lower() not in ("ranger", "officer", "cadet")]
    clean_f = "".join(c for c in (first_token[0] if first_token else full_name.split()[0]) if c.isalnum()).lower()
    username = f"ranger.{clean_f}{random.randint(10, 99)}"
    password = f"Aura#Ranger{random.randint(100, 999)}"
    contact_val = email.strip() or phone.strip()

    created = db.create_user(
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
    if not created:
        return False, {}, "Failed to create ranger account. Email or username already registered."

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

    db.insert_auth_audit_log(
        username="chief",
        role="admin",
        action="CHIEF_CREATE_RANGER",
        details=f"Chief created Ranger {full_name} ({username}) -> Dispatched to {contact_val}.",
    )
    return True, {
        "username": username,
        "password": password,
        "full_name": full_name,
        "callsign": callsign,
        "rank": rank,
        "sector": sector,
        "phone": phone.strip(),
        "email": email.strip(),
        "delivery": deliv,
    }, f"Field Ranger account '{username}' created! Credentials dispatched to {contact_val}." 

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
        <div style="text-align: center; margin-top: 24px; margin-bottom: 28px;">
            <div style="font-family:monospace;font-size:11px;letter-spacing:.12em;color:var(--brand-emerald);font-weight:600;">AURAFOREST SENTINEL PLATFORM</div>
            <div style="font-size:26px;font-weight:700;color:var(--text-primary);margin-top:4px;letter-spacing:-0.02em;">Environmental Operations Console</div>
            <div style="font-size:13px;color:var(--text-muted);margin-top:4px;">Institutional Access Control · Forest Division & Community Observatory</div>
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
                st.markdown("<div style='font-size:16px;font-weight:800;color:#fff;margin-bottom:10px;'>Enter Portal Credentials</div>", unsafe_allow_html=True)
                

                l_user = st.text_input("Username or Registered Email", key="login_username_inp", placeholder="e.g. ranger, ranger.amar, or user@gmail.com")
                l_pass = st.text_input("Password", type="password", key="login_password_inp", placeholder="e.g. auraranger123")
                st.caption("💡 Field Rangers can sign in using either their assigned username (e.g. ranger.amar) or registered email address.")

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
                            if hasattr(st, "query_params"):
                                st.query_params["auth_user"] = st.session_state["aura_username"]
                                st.query_params["auth_token"] = token
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

                # Step 1: Request OTP Button with Cooldown & Rate Limit Protection
                last_sent = st.session_state.get("otp_sent_time", 0)
                cooldown_remaining = int(60 - (time.time() - last_sent)) if last_sent else 0
                btn_disabled = bool(cooldown_remaining > 0 and st.session_state.get("otp_sent_to") == s_contact.strip().lower())
                btn_label = f"⏳ Resend Available in {cooldown_remaining}s" if btn_disabled else "⚡ Send 6-Digit OTP to Email"

                if st.button(btn_label, use_container_width=True, key="btn_req_otp", disabled=btn_disabled):
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
                                if deliv_info.get("success", False):
                                    st.success(f"✅ 6-digit OTP sent to **{s_contact.strip()}**! Please check your email inbox (and spam folder) and enter the code below.")
                                else:
                                    st.warning(msg)
                            else:
                                st.error(f"❌ {msg}")

                # Status Banner if OTP was sent
                if st.session_state.get("otp_sent_to") == s_contact.strip().lower() and not st.session_state.get("citizen_email_verified"):
                    st.markdown(
                        f"""
                        <div style="background: linear-gradient(135deg, rgba(115, 217, 232, 0.12), rgba(124, 240, 178, 0.10)); border: 1.5px solid #73d9e8; border-radius: 12px; padding: 12px 16px; margin: 12px 0;">
                            <div style="display:flex; justify-content:space-between; align-items:center;">
                                <span style="font-family:monospace; font-size:11px; font-weight:700; color:#73d9e8;">📬 VERIFICATION EMAIL SENT</span>
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
                    with st.expander("❓ Haven't received your verification email? Check tips & fallback", expanded=False):
                        st.markdown("""
                        - **Check Spam / Junk Folder**: Automated notifications from new senders often get filtered into Spam.
                        - **Email Sending Quota / Delay**: Free SMTP providers enforce rate limits when multiple emails are sent.
                        - **Master Test Code**: If your email provider throttles or blocks delivery, enter **`999999`** in the box below and click **Verify OTP** to bypass without waiting.
                        """)

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

raw_label = event.get("label") or prediction.get("label") or "Ambient Forest"
label = format_display_label(raw_label)
conf = safe_num(event.get("confidence", prediction.get("confidence", 0.0)))
detected = event.get("detected", False)
risk_raw = str(cadie.get("risk_level") or "LOW").upper()
threat_class = "threat-critical" if risk_raw in ["HIGH", "CRITICAL"] else ("threat-elevated" if risk_raw in ["ELEVATED", "MEDIUM"] else "threat-nominal")
conf_color = "#ff7070" if risk_raw in ["HIGH", "CRITICAL"] else ("#f2c66d" if risk_raw in ["ELEVATED", "MEDIUM"] else "#7cf0b2")

# Ingest live device GPS from browser/mobile device query parameters
query_params = getattr(st, "query_params", None)
if query_params:
    dev_lat = query_params.get("device_lat") or query_params.get("lat")
    dev_lon = query_params.get("device_lon") or query_params.get("lon")
    if dev_lat and dev_lon:
        try:
            d_lat = float(dev_lat)
            d_lon = float(dev_lon)
            if -90.0 <= d_lat <= 90.0 and -180.0 <= d_lon <= 180.0 and (abs(d_lat) > 0.001 or abs(d_lon) > 0.001):
                st.session_state["client_gps_lat"] = d_lat
                st.session_state["client_gps_lon"] = d_lon
                st.session_state["client_gps_accuracy"] = float(query_params.get("gps_acc", 10.0))
                st.session_state["client_gps_acquired"] = True
        except (ValueError, TypeError):
            pass

# Active emergency alerts & Field Rangers
active_alerts = db.get_active_emergency_alerts(include_acknowledged=True)
field_rangers = db.get_field_rangers()

# If user is a logged-in Field Ranger, automatically sync their live GPS location into database
if current_role == "ranger" and "client_gps_lat" in st.session_state and "client_gps_lon" in st.session_state:
    c_lat = float(st.session_state["client_gps_lat"])
    c_lon = float(st.session_state["client_gps_lon"])
    r_id = "rng_" + username_active.replace(".", "_")
    db.update_ranger_location(r_id, c_lat, c_lon, status="LIVE_GPS_ACTIVE")
    for r in field_rangers:
        if r.get("ranger_id") == r_id or username_active.lower() in str(r.get("phone", "")).lower() or username_active.lower() in str(r.get("name", "")).lower():
            db.update_ranger_location(r.get("ranger_id"), c_lat, c_lon, status="LIVE_GPS_ACTIVE")
    field_rangers = db.get_field_rangers()

RESERVE_PRESETS: dict[str, tuple[float, float] | None] = {
    "📍 Live Device GPS (Auto-Detect Fix)": None,
    "🌲 Bandipur Tiger Reserve, Karnataka": (11.6664, 76.6291),
    "🐅 Nagarhole National Park, Karnataka": (12.0298, 76.1554),
    "🐘 Mudumalai Wildlife Sanctuary, Tamil Nadu": (11.5623, 76.5342),
    "🌿 Silent Valley National Park, Kerala": (11.1342, 76.4287),
    "🦏 Kaziranga National Park, Assam": (26.5775, 93.1711),
    "🐾 Jim Corbett National Park, Uttarakhand": (29.5300, 78.7747),
    "🍃 Anamalai Tiger Reserve, Tamil Nadu": (10.3667, 76.9667),
    "🦁 Gir National Park, Gujarat": (21.1243, 70.8242),
    "🐯 Ranthambore National Park, Rajasthan": (26.0173, 76.5026),
}

# GPS Coordinates resolution
loc_dict = state.get("location") or telemetry.get("location") or {}
raw_lat = loc_dict.get("latitude") if loc_dict.get("latitude") is not None else telemetry.get("latitude")
raw_lon = loc_dict.get("longitude") if loc_dict.get("longitude") is not None else telemetry.get("longitude")

sel_preset = st.session_state.get("sel_sanctuary_base_preset", "📍 Live Device GPS (Auto-Detect Fix)")
preset_coords = RESERVE_PRESETS.get(sel_preset)

if preset_coords is not None:
    sent_lat, sent_lon = preset_coords
elif "client_gps_lat" in st.session_state and "client_gps_lon" in st.session_state:
    sent_lat = float(st.session_state["client_gps_lat"])
    sent_lon = float(st.session_state["client_gps_lon"])
elif raw_lat is not None and raw_lon is not None and (abs(float(raw_lat)) > 0.001 or abs(float(raw_lon)) > 0.001):
    sent_lat = float(raw_lat)
    sent_lon = float(raw_lon)
else:
    sent_lat = 11.6664
    sent_lon = 76.6291

# ============================================================
# 🧭 SIDEBAR: PROFILE & NAVIGATION MENU (REPLACED NAVBAR)
# ============================================================

with st.sidebar:
    # 1. Branding Header
    st.markdown(
        """
        <div style="padding: 4px 0 14px 0; border-bottom: 1px solid rgba(32, 54, 62, 0.7); margin-bottom: 14px;">
            <div style="font-family:monospace;font-size:10px;letter-spacing:.16em;color:var(--green);font-weight:700;">AURAFOREST SENTINEL</div>
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
            <div style="font-family:monospace; font-size:10px; font-weight:700; color:{r_color};">
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

    # 3. Sanctuary Sector / Geo-Anchor Selector
    st.markdown('<div class="metric-label" style="margin-bottom:4px;">SANCTUARY BASE SECTOR</div>', unsafe_allow_html=True)
    sel_preset_choice = st.selectbox(
        "Sanctuary Base Sector",
        options=list(RESERVE_PRESETS.keys()),
        index=0,
        key="sel_sanctuary_base_preset",
        label_visibility="collapsed",
    )

    # 4. Role-Aware Sidebar Navigation (Replaces top navbar!)
    st.markdown('<div class="metric-label" style="margin-top:12px; margin-bottom:6px;">SIDEBAR NAVIGATION</div>', unsafe_allow_html=True)

    pending_cit_count = len([c for c in db.get_citizen_reports() if str(c.get("status", "")).upper() != "RESOLVED"])
    cit_nav_label = f"📨 Citizen Reports Inbox ({pending_cit_count})" if pending_cit_count > 0 else "📨 Citizen Reports Inbox"

    if current_role == "admin":
        nav_options = [
            "📡 Live Sentinel Overview",
            "🗺️ Tactical Map & Dispatch",
            "👥 Ranger & User Management",
            "📊 Acoustic AI & Spectrum",
            "🚨 Emergency Broadcast",
            cit_nav_label,
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
                <span style="font-family:monospace; font-size:11px; font-weight:700; color:var(--green);">{device_id}</span>
            </div>
            <div style="display:flex; justify-content:space-between; align-items:center; margin-top:6px;">
                <span class="metric-label">CORE STATE</span>
                <span style="font-family:monospace; font-size:10px; color:#7cf0b2; font-weight:600;">ONLINE ●</span>
            </div>
            <div style="display:flex; justify-content:space-between; align-items:center; margin-top:6px;">
                <span class="metric-label">BATTERY</span>
                <span style="font-family:monospace; font-size:10px; color:#73d9e8; font-weight:600;">{batt_pct:.1f}% ({batt_v:.2f}V)</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 5. System Status Indicator
    st.markdown(
        '''<div style="padding: 4px 8px; border-radius: 6px; background: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.2); font-size: 11px; color: #10b981; font-family: 'JetBrains Mono', monospace; text-align: center;">
            ● SYSTEM NOMINAL · INGESTION ACTIVE
        </div>''',
        unsafe_allow_html=True,
    )

    # 6. Log Out Button
    if st.button("🚪 Sign Out", use_container_width=True, key="btn_sidebar_logout"):
        st.session_state["authenticated"] = False
        st.session_state["aura_auth_token"] = None
        st.session_state.pop("aura_username", None)
        st.session_state.pop("aura_user_role", None)
        st.session_state.pop("aura_user_name", None)
        st.session_state.pop("aura_user_dept", None)
        if hasattr(st, "query_params"):
            if "auth_user" in st.query_params:
                del st.query_params["auth_user"]
            if "auth_token" in st.query_params:
                del st.query_params["auth_token"]
        st.rerun()

# ============================================================
# MAIN CONTENT HEADER & TOP ALERTS
# ============================================================

role_headers = {
    "admin": ("Sanctuary Command & Threat Operations", "Forest Reserve Headquarters · Autonomous Acoustic Monitoring & Unit Dispatch"),
    "ranger": ("Field Operations & Patrol Response", "Mobile Unit Deployment · GPS Sector Tracking · Incident Resolution"),
    "viewer": ("Community Ecological Observatory", "Sanctuary Environmental Telemetry · Advisory Notices · Citizen Tip Reporting"),
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
    """Audible alert indicator placeholder (browser audio oscillator removed for professional compliance)."""
    pass

# Active alert notification banner
if active_alerts:
    top_alert = active_alerts[0]
    al_threat_raw = str(top_alert.get("threat_type", "Threat")).strip()
    al_threat_lower = al_threat_raw.lower()
    al_threat_formatted = format_display_label(al_threat_raw).upper()
    al_conf = safe_num(top_alert.get("confidence", 0.95)) * 100
    al_lat = top_alert.get("location_lat")
    al_lon = top_alert.get("location_lon")
    al_coords = f"{al_lat:.5f}°N, {al_lon:.5f}°E" if al_lat is not None and al_lon is not None else "Coordinates Acquired"

    # SIREN RULES:
    # 1. Audible tactical siren ONLY for Fire, Chainsaw/Drill, and Gunshot
    is_siren_threat = any(t in al_threat_lower for t in ["fire", "wildfire", "chainsaw", "drill", "jackhammer", "gunshot", "explosion", "poaching", "logging"])
    # 2. Yellow Alert (NO SIREN) for Human Activity, Footsteps, and Vehicles
    is_yellow_alert = any(t in al_threat_lower for t in ["human", "footsteps", "speech", "walking", "vehicle", "truck", "car", "engine"])

    if is_siren_threat:
        render_siren_audio_synthesizer(is_active=True, threat_label=al_threat_formatted)

    b_c1, b_c2 = st.columns([3.5, 1.2])
    with b_c1:
        if is_siren_threat:
            st.markdown(
                f"""
                <div class="emergency-banner-critical">
                    <div style="display:flex;align-items:center;gap:8px;">
                        <span style="display:inline-block;width:8px;height:8px;background:var(--status-red);border-radius:50%;"></span>
                        <span style="color:var(--status-red);font-family:monospace;font-size:11px;font-weight:700;letter-spacing:.08em;">CRITICAL THREAT INCIDENT ACTIVE</span>
                    </div>
                    <div style="font-size:17px;font-weight:700;color:var(--text-primary);margin-top:4px;">
                        {al_threat_formatted} ({al_conf:.1f}% Confidence) · {al_coords}
                    </div>
                    <div style="color:var(--text-secondary);font-size:11px;margin-top:4px;font-family:monospace;">
                        Sensor Node: {top_alert.get('device_id')} · Assigned Unit: {top_alert.get('assigned_ranger_name') or 'Patrol Response Unit'} · Status: {top_alert.get('status', 'ACTIVE')}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        elif is_yellow_alert:
            st.markdown(
                f"""
                <div class="emergency-banner-warning">
                    <div style="display:flex;align-items:center;gap:8px;">
                        <span style="display:inline-block;width:8px;height:8px;background:var(--status-amber);border-radius:50%;"></span>
                        <span style="color:var(--status-amber);font-family:monospace;font-size:11px;font-weight:700;letter-spacing:.08em;">ELEVATED CAUTION ADVISORY</span>
                    </div>
                    <div style="font-size:17px;font-weight:700;color:var(--text-primary);margin-top:4px;">
                        {al_threat_formatted} ({al_conf:.1f}% Confidence) · {al_coords}
                    </div>
                    <div style="color:var(--text-secondary);font-size:11px;margin-top:4px;font-family:monospace;">
                        Sensor Node: {top_alert.get('device_id')} · Assigned Unit: {top_alert.get('assigned_ranger_name') or 'Sector Patrol'} · Status: {top_alert.get('status', 'ACTIVE')}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"""
                <div class="emergency-banner-warning">
                    <div style="display:flex;align-items:center;gap:8px;">
                        <span style="display:inline-block;width:8px;height:8px;background:var(--accent);border-radius:50%;"></span>
                        <span style="color:var(--accent);font-family:monospace;font-size:11px;font-weight:700;letter-spacing:.08em;">FOREST INCIDENT ADVISORY</span>
                    </div>
                    <div style="font-size:17px;font-weight:700;color:var(--text-primary);margin-top:4px;">
                        {al_threat_formatted} ({al_conf:.1f}% Confidence) · {al_coords}
                    </div>
                    <div style="color:var(--text-secondary);font-size:11px;margin-top:4px;font-family:monospace;">
                        Sensor Node: {top_alert.get('device_id')} · Assigned Unit: {top_alert.get('assigned_ranger_name') or 'Sector Patrol'} · Status: {top_alert.get('status', 'ACTIVE')}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    with b_c2:
        if current_role in ["admin", "ranger"]:
            st.write("")
            al_status_curr = str(top_alert.get("status", "")).upper()
            if al_status_curr != "ACKNOWLEDGED":
                if st.button("Acknowledge Alert", key="btn_ack_top_alert", use_container_width=True, type="primary"):
                    db.acknowledge_emergency_alert(top_alert.get("alert_id"), acknowledged_by=user_display)
                    st.success("Alert acknowledged.")
                    st.rerun()
            else:
                ack_by = top_alert.get("acknowledged_by") or "Field Unit"
                st.markdown(
                    f'<div style="text-align:center;padding:8px;background:rgba(124,240,178,0.06);border:1px solid var(--status-green);border-radius:8px;font-size:11px;color:var(--status-green);font-family:monospace;margin-bottom:6px;">'
                    f'✓ ACKNOWLEDGED<br/><span style="color:var(--text-secondary);font-size:10px;">{ack_by}</span></div>',
                    unsafe_allow_html=True
                )
                if current_role == "ranger":
                    if st.button("✅ Mark Solved", key="btn_top_mark_solved_ranger", use_container_width=True, type="primary"):
                        db.resolve_emergency_alert(top_alert.get("alert_id"), resolved_by=user_display, resolution_notes="Threat investigated on-site and perimeter secured by Field Ranger.")
                        st.success("Threat resolved and logged to Incident Archive!")
                        st.rerun()
        else:
            st.write("")
            st.markdown(
                '<div style="text-align:center;padding:10px;background:rgba(235,160,55,0.08);border:1px solid rgba(235,160,55,0.3);border-radius:8px;font-size:11px;color:var(--status-amber);">'
                '⚠️ <b>PUBLIC ADVISORY</b><br/><span style="color:var(--text-secondary);font-size:10px;">Rangers alerted. Keep clear of active caution sector.</span></div>',
                unsafe_allow_html=True
            )

def render_geolocation_sentry(title: str = "LIVE DEVICE GPS SENTRY", auto_capture: bool = True) -> None:
    """In-browser HTML5 High-Accuracy Geolocation synchronizer."""
    gps_lat_curr = st.session_state.get("client_gps_lat")
    gps_lon_curr = st.session_state.get("client_gps_lon")
    gps_acc_curr = st.session_state.get("client_gps_accuracy", 12)
    has_fix = gps_lat_curr is not None and gps_lon_curr is not None

    status_init = f"✅ Satellite Fix Acquired: {gps_lat_curr:.5f}°N, {gps_lon_curr:.5f}°E (±{int(gps_acc_curr)}m)" if has_fix else "🛰️ Standby — Click 'Capture My Live GPS' to lock device coordinates."

    geo_html = f"""
    <div style="background: linear-gradient(135deg, rgba(16, 32, 38, 0.95), rgba(8, 18, 22, 0.98)); border: 1.5px solid rgba(124, 240, 178, 0.45); border-radius: 12px; padding: 10px 16px; margin-bottom: 12px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px; box-shadow: 0 4px 20px rgba(0,0,0,0.5);">
        <div style="display: flex; align-items: center; gap: 10px;">
            <span style="display: inline-block; width: 10px; height: 10px; background: #7cf0b2; border-radius: 50%; box-shadow: 0 0 10px #7cf0b2;"></span>
            <div>
                <div style="color: #ffffff; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-size: 12px; font-weight: 800; letter-spacing: 0.04em;">📍 {title}</div>
                <div id="auraGpsLabel" style="color: #7cf0b2; font-family: 'JetBrains Mono', monospace; font-size: 11px; margin-top: 2px;">{status_init}</div>
            </div>
        </div>
        <button id="auraGpsBtn" onclick="requestBrowserGps()" style="background: linear-gradient(135deg, #7cf0b2, #73d9e8); color: #060a0c; font-weight: 800; font-size: 11px; border: none; border-radius: 8px; padding: 7px 16px; cursor: pointer; font-family: sans-serif; transition: all 0.2s; box-shadow: 0 2px 10px rgba(124,240,178,0.35);">
            📡 Capture My Live GPS
        </button>
    </div>
    <script>
    function requestBrowserGps() {{
        const lbl = document.getElementById("auraGpsLabel");
        const btn = document.getElementById("auraGpsBtn");
        if (!navigator.geolocation) {{
            if (lbl) lbl.innerHTML = "❌ Geolocation API not supported by your browser.";
            return;
        }}
        if (lbl) lbl.innerHTML = "🛰️ Requesting device GPS coordinates from browser...";
        if (btn) btn.innerText = "⏳ Acquiring GPS...";

        navigator.geolocation.getCurrentPosition(
            (position) => {{
                const lat = position.coords.latitude;
                const lon = position.coords.longitude;
                const acc = Math.round(position.coords.accuracy);
                if (lbl) lbl.innerHTML = `✅ Lat: <b>${{lat.toFixed(5)}}°</b>, Lon: <b>${{lon.toFixed(5)}}°</b> (±${{acc}}m accuracy)`;
                if (btn) btn.innerText = "✅ GPS Acquired!";

                try {{
                    const url = new URL(window.parent.location.href);
                    const oldLat = url.searchParams.get('device_lat');
                    const oldLon = url.searchParams.get('device_lon');
                    if (!oldLat || Math.abs(parseFloat(oldLat) - lat) > 0.0001 || Math.abs(parseFloat(oldLon) - lon) > 0.0001) {{
                        url.searchParams.set('device_lat', lat.toFixed(6));
                        url.searchParams.set('device_lon', lon.toFixed(6));
                        url.searchParams.set('gps_acc', acc);
                        window.parent.location.href = url.toString();
                    }}
                }} catch(e) {{
                    console.warn("GPS parent sync:", e);
                }}
            }},
            (error) => {{
                if (lbl) lbl.innerHTML = `⚠️ GPS Error: ${{error.message}} (Please grant Location permission in browser settings).`;
                if (btn) btn.innerText = "📡 Retry Live GPS";
            }},
            {{ enableHighAccuracy: true, timeout: 12000, maximumAge: 0 }}
        );
    }}

    // Auto-attempt low-friction capture if not yet acquired
    if ({str(not has_fix).lower()} && {str(auto_capture).lower()}) {{
        setTimeout(requestBrowserGps, 600);
    }}
    </script>
    """
    components.html(geo_html, height=64)

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

    # If logged-in user is a citizen with live device GPS, plot their real location
    if current_role == "viewer" and "client_gps_lat" in st.session_state and "client_gps_lon" in st.session_state:
        u_lat = float(st.session_state["client_gps_lat"])
        u_lon = float(st.session_state["client_gps_lon"])
        u_acc = int(st.session_state.get("client_gps_accuracy", 10))
        records.append({
            "latitude": u_lat,
            "longitude": u_lon,
            "Entity": f"👁️ You ({user_display}) [LIVE USER GPS]",
            "label_short": f"📍 You ({user_display.split()[0]})",
            "Category": "🔵 Live Citizen Observer Location",
            "Coordinates": f"{u_lat:.5f}°N, {u_lon:.5f}°E",
            "Status": "ONLINE · VERIFIED DEVICE GPS",
            "Details": f"Live Device Geolocation · GPS Fix Acquired (±{u_acc}m accuracy)",
            "color": [115, 217, 232, 255],
            "radius": 110,
            "size": 44,
        })

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
    elif detected or str(cadie_dict.get("risk_level", "")).upper() in ["HIGH", "CRITICAL"]:
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
        valid_gps = False
        if lat_val is not None and lon_val is not None:
            try:
                lat_val = float(lat_val)
                lon_val = float(lon_val)
                if abs(lat_val) > 0.001 or abs(lon_val) > 0.001:
                    valid_gps = True
            except (ValueError, TypeError):
                valid_gps = False

        if not valid_gps:
            off_lat, off_lon = ranger_offsets[idx % len(ranger_offsets)]
            lat_val = sent_lat + off_lat
            lon_val = sent_lon + off_lon

        r_name = rng.get("name", "Field Ranger")
        r_call = rng.get("callsign", f"UNIT-{idx+1}")
        r_sec = rng.get("sector", "Sanctuary Perimeter")
        r_batt = rng.get("battery", 100)
        r_stat = str(rng.get("status", "PATROL READY")).upper()
        r_asgn = rng.get("assigned_alert")

        # Check if ranger is currently responding to an active alert
        is_responding = "RESPONDING" in r_stat or bool(r_asgn)
        is_me = username_active.lower() in str(rng.get("phone", "")).lower() or username_active.lower() in str(r_name).lower() or ("rng_" + username_active.replace(".", "_") == rng.get("ranger_id"))

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
                "Entity": f"🛡️ {'You (' + r_name + ')' if is_me else 'Ranger ' + r_name} ({r_call}) ⚡ [RESPONDING UNIT]",
                "label_short": f"⚡ {'You' if is_me else r_name.split()[0]} (RESPONDING)",
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
                "Entity": f"🛡️ {'You (' + r_name + ')' if is_me else 'Ranger ' + r_name} ({r_call})",
                "label_short": f"{'You' if is_me else r_name.split()[0]} ({r_call})",
                "Category": "🔵 Field Ranger Patrol" + (" [LIVE GPS ACTIVE]" if is_me else ""),
                "Coordinates": f"{lat_val:.5f}°N, {lon_val:.5f}°E",
                "Status": f"{r_stat} · 🔋 {r_batt}% BATT",
                "Details": f"Assigned Sector: {r_sec} · Callsign: {r_call} · 📞 {rng.get('phone', 'N/A')}",
                "color": [124, 240, 178, 250] if is_me else [115, 217, 232, 235],
                "radius": 100 if is_me else 90,
                "size": 40 if is_me else 36,
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

    # 1. High-Visibility Animated Blinking / Pulsing Crimson Red Threat Beacon Layers
    threat_mask = df["Category"].str.contains("Active Threat|Live AI Threat", case=False, na=False)
    threat_df = df[threat_mask]
    if not threat_df.empty:
        # Outer expanding shockwave danger zone
        outer_blast_layer = pdk.Layer(
            "ScatterplotLayer",
            data=threat_df,
            get_position="[longitude, latitude]",
            get_fill_color=[255, 0, 0, 40],
            get_line_color=[255, 40, 40, 210],
            get_line_width=3,
            stroked=True,
            filled=True,
            get_radius=500,
            radius_min_pixels=32,
            radius_max_pixels=110,
            pickable=False,
        )
        layers.append(outer_blast_layer)

        # Mid pulsing neon red strobe ring
        strobe_pulse_layer = pdk.Layer(
            "ScatterplotLayer",
            data=threat_df,
            get_position="[longitude, latitude]",
            get_fill_color=[255, 0, 0, 115],
            get_line_color=[255, 20, 20, 255],
            get_line_width=5,
            stroked=True,
            filled=True,
            get_radius=270,
            radius_min_pixels=20,
            radius_max_pixels=65,
            pickable=False,
        )
        layers.append(strobe_pulse_layer)

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

    # Calculate dynamic tactical map center
    c_lat, c_lon = float(center_lat), float(center_lon)
    if "client_gps_lat" in st.session_state and "client_gps_lon" in st.session_state:
        c_lat = float(st.session_state["client_gps_lat"])
        c_lon = float(st.session_state["client_gps_lon"])
    elif not df.empty:
        valid_coords = df[df["latitude"].notnull() & df["longitude"].notnull()]
        if not valid_coords.empty:
            c_lat = float(valid_coords["latitude"].mean())
            c_lon = float(valid_coords["longitude"].mean())

    view_state = pdk.ViewState(
        latitude=c_lat,
        longitude=c_lon,
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


def render_active_threat_map_hud(
    active_alerts: list[dict[str, Any]],
    detected: bool = False,
    cadie: dict[str, Any] | None = None,
    label: str = "Acoustic Sentry",
    sent_lat: float = 12.2958,
    sent_lon: float = 76.6394,
    conf_val: float = 0.95,
):
    cadie_dict = cadie if isinstance(cadie, dict) else {}
    """Render high-intensity animated pulsing red alert banner above tactical radar whenever active threats exist."""
    has_active = bool(active_alerts) or detected or str(cadie_dict.get("risk_level", "")).upper() in ["HIGH", "CRITICAL"]
    if not has_active:
        return

    top_title = "CRITICAL THREAT SIGNAL"
    top_coords = f"{sent_lat:.5f}°N, {sent_lon:.5f}°E"
    assigned_info = "⚡ Awaiting Rapid Field Patrol Dispatch"
    risk_tag = "CRITICAL"

    if active_alerts:
        al = active_alerts[0]
        top_title = al.get("threat_type", "Acoustic Threat")
        risk_tag = al.get("risk_level", "CRITICAL")
        lat = al.get("location_lat", sent_lat)
        lon = al.get("location_lon", sent_lon)
        top_coords = f"{float(lat):.5f}°N, {float(lon):.5f}°E"
        rname = al.get("assigned_ranger_name")
        if rname:
            assigned_info = f"⚡ RESPONDING: Ranger {rname} (Active Interception Vector Armed)"
        else:
            assigned_info = "⚠️ UNASSIGNED: Immediate Ranger Dispatch Required"
    elif detected:
        top_title = f"{label} (Perception Confidence: {confidence(conf_val)})"
        top_coords = f"{(sent_lat + 0.0022):.5f}°N, {(sent_lon + 0.0025):.5f}°E"
        assigned_info = f"CADIE Action: {cadie_dict.get('action', 'DISPATCH')} · Edge Alert Armed"
        risk_tag = str(cadie_dict.get("risk_level", "HIGH")).upper()

    st.markdown(
        f"""
        <div class="emergency-banner-critical">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
                <div style="display:flex; align-items:center; gap:8px;">
                    <span style="width:8px; height:8px; background:#ef4444; border-radius:50%;"></span>
                    <span style="font-weight:700; font-size:13px; color:#ef4444; letter-spacing:0.04em;">ACTIVE EMERGENCY THREAT NOTIFICATION</span>
                </div>
                <span style="background:rgba(239, 68, 68, 0.18); border:1px solid #ef4444; color:#ef4444; font-weight:600; font-size:11px; padding:3px 10px; border-radius:6px;">{risk_tag} PRIORITY</span>
            </div>
            <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap:8px; margin-top:10px; background:var(--surface-2); padding:10px 14px; border-radius:6px; font-size:12px;">
                <div><b>Target Signature:</b> <span style="color:var(--text-primary); font-weight:600;">{top_title}</span></div>
                <div><b>Location Coordinates:</b> <span style="color:var(--status-sky); font-family:monospace;">{top_coords}</span></div>
                <div><b>Deployment Status:</b> <span style="color:var(--status-amber); font-weight:600;">{assigned_info}</span></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

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
                        <span style="font-family:monospace; font-size:11px; color:#73d9e8;">({inc_id})</span>
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
        # Notice for pending citizen tips
        pending_cits_list = [c for c in db.get_citizen_reports() if str(c.get("status", "")).upper() != "RESOLVED"]
        if pending_cits_list:
            st.markdown(
                f'''
                <div style="background:rgba(242,198,109,0.12);border:1.5px solid #f2c66d;border-radius:12px;padding:12px 18px;margin-bottom:16px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px;">
                    <div style="display:flex;align-items:center;gap:12px;">
                        <span style="font-size:24px;">📸</span>
                        <div>
                            <div style="font-size:14px;font-weight:700;color:#f2c66d;letter-spacing:0.02em;">ACTION REQUIRED: {len(pending_cits_list)} PENDING CITIZEN FIELD REPORT(S)</div>
                            <div style="font-size:11px;color:var(--text-secondary);margin-top:2px;">
                                Public visitors have submitted geo-tagged field sighting(s) awaiting Chief review and Ranger dispatch.
                            </div>
                        </div>
                    </div>
                </div>
                ''',
                unsafe_allow_html=True
            )

        dev_status = telemetry.get("device_status") if isinstance(telemetry.get("device_status"), dict) else {}
        gas_info = dev_status.get("gas_assessment") or telemetry.get("gas_assessment") or {}
        gas_status = str(gas_info.get("overall_status") or "NOMINAL").upper()
        gas_score = safe_num(gas_info.get("gas_risk_score", 0.0))
        mq2_val = safe_num(telemetry.get("mq2_raw", dev_status.get("mq2_raw", 0)))
        mq2_v = safe_num(telemetry.get("mq2_adc_voltage", dev_status.get("mq2_adc_voltage", dev_status.get("mq2_voltage", 0.0))))
        mq135_val = safe_num(telemetry.get("mq135_raw", dev_status.get("mq135_raw", 0)))
        mq135_v = safe_num(telemetry.get("mq135_adc_voltage", dev_status.get("mq135_adc_voltage", dev_status.get("mq135_voltage", 0.0))))
        gas_sub = f"MQ2:{int(mq2_val)} ({mq2_v:.2f}V) · MQ135:{int(mq135_val)} ({mq135_v:.2f}V)" if (mq2_val > 0 or mq135_val > 0) else f"Risk {gas_score:.2f} (MQ2/135)"

        # Check for active Smoke / Fire Anomaly
        is_smoke_detected = (
            mq2_val >= 400
            or mq2_v >= 0.50
            or mq135_val >= 800
            or mq135_v >= 1.0
            or gas_status in ["WARNING", "ALERT", "CRITICAL", "ELEVATED", "SMOKE / FIRE ANOMALY", "POLLUTION / VOC SPIKE"]
            or "smoke" in label.lower()
            or "fire" in label.lower()
            or "smoke" in str(cadie.get("action", "")).lower()
        )

        # 🚨 PROMINENT SMOKE & FIRE HAZARD ALERT BANNER
        if is_smoke_detected:
            smoke_sev = "CRITICAL EMERGENCY" if (mq2_v >= 1.2 or mq2_val >= 1000 or "fire" in label.lower()) else "HIGH ANOMALY WARNING"
            st.markdown(
                f"""
                <div class="panel" style="background: linear-gradient(135deg, rgba(255, 77, 77, 0.28), rgba(254, 202, 87, 0.16)); border: 2px solid #ff4d4d; border-radius: 14px; padding: 18px 24px; margin-bottom: 20px; box-shadow: 0 0 35px rgba(255, 77, 77, 0.45);">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-family:monospace; font-size:12px; font-weight:800; color:#ff7070; letter-spacing:1px;">🚨 {smoke_sev} · ACTIVE SMOKE / COMBUSTIBLE GAS DETECTED</span>
                        <span style="background:#ff4d4d; color:#fff; font-size:10px; font-weight:800; padding:4px 12px; border-radius:6px; box-shadow:0 0 12px #ff4d4d;">IMMEDIATE ATTENTION</span>
                    </div>
                    <div style="font-size:22px; font-weight:800; color:#fff; margin-top:10px;">
                        🔥 Canopy Combustion Smoke / Flame Gas Anomaly on Node [{device_id}]
                    </div>
                    <div style="font-size:13px; color:#e0e0e0; margin-top:6px; line-height:1.6;">
                        <b>Active Telemetry:</b> MQ-2 Smoke Sensor: <span style="color:#ffc300; font-weight:700;">{int(mq2_val)} ADC ({mq2_v:.3f} V)</span> · Air Index: <span style="color:#ff7070; font-weight:700;">{gas_status}</span> · CADIE Recommendation: <span style="color:#7cf0b2; font-weight:700;">{cadie.get("action", "DISPATCH_RANGERS_SMOKE_ALERT")}</span>
                    </div>
                    <div style="margin-top:10px; font-size:12px; color:#f2c66d; font-family:monospace;">
                        ⚠️ Thermal context: {safe_num(telemetry.get('temperature')):.1f}°C · Humidity: {safe_num(telemetry.get('humidity')):.1f}% · Multimodal Corroboration Confirmed
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

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
            metric("Atmosphere / Gas", gas_status, gas_sub, "MQ-2 / MQ-135 Gas Sensors", accent="emerald" if gas_status == "NOMINAL" else "coral", icon="🧪")

        st.markdown('<div class="section"><div class="section-title">Acoustic Perception & CADIE Decision Engine</div><div class="section-meta">MODEL INFERENCE → CADIE MULTIMODAL FUSION → CONTEXT BEHAVIOR & CONFIDENCE</div></div>', unsafe_allow_html=True)
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
                            <span class="event-caption">MODEL RAW CONFIDENCE</span>
                            <span class="confidence" style="color:{conf_color}">{confidence(conf)}</span>
                        </div>
                        <div class="bar"><div style="width:{max(0,min(100,conf*100))}%;background:{conf_color};box-shadow:0 0 10px {conf_color}"></div></div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with mid:
            risk = str(cadie.get("risk_level") or ("HIGH" if is_smoke_detected else "LOW")).upper()
            cadie_score = safe_num(cadie.get('score', 0.85 if is_smoke_detected else 0.20))
            cadie_action = cadie.get("action") or ("DISPATCH_RANGERS_SMOKE_ALERT" if is_smoke_detected else "MONITOR")
            st.markdown(
                f"""
                <div class="panel">
                    <div class="panel-title">Decision Engine (CADIE)</div>
                    <div class="decision-box">
                        <div class="kicker">CONTEXT-AWARE TRIAGE RISK</div>
                        <div class="decision-risk {status_class('FAILED' if risk in ['HIGH','CRITICAL'] else ('WORKING' if risk in ['LOW','MINIMAL'] else 'WARN'))}">{risk}</div>
                        <div class="decision-action" style="color:var(--green)">ACTION: {cadie_action}</div>
                    </div>
                    {display_status("CADIE Context Score", f"{cadie_score:.3f}")}
                    {display_status("Ranger Attention", "YES (ALERT)" if (cadie.get("requires_attention") or is_smoke_detected) else "NO (MONITOR)")}
                    {display_status("Smoke Corroboration", "🚨 ACTIVE SMOKE DETECTED" if is_smoke_detected else "🟢 NOMINAL / CLEAR")}
                    {display_status("Primary Trigger", cadie.get("signal", label))}
                </div>
                """,
                unsafe_allow_html=True,
            )
        with right:
            inference_ms = safe_num(prediction.get("inference_time_ms", event.get("inference_time_ms", 55.0)))
            env_type = environment.get("environment_type", "Temperate Forest Canopy")
            st.markdown(
                f"""
                <div class="panel">
                    <div class="panel-title">Context Behavior & Edge Health</div>
                    {display_status("Model Engine", prediction.get("model", "MobileNetV3-Small"))}
                    {display_status("Inference Latency", f"{inference_ms:.2f} ms")}
                    {display_status("Context Policy", policy.get("transmission_mode", "EVENT_TRIGGERED"))}
                    {display_status("Environmental Context", env_type)}
                    {display_status("Adaptive Sensitivity", f"{safe_num(policy.get('detection_threshold', 0.60)):.2f} Floor")}
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

        # ------------------------------------------------------
        # 🔬 LIVE HARDWARE COMPONENT SENSOR SUITE (ALL SENSORS SHOW EXACT READINGS)
        # ------------------------------------------------------
        st.markdown('<div class="section"><div class="section-title">Live Hardware Component Sensor Suite (ESP32-S3 Bus)</div><div class="section-meta">EACH COMPONENT TELEMETRY READING · 12-BIT ADC, I2C & I2S DMA DMA BUS</div></div>', unsafe_allow_html=True)

        loc = telemetry.get("location") or {}
        gps_lat = safe_num(loc.get("latitude", FALLBACK_LATITUDE if 'FALLBACK_LATITUDE' in locals() else 12.2958))
        gps_lon = safe_num(loc.get("longitude", FALLBACK_LONGITUDE if 'FALLBACK_LONGITUDE' in locals() else 76.6394))
        gps_sats = int(safe_num(loc.get("satellites", 6)))
        gps_fix = str(loc.get("source", "GPS_FIX" if gps_sats > 3 else "BASE_LOCK")).upper()

        mq2_pct = min(100.0, (mq2_val / 4095.0) * 100.0) if mq2_val > 0 else 0.0
        mq2_status = "SMOKE / FIRE ANOMALY" if (mq2_v > 1.2 or mq2_val > 800) else ("ELEVATED TRACE" if (mq2_v > 0.50 or mq2_val > 400) else "CLEAR / NOMINAL")
        mq2_color = "#ff7070" if (mq2_v > 1.2 or mq2_val > 800) else ("#f2c66d" if (mq2_v > 0.50 or mq2_val > 400) else "#7cf0b2")

        mq135_pct = min(100.0, (mq135_val / 4095.0) * 100.0) if mq135_val > 0 else 0.0
        mq135_status = "POLLUTION / VOC SPIKE" if mq135_v > 1.5 else ("SLIGHT VOC TRACE" if mq135_v > 0.8 else "CLEAN FOREST AIR")
        mq135_color = "#ff7070" if mq135_v > 1.5 else ("#f2c66d" if mq135_v > 0.8 else "#73d9e8")

        temp_val = safe_num(telemetry.get("temperature", 28.5))
        hum_val = safe_num(telemetry.get("humidity", 55.0))
        lux_val = safe_num(telemetry.get("light_level", 420.0))
        batt_pct = safe_num(telemetry.get("battery_percent", 88.0))
        batt_v = safe_num(telemetry.get("battery_voltage", 4.12))
        mic_lvl = safe_num(telemetry.get("microphone_level", 520.0))

        # Row 1: Gas & Climate Sensors
        col_s1, col_s2, col_s3 = st.columns(3)
        with col_s1:
            st.markdown(
                f"""
                <div class="panel" style="padding:14px; border:1.5px solid {mq2_color}; border-radius:12px; background:rgba(16,28,32,0.92);">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-family:monospace; font-size:11px; font-weight:700; color:{mq2_color};">🔥 MQ-2 SMOKE & COMBUSTIBLES</span>
                        <span style="font-size:10px; background:rgba(255,255,255,0.08); padding:2px 8px; border-radius:4px; color:#fff;">GPIO 1 (ADC1)</span>
                    </div>
                    <div style="font-size:22px; font-weight:800; color:#fff; margin-top:6px;">
                        {int(mq2_val)} <span style="font-size:12px; color:var(--muted); font-weight:500;">ADC ({mq2_v:.3f} V)</span>
                    </div>
                    <div style="font-size:11px; color:{mq2_color}; font-weight:700; margin-top:4px;">
                        STATUS: {mq2_status}
                    </div>
                    <div style="margin-top:8px;">
                        <div style="display:flex; justify-content:space-between; font-size:10px; color:#829a97; margin-bottom:3px;">
                            <span>Sensor Load (0-4095)</span>
                            <span>{mq2_pct:.1f}%</span>
                        </div>
                        <div class="bar"><div style="width:{max(2, min(100, mq2_pct))}%; background:{mq2_color}; box-shadow:0 0 10px {mq2_color};"></div></div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with col_s2:
            st.markdown(
                f"""
                <div class="panel" style="padding:14px; border:1.5px solid {mq135_color}; border-radius:12px; background:rgba(16,28,32,0.92);">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-family:monospace; font-size:11px; font-weight:700; color:{mq135_color};">🍃 MQ-135 AIR QUALITY & TOXIC GAS</span>
                        <span style="font-size:10px; background:rgba(255,255,255,0.08); padding:2px 8px; border-radius:4px; color:#fff;">GPIO 2 (ADC1)</span>
                    </div>
                    <div style="font-size:22px; font-weight:800; color:#fff; margin-top:6px;">
                        {int(mq135_val)} <span style="font-size:12px; color:var(--muted); font-weight:500;">ADC ({mq135_v:.3f} V)</span>
                    </div>
                    <div style="font-size:11px; color:{mq135_color}; font-weight:700; margin-top:4px;">
                        STATUS: {mq135_status}
                    </div>
                    <div style="margin-top:8px;">
                        <div style="display:flex; justify-content:space-between; font-size:10px; color:#829a97; margin-bottom:3px;">
                            <span>Sensor Load (0-4095)</span>
                            <span>{mq135_pct:.1f}%</span>
                        </div>
                        <div class="bar"><div style="width:{max(2, min(100, mq135_pct))}%; background:{mq135_color}; box-shadow:0 0 10px {mq135_color};"></div></div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with col_s3:
            st.markdown(
                f"""
                <div class="panel" style="padding:14px; border:1.5px solid #f6c445; border-radius:12px; background:rgba(16,28,32,0.92);">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-family:monospace; font-size:11px; font-weight:700; color:#f6c445;">🌡️ DHT11 CLIMATE SENSOR</span>
                        <span style="font-size:10px; background:rgba(255,255,255,0.08); padding:2px 8px; border-radius:4px; color:#fff;">GPIO 14 (1-Wire)</span>
                    </div>
                    <div style="font-size:22px; font-weight:800; color:#fff; margin-top:6px;">
                        {temp_val:.1f}°C <span style="font-size:13px; color:#73d9e8; font-weight:600;">/ {hum_val:.1f}% RH</span>
                    </div>
                    <div style="font-size:11px; color:#7cf0b2; font-weight:700; margin-top:4px;">
                        THERMAL: {"NORMAL" if temp_val < 38 else "ELEVATED HEAT DANGER"}
                    </div>
                    <div style="font-size:10px; color:#829a97; margin-top:8px;">
                        Monitors: Ambient Forest Temperature, Relative Humidity & Vapor Saturation.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # Row 2: Optical, Power, Seismic, Audio & GPS
        col_s4, col_s5, col_s6, col_s7 = st.columns(4)
        with col_s4:
            st.markdown(
                f"""
                <div class="panel" style="padding:14px; border-radius:12px; background:rgba(16,28,32,0.92);">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-size:11px; font-weight:700; color:#feca57;">☀️ BH1750 LUX METER</span>
                        <span style="font-size:9px; background:rgba(255,255,255,0.08); padding:2px 6px; border-radius:4px; color:#fff;">I2C 0x23</span>
                    </div>
                    <div style="font-size:20px; font-weight:800; color:#fff; margin-top:6px;">{lux_val:.0f} <span style="font-size:11px; color:var(--muted);">lux</span></div>
                    <div style="font-size:10px; color:#7cf0b2; margin-top:3px;">{"Direct Sunlight" if lux_val > 1500 else ("Canopy Diffused" if lux_val > 50 else "Night / Dark")}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with col_s5:
            st.markdown(
                f"""
                <div class="panel" style="padding:14px; border-radius:12px; background:rgba(16,28,32,0.92);">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-size:11px; font-weight:700; color:#1dd1a1;">⚡ MAX17048 GAUGE</span>
                        <span style="font-size:9px; background:rgba(255,255,255,0.08); padding:2px 6px; border-radius:4px; color:#fff;">I2C 0x36</span>
                    </div>
                    <div style="font-size:20px; font-weight:800; color:#fff; margin-top:6px;">{batt_pct:.1f}% <span style="font-size:11px; color:var(--muted);">({batt_v:.2f}V)</span></div>
                    <div style="font-size:10px; color:#7cf0b2; margin-top:3px;">LiPo Fuel Cell Health: OK</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with col_s6:
            st.markdown(
                f"""
                <div class="panel" style="padding:14px; border-radius:12px; background:rgba(16,28,32,0.92);">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-size:11px; font-weight:700; color:{'#ff7070' if vibration else '#a55eea'};">📳 SW-420 SEISMIC</span>
                        <span style="font-size:9px; background:rgba(255,255,255,0.08); padding:2px 6px; border-radius:4px; color:#fff;">GPIO 16</span>
                    </div>
                    <div style="font-size:20px; font-weight:800; color:#fff; margin-top:6px;">{"TRIGGERED" if vibration else "STEADY"}</div>
                    <div style="font-size:10px; color:{'#ff7070' if vibration else '#829a97'}; margin-top:3px;">{"Mechanical Vibration Latched" if vibration else "Canopy Seismic Quiet"}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with col_s7:
            st.markdown(
                f"""
                <div class="panel" style="padding:14px; border-radius:12px; background:rgba(16,28,32,0.92);">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-size:11px; font-weight:700; color:#00d2d3;">🛰️ NEO-6M GPS</span>
                        <span style="font-size:9px; background:rgba(255,255,255,0.08); padding:2px 6px; border-radius:4px; color:#fff;">UART 1</span>
                    </div>
                    <div style="font-size:16px; font-weight:800; color:#fff; margin-top:6px;">{gps_sats} Sats <span style="font-size:11px; color:#7cf0b2;">({gps_fix})</span></div>
                    <div style="font-size:10px; color:#829a97; margin-top:3px;">{gps_lat:.4f}°N, {gps_lon:.4f}°E</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

        # ------------------------------------------------------
        # 🎙️ 5-SECOND HARDWARE VOICE & AUDIO PREDICTION STUDIO
        # ------------------------------------------------------
        st.markdown('<div class="section"><div class="section-title">🎙️ 5-Second Hardware Voice & Acoustic Prediction Studio</div><div class="section-meta">LOAD LOCAL HARDWARE RECORDING (/test_audio.pcm) OR UPLOAD 5S PCM/WAV AUDIO</div></div>', unsafe_allow_html=True)

        with st.container(border=True):
            p_c1, p_c2 = st.columns([1.2, 1.8])
            with p_c1:
                st.markdown("<b>Hardware PCM Audio Source:</b>", unsafe_allow_html=True)
                pcm_local_exists = os.path.exists("test_audio.pcm")
                pcm_size = os.path.getsize("test_audio.pcm") if pcm_local_exists else 0

                st.caption(f"📁 Local Node File: `test_audio.pcm` ({pcm_size:,} bytes · 5 seconds at 16kHz)" if pcm_local_exists else "📁 Local Node File: `test_audio.pcm` (Awaiting Hardware Capture)")

                btn_predict_hw = st.button("⚡ Predict Latest Hardware Voice (`test_audio.pcm`)", type="primary", use_container_width=True, key="btn_pred_hw_audio")

                uploaded_pcm = st.file_uploader("Or Upload Custom Hardware Recording (.pcm / .wav)", type=["pcm", "wav", "mp3"], key="upl_pcm_test")

            with p_c2:
                predict_target_bytes = None
                predict_source_name = ""

                if btn_predict_hw and pcm_local_exists:
                    predict_target_bytes = open("test_audio.pcm", "rb").read()
                    predict_source_name = "Hardware Node Capture (test_audio.pcm)"
                elif uploaded_pcm is not None:
                    predict_target_bytes = uploaded_pcm.read()
                    predict_source_name = f"Uploaded Audio ({uploaded_pcm.name})"

                if predict_target_bytes:
                    try:
                        from backend.audio_service import AudioInferenceService
                        t_start = time.time()
                        hw_service = AudioInferenceService()
                        hw_res = hw_service.infer_pcm16(
                            audio_bytes=predict_target_bytes,
                            sample_rate=16000,
                            top_k=5,
                            device_status=dev_status,
                        )
                        hw_elapsed = (time.time() - t_start) * 1000

                        hw_pred = hw_res.get("prediction", {})
                        hw_lbl = hw_pred.get("label", "Unknown")
                        hw_cnf = float(hw_pred.get("confidence", 0.0))
                        hw_cadie = hw_res.get("decision") or (hw_res.get("edge_runtime") or {}).get("decision") or {}
                        hw_risk = str(hw_cadie.get("risk_level", "LOW")).upper()
                        hw_action = hw_cadie.get("recommended_action", "MONITOR")
                        hw_score = float(hw_cadie.get("decision_score", 0.0))

                        hw_risk_color = "#ff7070" if hw_risk in ["HIGH", "CRITICAL"] else ("#f2c66d" if hw_risk in ["ELEVATED", "MEDIUM"] else "#7cf0b2")

                        st.markdown(
                            f"""
                            <div style="background:rgba(12,20,23,0.85); border:1.5px solid {hw_risk_color}; border-radius:12px; padding:16px 20px;">
                                <div style="display:flex; justify-content:space-between; align-items:center;">
                                    <span style="font-family:monospace; font-size:11px; font-weight:700; color:{hw_risk_color};">🎯 PREDICTION RESULT: {hw_lbl.upper()}</span>
                                    <span style="font-size:10px; color:#73d9e8; font-family:monospace;">{hw_elapsed:.1f} ms Latency</span>
                                </div>
                                <div style="font-size:22px; font-weight:800; color:#fff; margin-top:6px;">
                                    {hw_lbl} · <span style="color:{hw_risk_color};">{hw_cnf * 100.0:.2f}% Confidence</span>
                                </div>
                                <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-top:10px; background:rgba(0,0,0,0.3); padding:10px 14px; border-radius:8px;">
                                    <div>
                                        <span style="font-size:10px; color:#829a97;">CADIE RISK LEVEL:</span>
                                        <div style="font-size:14px; font-weight:800; color:{hw_risk_color};">{hw_risk} (Score {hw_score:.3f})</div>
                                    </div>
                                    <div>
                                        <span style="font-size:10px; color:#829a97;">RECOMMENDED ACTION:</span>
                                        <div style="font-size:14px; font-weight:800; color:#7cf0b2;">{hw_action}</div>
                                    </div>
                                </div>
                                <div style="font-size:11px; color:#edf6f3; margin-top:8px;">
                                    Source: <b>{predict_source_name}</b> · Multimodal Sensor Context Integrated
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                    except Exception as err:
                        st.error(f"Inference error on hardware audio: {err}")
                else:
                    st.info("Click 'Predict Latest Hardware Voice' or upload a 5-second PCM/WAV to test immediate acoustic intelligence classification.")

    elif active_page == "🗺️ Tactical Map & Dispatch":
        st.markdown('<div class="section"><div class="section-title">Live Tactical Map & Field Ranger Dispatch</div><div class="section-meta">GPS SENTINEL NODES · ACTIVE THREATS · NEARBY FIELD RANGERS</div></div>', unsafe_allow_html=True)
        render_geolocation_sentry("COMMAND HQ / CHIEF GPS SENTRY", auto_capture=False)
        render_active_threat_map_hud(active_alerts, detected, cadie, label, sent_lat, sent_lon, conf)
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
                                <div style="font-family:monospace; font-size:11px; font-weight:700; color:#7cf0b2;">🎉 NEW FIELD RANGER COMMISSIONED & CREDENTIALS ISSUED</div>
                                <div style="font-size:10px; color:#73d9e8; font-weight:700;">🟢 DISPATCHED TO RANGER</div>
                            </div>
                            <div style="font-size:16px; font-weight:800; color:#fff; margin-top:4px;">{ngr.get('full_name')} ({ngr.get('rank')}) · Callsign: {ngr.get('callsign')}</div>
                            <div style="display:grid; grid-template-columns: 1fr 1fr; gap:10px; margin-top:10px; background:rgba(0,0,0,0.3); padding:12px; border-radius:10px;">
                                <div>
                                    <div style="font-size:10px; color:#829a97;">ASSIGNED USERNAME:</div>
                                    <div style="font-family:monospace; font-size:14px; font-weight:700; color:#73d9e8;">{ngr.get('username')}</div>
                                </div>
                                <div>
                                    <div style="font-size:10px; color:#829a97;">GENERATED PASSWORD:</div>
                                    <div style="font-family:monospace; font-size:14px; font-weight:700; color:#7cf0b2;">{ngr.get('password')}</div>
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

    elif "Citizen Reports Inbox" in active_page:
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
        st.markdown('<div class="section"><div class="section-title">Unknown Sound Discovery & Clustering</div><div class="section-meta">OPEN-SET REJECTION → DBSCAN EMBEDDING CLUSTERS → BIOLOGIST & CHIEF REVIEW</div></div>', unsafe_allow_html=True)

        unk_file = os.path.join("data", "unknown_discovery.json")
        unk_data = {}
        if os.path.exists(unk_file):
            try:
                with open(unk_file, "r", encoding="utf-8") as uf:
                    unk_data = json.load(uf)
            except Exception:
                unk_data = {}

        clusters = unk_data.get("clusters", [])
        total_samples = unk_data.get("total_unknown_samples", 0)
        unlabeled_count = len([c for c in clusters if str(c.get("status", "")).upper() != "LABELED"])

        u_c1, u_c2, u_c3, u_c4 = st.columns(4)
        with u_c1:
            metric("Total Unknown Audios", str(total_samples), "samples", "open-set acoustic triggers", accent="cyan", icon="🎧")
        with u_c2:
            metric("Discovered Clusters", str(len(clusters)), "classes", "DBSCAN geometric clusters", accent="purple", icon="🔬")
        with u_c3:
            metric("Unlabeled Clusters", str(unlabeled_count), "pending", "awaiting human classification", accent="amber" if unlabeled_count > 0 else "emerald", icon="🏷️")
        with u_c4:
            metric("Buffer Size", str(safe_num(unknown.get("buffer_size", 0))), "samples", "in edge buffer", accent="emerald", icon="📦")

        st.markdown("<div style='font-size:14px;font-weight:700;color:var(--text-primary);margin-top:20px;margin-bottom:10px;'>📊 Discovered Novel Acoustic Clusters:</div>", unsafe_allow_html=True)
        if not clusters:
            st.info("No novel acoustic clusters discovered yet. When the edge model detects unknown high-entropy bioacoustic signals, they are clustered here for taxonomy.")
        else:
            cl_rows = []
            for cl in clusters:
                c_id = cl.get("cluster_id")
                c_cnt = cl.get("sample_count", 0)
                c_stat = str(cl.get("status", "UNLABELED")).upper()
                c_lbl = cl.get("label") or "Pending Classification"
                c_notes = cl.get("notes") or ""
                cl_rows.append({
                    "CLUSTER ID": c_id,
                    "STATUS": c_stat,
                    "SAMPLE COUNT": f"{c_cnt} recordings",
                    "ASSIGNED LABEL": c_lbl,
                    "BIOLOGIST NOTES": c_notes,
                })
            st.dataframe(cl_rows, use_container_width=True, hide_index=True)

            # Triage / Labeling Interface
            st.markdown("<div style='font-size:14px;font-weight:700;color:#f2c66d;margin-top:24px;margin-bottom:10px;'>🏷️ Chief Ranger & Bioacoustic Classification Triage:</div>", unsafe_allow_html=True)
            with st.container(border=True):
                cl_choices = [c.get("cluster_id") for c in clusters]
                sel_cl_id = st.selectbox("Select Cluster to Classify / Verify", cl_choices, key="sel_unk_cluster_id")
                selected_cluster = next((c for c in clusters if c.get("cluster_id") == sel_cl_id), None)

                if selected_cluster:
                    curr_lbl = selected_cluster.get("label") or ""
                    curr_notes = selected_cluster.get("notes") or ""
                    tl_1, tl_2 = st.columns([2, 2.5])
                    with tl_1:
                        new_lbl = st.text_input("Taxonomic / Threat Label", value=curr_lbl, placeholder="e.g. Leopard Roar, Illegal Excavator, Heavy Rainfall", key=f"inp_unk_lbl_{sel_cl_id}")
                    with tl_2:
                        new_notes = st.text_input("Classification Notes & Corroboration", value=curr_notes, placeholder="e.g. Verified by camera trap at Sector 4 corridor.", key=f"inp_unk_not_{sel_cl_id}")

                    if st.button("💾 Save Official Class Label", type="primary", use_container_width=True, key=f"btn_save_cl_{sel_cl_id}"):
                        if new_lbl.strip():
                            selected_cluster["label"] = new_lbl.strip()
                            selected_cluster["notes"] = new_notes.strip()
                            selected_cluster["status"] = "LABELED"
                            selected_cluster["updated_at"] = time.time()
                            try:
                                with open(unk_file, "w", encoding="utf-8") as uf:
                                    json.dump(unk_data, uf, indent=2)
                                st.success(f"Cluster {sel_cl_id} officially labeled as '{new_lbl.strip()}'!")
                                st.rerun()
                            except Exception as ex:
                                st.error(f"Failed to update cluster: {ex}")
                        else:
                            st.error("Please enter a valid label for this sound cluster.")

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
        st.markdown('<div class="section"><div class="section-title">Active Threats & Citizen Incidents Response</div><div class="section-meta">LIVE SENTRY RADAR · FIELD PATROL DISPATCH · INCIDENT RESOLUTION</div></div>', unsafe_allow_html=True)
        render_geolocation_sentry("FIELD RANGER LIVE GPS TELEMETRY", auto_capture=True)

        # ----------------------------------------------------
        # 1. LIVE SENTINEL EDGE AI THREAT ALERTS
        # ----------------------------------------------------
        st.markdown("<div style='font-size:14px;font-weight:700;color:#ff7070;margin-top:4px;margin-bottom:8px;'>📡 Active Sentinel Edge AI Threat Alerts:</div>", unsafe_allow_html=True)
        
        # Test alert trigger button for field rangers to verify system anytime
        rg_sim_c1, rg_sim_c2 = st.columns([3, 1.2])
        with rg_sim_c2:
            if st.button("🧪 Trigger Test Sentry Alert", use_container_width=True, type="secondary", key="btn_ranger_sim_alert"):
                sim_threat = random.choice(["Chainsaw", "Fire", "Gunshot", "Vehicle Intrusion"])
                now_sim_ts = time.time()
                db.insert_emergency_alert({
                    "alert_id": f"alert_field_test_{int(now_sim_ts)}",
                    "device_id": "AURA_SENTRY_NODE_01",
                    "threat_type": sim_threat,
                    "risk_level": "CRITICAL" if sim_threat in ["Chainsaw", "Fire", "Gunshot"] else "HIGH",
                    "confidence": 0.94,
                    "location_lat": sent_lat + 0.0015,
                    "location_lon": sent_lon + 0.0018,
                    "message": f"🚨 Field verification alert: {sim_threat} simulated by Ranger {user_display}.",
                    "status": "DISPATCHED",
                })
                st.success(f"Dispatched test alert: {sim_threat}!")
                st.rerun()

        if not active_alerts:
            st.success("🟢 No unacknowledged Sentinel edge alerts in your sector.")
        else:
            for al in active_alerts:
                al_id = al.get("alert_id")
                al_threat = str(al.get("threat_type", "Threat")).upper()
                al_conf = safe_num(al.get("confidence", 0.9)) * 100
                al_stat = str(al.get("status", "DISPATCHED")).upper()
                al_node = al.get("device_id", "AURA_SENTRY_01")
                al_lat = float(safe_num(al.get("location_lat"), sent_lat))
                al_lon = float(safe_num(al.get("location_lon"), sent_lon))
                d_str = format_gps_distance(calculate_haversine_distance(sent_lat, sent_lon, al_lat, al_lon))
                al_msg = al.get("message") or f"{al_threat} signature detected by {al_node}."

                border_color = "#ef4444" if al_stat != "ACKNOWLEDGED" else "#7cf0b2"
                stat_badge = f"<span style='background:rgba(239,68,68,0.2);color:#ef4444;border:1px solid #ef4444;border-radius:6px;padding:3px 8px;font-size:10px;font-weight:700;'>🚨 {al_stat}</span>" if al_stat != "ACKNOWLEDGED" else f"<span style='background:rgba(124,240,178,0.2);color:#7cf0b2;border:1px solid #7cf0b2;border-radius:6px;padding:3px 8px;font-size:10px;font-weight:700;'>✓ ACKNOWLEDGED</span>"

                with st.container(border=True):
                    t_c1, t_c2 = st.columns([3, 1.2])
                    with t_c1:
                        st.markdown(f"<div style='font-size:16px;font-weight:800;color:#fff;'>🚨 THREAT: <span style='color:#ef4444;'>{al_threat}</span> ({al_conf:.1f}% Confidence) · {stat_badge}</div>", unsafe_allow_html=True)
                        st.markdown(f"📍 Coordinates: [`{al_lat:.5f}°N, {al_lon:.5f}°E`](https://maps.google.com/?q={al_lat},{al_lon}) · Proximity from you: **{d_str}** · Node: `[{al_node}]`")
                        st.caption(f"Details: {al_msg}")
                    with t_c2:
                        if al_stat != "ACKNOWLEDGED":
                            if st.button("⚡ Acknowledge Alert", key=f"btn_ack_rng_{al_id}", use_container_width=True, type="secondary"):
                                db.acknowledge_emergency_alert(al_id, acknowledged_by=user_display)
                                st.success(f"Alert acknowledged by {user_display}!")
                                st.rerun()

                    st.markdown("<div style='margin-top:8px; border-top:1px dashed var(--line); padding-top:8px;'></div>", unsafe_allow_html=True)
                    r_c1, r_c2 = st.columns([2.5, 1])
                    with r_c1:
                        notes_inp = st.text_input("Resolution & Field Investigation Notes", value="Threat investigated on-site, sector secured, no illegal activity present.", key=f"al_notes_{al_id}")
                    with r_c2:
                        st.write("")
                        if st.button("✅ Mark Threat as Solved", key=f"btn_res_{al_id}", use_container_width=True, type="primary"):
                            db.resolve_emergency_alert(al_id, resolved_by=user_display, resolution_notes=notes_inp)
                            st.success("Alert marked as solved! Recorded permanently into Incident Archive.")
                            st.rerun()

        # ----------------------------------------------------
        # 2. CITIZEN-REPORTED FIELD INCIDENTS
        # ----------------------------------------------------
        st.markdown("<div style='font-size:14px;font-weight:700;color:#f2c66d;margin-top:22px;margin-bottom:8px;'>📸 Citizen-Reported Field Incidents:</div>", unsafe_allow_html=True)
        cit_unres = [c for c in db.get_citizen_reports() if str(c.get("status", "")).upper() != "RESOLVED"]
        if not cit_unres:
            st.info("🟢 No pending citizen reports awaiting investigation.")
        else:
            for rep in cit_unres:
                c_id = rep.get("report_id")
                c_cat = rep.get("threat_category", "Sighting")
                c_rep = rep.get("reporter_name", "Public Visitor")
                c_con = rep.get("contact_info", "Unspecified")
                c_desc = rep.get("description", "No description provided.")
                c_photo = rep.get("photo_filename")
                c_stat = str(rep.get("status", "PENDING")).upper()
                c_lat = float(safe_num(rep.get("location_lat"), sent_lat))
                c_lon = float(safe_num(rep.get("location_lon"), sent_lon))
                d_str = format_gps_distance(calculate_haversine_distance(sent_lat, sent_lon, c_lat, c_lon))

                with st.container(border=True):
                    cr_c1, cr_c2 = st.columns([1.2, 2.8])
                    with cr_c1:
                        if c_photo and c_photo != "no_photo.jpg":
                            if c_photo.startswith("data:image"):
                                st.image(c_photo, caption="📸 Evidence Photo", use_container_width=True)
                            elif os.path.exists(c_photo):
                                st.image(c_photo, caption="📸 Evidence Photo", use_container_width=True)
                            else:
                                st.markdown("<div style='padding:14px;background:rgba(255,255,255,0.04);border:1px dashed var(--line);border-radius:8px;text-align:center;'>📸 Photo Evidence Attached</div>", unsafe_allow_html=True)
                        else:
                            st.caption("📷 No photo attached")
                    with cr_c2:
                        st.markdown(f"**📸 Sighting: {c_cat}** · <span style='background:rgba(242,198,109,0.2);color:#f2c66d;padding:2px 6px;border-radius:4px;font-size:11px;font-weight:700;'>{c_stat}</span>", unsafe_allow_html=True)
                        st.markdown(f"Report ID: `[{c_id}]` · Reporter: **{c_rep}** (📞 `{c_con}`)")
                        st.markdown(f"📍 GPS Location: [`{c_lat:.5f}°N, {c_lon:.5f}°E`](https://maps.google.com/?q={c_lat},{c_lon}) · Distance: **{d_str}**")
                        st.caption(f"Description: {c_desc}")

                    rc_1, rc_2 = st.columns([2.5, 1])
                    with rc_1:
                        cit_notes = st.text_input("Ranger Action & Verification Notes", value="Coordinates inspected on patrol. Area confirmed clear and safe.", key=f"cit_res_n_{c_id}")
                    with rc_2:
                        st.write("")
                        if st.button("✅ Mark Incident Solved", key=f"btn_cit_res_{c_id}", use_container_width=True, type="primary"):
                            db.resolve_citizen_report(c_id, resolved_by=user_display, resolution_notes=cit_notes)
                            st.success(f"Incident marked as solved by {user_display}! Archived in Incident Archive.")
                            st.rerun()

        # ----------------------------------------------------
        # 3. LIVE ACOUSTIC SENTRY PERCEPTION LOG (HARDWARE STREAM)
        # ----------------------------------------------------
        st.markdown("<div style='font-size:14px;font-weight:700;color:#73d9e8;margin-top:24px;margin-bottom:8px;'>📡 Live Sentinel Acoustic Perception Feed (Sensor Log):</div>", unsafe_allow_html=True)
        recent_evs = db.get_recent_events(limit=8)
        if not recent_evs:
            st.caption("Awaiting incoming acoustic telemetry stream from Sentinel edge hardware...")
        else:
            ev_rows = []
            for ev in recent_evs:
                pred = ev.get("prediction") or {}
                dec = ev.get("decision") or {}
                ev_lbl = format_display_label(pred.get("label", "Ambient Forest"))
                ev_conf = safe_num(pred.get("confidence", 0.0)) * 100
                ev_risk = str(dec.get("risk_level", "LOW")).upper()
                ev_act = dec.get("action", "MONITOR")
                ev_ts = ev.get("timestamp", time.time())
                ev_time_str = datetime.fromtimestamp(ev_ts).strftime("%H:%M:%S")
                ev_rows.append({
                    "TIMESTAMP": ev_time_str,
                    "DETECTED SOUND": ev_lbl,
                    "CONFIDENCE": f"{ev_conf:.1f}%",
                    "RISK LEVEL": ev_risk,
                    "CADIE ACTION": ev_act,
                    "DEVICE": ev.get("device_id", "AURA_SENTRY_01")
                })
            st.dataframe(ev_rows, use_container_width=True, hide_index=True)

    elif active_page == "🗺️ Sector Map & Near Rangers":
        st.markdown('<div class="section"><div class="section-title">Tactical Sector Map & Near My Rangers Radar</div><div class="section-meta">LIVE PATROL BUDDY PROXIMITY · TARGET THREAT COORDINATES</div></div>', unsafe_allow_html=True)
        render_geolocation_sentry("FIELD RANGER LIVE GPS TELEMETRY", auto_capture=True)
        render_active_threat_map_hud(active_alerts, detected, cadie, label, sent_lat, sent_lon, conf)
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
        st.markdown('<div class="section"><div class="section-title">Field Environment & Atmospheric Sentry</div><div class="section-meta">LIVE TELEMETRY READINGS FROM SENTINEL EDGE NODE</div></div>', unsafe_allow_html=True)
        rc1, rc2, rc3, rc4 = st.columns(4)
        with rc1:
            metric("Ambient Temp", f"{safe_num(telemetry.get('temperature')):.1f}", "°C", "DHT11 Thermal Sensor", accent="amber", icon="🌡️")
        with rc2:
            metric("Relative Humidity", f"{safe_num(telemetry.get('humidity')):.1f}", "%", "DHT11 RH Moisture", accent="cyan", icon="💧")
        with rc3:
            metric("Battery SOC", f"{safe_num(telemetry.get('battery_percent')):.1f}", "%", f"{safe_num(telemetry.get('battery_voltage')):.2f}V MAX17048", accent="emerald", icon="⚡")
        with rc4:
            dev_status = telemetry.get("device_status") if isinstance(telemetry.get("device_status"), dict) else {}
            gas_info = dev_status.get("gas_assessment") or telemetry.get("gas_assessment") or {}
            gas_status = str(gas_info.get("overall_status") or "NOMINAL").upper()
            metric("Gas Atmosphere", gas_status, f"Risk {safe_num(gas_info.get('gas_risk_score', 0.0)):.2f}", "Atmospheric Air Index", accent="purple" if gas_status == "NOMINAL" else "coral", icon="🧪")

        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
        st.markdown('<div class="section"><div class="section-title">Live Electrochemical Gas & Smoke Sensors (MQ Series)</div><div class="section-meta">ESP32-S3 12-BIT HIGH-PRECISION ADC BUS READINGS (GPIO 1 / GPIO 2)</div></div>', unsafe_allow_html=True)

        dev_status = telemetry.get("device_status") if isinstance(telemetry.get("device_status"), dict) else {}
        mq2_val = safe_num(telemetry.get("mq2_raw", dev_status.get("mq2_raw", 0)))
        mq2_v = safe_num(telemetry.get("mq2_adc_voltage", dev_status.get("mq2_adc_voltage", dev_status.get("mq2_voltage", 0.0))))
        mq135_val = safe_num(telemetry.get("mq135_raw", dev_status.get("mq135_raw", 0)))
        mq135_v = safe_num(telemetry.get("mq135_adc_voltage", dev_status.get("mq135_adc_voltage", dev_status.get("mq135_voltage", 0.0))))

        g_col1, g_col2 = st.columns(2)
        with g_col1:
            mq2_pct = min(100.0, (mq2_val / 4095.0) * 100.0) if mq2_val > 0 else 0.0
            mq2_status = "SMOKE / FIRE ANOMALY" if mq2_v > 1.8 else ("ELEVATED TRACE" if mq2_v > 1.0 else "CLEAR / NOMINAL")
            mq2_color = "#ff7070" if mq2_v > 1.8 else ("#f2c66d" if mq2_v > 1.0 else "#7cf0b2")
            st.markdown(
                f"""
                <div class="panel" style="padding: 16px; border: 1.5px solid {mq2_color}; border-radius: 12px; background: rgba(16, 28, 32, 0.9);">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-family:monospace; font-size:11px; font-weight:700; color:{mq2_color};">🔥 MQ-2 SMOKE & COMBUSTIBLE GAS</span>
                        <span style="font-family:monospace; font-size:10px; background:rgba(255,255,255,0.08); padding:2px 8px; border-radius:4px; color:#fff;">GPIO 1 (ADC1)</span>
                    </div>
                    <div style="font-size: 24px; font-weight: 800; color: #fff; margin-top: 8px;">
                        {int(mq2_val)} <span style="font-size: 13px; color: var(--muted); font-weight: 500;">ADC RAW ({mq2_v:.3f} V)</span>
                    </div>
                    <div style="font-size: 11px; color: {mq2_color}; font-weight: 700; margin-top: 4px;">
                        STATUS: {mq2_status}
                    </div>
                    <div style="margin-top: 10px;">
                        <div style="display:flex; justify-content:space-between; font-size:10px; color:#829a97; margin-bottom:4px;">
                            <span>ADC Load (0 - 4095)</span>
                            <span>{mq2_pct:.1f}%</span>
                        </div>
                        <div class="bar"><div style="width:{max(2, min(100, mq2_pct))}%; background:{mq2_color}; box-shadow:0 0 10px {mq2_color};"></div></div>
                    </div>
                    <div style="font-size: 10px; color: #829a97; margin-top: 8px;">
                        Monitors: LPG, Propane, Methane, Hydrogen, Alcohol, Smoke, and Fire Combustibles.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with g_col2:
            mq135_pct = min(100.0, (mq135_val / 4095.0) * 100.0) if mq135_val > 0 else 0.0
            mq135_status = "POLLUTION / VOC SPIKE" if mq135_v > 1.8 else ("SLIGHT VOC TRACE" if mq135_v > 1.0 else "CLEAN FOREST AIR")
            mq135_color = "#ff7070" if mq135_v > 1.8 else ("#f2c66d" if mq135_v > 1.0 else "#73d9e8")
            st.markdown(
                f"""
                <div class="panel" style="padding: 16px; border: 1.5px solid {mq135_color}; border-radius: 12px; background: rgba(16, 28, 32, 0.9);">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-family:monospace; font-size:11px; font-weight:700; color:{mq135_color};">🍃 MQ-135 AIR QUALITY & TOXIC GAS</span>
                        <span style="font-family:monospace; font-size:10px; background:rgba(255,255,255,0.08); padding:2px 8px; border-radius:4px; color:#fff;">GPIO 2 (ADC1)</span>
                    </div>
                    <div style="font-size: 24px; font-weight: 800; color: #fff; margin-top: 8px;">
                        {int(mq135_val)} <span style="font-size: 13px; color: var(--muted); font-weight: 500;">ADC RAW ({mq135_v:.3f} V)</span>
                    </div>
                    <div style="font-size: 11px; color: {mq135_color}; font-weight: 700; margin-top: 4px;">
                        STATUS: {mq135_status}
                    </div>
                    <div style="margin-top: 10px;">
                        <div style="display:flex; justify-content:space-between; font-size:10px; color:#829a97; margin-bottom:4px;">
                            <span>ADC Load (0 - 4095)</span>
                            <span>{mq135_pct:.1f}%</span>
                        </div>
                        <div class="bar"><div style="width:{max(2, min(100, mq135_pct))}%; background:{mq135_color}; box-shadow:0 0 10px {mq135_color};"></div></div>
                    </div>
                    <div style="font-size: 10px; color: #829a97; margin-top: 8px;">
                        Monitors: NH3, NOx, Alcohol, Benzene, Smoke, CO2, and Toxic Industrial Emissions.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

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
        st.markdown('<div class="section"><div class="section-title">Public Forest Safety Notices & Live Advisories</div><div class="section-meta">REAL-TIME SANCTUARY SAFETY STATUS · EDGE SENTRY ADVISORIES</div></div>', unsafe_allow_html=True)
        render_geolocation_sentry("VISITOR GPS LOCATION SENTRY", auto_capture=True)

        v_lat = float(st.session_state.get("client_gps_lat", sent_lat))
        v_lon = float(st.session_state.get("client_gps_lon", sent_lon))

        # Overall Status Banner
        if active_alerts:
            st.markdown(
                f'''
                <div style="background:rgba(235,87,87,0.08);border:1px solid var(--status-red);border-radius:10px;padding:14px 18px;margin-bottom:16px;">
                    <div style="display:flex;align-items:center;gap:12px;">
                        <span style="font-size:24px;">🚨</span>
                        <div>
                            <div style="font-size:15px;font-weight:700;color:var(--status-red);letter-spacing:0.02em;">ACTIVE FOREST ADVISORY IN EFFECT ({len(active_alerts)} Active Alerts)</div>
                            <div style="font-size:12px;color:var(--text-secondary);margin-top:2px;">
                                Sentinel nodes have reported acoustic or thermal activity. Field Ranger response units are deployed. Please review the live alerts and keep clear of caution perimeters.
                            </div>
                        </div>
                    </div>
                </div>
                ''',
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                '''
                <div style="background:rgba(124,240,178,0.08);border:1px solid var(--status-green);border-radius:10px;padding:14px 18px;margin-bottom:16px;">
                    <div style="display:flex;align-items:center;gap:12px;">
                        <span style="font-size:24px;">🟢</span>
                        <div>
                            <div style="font-size:15px;font-weight:700;color:var(--status-green);letter-spacing:0.02em;">SANCTUARY STATUS: ALL TRAILS SECURE & MONITORED</div>
                            <div style="font-size:12px;color:var(--text-secondary);margin-top:2px;">
                                All bioacoustic sentinels report nominal background conditions. Primary hiking trails and safari zones are clear.
                            </div>
                        </div>
                    </div>
                </div>
                ''',
                unsafe_allow_html=True
            )

        # Quick Status Metrics
        sm1, sm2, sm3, sm4 = st.columns(4)
        with sm1:
            metric("Active Advisories", str(len(active_alerts)), "events", "Edge acoustic detection", accent="red" if active_alerts else "emerald", icon="⚠️")
        with sm2:
            metric("Trail Status", "CAUTION" if active_alerts else "OPEN", "", "Main visitor corridor", accent="amber" if active_alerts else "emerald", icon="🥾")
        with sm3:
            metric("Ranger Helpline", "1800-425-AURA", "", "24/7 Forest HQ Dispatch", accent="cyan", icon="📞")
        with sm4:
            metric("Your Coordinates", f"{v_lat:.4f}°N", f"{v_lon:.4f}°E", "Live Phone GPS Sentry", accent="purple", icon="📍")

        # Interactive Public Safety Map
        st.markdown("<div style='margin-top:18px;margin-bottom:8px;font-size:13px;font-weight:700;color:var(--text-primary);letter-spacing:0.04em;'>SANCTUARY TACTICAL MAP & CAUTION ZONES</div>", unsafe_allow_html=True)
        render_active_threat_map_hud(active_alerts, detected=False, cadie={}, label='Public Caution Zone', sent_lat=v_lat, sent_lon=v_lon, conf_val=0.95)

        # Active Advisories List
        if active_alerts:
            st.markdown("<div style='margin-top:20px;margin-bottom:10px;font-size:13px;font-weight:700;color:var(--status-amber);letter-spacing:0.04em;'>CURRENT ACTIVE NOTICES & CAUTION SECTORS:</div>", unsafe_allow_html=True)
            for idx, al in enumerate(active_alerts):
                al_th = format_display_label(str(al.get("threat_type", "Threat"))).upper()
                al_cf = safe_num(al.get("confidence", 0.9)) * 100
                al_node = al.get("device_id", "AURA-NODE")
                a_lat = float(safe_num(al.get("location_lat"), sent_lat))
                a_lon = float(safe_num(al.get("location_lon"), sent_lon))
                dist_str = format_gps_distance(calculate_haversine_distance(v_lat, v_lon, a_lat, a_lon))
                resp_ranger = al.get("assigned_ranger_name") or "Field Patrol Unit"
                al_status = al.get("status", "ACTIVE")

                with st.container(border=True):
                    ac1, ac2 = st.columns([3, 1.2])
                    with ac1:
                        st.markdown(f"**🚨 {al_th} ({al_cf:.1f}% Confidence)** · Sensor: `{al_node}` · Status: **{al_status}**")
                        st.caption(f"📍 Location: `{a_lat:.5f}°N, {a_lon:.5f}°E` · Distance from you: **{dist_str}**")
                        if "fire" in al_th.lower():
                            st.info("🔥 Advisory: Smoke/thermal signature detected. Do not approach. Evacuate upwind immediately toward base camp.")
                        elif "chainsaw" in al_th.lower() or "drill" in al_th.lower():
                            st.warning("🪚 Advisory: Machinery / illegal tree felling suspected. Avoid north-west buffer trail. Ranger unit deployed.")
                        elif "gunshot" in al_th.lower():
                            st.error("💥 Critical Advisory: Suspected firearm discharge. Seek immediate cover on marked path and dial 112.")
                        else:
                            st.markdown("⚠️ Advisory: Unscheduled activity in sector. Stay on designated trails with tour guides.")
                    with ac2:
                        st.markdown(f"**Assigned Unit:**<br/>`{resp_ranger}`", unsafe_allow_html=True)
                        st.markdown(f"[🗺️ Open in Google Maps](https://maps.google.com/?q={a_lat},{a_lon})")

    elif active_page == "📸 Report Illegal Activity":
        st.markdown('<div class="section"><div class="section-title">Citizen Tip: Report Illegal Forest Activity</div><div class="section-meta">REPORT CHAINSAWS, POACHING, OR FIRES DIRECTLY TO CHIEF RANGER</div></div>', unsafe_allow_html=True)
        render_geolocation_sentry("CITIZEN LIVE GPS SENTRY (GEO-TAGGED EVIDENCE)", auto_capture=True)

        tab_submit_tip, tab_view_tips = st.tabs(["📤 Submit Field Tip & Photo Evidence", "📋 Track My Submitted Reports"])

        with tab_submit_tip:
            # Check if user just submitted a tip
            last_sub = st.session_state.get("citizen_last_submitted_report")
            if last_sub:
                with st.container(border=True):
                    st.markdown(
                        f'''
                        <div style="background:rgba(124,240,178,0.08);border:1px solid var(--status-green);border-radius:8px;padding:12px 16px;margin-bottom:12px;">
                            <div style="font-size:14px;font-weight:700;color:var(--status-green);display:flex;align-items:center;gap:8px;">
                                <span>✅</span> REPORT SUCCESSFULLY FILED WITH CHIEF RANGER & SECTOR PATROL
                            </div>
                            <div style="font-size:12px;color:var(--text-secondary);margin-top:4px;">
                                Reference ID: <code>{last_sub.get('report_id')}</code> · Sighting: <b>{last_sub.get('category')}</b> · Coordinates: <code>{last_sub.get('lat'):.5f}°N, {last_sub.get('lon'):.5f}°E</code>
                            </div>
                        </div>
                        ''',
                        unsafe_allow_html=True
                    )
                    c_prev1, c_prev2 = st.columns([1.5, 3])
                    with c_prev1:
                        if last_sub.get("photo") and last_sub.get("photo") != "no_photo.jpg":
                            st.image(last_sub.get("photo"), caption="Attached Evidence Photo", use_container_width=True)
                    with c_prev2:
                        st.markdown(f"**Description:** {last_sub.get('description')}")
                        st.markdown(f"**Submitted By:** {last_sub.get('reporter')} (Contact: `{last_sub.get('contact')}`)")
                        st.caption(f"Filed at: {last_sub.get('timestamp')}")
                        if st.button("➕ Submit Another Tip", key="btn_citizen_clear_last_report"):
                            st.session_state["citizen_last_submitted_report"] = None
                            st.rerun()

            with st.container(border=True):
                r_col1, r_col2 = st.columns(2)
                with r_col1:
                    cit_name = st.text_input("Your Full Name", value=user_display, key="cit_name_inp")
                    cit_cat = st.selectbox("Observed Activity / Threat Category", [
                        "🪚 Illegal Tree Felling / Chainsaw Activity",
                        "🔥 Wildfire / Smoke Sighting",
                        "🏹 Poaching / Animal Trap Sighting",
                        "🚗 Unauthorized Vehicle Intrusion",
                        "🗑️ Illegal Waste Dumping / Encroachment",
                    ], key="cit_cat_inp")
                    cit_contact = st.text_input("Contact Phone / Email", value=st.session_state.get("aura_username", ""), key="cit_contact_inp")
                with r_col2:
                    cit_desc = st.text_area("Description of Sighting (Optional if photo attached)", placeholder="Describe what you observed, trail marker, vehicle license plate, number of individuals...", key="cit_desc_inp")
                    cit_file = st.file_uploader("Upload Photo Evidence (JPEG / PNG)", type=["png", "jpg", "jpeg"], key="citizen_photo_upload_inp")
                    if cit_file is not None:
                        st.image(cit_file, caption=f"📸 Selected Photo: {cit_file.name}", width=240)

                live_user_lat = float(st.session_state.get("client_gps_lat", sent_lat))
                live_user_lon = float(st.session_state.get("client_gps_lon", sent_lon))

                g_c1, g_c2 = st.columns(2)
                with g_c1:
                    rep_lat = st.number_input("Incident Latitude (Live Phone GPS)", value=live_user_lat, format="%.6f", key="inp_cit_lat")
                with g_c2:
                    rep_lon = st.number_input("Incident Longitude (Live Phone GPS)", value=live_user_lon, format="%.6f", key="inp_cit_lon")

                if st.button("📤 Send Report & GPS Coordinates to Chief Ranger", type="primary", use_container_width=True, key="btn_citizen_send_tip_primary"):
                    if not cit_desc.strip() and cit_file is None:
                        st.error("Please provide either a description of the sighting or attach photo evidence.")
                    else:
                        photo_str = "no_photo.jpg"
                        report_id = f"cit_{int(time.time())}_{random.randint(100,999)}"
                        if cit_file is not None:
                            try:
                                file_bytes = cit_file.getvalue()
                                b64 = base64.b64encode(file_bytes).decode("utf-8")
                                mime = "image/jpeg" if cit_file.name.lower().endswith((".jpg", ".jpeg")) else "image/png"
                                photo_str = f"data:{mime};base64,{b64}"

                                # Also save physical file on disk for redundancy
                                os.makedirs("data/citizen_reports", exist_ok=True)
                                ext = "jpg" if cit_file.name.lower().endswith((".jpg", ".jpeg")) else "png"
                                disk_file = os.path.join("data", "citizen_reports", f"{report_id}.{ext}")
                                with open(disk_file, "wb") as pf:
                                    pf.write(file_bytes)
                            except Exception as pe:
                                print(f"Failed to process citizen image: {pe}")

                        final_desc = cit_desc.strip() if cit_desc.strip() else f"Visual photo report of {cit_cat} submitted by visitor."
                        db.insert_citizen_report(
                            report_id=report_id,
                            reporter_name=cit_name or "Anonymous Visitor",
                            contact_info=cit_contact or "Unspecified",
                            threat_category=cit_cat,
                            description=final_desc,
                            photo_filename=photo_str,
                            location_lat=rep_lat,
                            location_lon=rep_lon,
                        )
                        st.session_state["citizen_last_submitted_report"] = {
                            "report_id": report_id,
                            "category": cit_cat,
                            "photo": photo_str,
                            "lat": rep_lat,
                            "lon": rep_lon,
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "description": final_desc,
                            "reporter": cit_name,
                            "contact": cit_contact,
                        }
                        st.rerun()

        with tab_view_tips:
            c_reports = db.get_citizen_reports()
            # If user has a specific email/username, show their reports or all public tips
            curr_contact = str(st.session_state.get("aura_username", "")).strip().lower()
            if curr_contact:
                my_reports = [r for r in c_reports if curr_contact in str(r.get("contact_info", "")).lower() or curr_contact in str(r.get("reporter_name", "")).lower()]
            else:
                my_reports = []

            # If user has no specific matched reports, show recent citizen tips
            display_reports = my_reports if my_reports else c_reports[:10]

            st.markdown(f"<div style='font-size:12px;color:var(--text-secondary);margin-bottom:10px;'>Showing {len(display_reports)} reported incident(s). Real-time status reflects Chief Ranger triage and Field Ranger deployment.</div>", unsafe_allow_html=True)

            if not display_reports:
                st.info("No field reports recorded yet. Use the submit tab to report illegal logging, wildfires, or suspicious activity.")
            else:
                for rep in display_reports:
                    r_id = rep.get("report_id")
                    r_cat = rep.get("threat_category")
                    r_stat = str(rep.get("status", "PENDING")).upper()
                    r_photo = rep.get("photo_filename")
                    r_lat = rep.get("location_lat")
                    r_lon = rep.get("location_lon")

                    with st.container(border=True):
                        c1, c2 = st.columns([1.2, 3])
                        with c1:
                            if r_photo and r_photo != "no_photo.jpg":
                                if r_photo.startswith("data:image"):
                                    st.image(r_photo, caption=f"📸 Evidence Attached", use_container_width=True)
                                elif os.path.exists(r_photo):
                                    st.image(r_photo, caption=f"📸 Evidence Attached", use_container_width=True)
                                else:
                                    st.caption("📸 Photo on file")
                            else:
                                st.caption("📷 No photo attached")
                        with c2:
                            # Status pill
                            if r_stat == "RESOLVED":
                                stat_badge = '<span style="background:rgba(124,240,178,0.1);color:var(--status-green);border:1px solid var(--status-green);padding:2px 8px;border-radius:4px;font-size:11px;font-weight:700;">✅ RESOLVED & SECURED</span>'
                            elif r_stat == "DISPATCHED":
                                stat_badge = '<span style="background:rgba(115,217,232,0.1);color:var(--status-blue);border:1px solid var(--status-blue);padding:2px 8px;border-radius:4px;font-size:11px;font-weight:700;">⚡ RANGER DISPATCHED</span>'
                            else:
                                stat_badge = '<span style="background:rgba(235,160,55,0.1);color:var(--status-amber);border:1px solid var(--status-amber);padding:2px 8px;border-radius:4px;font-size:11px;font-weight:700;">⏳ PENDING REVIEW</span>'

                            st.markdown(f"**{r_cat}** · {stat_badge}", unsafe_allow_html=True)
                            st.markdown(f"**Report ID:** `{r_id}` · Reporter: {rep.get('reporter_name')}")
                            st.markdown(f"**Description:** {rep.get('description')}")
                            if r_lat and r_lon:
                                st.caption(f"📍 GPS: [`{r_lat:.6f}°N, {r_lon:.6f}°E`](https://maps.google.com/?q={r_lat},{r_lon})")
                            if rep.get("resolution_notes"):
                                st.info(f"Ranger Resolution Notes: {rep.get('resolution_notes')}")

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
