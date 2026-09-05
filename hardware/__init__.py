"""
Hardware abstraction package.
"""

from hardware.telemetry import (
    DeviceTelemetry,
    HardwareTelemetry,
    LocationTelemetry,
)

from hardware.sensors import (
    BatterySensor,
    EnvironmentalSensor,
    GPSSensor,
    HardwareSensorManager,
    LightSensor,
    VibrationSensor,
)

__all__ = [
    "BatterySensor",
    "DeviceTelemetry",
    "EnvironmentalSensor",
    "GPSSensor",
    "HardwareSensorManager",
    "HardwareTelemetry",
    "LightSensor",
    "LocationTelemetry",
    "VibrationSensor",
]