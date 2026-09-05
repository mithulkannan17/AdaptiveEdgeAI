"""
Dummy Hardware Providers

Simulation implementations of the hardware sensor
interfaces used for software development and testing.
"""

from hardware.dummy.sensors import (
    DummyBatterySensor,
    DummyEnvironmentalSensor,
    DummyGPSSensor,
    DummyLightSensor,
    DummyMicrophoneSensor,
    DummyVibrationSensor,
)

from hardware.dummy.scenarios import (
    CHAINSAW,
    FOREST,
    HUMAN_ACTIVITY,
    LOW_BATTERY,
    RAIN,
    VEHICLE,
    HardwareScenario,
    create_sensor_manager,
    get_scenario,
)

__all__ = [

    "DummyBatterySensor",
    "DummyEnvironmentalSensor",
    "DummyGPSSensor",
    "DummyLightSensor",
    "DummyMicrophoneSensor",
    "DummyVibrationSensor",

    "HardwareScenario",

    "FOREST",
    "CHAINSAW",
    "RAIN",
    "LOW_BATTERY",
    "HUMAN_ACTIVITY",
    "VEHICLE",

    "create_sensor_manager",
    "get_scenario",

]