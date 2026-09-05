"""
Runtime Telemetry

Defines structured environmental, location, and power
information reported by an edge node.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class DeviceTelemetry:
    """
    Runtime status of the edge device and its environment.
    """

    battery_percent: Optional[float] = None

    battery_voltage: Optional[float] = None

    temperature: Optional[float] = None

    humidity: Optional[float] = None

    light_level: Optional[float] = None

    vibration_detected: Optional[bool] = None

    def __post_init__(self):
        if self.battery_percent is not None:

            if not 0.0 <= self.battery_percent <= 100.0:

                raise ValueError(
                    "battery_percent must be between 0 and 100."
                )

        if self.battery_voltage is not None:

            if self.battery_voltage < 0:

                raise ValueError(
                    "battery_voltage cannot be negative."
                )

        if self.humidity is not None:

            if not 0.0 <= self.humidity <= 100.0:

                raise ValueError(
                    "humidity must be between 0 and 100."
                )

    def to_dict(self) -> dict:
        """
        Convert telemetry to a serializable dictionary.
        """

        return {
            "battery_percent":
                self.battery_percent,

            "battery_voltage":
                self.battery_voltage,

            "temperature":
                self.temperature,

            "humidity":
                self.humidity,

            "light_level":
                self.light_level,

            "vibration_detected":
                self.vibration_detected,
        }


@dataclass(frozen=True)
class LocationTelemetry:
    """
    Geographic information reported by the edge node.
    """

    latitude: Optional[float] = None

    longitude: Optional[float] = None

    altitude: Optional[float] = None

    accuracy: Optional[float] = None

    def __post_init__(self):

        if self.latitude is not None:

            if not -90.0 <= self.latitude <= 90.0:

                raise ValueError(
                    "latitude must be between -90 and 90."
                )

        if self.longitude is not None:

            if not -180.0 <= self.longitude <= 180.0:

                raise ValueError(
                    "longitude must be between -180 and 180."
                )

        if self.accuracy is not None:

            if self.accuracy < 0:

                raise ValueError(
                    "accuracy cannot be negative."
                )

    def to_dict(self) -> dict:
        """
        Convert location to a serializable dictionary.
        """

        return {
            "latitude":
                self.latitude,

            "longitude":
                self.longitude,

            "altitude":
                self.altitude,

            "accuracy":
                self.accuracy,
        }