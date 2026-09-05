"""
Dashboard Styles
================

Central visual theme for the Adaptive Edge Intelligence Platform.

The stylesheet is intentionally independent from the application
logic. It provides the dark forest-monitoring interface used by
dashboard/app.py.
"""

from __future__ import annotations

import streamlit as st


# ==========================================================
# Theme Constants
# ==========================================================

BACKGROUND = "#07120d"
SURFACE = "#0b1a12"
SURFACE_LIGHT = "#0f2117"
SURFACE_DARK = "#08150e"

BORDER = "#183426"
BORDER_LIGHT = "#294a36"

TEXT = "#e5eee7"
TEXT_MUTED = "#76907f"
TEXT_DIM = "#50685a"

ACCENT = "#78a96d"
ACCENT_BRIGHT = "#8bc477"
ACCENT_DARK = "#315c3b"

LOW = "#82b86e"
MEDIUM = "#efa832"
HIGH = "#e5673f"
CRITICAL = "#ed4d3f"

CYAN = "#68a6a0"


# ==========================================================
# Main Style Application
# ==========================================================

def apply_dashboard_style() -> None:
    """
    Apply the complete Adaptive Edge dashboard theme.

    Must be called after st.set_page_config().
    """

    st.markdown(
        f"""
        <style>

        /* ==================================================
           GLOBAL
           ================================================== */

        html,
        body,
        [data-testid="stAppViewContainer"],
        [data-testid="stApp"] {{
            background:
                radial-gradient(
                    circle at 50% 0%,
                    #102319 0%,
                    {BACKGROUND} 40%,
                    #040b07 100%
                );
            color: {TEXT};
        }}

        [data-testid="stAppViewContainer"] > .main {{
            background: transparent;
        }}

        .main .block-container {{
            max-width: 1800px;
            padding-top: 0.75rem;
            padding-left: 1rem;
            padding-right: 1rem;
            padding-bottom: 1.5rem;
        }}

        /* ==================================================
           REMOVE STREAMLIT CHROME
           ================================================== */

        #MainMenu,
        footer,
        header,
        [data-testid="stDecoration"] {{
            visibility: hidden;
        }}

        /* ==================================================
           DEFAULT TYPOGRAPHY
           ================================================== */

        body,
        p,
        span,
        div,
        label,
        button {{
            font-family:
                "Courier New",
                Consolas,
                monospace;
        }}

        h1,
        h2,
        h3,
        h4 {{
            color: {TEXT};
        }}

        /* ==================================================
           HEADER
           ================================================== */

        .dashboard-header {{
            min-height: 70px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 20px;

            padding: 10px 15px;

            border: 1px solid {BORDER_LIGHT};

            background:
                linear-gradient(
                    100deg,
                    #0d1d14,
                    #0a1710
                );

            box-shadow:
                inset 0 1px 0 rgba(255,255,255,0.02),
                0 12px 30px rgba(0,0,0,0.22);
        }}

        .header-brand {{
            min-width: 0;
        }}

        .node-title {{
            display: inline-block;

            color: {TEXT};

            font-family:
                "Arial Narrow",
                Impact,
                sans-serif;

            font-size: 28px;
            font-weight: 800;
            letter-spacing: 1px;

            margin-right: 17px;
        }}

        .node-subtitle {{
            color: {TEXT_MUTED};
            font-size: 9px;
            letter-spacing: 1.7px;
            text-transform: uppercase;
        }}

        .header-status-container {{
            display: flex;
            align-items: center;
            justify-content: flex-end;
            flex-wrap: wrap;
            gap: 6px;
        }}

        .status-pill {{
            display: flex;
            align-items: center;
            gap: 6px;

            padding: 7px 9px;

            border: 1px solid {BORDER};

            background: #09160f;

            color: {TEXT_MUTED};

            font-size: 8px;
            letter-spacing: 0.8px;
            white-space: nowrap;
        }}

        .status-pill b {{
            color: {TEXT};
        }}

        .status-dot {{
            width: 7px;
            height: 7px;
            flex: 0 0 7px;

            border-radius: 50%;

            background: {LOW};

            box-shadow:
                0 0 8px rgba(130,184,110,0.65);
        }}

        .status-dot.warning {{
            background: {MEDIUM};
            box-shadow:
                0 0 8px rgba(239,168,50,0.55);
        }}

        .status-dot.danger {{
            background: {CRITICAL};
            box-shadow:
                0 0 8px rgba(237,77,63,0.55);
        }}

        /* ==================================================
           GENERAL PANEL
           ================================================== */

        .dashboard-panel {{
            margin-top: 8px;

            border: 1px solid {BORDER};

            background:
                linear-gradient(
                    145deg,
                    rgba(14,31,21,0.97),
                    rgba(7,18,12,0.98)
                );

            padding: 16px 17px;

            box-shadow:
                inset 0 1px 0 rgba(255,255,255,0.015);
        }}

        .panel-title {{
            color: {TEXT_MUTED};
            font-size: 9px;
            font-weight: 700;
            letter-spacing: 1.8px;
            text-transform: uppercase;
            margin-bottom: 12px;
        }}

        .panel-title-row {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 10px;
            margin-bottom: 12px;
        }}

        .panel-title-row .panel-title {{
            margin-bottom: 0;
        }}

        .panel-meta {{
            color: {TEXT_DIM};
            font-size: 7px;
            letter-spacing: 1.2px;
            white-space: nowrap;
        }}

        /* ==================================================
           METRICS
           ================================================== */

        .metric-row {{
            display: flex;
            justify-content: space-between;
            align-items: baseline;
            min-height: 38px;
            padding: 8px 0;

            border-bottom:
                1px dashed rgba(75,105,86,0.23);
        }}

        .metric-row:last-child {{
            border-bottom: none;
        }}

        .metric-label {{
            color: #82a18d;
            font-size: 10px;
        }}

        .metric-value {{
            color: {TEXT};
            font-size: 13px;
            font-weight: 700;
        }}

        .metric-unit {{
            color: {TEXT_MUTED};
            font-size: 8px;
            font-weight: 400;
            margin-left: 2px;
        }}

        /* ==================================================
           NODE HEALTH
           ================================================== */

        .health-line {{
            display: flex;
            justify-content: space-between;
            gap: 12px;

            padding: 7px 0;

            border-bottom:
                1px dashed rgba(75,105,86,0.20);

            color: {TEXT_MUTED};
            font-size: 9px;
        }}

        .health-line:last-of-type {{
            border-bottom: none;
        }}

        .health-line b {{
            color: {TEXT};
            font-weight: 700;
            text-align: right;
        }}

        .health-message {{
            margin-top: 12px;
            padding-top: 10px;

            border-top: 1px solid {BORDER};

            color: {TEXT_DIM};
            font-size: 8px;
            line-height: 1.7;
        }}

        /* ==================================================
           BATTERY
           ================================================== */

        .battery-container {{
            padding-top: 2px;
        }}

        .battery-track {{
            position: relative;

            width: calc(100% - 6px);
            height: 25px;

            border: 1px solid #496154;

            background: #09150e;

            padding: 3px;
        }}

        .battery-fill {{
            height: 100%;

            background:
                linear-gradient(
                    90deg,
                    #a3c76e,
                    {ACCENT}
                );

            transition: width 0.4s ease;
        }}

        .battery-fill.warning {{
            background: {MEDIUM};
        }}

        .battery-fill.danger {{
            background: {CRITICAL};
        }}

        .battery-meta {{
            display: flex;
            justify-content: space-between;

            margin-top: 7px;

            color: {TEXT_MUTED};
            font-size: 9px;
        }}

        .battery-voltage {{
            margin-top: 7px;
            color: {TEXT};
            font-size: 10px;
            text-align: right;
        }}

        /* ==================================================
           ACOUSTIC
           ================================================== */

        .acoustic-panel {{
            min-height: 250px;
        }}

        .acoustic-container {{
            height: 88px;
            padding: 13px 10px;

            border: 1px solid {BORDER};

            background: #07140c;

            overflow: hidden;
        }}

        .waveform {{
            height: 100%;

            display: flex;
            align-items: center;
            justify-content: center;

            gap: 2px;
        }}

        .wave-bar {{
            width: 4px;
            min-height: 3px;
            flex: 1 1 auto;
            max-width: 7px;

            border-radius: 1px;

            background:
                linear-gradient(
                    180deg,
                    #79aa75,
                    #355e42
                );

            opacity: 0.85;
        }}

        .classification-result {{
            display: flex;
            justify-content: space-between;
            align-items: center;

            margin-top: 12px;
        }}

        .classification-label {{
            color: {TEXT};
            font-size: 14px;
            font-weight: 700;
        }}

        .classification-subtitle {{
            margin-top: 4px;
            color: {TEXT_DIM};
            font-size: 8px;
        }}

        .classification-confidence {{
            color: {ACCENT_BRIGHT};
            font-size: 16px;
            font-weight: 700;
        }}

        .confidence-track {{
            width: 100%;
            height: 5px;

            margin-top: 8px;

            background: #1b2920;

            overflow: hidden;
        }}

        .confidence-fill {{
            height: 100%;

            background:
                linear-gradient(
                    90deg,
                    #7c4b4b,
                    #e45e5e
                );

            transition: width 0.4s ease;
        }}

        .classification-footer {{
            display: flex;
            justify-content: space-between;
            gap: 10px;

            margin-top: 8px;

            color: {TEXT_DIM};
            font-size: 8px;
        }}

        .classification-footer b {{
            color: {TEXT_MUTED};
        }}

        /* ==================================================
           DETECTION PIPELINE
           ================================================== */

        .pipeline {{
            border: 1px solid {BORDER};
            background: #07140c;
            padding: 10px 14px;
        }}

        .pipeline-step {{
            display: flex;
            align-items: center;
            gap: 8px;

            min-height: 38px;

            color: {TEXT};
            font-size: 9px;

            border-bottom:
                1px solid rgba(75,105,86,0.12);
        }}

        .pipeline-step:last-child {{
            border-bottom: none;
        }}

        .pipeline-dot {{
            width: 7px;
            height: 7px;
            flex: 0 0 7px;

            border-radius: 50%;

            background: {LOW};

            box-shadow:
                0 0 7px rgba(130,184,110,0.55);
        }}

        .pipeline-label {{
            color: {TEXT};
        }}

        .pipeline-label small {{
            color: {TEXT_DIM};
        }}

        .pipeline-result {{
            margin-left: auto;
            color: {ACCENT_BRIGHT};
            font-weight: 700;
            text-align: right;
        }}

        .pipeline-result.priority {{
            color: {MEDIUM};
        }}

        .pipeline-confidence {{
            width: 70px;
            height: 5px;
            margin-left: auto;

            background: #1b2920;
        }}

        .pipeline-number {{
            width: 38px;
            color: {TEXT_MUTED};
            font-size: 8px;
            text-align: right;
        }}

        /* ==================================================
           CADIE
           ================================================== */

        .cadie-panel {{
            min-height: 300px;
        }}

        .risk-display {{
            position: relative;

            width: 168px;
            height: 168px;

            margin: 5px auto 16px;

            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;

            border-radius: 50%;

            background:
                radial-gradient(
                    circle,
                    #102219 52%,
                    transparent 53%
                );
        }}

        .risk-display::before {{
            content: "";

            position: absolute;
            inset: 0;

            border-radius: 50%;

            border: 9px solid #23372a;

            box-shadow:
                0 0 18px rgba(0,0,0,0.18);
        }}

        .risk-display::after {{
            content: "";

            position: absolute;
            inset: 0;

            border-radius: 50%;

            border: 9px solid transparent;

            border-top-color: currentColor;
            border-right-color: currentColor;

            transform:
                rotate(
                    var(--risk-angle, 35deg)
                );
        }}

        .risk-display.risk-low {{
            color: {LOW};
            --risk-angle: 25deg;
        }}

        .risk-display.risk-medium {{
            color: {MEDIUM};
            --risk-angle: 110deg;
        }}

        .risk-display.risk-high {{
            color: {HIGH};
            --risk-angle: 205deg;
        }}

        .risk-display.risk-critical {{
            color: {CRITICAL};
            --risk-angle: 300deg;
        }}

        .risk-score {{
            position: relative;
            z-index: 2;

            text-align: center;
        }}

        .risk-level {{
            font-family:
                "Arial Narrow",
                Impact,
                sans-serif;

            font-size: 25px;
            letter-spacing: 1px;
            font-weight: 800;
        }}

        .risk-display.risk-low .risk-level {{
            color: {LOW};
        }}

        .risk-display.risk-medium .risk-level {{
            color: {MEDIUM};
        }}

        .risk-display.risk-high .risk-level {{
            color: {HIGH};
        }}

        .risk-display.risk-critical .risk-level {{
            color: {CRITICAL};
        }}

        .score-label {{
            margin-top: 4px;
            color: {TEXT_MUTED};
            font-size: 8px;
            letter-spacing: 0.8px;
        }}

        .cadie-signal,
        .cadie-baseline {{
            color: {TEXT_MUTED};
            font-size: 8px;
            line-height: 1.7;
            text-align: center;
        }}

        .cadie-signal b,
        .cadie-baseline b {{
            color: {TEXT};
        }}

        .cadie-reason {{
            margin-top: 8px;

            color: {TEXT_DIM};
            font-size: 8px;
            line-height: 1.65;
            text-align: center;
        }}

        .cadie-action {{
            margin-top: 13px;
            padding-top: 10px;

            border-top: 1px solid {BORDER};

            color: {TEXT_MUTED};
            font-size: 8px;
            text-align: center;
        }}

        .cadie-action b {{
            color: {TEXT};
        }}

        /* ==================================================
           RISK COLORS
           ================================================== */

        .risk-low {{
            color: {LOW} !important;
        }}

        .risk-medium {{
            color: {MEDIUM} !important;
        }}

        .risk-high {{
            color: {HIGH} !important;
        }}

        .risk-critical {{
            color: {CRITICAL} !important;
        }}

        /* ==================================================
           EVENT LOG
           ================================================== */

        .event-panel {{
            min-height: 300px;
        }}

        .event-list {{
            max-height: 410px;
            overflow-y: auto;
            padding-right: 3px;
        }}

        .event-row {{
            position: relative;

            padding: 10px 3px 11px;

            border-bottom:
                1px solid {BORDER};
        }}

        .event-row:last-child {{
            border-bottom: none;
        }}

        .event-row-top {{
            display: flex;
            align-items: center;
            gap: 7px;
        }}

        .event-marker {{
            font-size: 9px;
        }}

        .event-name {{
            color: {TEXT};
            font-size: 10px;
            font-weight: 700;
        }}

        .event-time {{
            margin-left: auto;
            color: {TEXT_DIM};
            font-size: 7px;
        }}

        .event-row-meta {{
            margin-top: 5px;
            color: {TEXT_MUTED};
            font-size: 7px;
            line-height: 1.5;
        }}

        .event-risk {{
            margin-top: 5px;
            font-size: 7px;
            font-weight: 700;
            letter-spacing: 0.8px;
        }}

        .empty-event-log {{
            padding: 25px 5px;
            color: {TEXT_DIM};
            font-size: 9px;
            text-align: center;
        }}

        /* ==================================================
           MAP
           ================================================== */

        .map-panel {{
            position: relative;

            min-height: 430px;

            overflow: hidden;

            border: 1px solid {BORDER};

            background: #07120c;
        }}

        .map-panel .panel-title-row {{
            position: absolute;
            z-index: 20;

            left: 16px;
            right: 16px;
            top: 14px;
        }}

        .deployment-map {{
            position: relative;

            width: 100%;
            height: 430px;

            overflow: hidden;

            background:
                radial-gradient(
                    circle at center,
                    rgba(31,66,42,0.28),
                    rgba(5,15,9,0.92) 68%
                );
        }}

        .map-grid {{
            position: absolute;
            inset: 0;

            background-image:
                linear-gradient(
                    rgba(71,108,78,0.18) 1px,
                    transparent 1px
                ),
                linear-gradient(
                    90deg,
                    rgba(71,108,78,0.18) 1px,
                    transparent 1px
                );

            background-size: 34px 34px;

            opacity: 0.65;
        }}

        .map-ring {{
            position: absolute;

            left: 50%;
            top: 50%;

            transform:
                translate(-50%, -50%);

            border:
                1px solid
                rgba(83,124,90,0.30);

            border-radius: 50%;
        }}

        .ring-one {{
            width: 130px;
            height: 130px;
        }}

        .ring-two {{
            width: 250px;
            height: 250px;
        }}

        .ring-three {{
            width: 400px;
            height: 400px;
        }}

        .map-node {{
            position: absolute;

            left: 50%;
            top: 50%;

            width: 15px;
            height: 15px;

            transform:
                translate(-50%, -50%);

            border-radius: 50%;

            background: #e8e6cf;

            box-shadow:
                0 0 0 5px
                rgba(232,230,207,0.08),

                0 0 20px
                rgba(232,230,207,0.60);

            z-index: 10;
        }}

        .map-node span {{
            position: absolute;

            left: 50%;
            top: 50%;

            width: 5px;
            height: 5px;

            transform:
                translate(-50%, -50%);

            border-radius: 50%;

            background: #142b1b;
        }}

        .map-event {{
            position: absolute;

            transform:
                translate(-50%, -50%);

            z-index: 8;

            display: flex;
            align-items: center;
            gap: 5px;

            padding: 4px 6px;

            border:
                1px solid
                rgba(45,70,52,0.8);

            background:
                rgba(7,18,12,0.90);

            color: {TEXT_MUTED};

            font-size: 7px;

            white-space: nowrap;
        }}

        .map-event-dot {{
            font-size: 11px;
        }}

        .map-event-label {{
            color: {TEXT_MUTED};
        }}

        .map-legend {{
            position: absolute;

            z-index: 30;

            left: 16px;
            right: 16px;
            bottom: 12px;

            display: flex;
            gap: 18px;

            padding-top: 9px;

            border-top:
                1px solid
                rgba(75,105,86,0.20);

            color: {TEXT_MUTED};

            font-size: 7px;
        }}

        .legend-dot {{
            display: inline-block;

            width: 6px;
            height: 6px;

            margin-right: 4px;

            border-radius: 50%;
        }}

        .legend-dot.low {{
            background: {LOW};
        }}

        .legend-dot.medium {{
            background: {MEDIUM};
        }}

        .legend-dot.high {{
            background: {HIGH};
        }}

        .location-summary {{
            display: flex;
            flex-wrap: wrap;
            gap: 25px;

            padding: 9px 4px 2px;

            color: {TEXT_DIM};
            font-size: 8px;
        }}

        .location-summary span {{
            color: {TEXT_MUTED};
        }}

        /* ==================================================
           TELEMETRY STRIP
           ================================================== */

        .telemetry-strip {{
            display: grid;

            grid-template-columns:
                repeat(6, minmax(0, 1fr));

            margin-top: 9px;

            border:
                1px solid
                {BORDER};

            background: #091710;
        }}

        .telemetry-card {{
            position: relative;

            min-height: 116px;

            padding: 14px 16px;

            border-right:
                1px solid
                {BORDER};

            overflow: hidden;
        }}

        .telemetry-card:last-child {{
            border-right: none;
        }}

        .telemetry-card-header {{
            display: flex;
            justify-content: space-between;

            color: {TEXT_MUTED};

            font-size: 7px;
            letter-spacing: 1.2px;
        }}

        .telemetry-card-header span:last-child {{
            color: #4c8d91;
        }}

        .telemetry-value {{
            margin-top: 12px;

            color: {TEXT};

            font-family:
                "Arial Narrow",
                Impact,
                sans-serif;

            font-size: 24px;
            font-weight: 700;
        }}

        .telemetry-value small {{
            color: {TEXT_MUTED};

            font-family:
                "Courier New",
                monospace;

            font-size: 8px;
            font-weight: 400;
        }}

        .telemetry-line {{
            position: absolute;

            left: 16px;
            right: 16px;
            bottom: 11px;

            height: 18px;

            display: flex;
            align-items: flex-end;
            gap: 2px;

            opacity: 0.65;
        }}

        .telemetry-line span {{
            flex: 1;

            min-height: 3px;

            background:
                linear-gradient(
                    180deg,
                    #4b7755,
                    #294834
                );
        }}

        .telemetry-line span:nth-child(1) {{
            height: 30%;
        }}

        .telemetry-line span:nth-child(2) {{
            height: 65%;
        }}

        .telemetry-line span:nth-child(3) {{
            height: 45%;
        }}

        .telemetry-line span:nth-child(4) {{
            height: 85%;
        }}

        .telemetry-line span:nth-child(5) {{
            height: 55%;
        }}

        /* ==================================================
           STREAMLIT BUTTON
           ================================================== */

        .stButton > button {{
            width: 100%;
            min-height: 38px;

            border:
                1px solid
                {BORDER_LIGHT};

            border-radius: 3px;

            background:
                linear-gradient(
                    180deg,
                    #102518,
                    #0b1b11
                );

            color: {TEXT};

            font-family:
                "Courier New",
                monospace;

            font-size: 9px;
            letter-spacing: 0.5px;

            transition:
                all 0.15s ease;
        }}

        .stButton > button:hover {{
            border-color: {ACCENT};
            color: #ffffff;

            background: #142d1c;

            box-shadow:
                0 0 15px
                rgba(120,169,109,0.08);
        }}

        .stButton > button:focus {{
            box-shadow:
                0 0 0 1px {ACCENT};
        }}

        /* ==================================================
           STREAMLIT COLUMNS
           ================================================== */

        [data-testid="column"] {{
            padding-left: 4px;
            padding-right: 4px;
        }}

        /* ==================================================
           SCROLLBARS
           ================================================== */

        ::-webkit-scrollbar {{
            width: 7px;
            height: 7px;
        }}

        ::-webkit-scrollbar-track {{
            background: #08140d;
        }}

        ::-webkit-scrollbar-thumb {{
            background: #294334;
            border-radius: 3px;
        }}

        ::-webkit-scrollbar-thumb:hover {{
            background: #3b5d46;
        }}

        /* ==================================================
           RESPONSIVE
           ================================================== */

        @media (max-width: 1100px) {{

            .dashboard-header {{
                align-items: flex-start;
                flex-direction: column;
                gap: 12px;
            }}

            .header-status-container {{
                justify-content: flex-start;
            }}

            .telemetry-strip {{
                grid-template-columns:
                    repeat(3, minmax(0, 1fr));
            }}

            .telemetry-card:nth-child(3) {{
                border-right: none;
            }}
        }}

        @media (max-width: 700px) {{

            .main .block-container {{
                padding-left: 0.5rem;
                padding-right: 0.5rem;
            }}

            .node-title {{
                font-size: 23px;
            }}

            .node-subtitle {{
                display: block;
                margin-top: 4px;
            }}

            .status-pill {{
                font-size: 7px;
            }}

            .telemetry-strip {{
                grid-template-columns:
                    repeat(2, minmax(0, 1fr));
            }}

            .telemetry-card:nth-child(3) {{
                border-right:
                    1px solid
                    {BORDER};
            }}

            .telemetry-card:nth-child(even) {{
                border-right: none;
            }}

            .map-panel,
            .deployment-map {{
                min-height: 350px;
                height: 350px;
            }}

            .ring-three {{
                width: 300px;
                height: 300px;
            }}
        }}

        </style>
        """,
        unsafe_allow_html=True,
    )


# ==========================================================
# Risk Utility
# ==========================================================

def risk_class(
    risk_level: str | None,
) -> str:
    """
    Convert a CADIE risk level to the corresponding
    CSS class.
    """

    if not risk_level:
        return "low"

    normalized = str(
        risk_level
    ).strip().lower()

    if normalized == "critical":
        return "critical"

    if normalized == "high":
        return "high"

    if normalized == "medium":
        return "medium"

    return "low"