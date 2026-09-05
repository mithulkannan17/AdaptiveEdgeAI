"""
Dummy Hardware Scenarios

Provides deterministic environmental scenarios for
development and integration testing.

These scenarios simulate the conditions that the
real hardware will eventually observe.
"""

from __future__ import annotations

from dataclasses import dataclass

from hardware.dummy.sensors import (
    DummyBatterySensor,
    DummyEnvironmentalSensor,
    DummyGPSSensor,
    DummyLightSensor,
    DummyMicrophoneSensor,
    DummyVibrationSensor,
)


@dataclass(frozen=True)
class HardwareScenario:
    """
    Complete simulated hardware state.
    """

    name: str

    microphone_frequency: float

    microphone_amplitude: float

    battery_percent: float

    battery_voltage: float

    temperature: float

    humidity: float

    light_level: float

    vibration_detected: bool

    latitude: float

    longitude: float

    altitude: float

    gps_accuracy: float


# ==========================================================
# Predefined Scenarios
# ==========================================================


FOREST = HardwareScenario(

    name="forest",

    microphone_frequency=440.0,

    microphone_amplitude=0.10,

    battery_percent=82.5,

    battery_voltage=3.91,

    temperature=28.4,

    humidity=67.2,

    light_level=145.0,

    vibration_detected=False,

    latitude=12.2958,

    longitude=76.6394,

    altitude=770.0,

    gps_accuracy=4.5,

)


CHAINSAW = HardwareScenario(

    name="chainsaw",

    microphone_frequency=180.0,

    microphone_amplitude=0.35,

    battery_percent=78.0,

    battery_voltage=3.87,

    temperature=29.1,

    humidity=61.0,

    light_level=210.0,

    vibration_detected=True,

    latitude=12.2958,

    longitude=76.6394,

    altitude=770.0,

    gps_accuracy=4.2,

)


RAIN = HardwareScenario(

    name="rain",

    microphone_frequency=120.0,

    microphone_amplitude=0.20,

    battery_percent=72.0,

    battery_voltage=3.82,

    temperature=24.5,

    humidity=91.0,

    light_level=35.0,

    vibration_detected=False,

    latitude=12.2958,

    longitude=76.6394,

    altitude=770.0,

    gps_accuracy=5.0,

)


LOW_BATTERY = HardwareScenario(

    name="low_battery",

    microphone_frequency=440.0,

    microphone_amplitude=0.10,

    battery_percent=12.0,

    battery_voltage=3.45,

    temperature=27.0,

    humidity=70.0,

    light_level=120.0,

    vibration_detected=False,

    latitude=12.2958,

    longitude=76.6394,

    altitude=770.0,

    gps_accuracy=5.5,

)


HUMAN_ACTIVITY = HardwareScenario(

    name="human_activity",

    microphone_frequency=300.0,

    microphone_amplitude=0.18,

    battery_percent=65.0,

    battery_voltage=3.76,

    temperature=28.0,

    humidity=68.0,

    light_level=180.0,

    vibration_detected=False,

    latitude=12.2958,

    longitude=76.6394,

    altitude=770.0,

    gps_accuracy=4.8,

)


VEHICLE = HardwareScenario(

    name="vehicle",

    microphone_frequency=95.0,

    microphone_amplitude=0.30,

    battery_percent=60.0,

    battery_voltage=3.72,

    temperature=30.0,

    humidity=55.0,

    light_level=250.0,

    vibration_detected=True,

    latitude=12.2958,

    longitude=76.6394,

    altitude=770.0,

    gps_accuracy=4.0,

)


# ==========================================================
# Scenario Registry
# ==========================================================


SCENARIOS = {

    scenario.name: scenario

    for scenario in [

        FOREST,

        CHAINSAW,

        RAIN,

        LOW_BATTERY,

        HUMAN_ACTIVITY,

        VEHICLE,

    ]

}


# ==========================================================
# Factory
# ==========================================================


def create_sensor_manager(
    scenario: HardwareScenario,
):
    """
    Create a HardwareSensorManager configured for
    the supplied dummy scenario.

    The returned manager uses exactly the same sensor
    interfaces that future real ESP32-S3 drivers will use.
    """

    from hardware.sensors import (
        HardwareSensorManager,
    )

    return HardwareSensorManager(

        microphone_sensor=(
            DummyMicrophoneSensor(

                frequency=(
                    scenario.microphone_frequency
                ),

                amplitude=(
                    scenario.microphone_amplitude
                ),

            )
        ),

        battery_sensor=(
            DummyBatterySensor(

                battery_percent=(
                    scenario.battery_percent
                ),

                battery_voltage=(
                    scenario.battery_voltage
                ),

            )
        ),

        environmental_sensor=(
            DummyEnvironmentalSensor(

                temperature=(
                    scenario.temperature
                ),

                humidity=(
                    scenario.humidity
                ),

            )
        ),

        light_sensor=(
            DummyLightSensor(

                light_level=(
                    scenario.light_level
                ),

            )
        ),

        vibration_sensor=(
            DummyVibrationSensor(

                detected=(
                    scenario.vibration_detected
                ),

            )
        ),

        gps_sensor=(
            DummyGPSSensor(

                latitude=(
                    scenario.latitude
                ),

                longitude=(
                    scenario.longitude
                ),

                altitude=(
                    scenario.altitude
                ),

                accuracy=(
                    scenario.gps_accuracy
                ),

            )
        ),

    )


def get_scenario(
    name: str,
) -> HardwareScenario:
    """
    Return a predefined hardware scenario.
    """

    key = name.strip().lower()

    if key not in SCENARIOS:

        available = ", ".join(
            sorted(SCENARIOS.keys())
        )

        raise ValueError(

            f"Unknown hardware scenario '{name}'. "

            f"Available scenarios: {available}"

        )

    return SCENARIOS[key]