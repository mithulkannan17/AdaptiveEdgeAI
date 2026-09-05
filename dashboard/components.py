"""
Dashboard Components
====================

Reusable visual components for the Adaptive Edge Intelligence
Platform dashboard.

This module is presentation-only.

Data flow:

    Simulator / Backend
            ↓
        app.py
            ↓
        components.py
            ↓
        Streamlit UI

No hardware access, database access, or AI inference belongs
in this module.
"""

from __future__ import annotations

import html
import math
from typing import Any, Iterable

import streamlit as st

from styles import risk_class


# ==========================================================
# HTML Helper
# ==========================================================

def render_html(
    content: str,
) -> None:
    """
    Render HTML using Streamlit's native HTML renderer.

    Using st.html() prevents Streamlit from interpreting
    dashboard HTML as a Markdown code block.
    """

    st.html(content)


def _safe(
    value: Any,
    default: str = "—",
) -> str:
    """
    Convert a value into HTML-safe text.
    """

    if value is None:

        return default

    return html.escape(
        str(value)
    )


def _number(
    value: Any,
    digits: int = 1,
    default: str = "—",
) -> str:
    """
    Format a numeric value safely.
    """

    if value is None:

        return default

    try:

        return f"{float(value):.{digits}f}"

    except (
        TypeError,
        ValueError,
    ):

        return default


# ==========================================================
# Header
# ==========================================================

def render_header(
    node_id: str,
    location_name: str,
    self_calibration_status: str = "BASELINED",
    aebe_status: str = "ACTIVE",
    battery_percent: float | None = None,
    network_status: str = "LINK OK",
    network_type: str = "WI-FI UDP",
    clock_text: str = "",
) -> None:
    """
    Render the main node header.

    Parameters are deliberately data-driven so the same
    component can later consume real ESP32/backend values.
    """

    battery_text = (
        f"{_number(battery_percent, 0)}%"
        if battery_percent is not None
        else "—"
    )

    render_html(

        f"""
        <div class="dashboard-header">

            <div>

                <span class="node-title">
                    {_safe(node_id)}
                </span>

                <span class="node-subtitle">
                    {_safe(location_name)}
                    ·
                    ADAPTIVE EDGE INTELLIGENCE PLATFORM
                </span>

            </div>

            <div class="header-status-container">

                <div class="status-pill">

                    <span class="status-dot"></span>

                    SELF-CAL
                    <b>{_safe(self_calibration_status)}</b>

                </div>

                <div class="status-pill">

                    <span class="status-dot"></span>

                    AEBE
                    <b>{_safe(aebe_status)}</b>

                </div>

                <div class="status-pill">

                    <span class="status-dot warning"></span>

                    BATT
                    <b>{battery_text}</b>

                </div>

                <div class="status-pill">

                    <span class="status-dot"></span>

                    {_safe(network_type)}
                    <b>{_safe(network_status)}</b>

                </div>

                {
                    f'''
                    <div class="status-pill">
                        {_safe(clock_text)}
                    </div>
                    '''
                    if clock_text
                    else ""
                }

            </div>

        </div>
        """

    )


# ==========================================================
# Section Header
# ==========================================================

def render_section_header(
    title: str,
    meta: str = "",
) -> None:
    """
    Render a small dashboard section heading.
    """

    meta_html = ""

    if meta:

        meta_html = f"""
        <span class="section-meta">
            {_safe(meta)}
        </span>
        """

    render_html(

        f"""
        <div class="section-header">

            <span class="section-title">
                {_safe(title)}
            </span>

            {meta_html}

        </div>
        """

    )


# ==========================================================
# Generic Panel
# ==========================================================

def render_panel(
    title: str,
    rows: Iterable[tuple[str, Any]],
) -> None:
    """
    Render a generic metric panel.
    """

    rows_html = ""

    for label, value in rows:

        rows_html += f"""
        <div class="metric-row">

            <span class="metric-label">
                {_safe(label)}
            </span>

            <span class="metric-value">
                {_safe(value)}
            </span>

        </div>
        """

    render_html(

        f"""
        <div class="dashboard-panel">

            <div class="panel-title">
                {_safe(title)}
            </div>

            {rows_html}

        </div>
        """

    )


# ==========================================================
# Environmental Conditions
# ==========================================================

def render_environmental_conditions(
    temperature: float | None,
    humidity: float | None,
    pressure: float | None,
    light_level: float | None,
) -> None:
    """
    Render environmental sensor conditions.
    """

    render_html(

        f"""
        <div class="dashboard-panel">

            <div class="panel-title">
                Environmental Conditions
            </div>

            <div class="metric-row">

                <span class="metric-label">
                    Temperature
                </span>

                <span class="metric-value">
                    {_number(temperature, 1)}
                    <span class="metric-unit">
                        °C
                    </span>
                </span>

            </div>

            <div class="metric-row">

                <span class="metric-label">
                    Humidity
                </span>

                <span class="metric-value">
                    {_number(humidity, 1)}
                    <span class="metric-unit">
                        %RH
                    </span>
                </span>

            </div>

            <div class="metric-row">

                <span class="metric-label">
                    Pressure
                </span>

                <span class="metric-value">
                    {_number(pressure, 1)}
                    <span class="metric-unit">
                        hPa
                    </span>
                </span>

            </div>

            <div class="metric-row">

                <span class="metric-label">
                    Ambient light
                </span>

                <span class="metric-value">
                    {_number(light_level, 1)}
                    <span class="metric-unit">
                        lux
                    </span>
                </span>

            </div>

        </div>
        """

    )


# ==========================================================
# Battery
# ==========================================================

def render_battery(
    battery_percent: float | None,
    battery_voltage: float | None = None,
    charging: bool = False,
) -> None:
    """
    Render the battery status panel.

    The component accepts both percentage and voltage so
    MAX17048 telemetry can later be passed directly.
    """

    percentage = 0.0

    if battery_percent is not None:

        try:

            percentage = max(
                0.0,
                min(
                    100.0,
                    float(battery_percent),
                ),
            )

        except (
            TypeError,
            ValueError,
        ):

            percentage = 0.0

    if percentage <= 20:

        fill_class = "danger"

    elif percentage <= 40:

        fill_class = "warning"

    else:

        fill_class = ""

    charging_text = (
        "CHARGING"
        if charging
        else "DISCHARGING"
    )

    voltage_text = (
        f"{_number(battery_voltage, 2)} V"
        if battery_voltage is not None
        else "—"
    )

    render_html(

        f"""
        <div class="dashboard-panel">

            <div class="panel-title">
                Battery Status
            </div>

            <div class="battery-container">

                <div class="battery-track">

                    <div
                        class="battery-fill {fill_class}"
                        style="width:{percentage:.1f}%"
                    ></div>

                    <div class="battery-terminal"></div>

                </div>

                <div class="battery-info">

                    <span>
                        {_number(percentage, 0)}%
                    </span>

                    <span>
                        {_safe(charging_text)}
                    </span>

                </div>

                <div class="metric-row">

                    <span class="metric-label">
                        Voltage
                    </span>

                    <span class="metric-value">
                        {_safe(voltage_text)}
                    </span>

                </div>

            </div>

        </div>
        """

    )


# ==========================================================
# Node Health / AEBE
# ==========================================================

def render_node_health(
    duty_cycle: float | None,
    sample_interval: int | float | None,
    storage_used_gb: float | None,
    storage_total_gb: float | None,
    status_message: str = "",
) -> None:
    """
    Render Adaptive Behaviour Engine node-health status.
    """

    if (
        storage_used_gb is not None
        and storage_total_gb is not None
        and float(storage_total_gb) > 0
    ):

        storage_percentage = (
            float(storage_used_gb)
            /
            float(storage_total_gb)
            *
            100.0
        )

    else:

        storage_percentage = 0.0

    interval_text = (
        f"every {sample_interval} sec"
        if sample_interval is not None
        else "—"
    )

    message_html = ""

    if status_message:

        message_html = f"""
        <div
            style="
                color:#76907f;
                font-size:10px;
                line-height:1.6;
                margin-top:14px;
                font-style:italic;
            "
        >
            {_safe(status_message)}
        </div>
        """

    render_html(

        f"""
        <div class="dashboard-panel">

            <div class="panel-title">
                Node Health · AEBE
            </div>

            <div class="metric-row">

                <span class="metric-label">
                    Duty cycle
                </span>

                <span class="metric-value">
                    {_number(duty_cycle, 0)}%
                </span>

            </div>

            <div class="metric-row">

                <span class="metric-label">
                    Sample interval
                </span>

                <span class="metric-value">
                    {_safe(interval_text)}
                </span>

            </div>

            <div class="metric-row">

                <span class="metric-label">
                    Storage used
                </span>

                <span class="metric-value">
                    {_number(storage_percentage, 1)}%
                </span>

            </div>

            {message_html}

        </div>
        """

    )


# ==========================================================
# Acoustic Waveform
# ==========================================================

def render_waveform(
    samples: Iterable[float] | None = None,
    height: int = 55,
) -> None:
    """
    Render a lightweight acoustic waveform.

    samples:
        Normalized values between -1 and +1.

    If samples are not supplied, a small deterministic
    waveform is generated only for visual rendering.
    """

    if samples is None:

        generated = []

        for index in range(64):

            value = (

                0.38
                * math.sin(
                    index * 0.55
                )

                + 0.18
                * math.sin(
                    index * 1.71
                )

                + 0.08
                * math.sin(
                    index * 3.2
                )

            )

            generated.append(value)

        samples = generated

    bars_html = ""

    values = list(samples)

    if not values:

        values = [0.0]

    for value in values:

        try:

            normalized = abs(
                float(value)
            )

        except (
            TypeError,
            ValueError,
        ):

            normalized = 0.0

        normalized = max(
            0.03,
            min(
                1.0,
                normalized,
            ),
        )

        bar_height = max(
            3,
            int(
                normalized
                * height
            ),
        )

        bars_html += f"""
        <div
            class="wave-bar"
            style="height:{bar_height}px"
        ></div>
        """

    render_html(

        f"""
        <div class="acoustic-container">

            <div class="waveform">

                {bars_html}

            </div>

        </div>
        """

    )


# ==========================================================
# Acoustic Classification
# ==========================================================

def render_acoustic_classification(
    label: str,
    confidence: float,
    alternate_classes: Iterable[tuple[str, float]]
    | None = None,
    waveform: Iterable[float] | None = None,
    feature_method: str = "Mel / spectral",
) -> None:
    """
    Render the acoustic classification panel.
    """

    confidence_value = max(
        0.0,
        min(
            100.0,
            float(confidence)
            if confidence is not None
            else 0.0,
        ),
    )

    alternate_html = ""

    if alternate_classes:

        alternate_items = []

        for alt_label, alt_confidence in (
            alternate_classes
        ):

            alternate_items.append(

                f"{_safe(alt_label)} "
                f"{_number(alt_confidence, 1)}%"

            )

        alternate_html = (
            " · ".join(
                alternate_items
            )
        )

    else:

        alternate_html = "—"

    render_html(

        f"""
        <div class="dashboard-panel">

            <div
                style="
                    display:flex;
                    justify-content:space-between;
                    align-items:center;
                    margin-bottom:12px;
                "
            >

                <div class="panel-title">
                    Acoustic Classification
                </div>

                <div
                    style="
                        color:#50685a;
                        font-size:8px;
                    "
                >
                    CNN · {_safe(feature_method)}
                </div>

            </div>

            <div>

                {render_waveform_to_html(waveform)}

            </div>

            <div
                style="
                    display:flex;
                    justify-content:space-between;
                    align-items:baseline;
                    margin-top:12px;
                "
            >

                <span
                    style="
                        color:#e5eee7;
                        font-size:13px;
                        font-weight:700;
                    "
                >
                    {_safe(label)}
                </span>

                <span
                    style="
                        color:#78a96d;
                        font-size:12px;
                    "
                >
                    {confidence_value:.1f}%
                </span>

            </div>

            <div class="confidence-track">

                <div
                    class="confidence-fill"
                    style="
                        width:{confidence_value:.1f}%;
                    "
                ></div>

            </div>

            <div
                style="
                    color:#76907f;
                    font-size:9px;
                    margin-top:8px;
                "
            >
                Alternate classes:
                {_safe(alternate_html)}
            </div>

        </div>
        """

    )


def render_waveform_to_html(
    samples: Iterable[float] | None = None,
    height: int = 45,
) -> str:
    """
    Build waveform HTML without directly rendering it.

    Useful when the waveform needs to be embedded inside
    another component.
    """

    if samples is None:

        generated = []

        for index in range(64):

            value = (

                0.38
                * math.sin(
                    index * 0.55
                )

                + 0.18
                * math.sin(
                    index * 1.71
                )

                + 0.08
                * math.sin(
                    index * 3.2
                )

            )

            generated.append(value)

        samples = generated

    bars_html = ""

    values = list(samples)

    if not values:

        values = [0.0]

    for value in values:

        try:

            normalized = abs(
                float(value)
            )

        except (
            TypeError,
            ValueError,
        ):

            normalized = 0.0

        normalized = max(
            0.03,
            min(
                1.0,
                normalized,
            ),
        )

        bar_height = max(
            3,
            int(
                normalized
                * height
            ),
        )

        bars_html += f"""
        <div
            class="wave-bar"
            style="height:{bar_height}px"
        ></div>
        """

    return f"""
    <div class="acoustic-container">

        <div class="waveform">

            {bars_html}

        </div>

    </div>
    """


# ==========================================================
# Detection Pipeline
# ==========================================================

def render_detection_pipeline(
    feature_status: str,
    classification_status: str,
    priority_status: str,
    cadie_status: str,
    feature_confidence: float | None = None,
    priority_label: str = "",
) -> None:
    """
    Render the complete edge detection pipeline.

    Represents:

        Feature extraction
            ↓
        CNN classification
            ↓
        AEPE priority
            ↓
        CADIE decision
    """

    confidence_html = ""

    if feature_confidence is not None:

        confidence = max(
            0.0,
            min(
                100.0,
                float(feature_confidence),
            ),
        )

        confidence_html = f"""
        <div class="confidence-track">

            <div
                class="confidence-fill"
                style="width:{confidence:.1f}%"
            ></div>

        </div>
        """

    priority_html = ""

    if priority_label:

        priority_html = f"""
        <span
            class="pipeline-result"
            style="color:#ed6745;"
        >
            {_safe(priority_label)}
        </span>
        """

    render_html(

        f"""
        <div class="dashboard-panel">

            <div class="panel-title">
                Detection Pipeline
            </div>

            <div class="pipeline">

                <div class="pipeline-step">

                    <span class="pipeline-dot"></span>

                    <span>
                        Feature extraction
                        (Mel / spectral)
                    </span>

                    <span class="pipeline-result">
                        {_safe(feature_status)}
                    </span>

                </div>

                <div class="pipeline-step">

                    <span class="pipeline-dot"></span>

                    <span>
                        CNN classification
                    </span>

                    <span class="pipeline-result">
                        {_safe(classification_status)}
                    </span>

                </div>

                {confidence_html}

                <div class="pipeline-step">

                    <span class="pipeline-dot"></span>

                    <span>
                        AEPE priority score
                    </span>

                    {priority_html}

                </div>

                <div class="pipeline-step">

                    <span class="pipeline-dot"></span>

                    <span>
                        CADIE decision
                    </span>

                    <span class="pipeline-result">
                        {_safe(cadie_status)}
                    </span>

                </div>

            </div>

        </div>
        """

    )


# ==========================================================
# CADIE Risk Assessment
# ==========================================================

def render_cadie(
    risk_level: str,
    score: float,
    signal: str,
    baseline_delta: str,
    action: str,
    reason: str = "",
) -> None:
    """
    Render CADIE context-aware risk assessment.
    """

    css_risk = risk_class(
        risk_level
    )

    normalized_score = max(
        0.0,
        min(
            1.0,
            float(score)
            if score is not None
            else 0.0,
        ),
    )

    display_score = normalized_score

    reason_html = ""

    if reason:

        reason_html = f"""
        <div class="cadie-reason">
            {_safe(reason)}
        </div>
        """

    render_html(

        f"""
        <div class="dashboard-panel cadie-panel">

            <div
                style="
                    display:flex;
                    justify-content:space-between;
                    align-items:center;
                "
            >

                <div class="panel-title">
                    CADIE · Risk Assessment
                </div>

                <div
                    style="
                        color:#50685a;
                        font-size:8px;
                    "
                >
                    CONTEXT-AWARE
                </div>

            </div>

            <div class="cadie-risk">

                <div
                    class="risk-ring {css_risk}"
                    style="
                        --risk-progress:
                        {normalized_score * 100:.1f}%;
                    "
                >

                    <div
                        class="risk-label {css_risk}"
                    >
                        {_safe(risk_level).upper()}
                    </div>

                    <div class="risk-score">
                        SCORE
                        {display_score:.2f}
                    </div>

                </div>

            </div>

            <div class="cadie-reason">

                Signal:
                {_safe(signal)}

                <br>

                Baseline delta:
                {_safe(baseline_delta)}

            </div>

            {reason_html}

            <div class="cadie-action">

                ACTION:
                <b>
                    {_safe(action)}
                </b>

            </div>

        </div>
        """

    )


# ==========================================================
# Event Log
# ==========================================================

def render_event_log(
    events: Iterable[dict[str, Any]],
    max_events: int = 10,
) -> None:
    """
    Render recent detected events.

    Expected event dictionary fields may include:

        label
        confidence
        risk_level
        timestamp
        latitude
        longitude
        priority
    """

    event_list = list(events)

    event_list = event_list[
        :max_events
    ]

    items_html = ""

    if not event_list:

        items_html = """
        <div
            style="
                color:#50685a;
                padding:20px 5px;
                font-size:10px;
            "
        >
            No events recorded.
        </div>
        """

    for event in event_list:

        label = event.get(
            "label",
            "Unknown event",
        )

        confidence = event.get(
            "confidence"
        )

        risk_level = event.get(
            "risk_level",
            "LOW",
        )

        timestamp = event.get(
            "timestamp",
            "",
        )

        latitude = event.get(
            "latitude"
        )

        longitude = event.get(
            "longitude"
        )

        confidence_text = (

            f"conf "
            f"{_number(confidence, 1)}%"

            if confidence is not None

            else "conf —"

        )

        if (
            latitude is not None
            and longitude is not None
        ):

            gps_text = (

                f"GPS "
                f"{_number(latitude, 4)}, "
                f"{_number(longitude, 4)}"

            )

        else:

            gps_text = "GPS unavailable"

        css_risk = risk_class(
            risk_level
        )

        items_html += f"""
        <div class="event-item">

            <div class="event-top">

                <span class="event-name">
                    {_safe(label)}
                </span>

                <span class="event-time">
                    {_safe(timestamp)}
                </span>

            </div>

            <div class="event-meta">

                {_safe(gps_text)}
                ·
                {_safe(confidence_text)}

            </div>

            <div
                class="event-risk risk-{css_risk}"
            >
                {_safe(risk_level).upper()}
                RISK
            </div>

        </div>
        """

    render_html(

        f"""
        <div class="dashboard-panel">

            <div
                style="
                    display:flex;
                    justify-content:space-between;
                    align-items:center;
                "
            >

                <div class="panel-title">
                    Event Log
                </div>

                <div
                    style="
                        color:#50685a;
                        font-size:8px;
                    "
                >
                    {len(event_list)} RECENT
                </div>

            </div>

            <div class="event-log">

                {items_html}

            </div>

        </div>
        """

    )


# ==========================================================
# Map
# ==========================================================

def render_deployment_map(
    latitude: float,
    longitude: float,
    events: Iterable[dict[str, Any]] | None = None,
    radius_text: str = "RADIUS ~40M",
) -> None:
    """
    Render a lightweight deployment/event map.

    This is intentionally implemented without an external
    mapping dependency. GPS coordinates are displayed as
    relative event positions around the node.

    A real map provider can be integrated later without
    changing the dashboard's data contract.
    """

    event_markers = ""

    event_list = list(
        events or []
    )

    for index, event in enumerate(
        event_list[:12]
    ):

        event_lat = event.get(
            "latitude",
            latitude,
        )

        event_lon = event.get(
            "longitude",
            longitude,
        )

        try:

            delta_lat = (
                float(event_lat)
                - float(latitude)
            )

            delta_lon = (
                float(event_lon)
                - float(longitude)
            )

        except (
            TypeError,
            ValueError,
        ):

            delta_lat = 0.0

            delta_lon = 0.0

        # Approximate local projection.
        x = 50.0 + (
            delta_lon * 1200.0
        )

        y = 50.0 - (
            delta_lat * 1200.0
        )

        x = max(
            8.0,
            min(
                92.0,
                x,
            ),
        )

        y = max(
            8.0,
            min(
                92.0,
                y,
            ),
        )

        risk_level = event.get(
            "risk_level",
            "LOW",
        )

        css_risk = risk_class(
            risk_level
        )

        label = event.get(
            "label",
            "Event",
        )

        event_markers += f"""
        <div
            class="map-label"
            style="
                left:{x:.1f}%;
                top:{y:.1f}%;
            "
        >
            <span
                class="risk-{css_risk}"
            >
                ●
            </span>
            {_safe(label)}
        </div>
        """

    render_html(

        f"""
        <div
            style="
                display:flex;
                justify-content:space-between;
                align-items:center;
                margin-bottom:7px;
            "
        >

            <span class="section-title">
                Deployment Map · Event Trace
            </span>

            <span class="section-meta">
                {_safe(radius_text)}
            </span>

        </div>

        <div class="map-panel">

            <div class="map-grid"></div>

            <div class="map-node"></div>

            {event_markers}

        </div>

        <div
            style="
                display:flex;
                gap:20px;
                padding:10px 4px;
                color:#76907f;
                font-size:9px;
            "
        >

            <span class="risk-low">
                ● Low risk
            </span>

            <span class="risk-medium">
                ● Medium risk
            </span>

            <span class="risk-high">
                ● High risk
            </span>

            <span
                style="
                    margin-left:auto;
                "
            >
                GPS
                {_number(latitude, 4)}°N,
                {_number(longitude, 4)}°E
            </span>

        </div>
        """

    )


# ==========================================================
# Telemetry Card
# ==========================================================

def render_telemetry_card(
    index: str,
    label: str,
    value: float | str | None,
    unit: str,
    history: Iterable[float] | None = None,
) -> None:
    """
    Render one bottom telemetry card.
    """

    spark_values = list(
        history or []
    )

    if not spark_values:

        spark_values = [

            0.25
            + (
                0.15
                * math.sin(
                    i * 0.7
                )
            )

            for i in range(18)

        ]

    minimum = min(
        spark_values
    )

    maximum = max(
        spark_values
    )

    difference = (
        maximum
        - minimum
    )

    spark_html = ""

    for spark_value in spark_values:

        if difference == 0:

            height = 40

        else:

            height = (

                (
                    float(spark_value)
                    - minimum
                )
                /
                difference
                *
                70

            ) + 20

        height = max(
            8,
            min(
                100,
                height,
            ),
        )

        spark_html += f"""
        <span
            class="spark"
            style="
                height:{height:.1f}%;
            "
        ></span>
        """

    render_html(

        f"""
        <div class="telemetry-card">

            <span class="telemetry-index">
                {_safe(index)}
            </span>

            <div class="telemetry-label">
                {_safe(label)}
            </div>

            <div class="telemetry-value">

                {_safe(value)}

                <span class="telemetry-unit">
                    {_safe(unit)}
                </span>

            </div>

            <div class="sparkline">

                {spark_html}

            </div>

        </div>
        """

    )


# ==========================================================
# Complete Telemetry Strip
# ==========================================================

def render_telemetry_strip(
    telemetry: dict[str, Any],
    histories: dict[str, Iterable[float]]
    | None = None,
) -> None:
    """
    Render all six environmental/device telemetry cards.
    """

    histories = histories or {}

    cards = [

        (
            "01",
            "TEMPERATURE",
            _number(
                telemetry.get(
                    "temperature"
                ),
                1,
            ),
            "°C",
            "temperature",
        ),

        (
            "02",
            "HUMIDITY",
            _number(
                telemetry.get(
                    "humidity"
                ),
                1,
            ),
            "%RH",
            "humidity",
        ),

        (
            "03",
            "LIGHT",
            _number(
                telemetry.get(
                    "light_level"
                ),
                1,
            ),
            "lux",
            "light_level",
        ),

        (
            "04",
            "VIBRATION",
            _number(
                telemetry.get(
                    "vibration"
                ),
                2,
            ),
            "g",
            "vibration",
        ),

        (
            "05",
            "PRESSURE",
            _number(
                telemetry.get(
                    "pressure"
                ),
                1,
            ),
            "hPa",
            "pressure",
        ),

        (
            "06",
            "BATTERY",
            _number(
                telemetry.get(
                    "battery_voltage"
                ),
                2,
            ),
            "V",
            "battery_voltage",
        ),

    ]

    cards_html = ""

    for (
        index,
        label,
        value,
        unit,
        history_key,
    ) in cards:

        history = list(
            histories.get(
                history_key,
                [],
            )
        )

        spark_values = ""

        if not history:

            history = [
                0.4
                + 0.15
                * math.sin(
                    i * 0.55
                )
                for i in range(20)
            ]

        minimum = min(
            history
        )

        maximum = max(
            history
        )

        difference = (
            maximum
            - minimum
        )

        for spark_value in history:

            if difference == 0:

                height = 45

            else:

                height = (

                    (
                        float(spark_value)
                        - minimum
                    )
                    /
                    difference
                    *
                    65

                ) + 20

            height = max(
                8,
                min(
                    100,
                    height,
                ),
            )

            spark_values += f"""
            <span
                class="spark"
                style="
                    height:{height:.1f}%;
                "
            ></span>
            """

        cards_html += f"""
        <div class="telemetry-card">

            <span class="telemetry-index">
                {_safe(index)}
            </span>

            <div class="telemetry-label">
                {_safe(label)}
            </div>

            <div class="telemetry-value">

                {_safe(value)}

                <span class="telemetry-unit">
                    {_safe(unit)}
                </span>

            </div>

            <div class="sparkline">

                {spark_values}

            </div>

        </div>
        """

    render_html(

        f"""
        <div class="telemetry-strip">

            {cards_html}

        </div>
        """

    )


# ==========================================================
# Coordinates / Deployment Information
# ==========================================================

def render_location_summary(
    latitude: float | None,
    longitude: float | None,
    altitude: float | None,
    uptime: str = "—",
    storage_text: str = "—",
) -> None:
    """
    Render the information line below the deployment map.
    """

    render_html(

        f"""
        <div
            style="
                display:flex;
                gap:28px;
                flex-wrap:wrap;
                padding:11px 4px 2px;
                color:#76907f;
                font-size:9px;
                border-bottom:1px solid #183426;
            "
        >

            <span>
                GPS
                {_number(latitude, 4)}°N,
                {_number(longitude, 4)}°E
            </span>

            <span>
                ALT
                {_number(altitude, 0)}m
            </span>

            <span>
                UPTIME
                {_safe(uptime)}
            </span>

            <span>
                SD
                {_safe(storage_text)}
            </span>

        </div>
        """

    )


# ==========================================================
# Empty / Waiting State
# ==========================================================

def render_waiting_state(
    message: str = "Waiting for acoustic event",
) -> None:
    """
    Render a neutral waiting state.
    """

    render_html(

        f"""
        <div
            class="dashboard-panel"
            style="
                text-align:center;
                padding:30px;
            "
        >

            <div
                style="
                    color:#50685a;
                    font-size:10px;
                    letter-spacing:1px;
                "
            >
                {_safe(message)}
            </div>

        </div>
        """

    )