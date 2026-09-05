"""
Dashboard Configuration

Central configuration for the Adaptive Edge Intelligence
Platform frontend.

No hardware-specific implementation belongs here.
"""

from __future__ import annotations


# ==========================================================
# Application
# ==========================================================

APP_TITLE = (
    "Adaptive Edge Intelligence Platform"
)

APP_ICON = "🌲"

NODE_ID = "NODE-07"

LOCATION_NAME = (
    "KOORGALLI FOREST BLOCK"
)


# ==========================================================
# Backend
# ==========================================================

DEFAULT_BACKEND_URL = (
    "http://127.0.0.1:8000"
)

LATEST_EVENT_ENDPOINT = (
    "/api/v1/edge/events/latest"
)

EVENT_ENDPOINT = (
    "/api/v1/edge/events"
)


# ==========================================================
# Simulation
# ==========================================================

DEFAULT_SIMULATION_SPEED = 1

DEFAULT_SIMULATION_INTERVAL = 1.0

DEFAULT_DUTY_CYCLE = 40

DEFAULT_SAMPLE_INTERVAL = 60


# ==========================================================
# Default Location
# ==========================================================

DEFAULT_LATITUDE = 12.3021

DEFAULT_LONGITUDE = 76.6510

DEFAULT_ALTITUDE = 812.0

DEFAULT_GPS_ACCURACY = 4.5


# ==========================================================
# Default Environmental Values
# ==========================================================

DEFAULT_TEMPERATURE = 26.4

DEFAULT_HUMIDITY = 70.9

DEFAULT_PRESSURE = 1007.9

DEFAULT_LIGHT_LEVEL = 186.4

DEFAULT_VIBRATION = 0.07


# ==========================================================
# Default Power Values
# ==========================================================

DEFAULT_BATTERY_PERCENT = 92.0

DEFAULT_BATTERY_VOLTAGE = 3.87

DEFAULT_BATTERY_CHARGING = True


# ==========================================================
# Environment Types
# ==========================================================

ENVIRONMENT_TYPES = [

    "Natural",

    "Urban",

    "Rural",

    "Industrial",

    "Aquatic",

    "Mixed",

]


# ==========================================================
# Acoustic Classes
# ==========================================================

ACOUSTIC_CLASSES = {

    "Bird": {

        "display_name":
            "Bird vocalization",

        "icon":
            "🐦",

        "default_priority":
            1,

        "default_risk":
            "LOW",

    },

    "Human": {

        "display_name":
            "Human speech",

        "icon":
            "👤",

        "default_priority":
            3,

        "default_risk":
            "MEDIUM",

    },

    "Vehicle": {

        "display_name":
            "Vehicle movement",

        "icon":
            "🚙",

        "default_priority":
            3,

        "default_risk":
            "MEDIUM",

    },

    "Chainsaw": {

        "display_name":
            "Chainsaw activity",

        "icon":
            "🪚",

        "default_priority":
            5,

        "default_risk":
            "HIGH",

    },

    "Rain": {

        "display_name":
            "Rainfall",

        "icon":
            "🌧",

        "default_priority":
            1,

        "default_risk":
            "LOW",

    },

    "Wind": {

        "display_name":
            "Wind gust",

        "icon":
            "💨",

        "default_priority":
            1,

        "default_risk":
            "LOW",

    },

}


# ==========================================================
# Model Configuration
# ==========================================================

MODEL_NAME = (
    "MobileNetV3Small"
)

SAMPLE_RATE = 16000

AUDIO_DURATION_SECONDS = 5

N_MELS = 128

N_FFT = 1024

HOP_LENGTH = 512


# ==========================================================
# Dashboard Limits
# ==========================================================

MAX_EVENT_HISTORY = 50

EVENT_LOG_DISPLAY_COUNT = 10

WAVEFORM_POINTS = 64

TELEMETRY_HISTORY_LENGTH = 30


# ==========================================================
# Risk Levels
# ==========================================================

RISK_LEVELS = [

    "LOW",

    "MEDIUM",

    "HIGH",

    "CRITICAL",

]


# ==========================================================
# Transmission Modes
# ==========================================================

TRANSMISSION_MODES = [

    "continuous",

    "event_driven",

    "selective",

]