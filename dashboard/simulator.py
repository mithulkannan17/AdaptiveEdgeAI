"""
Dashboard Runtime Simulator

Produces realistic dummy telemetry and acoustic events
for frontend development before the physical hardware
is connected.

The simulator intentionally follows the same conceptual
data structure that the real edge node will provide.
"""

from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


# ==========================================================
# Acoustic Event Definitions
# ==========================================================

EVENT_DEFINITIONS = {

    "Bird": {
        "display_name": "Bird calls",
        "confidence_range": (0.74, 0.96),
        "risk": "LOW",
        "priority": 1,
    },

    "Human": {
        "display_name": "Human voices",
        "confidence_range": (0.78, 0.94),
        "risk": "MEDIUM",
        "priority": 3,
    },

    "Vehicle": {
        "display_name": "Vehicle movement",
        "confidence_range": (0.76, 0.94),
        "risk": "MEDIUM",
        "priority": 3,
    },

    "Chainsaw": {
        "display_name": "Chainsaw operation",
        "confidence_range": (0.88, 0.99),
        "risk": "HIGH",
        "priority": 5,
    },

    "Rain": {
        "display_name": "Rainfall",
        "confidence_range": (0.80, 0.98),
        "risk": "LOW",
        "priority": 1,
    },

    "Wind": {
        "display_name": "Wind gust",
        "confidence_range": (0.76, 0.95),
        "risk": "LOW",
        "priority": 1,
    },

}


# ==========================================================
# Telemetry Snapshot
# ==========================================================

@dataclass
class SimulatedTelemetry:
    """
    Dummy hardware telemetry.

    These fields correspond to values that will eventually
    come from:

        BME280
        BH1750
        SW420
        MAX17048
        GPS
    """

    temperature: float = 26.4

    humidity: float = 70.9

    pressure: float = 1007.9

    light_level: float = 186.4

    vibration: float = 0.07

    battery_percent: float = 92.0

    battery_voltage: float = 3.87

    latitude: float = 12.3021

    longitude: float = 76.6510

    altitude: float = 812.0

    charging: bool = True

    uptime_seconds: float = 0.0

    storage_used_gb: float = 6.2

    storage_total_gb: float = 32.0

    timestamp: float = field(
        default_factory=time.time
    )

    def to_dict(self) -> dict[str, Any]:
        """
        Convert telemetry into a dashboard/backend-friendly
        dictionary.
        """

        return {

            "temperature":
                self.temperature,

            "humidity":
                self.humidity,

            "pressure":
                self.pressure,

            "light_level":
                self.light_level,

            "vibration":
                self.vibration,

            "battery_percent":
                self.battery_percent,

            "battery_voltage":
                self.battery_voltage,

            "latitude":
                self.latitude,

            "longitude":
                self.longitude,

            "altitude":
                self.altitude,

            "charging":
                self.charging,

            "uptime_seconds":
                self.uptime_seconds,

            "storage_used_gb":
                self.storage_used_gb,

            "storage_total_gb":
                self.storage_total_gb,

            "timestamp":
                self.timestamp,

        }


# ==========================================================
# Simulated Acoustic Event
# ==========================================================

@dataclass
class SimulatedEvent:
    """
    Dummy acoustic event following the same conceptual
    structure as the real edge event pipeline.
    """

    label: str

    display_name: str

    confidence: float

    risk_level: str

    priority: int

    detected: bool = True

    latitude: float = 12.3021

    longitude: float = 76.6510

    timestamp: float = field(
        default_factory=time.time
    )

    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        """
        Convert event into a serializable dictionary.
        """

        timestamp_text = datetime.fromtimestamp(
            self.timestamp
        ).strftime(
            "%H:%M:%S"
        )

        return {

            "label":
                self.display_name,

            "class_name":
                self.label,

            "confidence":
                self.confidence * 100.0,

            "risk_level":
                self.risk_level,

            "priority":
                self.priority,

            "detected":
                self.detected,

            "latitude":
                self.latitude,

            "longitude":
                self.longitude,

            "timestamp":
                timestamp_text,

            "reason":
                self.reason,

        }


# ==========================================================
# Simulator
# ==========================================================

class DashboardSimulator:
    """
    Stateful dummy runtime for frontend development.

    The simulator maintains:

        - environmental telemetry
        - battery state
        - GPS
        - acoustic events
        - event history
        - telemetry history
        - CADIE decision

    It is deliberately independent of Streamlit.
    """

    def __init__(
        self,
        seed: int | None = 42,
    ):

        if seed is not None:

            random.seed(seed)

        self.start_time = time.time()

        self.tick_count = 0

        self.current_event: SimulatedEvent | None = None

        self.event_history: list[
            SimulatedEvent
        ] = []

        self.telemetry_history: dict[
            str,
            list[float],
        ] = {

            "temperature": [],

            "humidity": [],

            "light_level": [],

            "vibration": [],

            "pressure": [],

            "battery_voltage": [],

        }

        self.telemetry = (
            SimulatedTelemetry()
        )

    # ======================================================
    # Telemetry
    # ======================================================

    def _generate_telemetry(
        self,
    ) -> SimulatedTelemetry:

        self.tick_count += 1

        t = self.tick_count

        self.telemetry.temperature = (

            26.4

            + 0.55
            * math.sin(
                t * 0.17
            )

            + random.uniform(
                -0.12,
                0.12,
            )

        )

        self.telemetry.humidity = (

            71.0

            + 2.5
            * math.sin(
                t * 0.11
                + 1.2
            )

            + random.uniform(
                -0.35,
                0.35,
            )

        )

        self.telemetry.pressure = (

            1007.5

            + 2.2
            * math.sin(
                t * 0.07
            )

            + random.uniform(
                -0.25,
                0.25,
            )

        )

        self.telemetry.light_level = max(

            0.0,

            185.0

            + 45.0
            * math.sin(
                t * 0.08
            )

            + random.uniform(
                -8.0,
                8.0,
            ),

        )

        self.telemetry.vibration = max(

            0.01,

            0.07

            + 0.025
            * abs(
                math.sin(
                    t * 0.25
                )
            )

            + random.uniform(
                -0.008,
                0.008,
            ),

        )

        # ----------------------------------------------
        # Battery
        # ----------------------------------------------

        if self.telemetry.charging:

            self.telemetry.battery_percent = min(

                100.0,

                self.telemetry.battery_percent
                + 0.015,

            )

            self.telemetry.battery_voltage = min(

                4.20,

                self.telemetry.battery_voltage
                + 0.0005,

            )

        else:

            self.telemetry.battery_percent = max(

                0.0,

                self.telemetry.battery_percent
                - 0.008,

            )

            self.telemetry.battery_voltage = max(

                3.30,

                self.telemetry.battery_voltage
                - 0.0002,

            )

        # ----------------------------------------------
        # Uptime
        # ----------------------------------------------

        self.telemetry.uptime_seconds = (

            time.time()
            - self.start_time

        )

        self.telemetry.timestamp = time.time()

        return self.telemetry

    # ======================================================
    # Event Generation
    # ======================================================

    def _generate_event(
        self,
    ) -> SimulatedEvent:

        labels = list(
            EVENT_DEFINITIONS.keys()
        )

        # Give natural events more frequency than
        # high-risk events during normal simulation.
        weights = [

            30,  # Bird

            15,  # Human

            15,  # Vehicle

            8,   # Chainsaw

            20,  # Rain

            12,  # Wind

        ]

        label = random.choices(

            labels,

            weights=weights,

            k=1,

        )[0]

        definition = (
            EVENT_DEFINITIONS[label]
        )

        low, high = (
            definition[
                "confidence_range"
            ]
        )

        confidence = random.uniform(
            low,
            high,
        )

        # Small location displacement to make the
        # deployment map visually meaningful.
        latitude = (

            self.telemetry.latitude

            + random.uniform(
                -0.0008,
                0.0008,
            )

        )

        longitude = (

            self.telemetry.longitude

            + random.uniform(
                -0.0008,
                0.0008,
            )

        )

        reason = self._event_reason(
            label
        )

        event = SimulatedEvent(

            label=label,

            display_name=definition[
                "display_name"
            ],

            confidence=confidence,

            risk_level=definition[
                "risk"
            ],

            priority=definition[
                "priority"
            ],

            latitude=latitude,

            longitude=longitude,

            reason=reason,

        )

        self.current_event = event

        self.event_history.insert(
            0,
            event,
        )

        # Keep memory bounded.
        self.event_history = (
            self.event_history[:50]
        )

        return event

    # ======================================================
    # Event Reason
    # ======================================================

    @staticmethod
    def _event_reason(
        label: str,
    ) -> str:

        reasons = {

            "Bird":
                "Natural acoustic activity detected.",

            "Human":
                "Human vocal activity detected.",

            "Vehicle":
                "Anthropogenic vehicle signature detected.",

            "Chainsaw":
                (
                    "Sustained chainsaw pattern detected "
                    "with corroborating environmental context."
                ),

            "Rain":
                "Broadband rainfall pattern detected.",

            "Wind":
                "Wind-dominant acoustic background detected.",

        }

        return reasons.get(
            label,
            "Acoustic event detected.",
        )

    # ======================================================
    # CADIE
    # ======================================================

    def _generate_cadie(
        self,
        event: SimulatedEvent | None,
    ) -> dict[str, Any]:

        if event is None:

            return {

                "risk_level":
                    "LOW",

                "score":
                    0.0,

                "signal":
                    "No active acoustic event",

                "baseline_delta":
                    "0.00",

                "action":
                    "Waiting for acoustic event",

                "reason":
                    "",

            }

        # Base risk score from priority.
        score = (

            event.priority
            / 5.0

        )

        # Add confidence contribution.
        score += (

            event.confidence
            * 0.15

        )

        # Environmental context.
        if event.label == "Chainsaw":

            score += 0.12

        elif event.label in (
            "Vehicle",
            "Human",
        ):

            score += 0.04

        else:

            score -= 0.08

        score = max(
            0.0,
            min(
                1.0,
                score,
            ),
        )

        if score >= 0.80:

            risk = "CRITICAL"

            action = (
                "Immediate attention required"
            )

        elif score >= 0.60:

            risk = "HIGH"

            action = (
                "Flag event for review"
            )

        elif score >= 0.35:

            risk = "MEDIUM"

            action = (
                "Continue contextual monitoring"
            )

        else:

            risk = "LOW"

            action = (
                "Continue routine monitoring"
            )

        baseline_delta = (

            score
            - 0.23

        )

        return {

            "risk_level":
                risk,

            "score":
                score,

            "signal":
                (
                    f"{event.display_name} "
                    f"@ simulated range"
                ),

            "baseline_delta":
                f"{baseline_delta:+.2f}",

            "action":
                action,

            "reason":
                event.reason,

        }

    # ======================================================
    # Waveform
    # ======================================================

    def _generate_waveform(
        self,
        event: SimulatedEvent | None,
        count: int = 64,
    ) -> list[float]:

        if event is None:

            frequency = 0.45

            amplitude = 0.35

        elif event.label == "Chainsaw":

            frequency = 0.85

            amplitude = 0.80

        elif event.label == "Vehicle":

            frequency = 0.55

            amplitude = 0.62

        elif event.label == "Human":

            frequency = 1.05

            amplitude = 0.55

        elif event.label == "Bird":

            frequency = 1.60

            amplitude = 0.42

        elif event.label == "Rain":

            frequency = 2.20

            amplitude = 0.48

        else:

            frequency = 1.30

            amplitude = 0.38

        waveform = []

        for index in range(count):

            value = (

                amplitude
                * math.sin(
                    index
                    * frequency
                    * 0.35
                )

                + 0.18
                * math.sin(
                    index
                    * frequency
                    * 1.7
                )

                + random.uniform(
                    -0.07,
                    0.07,
                )

            )

            waveform.append(
                value
            )

        return waveform

    # ======================================================
    # Tick
    # ======================================================

    def tick(
        self,
        generate_event: bool = True,
    ) -> dict[str, Any]:
        """
        Advance the simulation by one step.

        Returns the complete dashboard state.
        """

        telemetry = (
            self._generate_telemetry()
        )

        event = self.current_event

        if (
            generate_event
            and (
                self.tick_count == 1
                or self.tick_count % 4 == 0
            )
        ):

            event = (
                self._generate_event()
            )

        cadie = (
            self._generate_cadie(
                event
            )
        )

        waveform = (
            self._generate_waveform(
                event
            )
        )

        self._append_history(
            telemetry
        )

        return {

            "telemetry":
                telemetry.to_dict(),

            "event":
                (
                    event.to_dict()
                    if event is not None
                    else None
                ),

            "events":
                [
                    item.to_dict()
                    for item
                    in self.event_history
                ],

            "cadie":
                cadie,

            "waveform":
                waveform,

            "timestamp":
                time.time(),

        }

    # ======================================================
    # History
    # ======================================================

    def _append_history(
        self,
        telemetry: SimulatedTelemetry,
    ) -> None:

        values = {

            "temperature":
                telemetry.temperature,

            "humidity":
                telemetry.humidity,

            "light_level":
                telemetry.light_level,

            "vibration":
                telemetry.vibration,

            "pressure":
                telemetry.pressure,

            "battery_voltage":
                telemetry.battery_voltage,

        }

        for key, value in values.items():

            history = (
                self.telemetry_history[
                    key
                ]
            )

            history.append(
                float(value)
            )

            if len(history) > 30:

                del history[:-30]

    # ======================================================
    # Full State
    # ======================================================

    def state(
        self,
    ) -> dict[str, Any]:

        event = (
            self.current_event
        )

        cadie = (
            self._generate_cadie(
                event
            )
        )

        return {

            "telemetry":
                self.telemetry.to_dict(),

            "event":
                (
                    event.to_dict()
                    if event is not None
                    else None
                ),

            "events":
                [
                    item.to_dict()
                    for item
                    in self.event_history
                ],

            "cadie":
                cadie,

            "waveform":
                self._generate_waveform(
                    event
                ),

            "timestamp":
                time.time(),

        }

    # ======================================================
    # Reset
    # ======================================================

    def reset(
        self,
    ) -> None:
        """
        Reset the simulation.
        """

        self.start_time = time.time()

        self.tick_count = 0

        self.current_event = None

        self.event_history.clear()

        for history in (
            self.telemetry_history.values()
        ):

            history.clear()

        self.telemetry = (
            SimulatedTelemetry()
        )