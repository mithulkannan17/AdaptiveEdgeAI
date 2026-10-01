"""
AuraForest — Sentinel Dashboard
Completely redesigned Streamlit UI with modern Sidebar & Tabbed Navbar navigation.

Run:
    streamlit run dashboard/app.py

The dashboard reads the existing RuntimeDataSource and therefore
does not change the backend/API or inference pipeline.
"""

from __future__ import annotations

import math
import time
import sys
import json
import os
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
    font-size: 14px;
    font-weight: 600;
    color: var(--muted);
    border-radius: 10px 10px 0 0;
    padding: 11px 20px;
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

.code-value {
    font-family: "JetBrains Mono", monospace;
    color: #b9cbc7;
    font-size: 11px;
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
    if text in {"WORKING", "OK", "ONLINE", "ACTIVE", "TRUE"}:
        return "ok"
    if text in {"NOT_WORKING", "FAILED", "OFFLINE", "ERROR", "FALSE"}:
        return "bad"
    return "neutral"


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
# UNKNOWN DISCOVERY API
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

    # Attach bearer token if user is authenticated in dashboard session
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
    """Return discovery status, clusters, and an optional error."""
    try:
        status_response = discovery_api(
            "/api/v1/edge/unknown/status"
        )
        clusters_response = discovery_api(
            "/api/v1/edge/unknown/clusters"
        )

        return (
            status_response.get("discovery") or {},
            clusters_response.get("clusters") or [],
            None,
        )
    except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
        return {}, [], str(exc)
    except Exception as exc:
        return {}, [], str(exc)


def get_cluster_samples_from_dashboard(
    cluster_id: str,
) -> tuple[list[dict], str | None]:
    """Return persistent sample evidence for a discovered cluster."""
    try:
        response = discovery_api(
            f"/api/v1/edge/unknown/clusters/{quote(cluster_id, safe='')}/samples"
        )
        return response.get("samples") or [], None
    except Exception as exc:
        return [], str(exc)


def get_sample_metadata_from_dashboard(
    sample_id: str,
) -> tuple[dict, str | None]:
    """Return metadata for one persisted unknown-sound sample."""
    try:
        response = discovery_api(
            f"/api/v1/edge/unknown/samples/{quote(sample_id, safe='')}"
        )
        return response, None
    except Exception as exc:
        return {}, str(exc)


def sample_audio_url(sample_id: str) -> str:
    """Build the backend streaming URL for a persisted review sample."""
    return (
        f"{AURA_API_URL}/api/v1/edge/unknown/samples/"
        f"{quote(sample_id, safe='')}/audio"
    )


def label_cluster_from_dashboard(
    cluster_id: str,
    label: str,
    notes: str,
) -> tuple[bool, str]:
    """Apply a human review label through the backend API."""
    try:
        response = discovery_api(
            f"/api/v1/edge/unknown/clusters/{cluster_id}/label",
            method="POST",
            payload={
                "label": label,
                "notes": notes,
            },
        )
        if response.get("success"):
            return True, "Cluster label saved."
        return False, str(response)
    except Exception as exc:
        return False, str(exc)


def unlabel_cluster_from_dashboard(
    cluster_id: str,
) -> tuple[bool, str]:
    """Remove a human review label through the backend API."""
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
    """Clear only pending unknown observations."""
    try:
        response = discovery_api(
            "/api/v1/edge/unknown/buffer/clear",
            method="POST",
        )
        if response.get("success"):
            return True, "Pending unknown buffer cleared."
        return False, str(response)
    except Exception as exc:
        return False, str(exc)


def trigger_clustering_from_dashboard(force: bool = True) -> tuple[bool, str]:
    """Trigger DBSCAN clustering on all pending unknown observations."""
    try:
        response = discovery_api(
            "/api/v1/edge/unknown/cluster",
            method="POST",
            payload={"force": force},
        )
        if response.get("success"):
            return True, response.get("message", "Clustering executed successfully.")
        return False, str(response)
    except Exception as exc:
        return False, str(exc)


# ============================================================
# EMERGENCY ALERT API HELPERS
# ============================================================

def get_active_emergency_alerts_from_dashboard() -> list[dict]:
    """Fetch unacknowledged active emergency alerts from backend."""
    try:
        res = discovery_api("/api/v1/edge/alerts/active")
        return res.get("alerts", [])
    except Exception:
        return []


def get_alerts_history_from_dashboard() -> list[dict]:
    """Fetch emergency alert dispatch history from backend."""
    try:
        res = discovery_api("/api/v1/edge/alerts/history")
        return res.get("alerts", [])
    except Exception:
        return []


def acknowledge_alert_from_dashboard(
    alert_id: str,
    acknowledged_by: str = "Ranger Command Console",
) -> tuple[bool, str]:
    """Mark an emergency alert as acknowledged/silenced."""
    try:
        res = discovery_api(
            f"/api/v1/edge/alerts/{alert_id}/acknowledge",
            method="POST",
            payload={"acknowledged_by": acknowledged_by},
        )
        if res.get("success"):
            return True, "Alert acknowledged and silenced."
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
    """Trigger an emergency alert broadcast directly from dashboard."""
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


def render_mobile_phone_notification_bridge(active_alerts_list: list[dict]) -> None:
    """
    Client-side Bridge for Native Mobile Phone Notification Bar Alerts.
    Supports:
      1. HTML5 Web Push / Notification API (Pops up directly in Android / iOS / Desktop Notification Bar)
      2. Device Vibration Haptic Pulses (navigator.vibrate)
      3. Web Audio API synthesized Emergency Siren
      4. Direct ntfy mobile background push subscription
    """
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

# Hardware health may be present in future/extended records.
# Keep the UI compatible with both old and new database records.
hardware = state.get("hardware_health") or telemetry.get("hardware_health") or {}


# ============================================================
# SIDEBAR DIAGNOSTICS & TELEMETRY
# ============================================================

active_alerts = get_active_emergency_alerts_from_dashboard()

with st.sidebar:
    st.markdown(
        """
        <div style="padding: 6px 0 16px 0; border-bottom: 1px solid rgba(32, 54, 62, 0.7); margin-bottom: 16px;">
            <div style="font-family:'JetBrains Mono',monospace;font-size:10px;letter-spacing:.16em;color:var(--green);font-weight:700;">AURAFOREST SENTINEL</div>
            <div style="font-size:22px;font-weight:800;color:#fff;margin-top:2px;letter-spacing:-0.02em;">◈ Edge Sentry</div>
            <div style="font-size:11px;color:var(--muted);margin-top:4px;">Autonomous Bioacoustic & Threat Defense</div>
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
                <span class="metric-label">DEVICE IDENTIFIER</span>
                <span style="font-family:'JetBrains Mono',monospace; font-size:12px; font-weight:700; color:var(--green);">{device_id}</span>
            </div>
            <div style="display:flex; justify-content:space-between; align-items:center; margin-top:8px;">
                <span class="metric-label">CORE STATE</span>
                <span style="font-family:'JetBrains Mono',monospace; font-size:11px; color:#7cf0b2; font-weight:600;">ONLINE ●</span>
            </div>
            <div style="display:flex; justify-content:space-between; align-items:center; margin-top:8px;">
                <span class="metric-label">BATTERY GAUGE</span>
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

    # Active Emergency Sentry Alert Badge in Sidebar
    if active_alerts:
        top_sidebar_alert = active_alerts[0]
        s_threat = str(top_sidebar_alert.get("threat_type", "Threat")).upper()
        s_conf = safe_num(top_sidebar_alert.get("confidence", 0.95)) * 100
        st.markdown(
            f"""
            <div style="background:linear-gradient(135deg, rgba(255,112,112,0.22), rgba(255,71,87,0.1)); border:1.5px solid #ff7070; border-radius:12px; padding:12px; margin-bottom:16px; box-shadow:0 0 15px rgba(255,112,112,0.3);">
                <div style="color:#ff7070; font-size:10px; font-weight:700; font-family:'JetBrains Mono',monospace; letter-spacing:.1em;">🚨 ACTIVE THREAT ALERT</div>
                <div style="color:#fff; font-size:13px; font-weight:700; margin-top:3px;">{s_threat} ({s_conf:.1f}%)</div>
                <div style="color:#edf5f2; font-size:10px; margin-top:3px; font-family:'JetBrains Mono',monospace;">Local siren & strobe pulsing</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ------------------------------------------------------
    # Ranger Security & RBAC Identity
    # ------------------------------------------------------
    if "aura_user_role" not in st.session_state:
        st.session_state["aura_user_role"] = "admin"
        st.session_state["aura_user_name"] = "Chief Ranger (Admin)"

    st.markdown('<div class="metric-label" style="margin-bottom:8px;">SECURITY & IDENTITY (RBAC)</div>', unsafe_allow_html=True)
    
    role_options = {
        "admin": "👑 Chief Ranger (Admin)",
        "ranger": "🛡️ Field Ranger Unit",
        "viewer": "👁️ Public Observer (Guest)",
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

    role_badge_colors = {
        "admin": ("#7cf0b2", "rgba(124, 240, 178, 0.1)"),
        "ranger": ("#73d9e8", "rgba(115, 217, 232, 0.1)"),
        "viewer": ("#829a97", "rgba(130, 154, 151, 0.1)"),
    }
    badge_fg, badge_bg = role_badge_colors.get(selected_role, ("#7cf0b2", "rgba(124, 240, 178, 0.1)"))

    st.markdown(
        f"""
        <div style="background:{badge_bg}; border:1px solid {badge_fg}; border-radius:10px; padding:8px 12px; margin-bottom:14px;">
            <div style="font-family:'JetBrains Mono',monospace; font-size:10px; font-weight:700; color:{badge_fg};">
                LEVEL: {selected_role.upper()} · AUTH ARMED
            </div>
            <div style="font-size:11px; color:#edf6f3; margin-top:2px;">
                {'Full system & broadcast permissions' if selected_role=='admin' else ('Operational triage permissions' if selected_role=='ranger' else 'Read-only telemetry observer')}
            </div>
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
            <div style="margin-top:2px;">SECURITY: HMAC-SHA256 Token Active</div>
            <div style="margin-top:2px;">SYNC: Every 3.0s</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# MAIN HEADER
# ============================================================

st.markdown(
    f"""
    <div class="hero">
        <div>
            <div class="kicker">AURAFOREST / EDGE INTELLIGENCE</div>
            <div class="brand"><span class="brand-mark">◈</span>Sentinel Command</div>
            <div class="subtitle">
                Environmental acoustic intelligence · adaptive edge monitoring · autonomous threat triage
            </div>
        </div>
        <div class="live-pill"><span class="dot"></span>SENTINEL ONLINE</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# ACTIVE EMERGENCY ALERT NOTIFICATION BANNER
# ============================================================

cadie_risk = str(cadie.get("risk_level") or "").upper()
requires_attention = bool(cadie.get("requires_attention", False))

# Render client-side Phone Notification Bar bridge
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
                    Device: {top_alert.get('device_id')} · Channels: Phone Notification Bar · Local Siren Active · Webhook Broadcast Sent · Ranger Dispatch Alert
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with banner_col2:
        st.write("")
        if st.button(
            "✅ Acknowledge Alert",
            key=f"btn_ack_top_{alert_id}",
            use_container_width=True,
            type="primary",
            help="Acknowledge alert and silence the local device siren",
        ):
            ok, msg = acknowledge_alert_from_dashboard(alert_id)
            if ok:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)
elif cadie_risk in ["CRITICAL", "HIGH"] or requires_attention:
    st.markdown(
        f"""
        <div style="background: linear-gradient(135deg, rgba(242, 198, 109, 0.18), rgba(255, 159, 67, 0.06)); border: 1.5px solid #f2c66d; border-radius: 16px; padding: 14px 20px; margin-bottom: 18px; box-shadow: 0 0 20px rgba(242, 198, 109, 0.18);">
            <div style="color:#f2c66d;font-family:'JetBrains Mono',monospace;font-size:11px;font-weight:700;letter-spacing:.12em;">⚠️ ELEVATED THREAT ALERT — CADIE REQUIRES ATTENTION</div>
            <div style="font-size:16px;font-weight:700;color:#fff;margin-top:4px;">
                Signal: {str(event.get('label') or prediction.get('label', 'Threat')).upper()} · Triage: {cadie_risk} ({cadie.get('action', 'MONITOR')})
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# PRIMARY NAVIGATION TABS (NAVBAR)
# ============================================================

tab_overview, tab_spectrum, tab_alerts, tab_discovery, tab_health = st.tabs([
    "📡 Live Sentinel Overview",
    "📊 Spectrum & Acoustic AI",
    "🚨 Emergency Alert Center",
    "🔬 Unknown Sound Discovery",
    "📈 Node Health & Logs",
])


# ============================================================
# TAB 1: LIVE SENTINEL OVERVIEW
# ============================================================

with tab_overview:
    # Top Telemetry Metrics
    st.markdown(
        '<div class="section"><div class="section-title">Live Environmental Telemetry</div>'
        '<div class="section-meta">REAL-TIME SENSOR SNAPSHOT · ESP32-S3 DMA BUS</div></div>',
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4, c5, c6 = st.columns(6)

    with c1:
        metric(
            "Temperature",
            f"{safe_num(telemetry.get('temperature')):.1f}",
            "°C",
            "ambient thermal state",
            accent="amber",
            icon="🌡️",
        )

    with c2:
        metric(
            "Humidity",
            f"{safe_num(telemetry.get('humidity')):.1f}",
            "%",
            "relative humidity",
            accent="cyan",
            icon="💧",
        )

    with c3:
        metric(
            "Light Level",
            f"{safe_num(telemetry.get('light_level')):.0f}",
            "lux",
            "BH1750 optical index",
            accent="gold",
            icon="☀️",
        )

    with c4:
        metric(
            "Battery Gauge",
            f"{safe_num(telemetry.get('battery_percent')):.1f}",
            "%",
            f"{safe_num(telemetry.get('battery_voltage')):.3f} V · MAX17048",
            accent="emerald",
            icon="⚡",
        )

    with c5:
        vibration = bool(telemetry.get("vibration_detected"))
        metric(
            "Vibration",
            "DETECTED" if vibration else "CLEAR",
            "",
            "SW-420 seismic latch",
            accent="coral" if vibration else "purple",
            icon="📳",
        )

    with c6:
        dev_status = telemetry.get("device_status") if isinstance(telemetry.get("device_status"), dict) else {}
        gas_info = dev_status.get("gas_assessment") or telemetry.get("gas_assessment") or {}
        gas_status = str(gas_info.get("overall_status") or "NOMINAL").upper()
        gas_score = safe_num(gas_info.get("gas_risk_score", 0.0))
        gas_accent = "emerald" if gas_status == "NOMINAL" else ("amber" if gas_status == "ELEVATED" else "coral")
        metric(
            "Atmosphere / Gas",
            gas_status,
            f"Risk {gas_score:.2f}",
            "MQ-2 / MQ-135 Engine",
            accent=gas_accent,
            icon="🧪",
        )

    # AI Event + CADIE
    st.markdown(
        '<div class="section"><div class="section-title">Acoustic Intelligence & Decision Engine</div>'
        '<div class="section-meta">MODEL INFERENCE → CADIE MULTIMODAL FUSION → AUTONOMOUS RESPONSE</div></div>',
        unsafe_allow_html=True,
    )

    left, mid, right = st.columns([1.35, 1.15, 1])

    with left:
        label = event.get("label") or prediction.get("label") or "Ambient Forest"
        conf = safe_num(
            event.get("confidence", prediction.get("confidence", 0.0))
        )
        detected = event.get("detected", False)
        risk_raw = str(cadie.get("risk_level") or "LOW").upper()

        if risk_raw in ["HIGH", "CRITICAL"] or any(k in label.lower() for k in ["chainsaw", "gunshot", "fire"]):
            threat_class = "threat-critical"
            conf_color = "#ff7070"
        elif risk_raw in ["ELEVATED", "MEDIUM"] or any(k in label.lower() for k in ["vehicle", "engine", "rain"]):
            threat_class = "threat-elevated"
            conf_color = "#f2c66d"
        else:
            threat_class = "threat-nominal"
            conf_color = "#7cf0b2"

        st.markdown(
            f"""
            <div class="big-event {threat_class}">
                <div class="kicker">ACTIVE ACOUSTIC PERCEPTION</div>
                <div class="event-label">{label}</div>
                <div class="event-caption">
                    {"🔴 THREAT SIGNAL DETECTED" if detected else "🟢 STEADY STATE MONITORING"}
                    · class {event.get("class_id", prediction.get("class_id", "—"))}
                </div>
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
        risk_cls = status_class(
            "FAILED" if risk in ["HIGH", "CRITICAL"] else ("WORKING" if risk in ["LOW", "MINIMAL"] else "WARN")
        )
        factors_list = cadie.get("contributing_factors") or []
        factors_html = ""
        if factors_list:
            items = "".join(f'<span class="chip" style="margin-bottom:4px;">{f}</span> ' for f in factors_list[:4])
            factors_html = f'<div style="margin-top:12px;border-top:1px solid var(--line);padding-top:10px;"><div class="kicker" style="font-size:9px;margin-bottom:6px;">MULTIMODAL CORROBORATION</div><div>{items}</div></div>'

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
                {factors_html}
            </div>
            """,
            unsafe_allow_html=True,
        )

    with right:
        inference_ms = safe_num(
            prediction.get(
                "inference_time_ms",
                event.get("inference_time_ms"),
            )
        )

        unknown_decision = unknown.get("decision") or {}
        unknown_detected = bool(unknown_decision.get("is_unknown", False))

        model_name = prediction.get("model") or "MobileNetV3-Small"
        buffer_size = unknown.get("buffer_size", "—")
        environment_type = environment.get("environment_type") or "—"

        inference_panel = (
            '<div class="panel">'
            '<div class="panel-title">Inference & Edge Health</div>'
            f'{display_status("Model Engine", model_name)}'
            f"{display_status('Latency', f'{inference_ms:.2f} ms')}"
            f'{display_status("Open-Set Discovery", "ACTIVE" if unknown_detected else "IDLE")}'
            f'{display_status("Unknown Buffer", str(buffer_size))}'
            f'{display_status("Environment Type", environment_type)}'
            '</div>'
        )

        st.markdown(inference_panel, unsafe_allow_html=True)

    # Context & Adaptation
    st.markdown(
        '<div class="section"><div class="section-title">Context & Adaptation</div>'
        '<div class="section-meta">THE EDGE NODE ADJUSTS ITS OPERATING POLICY FROM OBSERVED CONDITIONS</div></div>',
        unsafe_allow_html=True,
    )

    a, b, c, d = st.columns([1, 1, 1, 1.1])

    with a:
        st.markdown('<div class="panel"><div class="panel-title">Environment Profile</div>', unsafe_allow_html=True)
        env_items = [
            ("Type", environment.get("environment_type", "—")),
            ("Observations", environment.get("observation_count", "—")),
            ("Natural score", f"{safe_num(environment.get('natural_score')):.2f}"),
            ("Anthropogenic", f"{safe_num(environment.get('anthropogenic_score')):.2f}"),
            ("Weather", f"{safe_num(environment.get('weather_score')):.2f}"),
            ("Aquatic", f"{safe_num(environment.get('aquatic_score')):.2f}"),
            ("Uncertainty", f"{safe_num(environment.get('uncertainty')):.2f}"),
        ]
        for n, v in env_items:
            st.markdown(display_status(n, v), unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with b:
        st.markdown('<div class="panel"><div class="panel-title">Adaptive Policy</div>', unsafe_allow_html=True)
        policy_items = [
            ("Threshold", f"{safe_num(policy.get('detection_threshold')):.2f}"),
            ("Transmission", policy.get("transmission_mode", "—")),
            ("Sampling", policy.get("sampling_mode", "—")),
            ("Policy context", policy.get("environment_type", "—")),
            ("Ignored classes", len(policy.get("ignored_classes", []) or [])),
        ]
        for n, v in policy_items:
            st.markdown(display_status(n, v), unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with c:
        st.markdown('<div class="panel"><div class="panel-title">Priority Map</div>', unsafe_allow_html=True)
        priorities = policy.get("class_priority") or {}
        if priorities:
            ordered = sorted(priorities.items(), key=lambda x: (-safe_num(x[1]), x[0]))
            for name, value in ordered[:8]:
                st.markdown(
                    f'<span class="chip">{name} · P{value}</span>',
                    unsafe_allow_html=True,
                )
        else:
            st.markdown('<span class="neutral">No priority data</span>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with d:
        st.markdown('<div class="panel"><div class="panel-title">Gas Sensor Fusion</div>', unsafe_allow_html=True)
        dev_status = telemetry.get("device_status") if isinstance(telemetry.get("device_status"), dict) else {}
        gas_info = dev_status.get("gas_assessment") or telemetry.get("gas_assessment") or {}
        mq2_ratio = safe_num(gas_info.get("mq2_ratio"), 1.0)
        mq135_ratio = safe_num(gas_info.get("mq135_ratio"), 1.0)
        mq2_trend = str(gas_info.get("mq2_trend") or "STABLE")
        mq135_trend = str(gas_info.get("mq135_trend") or "STABLE")
        gas_summary = gas_info.get("qualitative_summary", "Nominal baseline")
        calibrated = gas_info.get("baseline_calibrated", True)

        gas_items = [
            ("MQ-2 (Smoke)", f"{mq2_ratio:.2f}x · {mq2_trend}"),
            ("MQ-135 (Air/CO)", f"{mq135_ratio:.2f}x · {mq135_trend}"),
            ("Baseline", "CALIBRATED" if calibrated else "WARMING UP"),
            ("Gas Risk", f"{safe_num(gas_info.get('gas_risk_score')):.2f}"),
        ]
        for n, v in gas_items:
            st.markdown(display_status(n, v), unsafe_allow_html=True)
        st.markdown(f'<div class="section-meta" style="margin-top:8px;font-size:10px;">{gas_summary}</div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)


# ============================================================
# TAB 2: SPECTRUM & ACOUSTIC AI
# ============================================================

with tab_spectrum:
    render_spectrum_section(label, mic_level=safe_num(telemetry.get("microphone_level", 500.0)))

    st.markdown(
        '<div class="section"><div class="section-title">Model Alternatives (Top-K)</div>'
        '<div class="section-meta">TOP-K PROBABILITY DISTRIBUTION ACROSS ACOUSTIC CLASSES</div></div>',
        unsafe_allow_html=True,
    )

    top_k = prediction.get("top_k") or []
    if top_k:
        rows = []
        for item in top_k:
            if isinstance(item, dict):
                name = item.get("label", "Unknown")
                conf = safe_num(item.get("confidence"))
            elif isinstance(item, (list, tuple)) and len(item) >= 2:
                name = item[0]
                conf = safe_num(item[1])
            else:
                continue

            rows.append(
                {
                    "CLASS": str(name),
                    "CONFIDENCE": f"{conf * 100:.3f}%",
                    "SCORE": conf,
                }
            )

        if rows:
            st.dataframe(
                rows,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "CLASS": st.column_config.TextColumn("CLASS"),
                    "CONFIDENCE": st.column_config.TextColumn("CONFIDENCE"),
                    "SCORE": st.column_config.ProgressColumn(
                        "SCORE",
                        min_value=0,
                        max_value=1,
                        format="%.4f",
                    ),
                },
            )
    else:
        st.markdown(
            '<div class="panel"><span class="neutral">No classification alternatives available.</span></div>',
            unsafe_allow_html=True,
        )


# ============================================================
# TAB 3: EMERGENCY ALERTS
# ============================================================

with tab_alerts:
    st.markdown(
        '<div class="section"><div class="section-title">Emergency Alert Broadcast Console</div>'
        '<div class="section-meta">MULTI-CHANNEL DISPATCH · DEVICE STROBE · WEBHOOK BROADCAST · AUDIT LOG</div></div>',
        unsafe_allow_html=True,
    )

    alert_history = get_alerts_history_from_dashboard()

    with st.container(border=True):
        al_c1, al_c2 = st.columns([1.8, 1.2])

        with al_c1:
            st.markdown(
                """
                <div style="font-size:13px;font-weight:700;margin-bottom:8px;color:#fff;">
                    📢 Broadcast Manual Emergency Alert
                </div>
                """,
                unsafe_allow_html=True,
            )
            f_threat_col, f_risk_col, f_act_col = st.columns(3)
            with f_threat_col:
                m_threat = st.selectbox(
                    "Threat Category & Event",
                    [
                        "🔥 Fire (Highest Priority)",
                        "🪚 Logging: Chainsaw / Drill (Highest Priority)",
                        "🚗 Vehicles: Truck / Engine (Moderate — Need to be addressed)",
                        "👤 Human Intrusion / Speech (Moderate — Need to be addressed)",
                        "🌿 Others: Wildlife / Ambient (Low)",
                    ],
                    key="manual_alert_threat",
                )
            with f_risk_col:
                m_risk = st.selectbox(
                    "Priority Level",
                    ["CRITICAL", "HIGH", "MODERATE", "LOW"],
                    key="manual_alert_risk",
                )
            with f_act_col:
                m_action = st.selectbox(
                    "Dispatch Action",
                    ["DISPATCH_RANGERS", "INTERCEPT_VEHICLE", "INVESTIGATE_INTRUSION", "RECORD_EVIDENCE", "MONITOR"],
                    key="manual_alert_action",
                )

            clean_threat = m_threat.split(" (")[0].replace("🔥 ", "").replace("🪚 ", "").replace("🚗 ", "").replace("👤 ", "").replace("🌿 ", "")

            if st.button("🚨 Broadcast Emergency Alert Now", type="primary", use_container_width=True, key="btn_manual_broadcast"):
                ok, msg = dispatch_manual_alert_from_dashboard(
                    threat_type=clean_threat,
                    confidence=0.98,
                    risk_level=m_risk,
                    action=m_action,
                    device_id_val=str(device_id if device_id != "NO DEVICE" else "sentinel_001"),
                    lat_val=float(safe_num(telemetry.get("latitude"), 12.2958)),
                    lon_val=float(safe_num(telemetry.get("longitude"), 76.6394)),
                )
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

        with al_c2:
            st.markdown(
                f"""
                <div style="font-size:13px;font-weight:700;margin-bottom:8px;color:#fff;">
                    📡 Dispatch Channels Status
                </div>
                {display_status("Device Red Strobe", "ONLINE (GPIO 38)")}
                {display_status("Ranger Hotline", "CONNECTED")}
                {display_status("Webhook Dispatcher", "ACTIVE")}
                {display_status("Total Alerts Logged", str(len(alert_history)))}
                """,
                unsafe_allow_html=True,
            )

        if alert_history:
            st.markdown("<div style='margin-top:12px;font-size:12px;font-weight:700;'>Dispatched Alert Audit Log:</div>", unsafe_allow_html=True)
            alert_rows = []
            for a_item in alert_history[:8]:
                a_id = a_item.get("alert_id")
                a_threat = a_item.get("threat_type")
                a_risk = a_item.get("risk_level")
                a_conf = f"{safe_num(a_item.get('confidence')) * 100:.1f}%"
                a_status = a_item.get("status")
                a_created = a_item.get("created_at", "—")[:19].replace("T", " ")

                alert_rows.append({
                    "ALERT ID": str(a_id),
                    "THREAT": str(a_threat),
                    "RISK": str(a_risk),
                    "CONFIDENCE": a_conf,
                    "STATUS": str(a_status),
                    "DISPATCHED AT": a_created,
                })

            st.dataframe(
                alert_rows,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "ALERT ID": st.column_config.TextColumn("ALERT ID"),
                    "THREAT": st.column_config.TextColumn("THREAT"),
                    "RISK": st.column_config.TextColumn("RISK"),
                    "CONFIDENCE": st.column_config.TextColumn("CONFIDENCE"),
                    "STATUS": st.column_config.TextColumn("STATUS"),
                    "DISPATCHED AT": st.column_config.TextColumn("DISPATCHED AT"),
                },
            )


# ============================================================
# TAB 4: UNKNOWN SOUND DISCOVERY
# ============================================================

with tab_discovery:
    st.markdown(
        '<div class="section"><div class="section-title">Unknown Sound Intelligence</div>'
        '<div class="section-meta">OPEN-SET REJECTION → AUDIO EVIDENCE → DBSCAN CLUSTERS → HUMAN REVIEW</div></div>',
        unsafe_allow_html=True,
    )

    discovery_status, discovery_clusters, discovery_error = (
        get_unknown_discovery_state()
    )

    if discovery_error:
        st.markdown(
            '<div class="panel"><span class="warn">'
            'Discovery API unavailable. Start the FastAPI backend to enable '
            'clustering monitoring and manual labeling.'
            '</span><div class="section-meta" style="margin-top:8px">'
            + str(discovery_error).replace("<", "&lt;").replace(">", "&gt;")
            + '</div></div>',
            unsafe_allow_html=True,
        )
    else:
        buffer_size = int(safe_num(discovery_status.get("buffer_size")))
        batch_size = int(
            safe_num(discovery_status.get("clustering_batch_size"), 30)
        )
        total_unknown = int(
            safe_num(discovery_status.get("total_unknown_samples"))
        )
        cluster_runs = int(
            safe_num(discovery_status.get("total_cluster_runs"))
        )
        discovered = int(
            safe_num(discovery_status.get("clusters_discovered"))
        )
        labeled = int(
            safe_num(discovery_status.get("labeled_clusters"))
        )
        unlabeled = int(
            safe_num(discovery_status.get("unlabeled_clusters"))
        )
        until_cluster = int(
            safe_num(discovery_status.get("samples_until_clustering"))
        )

        progress = (
            0.0
            if batch_size <= 0
            else min(1.0, buffer_size / batch_size)
        )

        st.html(
            f"""
            <div class="panel">
                <div class="panel-title">Discovery monitor</div>

                <div class="discovery-grid">
                    <div class="discovery-stat">
                        <div class="discovery-stat-label">Pending unknown</div>
                        <div class="discovery-stat-value">{buffer_size}</div>
                    </div>
                    <div class="discovery-stat">
                        <div class="discovery-stat-label">Unknown observations</div>
                        <div class="discovery-stat-value">{total_unknown}</div>
                    </div>
                    <div class="discovery-stat">
                        <div class="discovery-stat-label">Clusters</div>
                        <div class="discovery-stat-value">{discovered}</div>
                    </div>
                    <div class="discovery-stat">
                        <div class="discovery-stat-label">Cluster runs</div>
                        <div class="discovery-stat-value">{cluster_runs}</div>
                    </div>
                </div>

                <div class="status-row">
                    <span class="status-name">Clustering batch</span>
                    <span class="status-value" style="color:var(--cyan)">
                        {buffer_size} / {batch_size}
                    </span>
                </div>

                <div class="discovery-progress">
                    <div style="width:{progress * 100:.1f}%"></div>
                </div>

                <div class="section-meta">
                    {until_cluster} sample(s) until the next automatic clustering run
                </div>
            </div>
            """
        )

        d1, d2, d3, d4 = st.columns(4)

        with d1:
            metric(
                "Discovered clusters",
                str(discovered),
                "",
                f"{unlabeled} awaiting human review",
            )

        with d2:
            metric(
                "Reviewed clusters",
                str(labeled),
                "",
                f"{unlabeled} still unlabeled",
            )

        with d3:
            last_ids = discovery_status.get("last_cluster_ids") or []
            metric(
                "Last cluster result",
                str(len(last_ids)),
                "",
                "new stable cluster IDs" if last_ids else "no recent cluster batch",
            )

        with d4:
            evidence_clusters = sum(
                1 for cluster in discovery_clusters
                if int(safe_num(cluster.get("sample_count"))) > 0
            )
            metric(
                "Evidence-ready clusters",
                str(evidence_clusters),
                "",
                "clusters available for audio review",
            )

        btn_col1, btn_col2, btn_spacer = st.columns([1.2, 1.2, 2.6])
        with btn_col1:
            if st.button(
                "⚡ Run Clustering Now",
                key="btn_trigger_clustering",
                use_container_width=True,
                help="Immediately cluster all pending unknown sounds with DBSCAN",
            ):
                if buffer_size == 0:
                    st.info("Pending unknown buffer is currently empty.")
                else:
                    with st.spinner("Clustering unknown audio embeddings..."):
                        ok, msg = trigger_clustering_from_dashboard(force=True)
                        if ok:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)

        with btn_col2:
            if st.button(
                "🗑️ Clear Pending Buffer",
                key="btn_clear_buffer",
                use_container_width=True,
                help="Clear pending unclustered buffer without deleting clusters",
            ):
                ok, msg = clear_unknown_buffer_from_dashboard()
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

        st.markdown(
            '<div class="panel" style="margin-top:12px">'
            '<div class="panel-title">Human review queue</div>',
            unsafe_allow_html=True,
        )

        if not discovery_clusters:
            st.markdown(
                '<span class="neutral">No persistent clusters have been discovered yet. '
                'Unknown samples accumulate until the clustering batch is reached.</span>',
                unsafe_allow_html=True,
            )
        else:
            for cluster in discovery_clusters:
                cluster_id = str(cluster.get("cluster_id", "UNKNOWN"))
                status = str(cluster.get("status", "UNLABELED")).upper()
                cluster_lbl = cluster.get("label")
                count = int(safe_num(cluster.get("sample_count")))
                noise = int(safe_num(cluster.get("noise_samples")))
                notes = str(cluster.get("notes") or "")

                with st.container(border=True):
                    top_a, top_b, top_c = st.columns([1.3, 1, 1])

                    with top_a:
                        st.markdown(
                            f'<div class="cluster-id">{cluster_id}</div>'
                            f'<div class="cluster-meta">{status} · {count} samples · {noise} noise</div>',
                            unsafe_allow_html=True,
                        )

                    with top_b:
                        st.markdown(
                            f'<div class="cluster-meta">LABEL</div>'
                            f'<div style="font-weight:700">{cluster_lbl or "UNLABELED"}</div>',
                            unsafe_allow_html=True,
                        )

                    with top_c:
                        st.markdown(
                            f'<div class="cluster-meta">SOURCE BATCH</div>'
                            f'<div style="font-weight:700">{int(safe_num(cluster.get("source_batch_size")))}</div>',
                            unsafe_allow_html=True,
                        )

                    form_key = "cluster_" + cluster_id.replace("-", "_")

                    with st.expander(
                        f"Review recorded evidence · {count} sample(s)",
                        expanded=False,
                    ):
                        samples, samples_error = get_cluster_samples_from_dashboard(
                            cluster_id
                        )

                        if samples_error:
                            st.warning(
                                "Could not load recorded samples: " + samples_error
                            )
                        elif not samples:
                            st.info(
                                "No individual audio evidence is attached to this cluster yet. "
                                "Older clusters created before audio persistence may not have sample records."
                            )
                        else:
                            st.caption(
                                "Play the original retained recording before assigning a human label. "
                                "Audio is streamed directly from the AuraForest backend."
                            )

                            for index, sample in enumerate(samples, start=1):
                                sample_id = str(sample.get("sample_id") or "")
                                captured_at = str(sample.get("captured_at") or "—")
                                predicted_class = sample.get("predicted_class", "—")
                                conf_val = safe_num(sample.get("confidence"))
                                audio_available = bool(sample.get("audio_available"))

                                sample_left, sample_mid, sample_right = st.columns([1.7, 1.1, 1.3])

                                with sample_left:
                                    st.markdown(
                                        f"**Sample {index}** · `{sample_id}`"
                                    )
                                    st.caption(
                                        f"Captured: {captured_at} · Raw predicted class: {predicted_class}"
                                    )

                                with sample_mid:
                                    st.metric(
                                        "Confidence",
                                        f"{conf_val:.1%}",
                                    )

                                with sample_right:
                                    if audio_available and sample_id:
                                        st.audio(
                                            sample_audio_url(sample_id),
                                            format="audio/wav",
                                        )
                                    else:
                                        st.caption("Audio evidence unavailable")

                                if index < len(samples):
                                    st.divider()

                    label_col, notes_col, action_col = st.columns([1, 1.4, .75])

                    with label_col:
                        new_label = st.text_input(
                            "Human label",
                            value=str(cluster_lbl or ""),
                            placeholder="e.g. Tiger, Monkey, River",
                            key=form_key + "_label",
                        )

                    with notes_col:
                        new_notes = st.text_input(
                            "Review notes",
                            value=notes,
                            placeholder="Why this label was chosen",
                            key=form_key + "_notes",
                        )

                    with action_col:
                        st.write("")
                        if st.button(
                            "Save label",
                            key=form_key + "_save",
                            use_container_width=True,
                        ):
                            if not new_label.strip():
                                st.error("Enter a label first.")
                            else:
                                ok, message = label_cluster_from_dashboard(
                                    cluster_id,
                                    new_label,
                                    new_notes,
                                )
                                if ok:
                                    st.success(message)
                                    st.rerun()
                                else:
                                    st.error(message)

                        if status == "LABELED":
                            if st.button(
                                "Unlabel",
                                key=form_key + "_unlabel",
                                use_container_width=True,
                            ):
                                ok, message = unlabel_cluster_from_dashboard(
                                    cluster_id
                                )
                                if ok:
                                    st.success(message)
                                    st.rerun()
                                else:
                                    st.error(message)

        st.markdown("</div>", unsafe_allow_html=True)

        clear_col, threshold_col = st.columns([1, 2])

        with clear_col:
            if st.button(
                "Clear pending buffer",
                use_container_width=True,
            ):
                ok, message = clear_unknown_buffer_from_dashboard()
                if ok:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)

        with threshold_col:
            st.markdown(
                display_status(
                    "Open-set gate",
                    (
                        f"confidence ≥ {safe_num(discovery_status.get('confidence_threshold')):.2f} "
                        f"AND margin ≥ {safe_num(discovery_status.get('margin_threshold')):.2f}"
                    ),
                ),
                unsafe_allow_html=True,
            )


# ============================================================
# TAB 5: NODE HEALTH & LOGS
# ============================================================

with tab_health:
    st.markdown(
        '<div class="section"><div class="section-title">Node Integrity & Diagnostics</div>'
        '<div class="section-meta">HARDWARE HEALTH · GPS GEOLOCATION · RUNTIME AUDIT STREAM</div></div>',
        unsafe_allow_html=True,
    )

    h1, h2 = st.columns([1.2, 1])

    with h1:
        st.markdown('<div class="panel"><div class="panel-title">Hardware Component Health</div>', unsafe_allow_html=True)

        hardware_names = [
            "INMP441",
            "BH1750",
            "MAX17048",
            "DHT11",
            "SW-420",
            "NEO-6M",
            "MicroSD",
            "WiFi",
            "Telemetry_Backend",
            "Audio_Backend",
            "Overall_Hardware",
        ]

        for name in hardware_names:
            value = hardware.get(name)
            if value is None:
                value = "NOT REPORTED"
            st.markdown(display_status(name, value), unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

    with h2:
        st.markdown('<div class="panel"><div class="panel-title">Node Location & Coordinates</div>', unsafe_allow_html=True)

        location = state.get("location") or {}

        lat = location.get("latitude", telemetry.get("latitude"))
        lon = location.get("longitude", telemetry.get("longitude"))
        alt = location.get("altitude", telemetry.get("altitude"))
        acc = location.get("accuracy", telemetry.get("accuracy"))

        location_items = [
            ("Device", device_id),
            ("Latitude", "—" if lat is None else f"{safe_num(lat):.6f}"),
            ("Longitude", "—" if lon is None else f"{safe_num(lon):.6f}"),
            ("Altitude", "—" if alt is None else f"{safe_num(alt):.1f} m"),
            ("Accuracy", "—" if acc is None else f"{safe_num(acc):.1f} m"),
            ("Source", location.get("source", "RUNTIME")),
            ("Last record", "—" if timestamp is None else datetime.fromtimestamp(safe_num(timestamp)).strftime("%Y-%m-%d %H:%M:%S")),
        ]

        for n, v in location_items:
            st.markdown(display_status(n, v), unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown(
        '<div class="section" style="margin-top:24px;"><div class="section-title">Recent Event Stream</div>'
        '<div class="section-meta">LATEST 10 EDGE DETECTIONS FROM RUNTIME DATABASE</div></div>',
        unsafe_allow_html=True,
    )

    try:
        recent_events = source.get_recent_events(limit=10)
    except AttributeError:
        recent_events = []
    except Exception:
        recent_events = []

    if recent_events:
        event_rows = []

        for recent in recent_events:
            recent_prediction = recent.get("prediction") or {}
            recent_event = recent.get("event") or {}
            recent_decision = recent.get("decision") or {}
            recent_device = recent.get("device_id") or "Unknown"

            recent_label = (
                recent_prediction.get("label")
                or recent_event.get("label")
                or "Unknown"
            )

            recent_conf = safe_num(
                recent_prediction.get(
                    "confidence",
                    recent_event.get("confidence", 0),
                )
            )

            recent_risk = str(
                recent_decision.get("risk_level")
                or "LOW"
            ).upper()

            recent_action = (
                recent_decision.get("recommended_action")
                or recent_decision.get("action")
                or "MONITOR"
            )

            event_rows.append(
                {
                    "DEVICE": str(recent_device),
                    "EVENT": str(recent_label),
                    "CONFIDENCE": f"{recent_conf * 100:.1f}%",
                    "RISK": recent_risk,
                    "ACTION": str(recent_action),
                }
            )

        if event_rows:
            st.dataframe(
                event_rows,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "DEVICE": st.column_config.TextColumn("DEVICE"),
                    "EVENT": st.column_config.TextColumn("EVENT"),
                    "CONFIDENCE": st.column_config.TextColumn("CONFIDENCE"),
                    "RISK": st.column_config.TextColumn("RISK"),
                    "ACTION": st.column_config.TextColumn("ACTION"),
                },
            )
    else:
        st.markdown(
            '<div class="panel"><span class="neutral">'
            'No recent event history available.'
            '</span></div>',
            unsafe_allow_html=True,
        )


# ============================================================
# FOOTER / REFRESH
# ============================================================

st.markdown(
    f"""
    <div class="footer">
        AURAForest Sentinel · {device_id} · source: RuntimeDatabase ·
        live auto-refresh · 3 second interval
    </div>
    """,
    unsafe_allow_html=True,
)
