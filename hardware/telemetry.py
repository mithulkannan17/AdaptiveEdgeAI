"""
Hardware Telemetry

Defines the standardized telemetry data produced by the
edge hardware layer.

This module is intentionally hardware-independent.

Actual sensor drivers can later populate these structures
from:

    - MAX17048
    - BME280
    - BH1750
    - SW420
    - GPS

The communication layer should consume these structures
without knowing how the sensors are implemented.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional


@dataclass
class LocationTelemetry:
    """
    GPS/location information reported by the edge node.
    """

    latitude: Optional[float] = None

    longitude: Optional[float] = None

    altitude: Optional[float] = None

    accuracy: Optional[float] = None

    def to_dict(self) -> dict:
        """
        Convert location telemetry to a dictionary.
        """

        return asdict(self)


@dataclass
class DeviceTelemetry:
    """
    Environmental and power telemetry reported by the
    edge hardware.
    """

    battery_percent: Optional[float] = None

    battery_voltage: Optional[float] = None

    temperature: Optional[float] = None

    humidity: Optional[float] = None

    light_level: Optional[float] = None

    vibration_detected: Optional[bool] = None

    def to_dict(self) -> dict:
        """
        Convert device telemetry to a dictionary.
        """

        return asdict(self)


@dataclass
class HardwareTelemetry:
    """
    Complete hardware telemetry snapshot.

    Combines device status and location into one object.
    """

    location: Optional[LocationTelemetry] = None

    device_status: Optional[DeviceTelemetry] = None

    def to_dict(self) -> dict:
        """
        Convert complete hardware telemetry into a
        communication-ready dictionary.
        """

        return {

            "location": (
                self.location.to_dict()
                if self.location is not None
                else None
            ),

            "device_status": (
                self.device_status.to_dict()
                if self.device_status is not None
                else None
            ),

        }