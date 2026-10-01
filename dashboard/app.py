"""
AuraForest — Sentinel Dashboard
Completely redesigned Streamlit UI with Role-Based Access Control (RBAC):
  1. 👑 Chief Ranger (Admin): Full sentinel control, nearby field ranger dispatcher, map, citizen reports inbox, auth audit log.
  2. 🛡️ Field Ranger Unit: Tactical incident response, GPS sector map, alert resolution ("Mark as Solved"), field telemetry.
  3. 👁️ Public Citizen & Visitor: Environmental climate readings, forest safety advisories, and public illegal activity tip report box with photo upload.

Run:
    streamlit run dashboard/app.py
"""

from __future__ import annotations

import math
import time
import sys
import json
import os
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

# Existing project data source
from runtime_data_source import RuntimeDataSource
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

# ==========================================================
# LIVE DASHBOARD REFRESH
# ==========================================================

if st_autorefresh is not None:
    st_autorefresh(
        interval=3000,
        key="aura_live_refresh",
    )
else:
    st.warning(
        "Live refresh is unavailable. Install it with: "
        "pip install streamlit-autorefresh"
    )

# ============================================================
# DESIGN SYSTEM
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
    font-family: "DM Sans", sans-serif;
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
    padding: 20px 32px 48px 32px;
}

header[data-testid="stHeader"] {
    background: transparent;
}

section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, rgba(12, 20, 23, 0.97) 0%, rgba(6, 10, 12, 0.99) 100%) !important;
    border-right: 1px solid rgba(32, 54, 62, 0.8) !important;
    box-shadow: 4px 0 25px rgba(0, 0, 0, 0.4);
}

div[data-testid="stSidebarUserContent"] {
    padding: 20px 14px;
}

/* Radio button styling in sidebar */
div[data-testid="stRadio"] > div {
    gap: 6px;
}

div[data-testid="stRadio"] label {
    background: rgba(255, 255, 255, 0.02);
    border: 1px solid rgba(32, 54, 62, 0.6);
    border-radius: 10px;
    padding: 8px 12px;
    transition: all 0.2s ease;
    cursor: pointer;
    font-size: 13px;
    font-weight: 500;
}

div[data-testid="stRadio"] label:hover {
    background: rgba(124, 240, 178, 0.06);
    border-color: rgba(124, 240, 178, 0.3);
}

/* Tab bar styling for clean navbar navigation */
div[data-baseweb="tab-list"] {
    gap: 8px;
    border-bottom: 1px solid rgba(32, 54, 62, 0.7);
    margin-bottom: 22px;
}

button[data-baseweb="tab"] {
    font-family: 'DM Sans', sans-serif;
    font-size: 13px;
    font-weight: 600;
    color: var(--muted);
    border-radius: 10px 10px 0 0;
    padding: 10px 18px;
    background: transparent;
    border: none;
    transition: all 0.2s ease;
}

button[data-baseweb="tab"]:hover {
    color: #edf6f3;
    background: rgba(255, 255, 255, 0.03);
}

button[data-baseweb="tab"][aria-selected="true"] {
    color: var(--green) !important;
    background: rgba(124, 240, 178, 0.08) !important;
    border-bottom: 2px solid var(--green) !important;
    text-shadow: 0 0 12px rgba(124, 240, 178, 0.4);
}

div[data-testid="stMetric"] {
    background: transparent;
}

/* Metric Cards with Vibrant Colored Top Bars & Glows */
.metric-card {
    background: linear-gradient(145deg, rgba(16, 26, 31, 0.94), rgba(9, 15, 18, 0.98));
    border: 1px solid var(--line);
    border-radius: 18px;
    padding: 18px 20px;
    min-height: 130px;
    box-shadow: 0 12px 35px rgba(0,0,0,0.3);
    position: relative;
    overflow: hidden;
    transition: transform 0.25s ease, box-shadow 0.25s ease, border-color 0.25s ease;
}

.metric-card:hover {
    transform: translateY(-3px);
    box-shadow: 0 18px 40px rgba(0,0,0,0.45);
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
    margin-bottom: 8px;
}

.metric-label {
    color: var(--muted);
    font-size: 11px;
    letter-spacing: .09em;
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
    color: var(--text);
    font-size: 28px;
    line-height: 1.1;
    font-weight: 700;
    letter-spacing: -0.02em;
}

.metric-unit {
    color: var(--muted);
    font-size: 13px;
    margin-left: 4px;
    font-weight: 500;
}

.metric-sub {
    color: var(--muted);
    font-size: 11px;
    margin-top: 8px;
    font-family: "JetBrains Mono", monospace;
}

.hero {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 25px;
    padding: 10px 0 24px 0;
    border-bottom: 1px solid var(--line);
    margin-bottom: 22px;
}

.brand {
    font-size: 32px;
    font-weight: 800;
    letter-spacing: -.04em;
    background: linear-gradient(135deg, #ffffff 40%, #7cf0b2 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

.brand-mark {
    color: var(--green);
    margin-right: 10px;
    -webkit-text-fill-color: var(--green);
}

.kicker {
    color: var(--green);
    font-family: "JetBrains Mono", monospace;
    font-size: 10px;
    letter-spacing: .18em;
    text-transform: uppercase;
    margin-bottom: 6px;
    font-weight: 600;
}

.subtitle {
    color: var(--muted);
    font-size: 13px;
    margin-top: 6px;
}

.live-pill {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    border: 1px solid rgba(124, 240, 178, 0.35);
    background: linear-gradient(135deg, rgba(124, 240, 178, 0.12), rgba(115, 217, 232, 0.05));
    color: var(--green);
    border-radius: 999px;
    padding: 8px 14px;
    font-family: "JetBrains Mono", monospace;
    font-size: 11px;
    font-weight: 600;
    box-shadow: 0 0 15px rgba(124, 240, 178, 0.15);
}

.dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--green);
    box-shadow: 0 0 10px var(--green);
    animation: pulseDot 2s infinite ease-in-out;
}

@keyframes pulseDot {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.45; transform: scale(0.85); }
}

.section {
    margin-top: 20px;
    margin-bottom: 12px;
}

.section-title {
    font-size: 15px;
    font-weight: 700;
    letter-spacing: .02em;
    color: var(--text);
}

.section-meta {
    color: var(--muted);
    font-size: 10px;
    font-family: "JetBrains Mono", monospace;
    margin-top: 3px;
    letter-spacing: .06em;
}

.panel {
    background: linear-gradient(145deg, rgba(14, 24, 29, 0.95), rgba(8, 14, 17, 0.98));
    border: 1px solid var(--line);
    border-radius: 18px;
    padding: 20px;
    height: 100%;
    box-shadow: 0 12px 35px rgba(0,0,0,0.25);
}

.panel-title {
    font-size: 13px;
    font-weight: 700;
    margin-bottom: 16px;
    letter-spacing: .02em;
    color: #edf5f2;
}

/* Dynamic Threat-Level Hero Cards */
.big-event {
    border-radius: 20px;
    padding: 26px;
    border: 1px solid var(--line);
    transition: all 0.3s ease;
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
    font-size: 40px;
    font-weight: 800;
    letter-spacing: -.04em;
    margin: 4px 0 10px;
    line-height: 1.1;
}

.event-caption {
    color: var(--muted);
    font-size: 11px;
    letter-spacing: .04em;
}

.confidence {
    font-family: "JetBrains Mono", monospace;
    font-size: 18px;
    font-weight: 700;
}

.bar {
    height: 8px;
    background: rgba(24, 35, 39, 0.8);
    border-radius: 99px;
    overflow: hidden;
    margin-top: 9px;
    box-shadow: inset 0 1px 3px rgba(0,0,0,0.5);
}

.bar > div {
    height: 100%;
    border-radius: 99px;
    transition: width 0.4s ease;
}

.status-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 0;
    border-bottom: 1px solid rgba(32, 54, 62, 0.6);
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

.ok { color: var(--green); text-shadow: 0 0 8px rgba(124, 240, 178, 0.4); }
.warn { color: var(--amber); text-shadow: 0 0 8px rgba(242, 198, 109, 0.4); }
.bad { color: var(--red); text-shadow: 0 0 8px rgba(255, 112, 112, 0.4); }
.neutral { color: var(--muted); }

.decision-box {
    border-radius: 16px;
    border: 1px solid var(--line);
    padding: 16px 18px;
    margin-bottom: 12px;
    background: rgba(255, 255, 255, 0.02);
}

.decision-risk {
    font-size: 24px;
    font-weight: 800;
    letter-spacing: -0.02em;
}

.decision-action {
    font-family: "JetBrains Mono", monospace;
    font-size: 11px;
    margin-top: 4px;
    font-weight: 600;
    letter-spacing: .06em;
}

.chip {
    display: inline-block;
    border: 1px solid rgba(124, 240, 178, 0.25);
    background: rgba(124, 240, 178, 0.06);
    border-radius: 999px;
    padding: 5px 10px;
    color: var(--green);
    font-family: "JetBrains Mono", monospace;
    font-size: 10px;
    font-weight: 600;
    margin: 3px 4px 3px 0;
}

.footer {
    color: #526563;
    font-family: "JetBrains Mono", monospace;
    font-size: 10px;
    text-align: center;
    padding-top: 32px;
}

[data-testid="stDataFrame"] {
    border: 1px solid var(--line);
    border-radius: 14px;
    overflow: hidden;
}

button[kind="secondary"] {
    border-radius: 10px;
    border: 1px solid var(--line);
    transition: all 0.2s ease;
}

button[kind="secondary"]:hover {
    border-color: var(--green);
    color: var(--green);
}

.discovery-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 10px;
    margin-bottom: 12px;
}
.discovery-stat {
    border: 1px solid var(--line);
    border-radius: 14px;
    background: rgba(255, 255, 255, 0.025);
    padding: 14px;
}
.discovery-stat-label {
    color: var(--muted);
    font-family: "JetBrains Mono", monospace;
    font-size: 9px;
    letter-spacing: .10em;
    text-transform: uppercase;
}
.discovery-stat-value {
    color: var(--text);
    font-size: 22px;
    font-weight: 700;
    margin-top: 6px;
}
.discovery-progress {
    height: 8px;
    background: #182327;
    border-radius: 99px;
    overflow: hidden;
    margin: 10px 0 6px;
}
.discovery-progress > div {
    height: 100%;
    background: linear-gradient(90deg, #00d2d3, #73d9e8);
    border-radius: 99px;
    box-shadow: 0 0 10px rgba(115, 217, 232, 0.5);
}
.cluster-card {
    border: 1px solid var(--line);
    border-radius: 14px;
    background: rgba(255, 255, 255, 0.02);
    padding: 14px;
    margin-bottom: 10px;
}
.cluster-id {
    font-family: "JetBrains Mono", monospace;
    color: var(--cyan);
    font-size: 12px;
    font-weight: 600;
}
.cluster-meta {
    color: var(--muted);
    font-family: "JetBrains Mono", monospace;
    font-size: 10px;
    margin-top: 5px;
}

</style>
""",
    unsafe_allow_html=True,
)


# ============================================================
# DATA HELPERS
# ============================================================

@st.cache_resource
def get_source() -> RuntimeDataSource:
    return RuntimeDataSource()


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


# ============================================================
# BACKEND API CLIENT WITH AUTH HEADERS
# ============================================================

AURA_API_URL = os.getenv(
    "AURAFOREST_API_URL",
    "http://127.0.0.1:8000",
).rstrip("/")


def discovery_api(
    path: str,
    method: str = "GET",
    payload: dict | None = None,
    timeout: float = 2.5,
) -> dict:
    """Call the live AuraForest backend discovery API with security auth headers."""
    url = f"{AURA_API_URL}{path}"
    body = None
    headers = {
        "Accept": "application/json",
        "X-API-Key": os.getenv("AURAFOREST_MASTER_KEY", "aura_sentry_sec_key_99"),
    }

    auth_token = st.session_state.get("aura_auth_token")
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"

    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = Request(
        url,
        data=body,
        headers=headers,
        method=method,
    )

    with urlopen(request, timeout=timeout) as response:
        raw = response.read().decode("utf-8")
        return json.loads(raw) if raw else {}


def get_unknown_discovery_state() -> tuple[dict, list[dict], str | None]:
    try:
        status_response = discovery_api("/api/v1/edge/unknown/status")
        clusters_response = discovery_api("/api/v1/edge/unknown/clusters")
        return (
            status_response.get("discovery") or {},
            clusters_response.get("clusters") or [],
            None,
        )
    except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
        return {}, [], str(exc)
    except Exception as exc:
        return {}, [], str(exc)


def get_cluster_samples_from_dashboard(cluster_id: str) -> tuple[list[dict], str | None]:
    try:
        response = discovery_api(f"/api/v1/edge/unknown/clusters/{quote(cluster_id, safe='')}/samples")
        return response.get("samples") or [], None
    except Exception as exc:
        return [], str(exc)


def sample_audio_url(sample_id: str) -> str:
    return f"{AURA_API_URL}/api/v1/edge/unknown/samples/{quote(sample_id, safe='')}/audio"


def label_cluster_from_dashboard(cluster_id: str, label: str, notes: str) -> tuple[bool, str]:
    try:
        response = discovery_api(
            f"/api/v1/edge/unknown/clusters/{cluster_id}/label",
            method="POST",
            payload={"label": label, "notes": notes},
        )
        if response.get("success"):
            return True, "Cluster label saved."
        return False, str(response)
    except Exception as exc:
        return False, str(exc)


def unlabel_cluster_from_dashboard(cluster_id: str) -> tuple[bool, str]:
    try:
        response = discovery_api(
            f"/api/v1/edge/unknown/clusters/{cluster_id}/unlabel",
            method="POST",
        )
        if response.get("success"):
            return True, "Cluster returned to UNLABELED."
        return False, str(response)
    except Exception as exc:
        return False, str(exc)


def clear_unknown_buffer_from_dashboard() -> tuple[bool, str]:
    try:
        response = discovery_api("/api/v1/edge/unknown/buffer/clear", method="POST")
        if response.get("success"):
            return True, "Pending unknown buffer cleared."
        return False, str(response)
    except Exception as exc:
        return False, str(exc)


def trigger_clustering_from_dashboard(force: bool = True) -> tuple[bool, str]:
    try:
        response = discovery_api("/api/v1/edge/unknown/cluster", method="POST", payload={"force": force})
        if response.get("success"):
            return True, response.get("message", "Clustering executed successfully.")
        return False, str(response)
    except Exception as exc:
        return False, str(exc)


# ============================================================
# EMERGENCY ALERT API & RESOLUTION HELPERS
# ============================================================

def get_active_emergency_alerts_from_dashboard() -> list[dict]:
    try:
        res = discovery_api("/api/v1/edge/alerts/active")
        return res.get("alerts", [])
    except Exception:
        return []


def get_alerts_history_from_dashboard() -> list[dict]:
    try:
        res = discovery_api("/api/v1/edge/alerts/history")
        return res.get("alerts", [])
    except Exception:
        return []


def acknowledge_alert_from_dashboard(alert_id: str, acknowledged_by: str = "Ranger Station") -> tuple[bool, str]:
    try:
        res = discovery_api(
            f"/api/v1/edge/alerts/{alert_id}/acknowledge",
            method="POST",
            payload={"acknowledged_by": acknowledged_by},
        )
        if res.get("success"):
            return True, "Alert acknowledged and siren silenced."
        return False, str(res)
    except Exception as e:
        return False, str(e)


def resolve_alert_from_dashboard(alert_id: str, resolved_by: str, notes: str) -> tuple[bool, str]:
    try:
        res = discovery_api(
            f"/api/v1/edge/alerts/{alert_id}/resolve",
            method="POST",
            payload={"resolved_by": resolved_by, "resolution_notes": notes},
        )
        if res.get("success"):
            return True, "Alert successfully marked as RESOLVED and secured on site."
        return False, str(res)
    except Exception as e:
        return False, str(e)


def assign_alert_from_dashboard(alert_id: str, ranger_id: str, ranger_name: str) -> tuple[bool, str]:
    try:
        res = discovery_api(
            f"/api/v1/edge/alerts/{alert_id}/assign",
            method="POST",
            payload={"ranger_id": ranger_id, "ranger_name": ranger_name},
        )
        if res.get("success"):
            return True, f"Alert assigned to {ranger_name}."
        return False, str(res)
    except Exception as e:
        return False, str(e)


def dispatch_manual_alert_from_dashboard(
    threat_type: str,
    confidence: float,
    risk_level: str,
    action: str,
    device_id_val: str = "sentinel_001",
    lat_val: float = 12.2958,
    lon_val: float = 76.6394,
) -> tuple[bool, str]:
    try:
        res = discovery_api(
            "/api/v1/edge/alerts/dispatch",
            method="POST",
            payload={
                "device_id": device_id_val,
                "threat_type": threat_type,
                "confidence": confidence,
                "risk_level": risk_level,
                "action": action,
                "latitude": lat_val,
                "longitude": lon_val,
                "contributing_factors": [
                    "Operator Manual Alert Trigger",
                    f"Threat: {threat_type} (Confidence: {confidence * 100:.1f}%)",
                ],
            },
        )
        if res.get("success"):
            return True, "Emergency alert broadcast successfully dispatched."
        return False, str(res)
    except Exception as e:
        return False, str(e)


def get_field_rangers_from_dashboard() -> list[dict]:
    try:
        res = discovery_api("/api/v1/edge/rangers")
        return res.get("rangers", [])
    except Exception:
        # Fallback list
        return [
            {"ranger_id": "ranger_01", "name": "Ranger Amar Singh", "callsign": "ALPHA-1", "sector": "Sector 4 (Tiger Corridor)", "latitude": 12.2980, "longitude": 76.6420, "status": "ON_PATROL", "battery": 92},
            {"ranger_id": "ranger_02", "name": "Ranger Deepa Rao", "callsign": "BRAVO-2", "sector": "Sector 2 (River Ridge)", "latitude": 12.2920, "longitude": 76.6340, "status": "RESPONDING", "battery": 85},
            {"ranger_id": "ranger_03", "name": "Ranger Vikrant Kumar", "callsign": "SIERRA-3", "sector": "Sector 7 (North Boundary)", "latitude": 12.3020, "longitude": 76.6450, "status": "STANDBY", "battery": 98},
        ]


def submit_citizen_report_from_dashboard(
    reporter_name: str,
    category: str,
    description: str,
    contact_info: str = "",
    photo_filename: str = "",
    lat_val: float = 12.2960,
    lon_val: float = 76.6400,
) -> tuple[bool, str]:
    try:
        res = discovery_api(
            "/api/v1/public/report",
            method="POST",
            payload={
                "reporter_name": reporter_name,
                "contact_info": contact_info,
                "threat_category": category,
                "description": description,
                "photo_filename": photo_filename,
                "location_lat": lat_val,
                "location_lon": lon_val,
            },
        )
        if res.get("success"):
            return True, res.get("message", "Citizen report submitted.")
        return False, str(res)
    except Exception as e:
        return False, str(e)


def get_citizen_reports_from_dashboard() -> list[dict]:
    try:
        res = discovery_api("/api/v1/public/reports")
        return res.get("reports", [])
    except Exception:
        return []


def update_citizen_report_status_from_dashboard(report_id: str, status: str, notes: str) -> tuple[bool, str]:
    try:
        res = discovery_api(
            f"/api/v1/public/reports/{report_id}/status",
            method="POST",
            payload={"status": status, "notes": notes},
        )
        if res.get("success"):
            return True, f"Report {report_id} updated to {status}."
        return False, str(res)
    except Exception as e:
        return False, str(e)


def get_auth_audit_log_from_dashboard() -> list[dict]:
    try:
        res = discovery_api("/api/v1/auth/audit_log")
        return res.get("audit_logs", [])
    except Exception:
        return []


def render_mobile_phone_notification_bridge(active_alerts_list: list[dict]) -> None:
    has_alert = len(active_alerts_list) > 0
    top_alert = active_alerts_list[0] if has_alert else {}
    threat_type = str(top_alert.get("threat_type", "Threat")).upper()
    confidence_pct = safe_num(top_alert.get("confidence", 0.95)) * 100
    alert_id = top_alert.get("alert_id", "")
    lat = top_alert.get("location_lat")
    lon = top_alert.get("location_lon")
    coords = f"{lat:.4f}°N, {lon:.4f}°E" if lat is not None and lon is not None else "Forest Reserve"
    device_id_str = str(top_alert.get("device_id", "sentinel_001"))

    alert_data_json = json.dumps({
        "has_alert": has_alert,
        "alert_id": alert_id,
        "threat_type": threat_type,
        "confidence": confidence_pct,
        "coords": coords,
        "device_id": device_id_str,
    })

    component_html = f"""
    <div id="phone-notif-container" style="background: linear-gradient(145deg, rgba(16, 28, 34, 0.92), rgba(8, 14, 18, 0.96)); border: 1px solid rgba(115, 217, 232, 0.25); border-radius: 14px; padding: 12px 18px; margin-bottom: 16px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px; box-shadow: 0 4px 20px rgba(0,0,0,0.25);">
        <div style="display: flex; align-items: center; gap: 12px;">
            <div style="width: 34px; height: 34px; border-radius: 10px; background: rgba(115, 217, 232, 0.12); border: 1px solid rgba(115, 217, 232, 0.3); display: flex; align-items: center; justify-content: center; font-size: 17px;">
                📱
            </div>
            <div>
                <div style="font-family: 'DM Sans', sans-serif; font-size: 13px; font-weight: 700; color: #edf6f3;">
                    Phone Notification Bar Alert System
                </div>
                <div id="phone-notif-status" style="font-family: 'JetBrains Mono', monospace; font-size: 10px; color: #829a97; margin-top: 2px;">
                    Status: Initializing notification permissions...
                </div>
            </div>
        </div>
        <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
            <button id="btn-enable-notifs" onclick="enablePhoneNotifications()" style="background: linear-gradient(135deg, rgba(115, 217, 232, 0.2), rgba(124, 240, 178, 0.15)); border: 1px solid rgba(115, 217, 232, 0.4); color: #73d9e8; font-family: 'JetBrains Mono', monospace; font-size: 11px; font-weight: 600; padding: 6px 14px; border-radius: 8px; cursor: pointer; transition: all 0.2s ease;">
                🔔 Enable Phone Alerts
            </button>
            <button id="btn-test-notif" onclick="triggerTestNotification()" style="background: rgba(255, 255, 255, 0.04); border: 1px solid rgba(255, 255, 255, 0.15); color: #c4d7d3; font-family: 'JetBrains Mono', monospace; font-size: 11px; font-weight: 500; padding: 6px 12px; border-radius: 8px; cursor: pointer;">
                🧪 Test Phone Pop-up
            </button>
            <a href="https://ntfy.sh/auraforest-alerts" target="_blank" style="background: rgba(255, 112, 112, 0.12); border: 1px solid rgba(255, 112, 112, 0.35); color: #ff7070; font-family: 'JetBrains Mono', monospace; font-size: 10px; font-weight: 600; padding: 6px 10px; border-radius: 8px; text-decoration: none; display: inline-flex; align-items: center; gap: 4px;">
                ⚡ ntfy Mobile Push
            </a>
        </div>
    </div>

    <script>
    const alertData = {alert_data_json};

    function updateStatusUI() {{
        const statusEl = document.getElementById("phone-notif-status");
        const btnEnable = document.getElementById("btn-enable-notifs");
        if (!statusEl || !btnEnable) return;
        if (!("Notification" in window)) {{
            statusEl.innerHTML = "<span style='color:#ff7070;'>Web Notifications not supported on this browser.</span>";
            btnEnable.style.display = "none";
            return;
        }}
        if (Notification.permission === "granted") {{
            statusEl.innerHTML = "<span style='color:#7cf0b2;'>● ACTIVE & ARMED</span> · Alerts pop up directly in your phone status bar";
            btnEnable.innerHTML = "✅ Phone Alerts Active";
            btnEnable.style.borderColor = "rgba(124, 240, 178, 0.5)";
            btnEnable.style.color = "#7cf0b2";
        }} else if (Notification.permission === "denied") {{
            statusEl.innerHTML = "<span style='color:#ff7070;'>● BLOCKED</span> · Permission denied. Please enable in browser settings";
            btnEnable.innerHTML = "⚠️ Permission Blocked";
        }} else {{
            statusEl.innerHTML = "<span style='color:#f2c66d;'>● STANDBY</span> · Tap 'Enable Phone Alerts' for notification bar alerts";
            btnEnable.innerHTML = "🔔 Enable Phone Alerts";
        }}
    }}

    function enablePhoneNotifications() {{
        if (!("Notification" in window)) {{
            alert("This browser does not support native notification popups.");
            return;
        }}
        Notification.requestPermission().then(function(permission) {{
            updateStatusUI();
            if (permission === "granted") {{
                new Notification("🚨 AuraForest Sentinel Armed", {{
                    body: "Local Emergency Alert notifications are now active on your phone!",
                    icon: "https://img.icons8.com/color/96/siren.png",
                    tag: "auraforest-armed",
                    vibrate: [200, 100, 200]
                }});
                if (navigator.vibrate) {{
                    navigator.vibrate([200, 100, 200]);
                }}
            }}
        }});
    }}

    function triggerTestNotification() {{
        if (!("Notification" in window)) return;
        if (Notification.permission !== "granted") {{
            enablePhoneNotifications();
            return;
        }}
        sendPhoneNotification("🚨 TEST ALERT: Chainsaw Detected", "Acoustic signature (96.4% confidence) at 12.2958°N, 76.6394°E. Sentinel: sentinel_001", "test-" + Date.now());
        playEmergencySirenAudio();
    }}

    function playEmergencySirenAudio() {{
        try {{
            const AudioContext = window.AudioContext || window.webkitAudioContext;
            if (!AudioContext) return;
            const ctx = new AudioContext();
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.type = "sawtooth";
            osc.frequency.setValueAtTime(650, ctx.currentTime);
            osc.frequency.linearRampToValueAtTime(1100, ctx.currentTime + 0.35);
            osc.frequency.linearRampToValueAtTime(650, ctx.currentTime + 0.7);
            gain.gain.setValueAtTime(0.15, ctx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 1.2);
            osc.connect(gain);
            gain.connect(ctx.destination);
            osc.start();
            osc.stop(ctx.currentTime + 1.2);
        }} catch(e) {{}}
    }}

    function sendPhoneNotification(title, body, tagId) {{
        if (!("Notification" in window) || Notification.permission !== "granted") return;
        const notif = new Notification(title, {{
            body: body,
            icon: "https://img.icons8.com/color/96/siren.png",
            badge: "https://img.icons8.com/color/48/siren.png",
            tag: tagId,
            renotify: true,
            requireInteraction: true,
            vibrate: [400, 200, 400, 200, 600],
        }});
        notif.onclick = function() {{
            window.focus();
            this.close();
        }};
        if (navigator.vibrate) {{
            navigator.vibrate([400, 200, 400, 200, 600]);
        }}
    }}

    function checkAndFireActiveEmergency() {{
        updateStatusUI();
        if (!alertData.has_alert) return;
        const lastNotified = sessionStorage.getItem("aura_last_notified_alert");
        if (lastNotified === alertData.alert_id) return;

        if (Notification.permission === "granted") {{
            const title = "🚨 EMERGENCY: " + alertData.threat_type + " DETECTED!";
            const body = alertData.threat_type + " (" + alertData.confidence.toFixed(1) + "%) at " + alertData.coords + ". Device: " + alertData.device_id + ". Tap to open console.";
            sendPhoneNotification(title, body, alertData.alert_id);
            playEmergencySirenAudio();
            sessionStorage.setItem("aura_last_notified_alert", alertData.alert_id);
        }}
    }}

    updateStatusUI();
    checkAndFireActiveEmergency();
    </script>
    """

    components.html(component_html, height=80)


# ============================================================
# LOAD RUNTIME STATE
# ============================================================

source = get_source()
state = source.tick()

telemetry = state.get("telemetry") or {}
event = state.get("event") or {}
cadie = state.get("cadie") or {}
prediction = state.get("prediction") or {}
environment = state.get("environment") or {}
policy = state.get("adaptive_policy") or {}
unknown = state.get("unknown_discovery") or {}
device_id = state.get("device_id") or "NO DEVICE"
timestamp = state.get("timestamp")
hardware = state.get("hardware_health") or telemetry.get("hardware_health") or {}


# ============================================================
# SIDEBAR: RBAC & DIAGNOSTICS
# ============================================================

active_alerts = get_active_emergency_alerts_from_dashboard()

if "aura_user_role" not in st.session_state:
    st.session_state["aura_user_role"] = "admin"
    st.session_state["aura_user_name"] = "Chief Ranger (Admin)"

with st.sidebar:
    st.markdown(
        """
        <div style="padding: 6px 0 16px 0; border-bottom: 1px solid rgba(32, 54, 62, 0.7); margin-bottom: 16px;">
            <div style="font-family:'JetBrains Mono',monospace;font-size:10px;letter-spacing:.16em;color:var(--green);font-weight:700;">AURAFOREST SENTINEL</div>
            <div style="font-size:22px;font-weight:800;color:#fff;margin-top:2px;letter-spacing:-0.02em;">◈ Bio-Defense Sentry</div>
            <div style="font-size:11px;color:var(--muted);margin-top:4px;">Multi-Tier Acoustic & Threat Intelligence</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ------------------------------------------------------
    # RBAC Identity Switcher
    # ------------------------------------------------------
    st.markdown('<div class="metric-label" style="margin-bottom:6px;">ACTIVE USER ROLE (RBAC)</div>', unsafe_allow_html=True)
    role_options = {
        "admin": "👑 Chief Ranger (Admin)",
        "ranger": "🛡️ Field Ranger Unit",
        "viewer": "👁️ Public Citizen / Visitor",
    }
    current_role = st.session_state.get("aura_user_role", "admin")
    selected_role = st.selectbox(
        "Active Role",
        options=list(role_options.keys()),
        format_func=lambda r: role_options[r],
        index=list(role_options.keys()).index(current_role) if current_role in role_options else 0,
        key="rbac_role_selector",
        label_visibility="collapsed",
    )
    if selected_role != current_role:
        st.session_state["aura_user_role"] = selected_role
        st.session_state["aura_user_name"] = role_options[selected_role]
        st.rerun()

    role_colors = {
        "admin": ("#7cf0b2", "rgba(124, 240, 178, 0.12)", "Chief Admin Control"),
        "ranger": ("#73d9e8", "rgba(115, 217, 232, 0.12)", "Tactical Response Unit"),
        "viewer": ("#f2c66d", "rgba(242, 198, 109, 0.12)", "Public Eco-Visitor"),
    }
    b_color, b_bg, b_desc = role_colors.get(selected_role, ("#7cf0b2", "rgba(124, 240, 178, 0.1)", "Standard"))

    st.markdown(
        f"""
        <div style="background:{b_bg}; border:1px solid {b_color}; border-radius:12px; padding:10px 14px; margin-bottom:16px;">
            <div style="font-family:'JetBrains Mono',monospace; font-size:11px; font-weight:700; color:{b_color};">
                ● {selected_role.upper()} MODE ACTIVE
            </div>
            <div style="font-size:11px; color:#edf6f3; margin-top:3px;">
                {b_desc}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Node Status Panel
    batt_pct = safe_num(telemetry.get("battery_percent", 0.0))
    batt_v = safe_num(telemetry.get("battery_voltage", 0.0))
    gas_status_side = str(
        (telemetry.get("device_status") or {}).get("gas_assessment", {}).get("overall_status")
        or telemetry.get("gas_assessment", {}).get("overall_status")
        or "NOMINAL"
    ).upper()

    st.markdown(
        f"""
        <div class="panel" style="padding:14px; margin-bottom:16px; border-radius:14px; background:rgba(16, 26, 31, 0.9);">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span class="metric-label">NODE ID</span>
                <span style="font-family:'JetBrains Mono',monospace; font-size:12px; font-weight:700; color:var(--green);">{device_id}</span>
            </div>
            <div style="display:flex; justify-content:space-between; align-items:center; margin-top:8px;">
                <span class="metric-label">CORE STATE</span>
                <span style="font-family:'JetBrains Mono',monospace; font-size:11px; color:#7cf0b2; font-weight:600;">ONLINE ●</span>
            </div>
            <div style="display:flex; justify-content:space-between; align-items:center; margin-top:8px;">
                <span class="metric-label">BATTERY</span>
                <span style="font-family:'JetBrains Mono',monospace; font-size:11px; color:#73d9e8; font-weight:600;">{batt_pct:.1f}% ({batt_v:.2f}V)</span>
            </div>
            <div style="display:flex; justify-content:space-between; align-items:center; margin-top:8px;">
                <span class="metric-label">ATMOSPHERE</span>
                <span style="font-family:'JetBrains Mono',monospace; font-size:11px; color:{'#7cf0b2' if gas_status_side=='NOMINAL' else '#ff7070'}; font-weight:600;">{gas_status_side}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if active_alerts:
        top_sidebar_alert = active_alerts[0]
        s_threat = str(top_sidebar_alert.get("threat_type", "Threat")).upper()
        s_conf = safe_num(top_sidebar_alert.get("confidence", 0.95)) * 100
        st.markdown(
            f"""
            <div style="background:linear-gradient(135deg, rgba(255,112,112,0.22), rgba(255,71,87,0.1)); border:1.5px solid #ff7070; border-radius:12px; padding:12px; margin-bottom:16px; box-shadow:0 0 15px rgba(255,112,112,0.3);">
                <div style="color:#ff7070; font-size:10px; font-weight:700; font-family:'JetBrains Mono',monospace; letter-spacing:.1em;">🚨 ACTIVE THREAT ALERT</div>
                <div style="color:#fff; font-size:13px; font-weight:700; margin-top:3px;">{s_threat} ({s_conf:.1f}%)</div>
                <div style="color:#edf5f2; font-size:10px; margin-top:3px; font-family:'JetBrains Mono',monospace;">Local siren & strobe active</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown('<div class="metric-label" style="margin-bottom:8px;">SYSTEM TELEMETRY CONTROL</div>', unsafe_allow_html=True)
    if st.button("↻ Force Telemetry Sync", use_container_width=True, key="btn_sidebar_refresh"):
        st.rerun()

    st.markdown(
        f"""
        <div style="margin-top:24px; padding-top:14px; border-top:1px solid var(--line); font-family:'JetBrains Mono',monospace; font-size:10px; color:#526563;">
            <div>BACKEND: {AURA_API_URL}</div>
            <div style="margin-top:2px;">SECURITY: HMAC-SHA256 Token Armed</div>
            <div style="margin-top:2px;">SYNC: Every 3.0s</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# MAIN HEADER
# ============================================================

role_header_titles = {
    "admin": ("CHIEF RANGER COMMAND CONSOLE", "Autonomous Bioacoustic & Threat Defense · Full Sentinel Access"),
    "ranger": ("FIELD RANGER TACTICAL RESPONSE CONSOLE", "Incident Response · GPS Navigation · On-Site Resolution"),
    "viewer": ("AURAFOREST PUBLIC CITIZEN & ECO-SENTRY", "Live Climate & Air Quality · Safety Alerts · Public Tip Box"),
}
h_title, h_sub = role_header_titles.get(current_role, ("Sentinel Command", "Edge Intelligence"))

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

# Active Emergency Alert Notification Banner
cadie_risk = str(cadie.get("risk_level") or "").upper()
requires_attention = bool(cadie.get("requires_attention", False))
render_mobile_phone_notification_bridge(active_alerts)

if active_alerts:
    top_alert = active_alerts[0]
    alert_id = top_alert["alert_id"]
    threat_name = str(top_alert.get("threat_type", "Threat")).upper()
    threat_conf = safe_num(top_alert.get("confidence", 0.95)) * 100
    lat_val = top_alert.get("location_lat")
    lon_val = top_alert.get("location_lon")
    coords_text = f"{lat_val:.5f}°N, {lon_val:.5f}°E" if lat_val is not None and lon_val is not None else "Coordinates Acquired"

    banner_col1, banner_col2 = st.columns([3.5, 1.2])
    with banner_col1:
        st.markdown(
            f"""
            <div style="background: linear-gradient(135deg, rgba(255, 112, 112, 0.22), rgba(255, 71, 87, 0.08)); border: 1.5px solid #ff7070; border-radius: 16px; padding: 16px 20px; margin-bottom: 18px; box-shadow: 0 0 25px rgba(255, 112, 112, 0.25);">
                <div style="display:flex;align-items:center;gap:10px;">
                    <span style="display:inline-block;width:10px;height:10px;background:#ff7070;border-radius:50%;box-shadow:0 0 10px #ff7070;animation:pulseDot 1.2s infinite ease-in-out;"></span>
                    <span style="color:#ff7070;font-family:'JetBrains Mono',monospace;font-size:11px;font-weight:700;letter-spacing:.14em;">🚨 ACTIVE LOCAL EMERGENCY ALERT BROADCAST</span>
                </div>
                <div style="font-size:19px;font-weight:800;color:#fff;margin-top:6px;">
                    {threat_name} DETECTED ({threat_conf:.1f}% Confidence) · {coords_text}
                </div>
                <div style="color:#edf5f2;font-size:11px;margin-top:4px;font-family:'JetBrains Mono',monospace;">
                    Device: {top_alert.get('device_id')} · Assigned: {top_alert.get('assigned_ranger_name') or 'Unassigned'} · Status: {top_alert.get('status')}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with banner_col2:
        st.write("")
        if current_role in ["admin", "ranger"]:
            if st.button(
                "✅ Silence Siren",
                key=f"btn_ack_top_{alert_id}",
                use_container_width=True,
                type="primary",
                help="Acknowledge alert and silence local siren",
            ):
                ok, msg = acknowledge_alert_from_dashboard(alert_id, acknowledged_by=st.session_state.get("aura_user_name", "Ranger"))
                if ok:
                    st.success(msg)
                    st.rerun()


# ============================================================
# HELPER: BUILD INTERACTIVE MAP DATAFRAME
# ============================================================

def build_map_data(sentinel_lat: float, sentinel_lon: float, alerts: list[dict], rangers: list[dict]) -> pd.DataFrame:
    records = []
    # 1. Sentinel Node
    records.append({
        "latitude": sentinel_lat,
        "longitude": sentinel_lon,
        "name": f"Sentinel Node: {device_id}",
        "type": "Sentinel Node",
    })
    # 2. Active Alerts
    for al in alerts:
        a_lat = al.get("location_lat")
        a_lon = al.get("location_lon")
        if a_lat and a_lon:
            records.append({
                "latitude": float(a_lat),
                "longitude": float(a_lon),
                "name": f"🚨 {al.get('threat_type')} Alert",
                "type": "Emergency Threat",
            })
    # 3. Field Rangers
    for rng in rangers:
        r_lat = rng.get("latitude")
        r_lon = rng.get("longitude")
        if r_lat and r_lon:
            records.append({
                "latitude": float(r_lat),
                "longitude": float(r_lon),
                "name": f"🛡️ {rng.get('name')} ({rng.get('callsign')})",
                "type": "Field Ranger",
            })
    return pd.DataFrame(records)


sent_lat = float(safe_num(telemetry.get("latitude"), 12.2958))
sent_lon = float(safe_num(telemetry.get("longitude"), 76.6394))
field_rangers = get_field_rangers_from_dashboard()
map_dataframe = build_map_data(sent_lat, sent_lon, active_alerts, field_rangers)


# ============================================================
# 👑 VIEW 1: CHIEF RANGER (ADMIN) DASHBOARD
# ============================================================

if current_role == "admin":
    t1, t2, t3, t4, t5, t6, t7 = st.tabs([
        "📡 Live Sentinel Overview",
        "🗺️ Sentinel Map & Ranger Dispatch",
        "📊 Spectrum & Acoustic AI",
        "🚨 Emergency Broadcast Console",
        "📨 Public Citizen Reports",
        "🔬 Unknown Sound Discovery",
        "🔒 Auth & Security Audit Log",
    ])

    # Tab 1: Live Overview
    with t1:
        st.markdown(
            '<div class="section"><div class="section-title">Live Environmental Telemetry</div>'
            '<div class="section-meta">REAL-TIME SENSOR SNAPSHOT · ESP32-S3 DMA BUS</div></div>',
            unsafe_allow_html=True,
        )
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        with c1:
            metric("Temperature", f"{safe_num(telemetry.get('temperature')):.1f}", "°C", "ambient thermal state", accent="amber", icon="🌡️")
        with c2:
            metric("Humidity", f"{safe_num(telemetry.get('humidity')):.1f}", "%", "relative humidity", accent="cyan", icon="💧")
        with c3:
            metric("Light Level", f"{safe_num(telemetry.get('light_level')):.0f}", "lux", "BH1750 optical index", accent="gold", icon="☀️")
        with c4:
            metric("Battery Gauge", f"{safe_num(telemetry.get('battery_percent')):.1f}", "%", f"{safe_num(telemetry.get('battery_voltage')):.3f} V · MAX17048", accent="emerald", icon="⚡")
        with c5:
            vibration = bool(telemetry.get("vibration_detected"))
            metric("Vibration", "DETECTED" if vibration else "CLEAR", "", "SW-420 seismic latch", accent="coral" if vibration else "purple", icon="📳")
        with c6:
            dev_status = telemetry.get("device_status") if isinstance(telemetry.get("device_status"), dict) else {}
            gas_info = dev_status.get("gas_assessment") or telemetry.get("gas_assessment") or {}
            gas_status = str(gas_info.get("overall_status") or "NOMINAL").upper()
            gas_score = safe_num(gas_info.get("gas_risk_score", 0.0))
            gas_accent = "emerald" if gas_status == "NOMINAL" else ("amber" if gas_status == "ELEVATED" else "coral")
            metric("Atmosphere / Gas", gas_status, f"Risk {gas_score:.2f}", "MQ-2 / MQ-135 Engine", accent=gas_accent, icon="🧪")

        # Decision Engine
        st.markdown(
            '<div class="section"><div class="section-title">Acoustic Intelligence & CADIE Decision Engine</div>'
            '<div class="section-meta">MODEL INFERENCE → CADIE MULTIMODAL FUSION → AUTONOMOUS RESPONSE</div></div>',
            unsafe_allow_html=True,
        )
        left, mid, right = st.columns([1.35, 1.15, 1])
        with left:
            label = event.get("label") or prediction.get("label") or "Ambient Forest"
            conf = safe_num(event.get("confidence", prediction.get("confidence", 0.0)))
            detected = event.get("detected", False)
            risk_raw = str(cadie.get("risk_level") or "LOW").upper()
            threat_class = "threat-critical" if risk_raw in ["HIGH", "CRITICAL"] else ("threat-elevated" if risk_raw in ["ELEVATED", "MEDIUM"] else "threat-nominal")
            conf_color = "#ff7070" if risk_raw in ["HIGH", "CRITICAL"] else ("#f2c66d" if risk_raw in ["ELEVATED", "MEDIUM"] else "#7cf0b2")

            st.markdown(
                f"""
                <div class="big-event {threat_class}">
                    <div class="kicker">ACTIVE ACOUSTIC PERCEPTION</div>
                    <div class="event-label">{label}</div>
                    <div class="event-caption">{"🔴 THREAT SIGNAL DETECTED" if detected else "🟢 STEADY STATE MONITORING"} · class {event.get("class_id", prediction.get("class_id", "—"))}</div>
                    <div style="margin-top:24px">
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
            risk_cls = status_class("FAILED" if risk in ["HIGH", "CRITICAL"] else ("WORKING" if risk in ["LOW", "MINIMAL"] else "WARN"))
            factors_list = cadie.get("contributing_factors") or []
            factors_html = "".join(f'<span class="chip" style="margin-bottom:4px;">{f}</span> ' for f in factors_list[:4])
            st.markdown(
                f"""
                <div class="panel">
                    <div class="panel-title">Decision Engine (CADIE)</div>
                    <div class="decision-box">
                        <div class="kicker">TRIAGE RISK LEVEL</div>
                        <div class="decision-risk {risk_cls}">{risk}</div>
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
                    {display_status("Unknown Buffer", str(unknown.get("buffer_size", "—")))}
                    {display_status("Environment Type", environment.get("environment_type", "—"))}
                </div>
                """,
                unsafe_allow_html=True,
            )

    # Tab 2: Map & Field Ranger Dispatch
    with t2:
        st.markdown(
            '<div class="section"><div class="section-title">Live Tactical Map & Field Ranger Dispatch</div>'
            '<div class="section-meta">GPS LOCATION OF SENTINELS · ACTIVE THREATS · NEARBY FIELD RANGER PATROL UNITS</div></div>',
            unsafe_allow_html=True,
        )
        map_col, dispatch_col = st.columns([2.2, 1.3])
        with map_col:
            st.map(map_dataframe, zoom=13, use_container_width=True)
            st.caption("🟢 Sentinel Nodes | 🔴 Active Threat Coordinates | 🔵 Nearby Field Ranger Units")

        with dispatch_col:
            st.markdown(
                """
                <div class="panel">
                    <div class="panel-title">Nearby Field Rangers Roster</div>
                """,
                unsafe_allow_html=True,
            )
            for rng in field_rangers:
                r_id = rng.get("ranger_id")
                r_name = rng.get("name")
                r_call = rng.get("callsign")
                r_sec = rng.get("sector")
                r_status = rng.get("status")
                r_batt = rng.get("battery")
                r_phone = rng.get("phone", "—")

                with st.container(border=True):
                    st.markdown(f"**{r_name}** (`{r_call}`)")
                    st.caption(f"📍 {r_sec} · 🔋 {r_batt}% · 📞 {r_phone}")
                    st.markdown(f"Status: `{r_status}`")

                    if active_alerts:
                        top_a_id = active_alerts[0].get("alert_id")
                        if st.button(f"⚡ Assign Alert to {r_call}", key=f"btn_assign_{r_id}_{top_a_id}", use_container_width=True):
                            ok, msg = assign_alert_from_dashboard(top_a_id, r_id, r_name)
                            if ok:
                                st.success(msg)
                                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    # Tab 3: Spectrum & AI
    with t3:
        render_spectrum_section(label, mic_level=safe_num(telemetry.get("microphone_level", 500.0)))

    # Tab 4: Emergency Broadcast Console
    with t4:
        st.markdown(
            '<div class="section"><div class="section-title">Emergency Alert Broadcast Console</div>'
            '<div class="section-meta">MULTI-CHANNEL DISPATCH · DEVICE STROBE · WEBHOOK BROADCAST · AUDIT LOG</div></div>',
            unsafe_allow_html=True,
        )
        alert_history = get_alerts_history_from_dashboard()
        with st.container(border=True):
            al_c1, al_c2 = st.columns([1.8, 1.2])
            with al_c1:
                st.markdown("<div style='font-size:13px;font-weight:700;margin-bottom:8px;color:#fff;'>📢 Broadcast Manual Emergency Alert</div>", unsafe_allow_html=True)
                f_th, f_rk, f_ac = st.columns(3)
                with f_th:
                    m_threat = st.selectbox("Threat Category", ["🔥 Fire (Highest Priority)", "🪚 Logging: Chainsaw / Drill (Highest Priority)", "🚗 Vehicles: Truck / Engine (Moderate)", "👤 Human Intrusion / Speech (Moderate)", "🌿 Others: Wildlife / Ambient (Low)"], key="adm_threat")
                with f_rk:
                    m_risk = st.selectbox("Priority Level", ["CRITICAL", "HIGH", "MODERATE", "LOW"], key="adm_risk")
                with f_ac:
                    m_action = st.selectbox("Dispatch Action", ["DISPATCH_RANGERS", "INTERCEPT_VEHICLE", "INVESTIGATE_INTRUSION", "RECORD_EVIDENCE", "MONITOR"], key="adm_action")

                clean_th = m_threat.split(" (")[0].replace("🔥 ", "").replace("🪚 ", "").replace("🚗 ", "").replace("👤 ", "").replace("🌿 ", "")
                if st.button("🚨 Broadcast Emergency Alert Now", type="primary", use_container_width=True, key="btn_adm_broadcast"):
                    ok, msg = dispatch_manual_alert_from_dashboard(threat_type=clean_th, confidence=0.98, risk_level=m_risk, action=m_action, device_id_val=device_id, lat_val=sent_lat, lon_val=sent_lon)
                    if ok:
                        st.success(msg)
                        st.rerun()

            with al_c2:
                st.markdown(f"""
                <div style='font-size:13px;font-weight:700;margin-bottom:8px;color:#fff;'>📡 Dispatch Channels Status</div>
                {display_status("Device Red Strobe", "ONLINE (GPIO 38)")}
                {display_status("Ranger Hotline", "CONNECTED")}
                {display_status("Webhook Dispatcher", "ACTIVE")}
                {display_status("Total Alerts Logged", str(len(alert_history)))}
                """, unsafe_allow_html=True)

        if alert_history:
            st.markdown("<div style='margin-top:12px;font-size:12px;font-weight:700;'>Dispatched Alert Audit Log:</div>", unsafe_allow_html=True)
            a_rows = []
            for a_item in alert_history[:8]:
                a_rows.append({
                    "ALERT ID": str(a_item.get("alert_id")),
                    "THREAT": str(a_item.get("threat_type")),
                    "RISK": str(a_item.get("risk_level")),
                    "CONFIDENCE": f"{safe_num(a_item.get('confidence')) * 100:.1f}%",
                    "STATUS": str(a_item.get("status")),
                    "ASSIGNED RANGER": str(a_item.get("assigned_ranger_name") or "Unassigned"),
                    "RESOLVED BY": str(a_item.get("resolved_by") or "—"),
                })
            st.dataframe(a_rows, use_container_width=True, hide_index=True)

    # Tab 5: Citizen Reports Inbox
    with t5:
        st.markdown(
            '<div class="section"><div class="section-title">Public Citizen Reports & Illegal Activity Inbox</div>'
            '<div class="section-meta">CITIZEN TIPS · PHOTO EVIDENCE · REVIEW & DISPATCH CONTROLS</div></div>',
            unsafe_allow_html=True,
        )
        citizen_reports = get_citizen_reports_from_dashboard()
        if not citizen_reports:
            st.info("No citizen reports pending review.")
        else:
            for rep in citizen_reports:
                r_id = rep.get("report_id")
                r_name = rep.get("reporter_name", "Anonymous")
                r_cat = rep.get("threat_category", "Illegal Activity")
                r_desc = rep.get("description", "")
                r_stat = rep.get("status", "PENDING")
                r_time = rep.get("created_at", "")[:19].replace("T", " ")

                with st.container(border=True):
                    c_h1, c_h2, c_h3 = st.columns([1.5, 1.5, 1.2])
                    with c_h1:
                        st.markdown(f"**Report ID:** `{r_id}`")
                        st.markdown(f"**Reporter:** {r_name} · **Category:** `{r_cat}`")
                    with c_h2:
                        st.markdown(f"**Description:** {r_desc}")
                        st.caption(f"Logged: {r_time}")
                    with c_h3:
                        st.markdown(f"Status: **{r_stat}**")
                        b1, b2 = st.columns(2)
                        with b1:
                            if st.button("✅ Verify", key=f"btn_ver_{r_id}", use_container_width=True):
                                update_citizen_report_status_from_dashboard(r_id, "VERIFIED", "Chief Ranger verified report")
                                st.rerun()
                        with b2:
                            if st.button("🛡️ Dispatch", key=f"btn_disp_{r_id}", use_container_width=True):
                                update_citizen_report_status_from_dashboard(r_id, "DISPATCHED", "Ranger unit dispatched to investigate")
                                st.rerun()

    # Tab 6: Unknown Discovery
    with t6:
        st.markdown(
            '<div class="section"><div class="section-title">Unknown Sound Intelligence</div>'
            '<div class="section-meta">OPEN-SET REJECTION → AUDIO EVIDENCE → DBSCAN CLUSTERS → HUMAN REVIEW</div></div>',
            unsafe_allow_html=True,
        )
        discovery_status, discovery_clusters, discovery_error = get_unknown_discovery_state()
        if discovery_error:
            st.warning("Discovery backend unavailable.")
        else:
            buffer_size = int(safe_num(discovery_status.get("buffer_size")))
            discovered = int(safe_num(discovery_status.get("clusters_discovered")))
            col1, col2, col3 = st.columns(3)
            with col1:
                metric("Pending Unknown", str(buffer_size), "samples", "awaiting batch", accent="cyan")
            with col2:
                metric("Discovered Clusters", str(discovered), "classes", "DBSCAN clusters", accent="purple")
            with col3:
                if st.button("⚡ Run Clustering Now", key="btn_disc_cluster", use_container_width=True):
                    trigger_clustering_from_dashboard(force=True)
                    st.rerun()

    # Tab 7: Security Audit Log
    with t7:
        st.markdown(
            '<div class="section"><div class="section-title">Security & Authentication Audit Log</div>'
            '<div class="section-meta">IMMUTABLE RECORD OF LOGINS, KEY CHECKS, DISPATCHES, AND RESOLUTIONS</div></div>',
            unsafe_allow_html=True,
        )
        audit_logs = get_auth_audit_log_from_dashboard()
        if audit_logs:
            log_rows = []
            for l_item in audit_logs:
                log_rows.append({
                    "TIMESTAMP": str(l_item.get("created_at", ""))[:19].replace("T", " "),
                    "USER": str(l_item.get("username")),
                    "ROLE": str(l_item.get("role")).upper(),
                    "ACTION": str(l_item.get("action")),
                    "DETAILS": str(l_item.get("details")),
                })
            st.dataframe(log_rows, use_container_width=True, hide_index=True)
        else:
            st.info("No security audit logs recorded yet.")


# ============================================================
# 🛡️ VIEW 2: FIELD RANGER TACTICAL RESPONSE DASHBOARD
# ============================================================

elif current_role == "ranger":
    r_tab1, r_tab2, r_tab3, r_tab4 = st.tabs([
        "🚨 Tactical Alert Response & Resolution",
        "🗺️ Patrol Sector Map & GPS Nav",
        "📡 Field Telemetry & Gas Sentry",
        "📊 Acoustic Frequency Monitor",
    ])

    # Tab 1: Alert Response & Resolve
    with r_tab1:
        st.markdown(
            '<div class="section"><div class="section-title">Assigned Threat Incidents & Tactical Resolution</div>'
            '<div class="section-meta">ADDRESS ACTIVE EMERGENCY ALERTS · SECURE PERIMETER · MARK AS SOLVED</div></div>',
            unsafe_allow_html=True,
        )
        if not active_alerts:
            st.success("🟢 No active emergency alerts in your sector. Perimeter is secure.")
        else:
            for al in active_alerts:
                al_id = al.get("alert_id")
                al_th = str(al.get("threat_type")).upper()
                al_cf = safe_num(al.get("confidence")) * 100
                al_lat = al.get("location_lat", sent_lat)
                al_lon = al.get("location_lon", sent_lon)
                al_stat = al.get("status")

                with st.container(border=True):
                    st.markdown(
                        f"""
                        <div style="background:rgba(255,112,112,0.12); border-left:4px solid #ff7070; padding:12px 16px; border-radius:10px; margin-bottom:12px;">
                            <div style="font-size:16px; font-weight:800; color:#ff7070;">🚨 THREAT: {al_th} ({al_cf:.1f}% Confidence)</div>
                            <div style="font-size:12px; color:#edf6f3; margin-top:4px;">Coordinates: {al_lat:.5f}°N, {al_lon:.5f}°E · Alert ID: <code>{al_id}</code></div>
                            <div style="font-size:11px; color:#829a97; margin-top:2px;">Assigned: {al.get('assigned_ranger_name') or 'Field Unit'} · Status: {al_stat}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    res_col1, res_col2 = st.columns([2.5, 1])
                    with res_col1:
                        res_notes = st.text_input(
                            "On-Site Action / Resolution Notes",
                            value="Threat investigated, perpetrators deterred, location secured.",
                            key=f"notes_{al_id}",
                        )
                    with res_col2:
                        st.write("")
                        if st.button("✅ Mark Alert as Solved", key=f"btn_res_{al_id}", use_container_width=True, type="primary"):
                            ok, msg = resolve_alert_from_dashboard(al_id, resolved_by=st.session_state.get("aura_user_name", "Field Ranger"), notes=res_notes)
                            if ok:
                                st.success(msg)
                                st.rerun()

    # Tab 2: Sector Map
    with r_tab2:
        st.markdown(
            '<div class="section"><div class="section-title">Tactical Sector Map & Navigation</div>'
            '<div class="section-meta">FIELD RANGER GPS · TARGET THREAT COORDINATES · PATROL BUDDY POSITIONS</div></div>',
            unsafe_allow_html=True,
        )
        st.map(map_dataframe, zoom=14, use_container_width=True)

    # Tab 3: Field Telemetry
    with r_tab3:
        st.markdown(
            '<div class="section"><div class="section-title">Field Environment & Gas Sentry</div>'
            '<div class="section-meta">LIVE SENSOR READINGS FROM CLOSEST SENTINEL NODE</div></div>',
            unsafe_allow_html=True,
        )
        rc1, rc2, rc3, rc4 = st.columns(4)
        with rc1:
            metric("Ambient Temp", f"{safe_num(telemetry.get('temperature')):.1f}", "°C", "thermal sensor", accent="amber", icon="🌡️")
        with rc2:
            metric("Humidity", f"{safe_num(telemetry.get('humidity')):.1f}", "%", "RH level", accent="cyan", icon="💧")
        with rc3:
            metric("Battery SOC", f"{safe_num(telemetry.get('battery_percent')):.1f}", "%", "MAX17048", accent="emerald", icon="⚡")
        with rc4:
            metric("Gas Atmosphere", str((telemetry.get("device_status") or {}).get("gas_assessment", {}).get("overall_status") or "NOMINAL").upper(), "", "MQ-2/MQ-135", accent="purple", icon="🧪")

    # Tab 4: Acoustic Frequency
    with r_tab4:
        render_spectrum_section(label, mic_level=safe_num(telemetry.get("microphone_level", 500.0)))


# ============================================================
# 👁️ VIEW 3: PUBLIC CITIZEN & VISITOR ECO-DASHBOARD
# ============================================================

elif current_role == "viewer":
    p_tab1, p_tab2, p_tab3 = st.tabs([
        "🌿 Forest Climate & Eco-Readings",
        "⚠️ Forest Safety & Alerts",
        "📸 Report Illegal Activity / Sighting",
    ])

    # Tab 1: Eco-Readings
    with p_tab1:
        st.markdown(
            '<div class="section"><div class="section-title">Live Forest Environmental Readings</div>'
            '<div class="section-meta">PUBLIC REAL-TIME CLIMATE AND AIR QUALITY IN THE FOREST RESERVE</div></div>',
            unsafe_allow_html=True,
        )
        pc1, pc2, pc3 = st.columns(3)
        with pc1:
            metric("Forest Temperature", f"{safe_num(telemetry.get('temperature')):.1f}", "°C", "Pleasant climate", accent="amber", icon="🌲")
        with pc2:
            metric("Relative Humidity", f"{safe_num(telemetry.get('humidity')):.1f}", "%", "Canopy moisture", accent="cyan", icon="💧")
        with pc3:
            metric("Air Quality", "FRESH & CLEAN", "", "Natural forest atmosphere", accent="emerald", icon="🍃")

    # Tab 2: Forest Safety Advisories
    with p_tab2:
        st.markdown(
            '<div class="section"><div class="section-title">Public Forest Safety Notices</div>'
            '<div class="section-meta">OFFICIAL RANGER ADVISORIES AND WEATHER/WILDFIRE ALERTS</div></div>',
            unsafe_allow_html=True,
        )
        if active_alerts:
            for al in active_alerts:
                st.error(f"⚠️ SAFETY NOTICE: Elevated activity ({al.get('threat_type')}) detected in Sector. Please stay on marked trails.")
        else:
            st.success("✅ Forest Reserve is safe. All sectors are currently green.")

    # Tab 3: Citizen Tip Box
    with p_tab3:
        st.markdown(
            '<div class="section"><div class="section-title">Citizen Tip: Report Illegal Forest Activity</div>'
            '<div class="section-meta">REPORT CHAINSAWS, ILLEGAL FELLING, POACHERS, OR FIRES DIRECTLY TO CHIEF RANGER</div></div>',
            unsafe_allow_html=True,
        )
        with st.container(border=True):
            r_col1, r_col2 = st.columns(2)
            with r_col1:
                cit_name = st.text_input("Your Name (or leave Anonymous)", value="Citizen Observer")
                cit_cat = st.selectbox("Observed Threat Category", [
                    "🪚 Illegal Tree Felling / Chainsaw Activity",
                    "🔥 Wildfire / Smoke Sighting",
                    "🏹 Poaching / Animal Trap Sighting",
                    "🚗 Unauthorized Vehicle Intrusion",
                    "🗑️ Illegal Waste Dumping / Encroachment",
                ])
                cit_contact = st.text_input("Contact Phone / Email (Optional)")
            with r_col2:
                cit_desc = st.text_area("Detailed Description of Sighting", placeholder="Describe what you heard or saw, number of persons/vehicles, exact trail marker, etc.")
                cit_file = st.file_uploader("Upload Photo Evidence (Optional)", type=["png", "jpg", "jpeg"])

            if st.button("📤 Send Report to Chief Ranger Command", type="primary", use_container_width=True):
                if not cit_desc.strip():
                    st.error("Please provide a description of the observed activity.")
                else:
                    photo_name = cit_file.name if cit_file else "no_photo.jpg"
                    ok, msg = submit_citizen_report_from_dashboard(
                        reporter_name=cit_name,
                        category=cit_cat,
                        description=cit_desc,
                        contact_info=cit_contact,
                        photo_filename=photo_name,
                        lat_val=sent_lat,
                        lon_val=sent_lon,
                    )
                    if ok:
                        st.success(f"✅ {msg} Chief Ranger has been alerted.")


# ============================================================
# FOOTER
# ============================================================

st.markdown(
    f"""
    <div class="footer">
        AURAForest Sentinel · {device_id} · Role: {current_role.upper()} ·
        HMAC Authenticated · live auto-refresh (3s)
    </div>
    """,
    unsafe_allow_html=True,
)
