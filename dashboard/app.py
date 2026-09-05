"""
AuraForest — Sentinel Dashboard
Completely redesigned Streamlit UI.

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

# Existing project data source
from runtime_data_source import RuntimeDataSource
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
    initial_sidebar_state="collapsed",
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
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

:root {
    --bg: #070b0d;
    --panel: #0d1316;
    --panel-2: #11191d;
    --line: #203036;
    --text: #edf5f2;
    --muted: #7f9290;
    --green: #7cf0b2;
    --cyan: #73d9e8;
    --amber: #f2c66d;
    --red: #ff7777;
    --blue: #83a7ff;
}

html, body, [class*="css"] {
    font-family: "DM Sans", sans-serif;
}

.stApp {
    background:
        radial-gradient(circle at 15% 0%, rgba(64, 150, 116, .11), transparent 30%),
        radial-gradient(circle at 88% 12%, rgba(54, 133, 156, .08), transparent 28%),
        var(--bg);
    color: var(--text);
}

.block-container {
    max-width: 1500px;
    padding: 28px 42px 50px 42px;
}

header[data-testid="stHeader"] {
    background: transparent;
}

section[data-testid="stSidebar"] {
    display: none;
}

div[data-testid="stMetric"] {
    background: transparent;
}

.metric-card {
    background: linear-gradient(145deg, rgba(17,25,29,.96), rgba(10,15,18,.96));
    border: 1px solid var(--line);
    border-radius: 18px;
    padding: 19px 20px;
    min-height: 126px;
    box-shadow: 0 15px 45px rgba(0,0,0,.18);
}

.metric-label {
    color: var(--muted);
    font-size: 12px;
    letter-spacing: .08em;
    text-transform: uppercase;
    margin-bottom: 10px;
}

.metric-value {
    color: var(--text);
    font-size: 29px;
    line-height: 1;
    font-weight: 700;
}

.metric-unit {
    color: var(--muted);
    font-size: 13px;
    margin-left: 4px;
}

.metric-sub {
    color: var(--muted);
    font-size: 12px;
    margin-top: 11px;
}

.hero {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 25px;
    padding: 12px 0 27px 0;
    border-bottom: 1px solid var(--line);
    margin-bottom: 25px;
}

.brand {
    font-size: 31px;
    font-weight: 700;
    letter-spacing: -.04em;
}

.brand-mark {
    color: var(--green);
    margin-right: 10px;
}

.kicker {
    color: var(--green);
    font-family: "JetBrains Mono", monospace;
    font-size: 11px;
    letter-spacing: .16em;
    text-transform: uppercase;
    margin-bottom: 8px;
}

.subtitle {
    color: var(--muted);
    font-size: 13px;
    margin-top: 7px;
}

.live-pill {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    border: 1px solid rgba(124,240,178,.25);
    background: rgba(124,240,178,.06);
    color: var(--green);
    border-radius: 999px;
    padding: 9px 13px;
    font-family: "JetBrains Mono", monospace;
    font-size: 11px;
}

.dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: var(--green);
    box-shadow: 0 0 12px rgba(124,240,178,.8);
}

.section {
    margin-top: 28px;
    margin-bottom: 12px;
}

.section-title {
    font-size: 14px;
    font-weight: 700;
    letter-spacing: .02em;
}

.section-meta {
    color: var(--muted);
    font-size: 11px;
    font-family: "JetBrains Mono", monospace;
    margin-top: 3px;
}

.panel {
    background: linear-gradient(145deg, rgba(15,22,25,.96), rgba(9,14,16,.96));
    border: 1px solid var(--line);
    border-radius: 18px;
    padding: 20px;
    height: 100%;
}

.panel-title {
    font-size: 13px;
    font-weight: 700;
    margin-bottom: 16px;
}

.big-event {
    border-radius: 20px;
    padding: 27px;
    border: 1px solid var(--line);
    background:
        radial-gradient(circle at 85% 15%, rgba(124,240,178,.10), transparent 25%),
        linear-gradient(145deg, #101a1d, #0b1114);
}

.event-label {
    font-size: 42px;
    font-weight: 700;
    letter-spacing: -.04em;
    margin: 5px 0 12px;
}

.event-caption {
    color: var(--muted);
    font-size: 12px;
}

.confidence {
    font-family: "JetBrains Mono", monospace;
    color: var(--green);
    font-size: 18px;
}

.bar {
    height: 7px;
    background: #182327;
    border-radius: 99px;
    overflow: hidden;
    margin-top: 9px;
}

.bar > div {
    height: 100%;
    border-radius: 99px;
    background: var(--green);
}

.status-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 11px 0;
    border-bottom: 1px solid rgba(32,48,54,.65);
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
}

.ok { color: var(--green); }
.warn { color: var(--amber); }
.bad { color: var(--red); }
.neutral { color: var(--muted); }

.decision-box {
    border-radius: 16px;
    border: 1px solid var(--line);
    padding: 18px;
    margin-bottom: 10px;
}

.decision-risk {
    font-size: 23px;
    font-weight: 700;
}

.decision-action {
    color: var(--green);
    font-family: "JetBrains Mono", monospace;
    font-size: 12px;
    margin-top: 4px;
}

.code-value {
    font-family: "JetBrains Mono", monospace;
    color: #b9cbc7;
    font-size: 11px;
}

.chip {
    display: inline-block;
    border: 1px solid var(--line);
    background: rgba(255,255,255,.02);
    border-radius: 999px;
    padding: 6px 9px;
    color: var(--muted);
    font-family: "JetBrains Mono", monospace;
    font-size: 10px;
    margin: 3px 4px 3px 0;
}

.footer {
    color: #526563;
    font-family: "JetBrains Mono", monospace;
    font-size: 10px;
    text-align: center;
    padding-top: 30px;
}

[data-testid="stDataFrame"] {
    border: 1px solid var(--line);
    border-radius: 14px;
}

button[kind="secondary"] {
    border-radius: 10px;
    border: 1px solid var(--line);
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
    background: rgba(255,255,255,.018);
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
    background: var(--cyan);
    border-radius: 99px;
}
.cluster-card {
    border: 1px solid var(--line);
    border-radius: 14px;
    background: rgba(255,255,255,.018);
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


def metric(label: str, value: str, unit: str = "", sub: str = "") -> None:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
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
    """Call the live AuraForest backend discovery API."""
    url = f"{AURA_API_URL}{path}"
    body = None
    headers = {"Accept": "application/json"}

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


# ============================================================
# LOAD RUNTIME
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
# HEADER
# ============================================================

st.markdown(
    f"""
    <div class="hero">
        <div>
            <div class="kicker">AURAForest / EDGE INTELLIGENCE</div>
            <div class="brand"><span class="brand-mark">◈</span>Sentinel</div>
            <div class="subtitle">
                Environmental acoustic intelligence · adaptive edge monitoring · autonomous event triage
            </div>
        </div>
        <div class="live-pill"><span class="dot"></span>RUNTIME CONNECTED</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# TOP TELEMETRY
# ============================================================

st.markdown(
    '<div class="section"><div class="section-title">Live telemetry</div>'
    '<div class="section-meta">EDGE SENSOR SNAPSHOT</div></div>',
    unsafe_allow_html=True,
)

c1, c2, c3, c4, c5 = st.columns(5)

with c1:
    metric(
        "Temperature",
        f"{safe_num(telemetry.get('temperature')):.1f}",
        "°C",
        "ambient thermal state",
    )

with c2:
    metric(
        "Humidity",
        f"{safe_num(telemetry.get('humidity')):.1f}",
        "%",
        "relative humidity",
    )

with c3:
    metric(
        "Light",
        f"{safe_num(telemetry.get('light_level')):.1f}",
        "lux",
        "BH1750 optical level",
    )

with c4:
    metric(
        "Battery",
        f"{safe_num(telemetry.get('battery_percent')):.1f}",
        "%",
        f"{safe_num(telemetry.get('battery_voltage')):.3f} V",
    )

with c5:
    vibration = telemetry.get("vibration_detected")
    metric(
        "Vibration",
        "DETECTED" if vibration else "CLEAR",
        "",
        "SW-420 state",
    )

# ============================================================
# AI EVENT + CADIE
# ============================================================

st.markdown(
    '<div class="section"><div class="section-title">Acoustic intelligence</div>'
    '<div class="section-meta">MODEL OUTPUT → EVENT ENGINE → DECISION ENGINE</div></div>',
    unsafe_allow_html=True,
)

left, mid, right = st.columns([1.35, 1, 1])

with left:
    label = event.get("label") or prediction.get("label") or "Waiting"
    conf = safe_num(
        event.get("confidence", prediction.get("confidence", 0.0))
    )
    detected = event.get("detected", False)

    st.markdown(
        f"""
        <div class="big-event">
            <div class="kicker">CURRENT ACOUSTIC SIGNAL</div>
            <div class="event-label">{label}</div>
            <div class="event-caption">
                {"EVENT DETECTED" if detected else "NO ACTIVE EVENT"}
                · class {event.get("class_id", prediction.get("class_id", "—"))}
            </div>
            <div style="margin-top:24px">
                <div style="display:flex;justify-content:space-between">
                    <span class="event-caption">MODEL CONFIDENCE</span>
                    <span class="confidence">{confidence(conf)}</span>
                </div>
                <div class="bar"><div style="width:{max(0,min(100,conf*100))}%"></div></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with mid:
    risk = str(cadie.get("risk_level") or "LOW").upper()
    risk_cls = status_class(
        "FAILED" if risk == "HIGH" else ("WORKING" if risk == "LOW" else "UNKNOWN")
    )

    st.markdown(
        f"""
        <div class="panel">
            <div class="panel-title">Decision engine</div>
            <div class="decision-box">
                <div class="kicker">RISK LEVEL</div>
                <div class="decision-risk {risk_cls}">{risk}</div>
                <div class="decision-action">{cadie.get("action", "WAITING")}</div>
            </div>
            {display_status("Decision score", f"{safe_num(cadie.get('score')):.3f}")}
            {display_status("Attention", "YES" if cadie.get("requires_attention") else "NO")}
            {display_status("Signal", cadie.get("signal", label))}
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
        '<div class="panel-title">Inference performance</div>'
        f'{display_status("Model", model_name)}'
        f"{display_status('Inference', f'{inference_ms:.2f} ms')}"
        f'{display_status("Unknown discovery", "YES" if unknown_detected else "NO")}'
        f'{display_status("Buffer", str(buffer_size))}'
        f'{display_status("Environment", environment_type)}'
        '</div>'
    )

    st.markdown(inference_panel, unsafe_allow_html=True)

# ============================================================
# ENVIRONMENT + ADAPTIVE POLICY
# ============================================================

st.markdown(
    '<div class="section"><div class="section-title">Context & adaptation</div>'
    '<div class="section-meta">THE EDGE NODE ADJUSTS ITS OPERATING POLICY FROM OBSERVED CONDITIONS</div></div>',
    unsafe_allow_html=True,
)

a, b, c = st.columns([1, 1, 1])

with a:
    st.markdown('<div class="panel"><div class="panel-title">Environment profile</div>', unsafe_allow_html=True)
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
    st.markdown('<div class="panel"><div class="panel-title">Adaptive policy</div>', unsafe_allow_html=True)
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
    st.markdown('<div class="panel"><div class="panel-title">Priority map</div>', unsafe_allow_html=True)
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


# ============================================================
# UNKNOWN SOUND DISCOVERY
# ============================================================

st.markdown(
    '<div class="section"><div class="section-title">Unknown sound intelligence</div>'
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

    # Use st.html here rather than st.markdown. The generated HTML is
    # intentionally indented inside the Python f-string; Streamlit's
    # Markdown parser can interpret that indentation as a code block and
    # display the HTML source literally.
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

    # Manual review / labeling workflow.
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
            label = cluster.get("label")
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
                        f'<div style="font-weight:700">{label or "UNLABELED"}</div>',
                        unsafe_allow_html=True,
                    )

                with top_c:
                    st.markdown(
                        f'<div class="cluster-meta">SOURCE BATCH</div>'
                        f'<div style="font-weight:700">{int(safe_num(cluster.get("source_batch_size")))}</div>',
                        unsafe_allow_html=True,
                    )

                form_key = "cluster_" + cluster_id.replace("-", "_")

                # --------------------------------------------------
                # Recorded sample evidence
                # --------------------------------------------------
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
                            confidence = safe_num(sample.get("confidence"))
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
                                    f"{confidence:.1%}",
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
                        value=str(label or ""),
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
# HARDWARE + LOCATION
# ============================================================

st.markdown(
    '<div class="section"><div class="section-title">Node integrity</div>'
    '<div class="section-meta">HARDWARE · LOCATION · RUNTIME IDENTITY</div></div>',
    unsafe_allow_html=True,
)

h1, h2 = st.columns([1.2, 1])

with h1:
    st.markdown('<div class="panel"><div class="panel-title">Hardware health</div>', unsafe_allow_html=True)

    # Known deployed hardware list. Values are read from the runtime state
    # when available; otherwise show "NOT REPORTED" instead of inventing status.
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
    st.markdown('<div class="panel"><div class="panel-title">Node location</div>', unsafe_allow_html=True)

    location = state.get("location") or {}

    # RuntimeDataSource currently exposes coordinates inside telemetry.
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

# ============================================================
# RECENT EVENTS
# ============================================================

st.markdown(
    '<div class="section"><div class="section-title">Recent detections</div>'
    '<div class="section-meta">LATEST EDGE EVENTS FROM RUNTIME DATABASE</div></div>',
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
# TOP-K
# ============================================================

st.markdown(
    '<div class="section"><div class="section-title">Model alternatives</div>'
    '<div class="section-meta">TOP-K CLASSIFICATION OUTPUT</div></div>',
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

if st.button("↻ Refresh now", type="secondary", use_container_width=False):
    st.rerun()

