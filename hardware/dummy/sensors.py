"""
Dummy Hardware Sensors

Provides deterministic software implementations of the
hardware sensor interfaces.

These classes are used for:

    - Development
    - Integration testing
    - Dashboard development
    - Runtime simulation
    - CADIE testing

They implement the same interfaces that the future
ESP32-S3 hardware drivers will implement.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from hardware.sensors import (
    BatterySensor,
    EnvironmentalSensor,
    GPSSensor,
    LightSensor,
    MicrophoneSensor,
    VibrationSensor,
)

from hardware.telemetry import (
    LocationTelemetry,
)


# ==========================================================
# Dummy Microphone
# ==========================================================


@dataclass
class DummyMicrophoneSensor(
    MicrophoneSensor
):
    """
    Software microphone simulator.

    Generates deterministic mono PCM audio.

    Parameters
    ----------
    frequency:
        Base tone frequency in Hz.

    amplitude:
        Signal amplitude.

    noise_level:
        Gaussian noise level.

    seed:
        Random seed for reproducible output.
    """

    frequency: float = 440.0

    amplitude: float = 0.1

    noise_level: float = 0.005

    seed: int = 42

    def read_audio(
        self,
        duration_seconds: float,
        sample_rate: int,
    ) -> np.ndarray:

        if duration_seconds <= 0:

            raise ValueError(
                "duration_seconds must be greater than zero."
            )

        if sample_rate <= 0:

            raise ValueError(
                "sample_rate must be greater than zero."
            )

        sample_count = int(
            duration_seconds * sample_rate
        )

        if sample_count <= 0:

            raise ValueError(
                "Audio duration is too short."
            )

        time_axis = (
            np.arange(sample_count)
            / sample_rate
        )

        signal = (
            self.amplitude
            * np.sin(
                2.0
                * np.pi
                * self.frequency
                * time_axis
            )
        )

        rng = np.random.default_rng(
            self.seed
        )

        noise = rng.normal(
            0.0,
            self.noise_level,
            sample_count,
        )

        audio = signal + noise

        return audio.astype(
            np.float32
        )


# ==========================================================
# Dummy Battery
# ==========================================================


@dataclass
class DummyBatterySensor(
    BatterySensor
):
    """
    Software battery/fuel-gauge simulator.

    Production equivalent:
        MAX17048
    """

    battery_percent: float = 82.5

    battery_voltage: float = 3.91

    def read_battery_percent(
        self,
    ) -> float:

        return float(
            self.battery_percent
        )

    def read_battery_voltage(
        self,
    ) -> float:

        return float(
            self.battery_voltage
        )


# ==========================================================
# Dummy Environmental Sensor
# ==========================================================


@dataclass
class DummyEnvironmentalSensor(
    EnvironmentalSensor
):
    """
    Software temperature/humidity simulator.

    Production equivalent:
        BME280
    """

    temperature: float = 28.4

    humidity: float = 67.2

    def read_temperature(
        self,
    ) -> float:

        return float(
            self.temperature
        )

    def read_humidity(
        self,
    ) -> float:

        return float(
            self.humidity
        )


# ==========================================================
# Dummy Light Sensor
# ==========================================================


@dataclass
class DummyLightSensor(
    LightSensor
):
    """
    Software ambient-light simulator.

    Production equivalent:
        BH1750
    """

    light_level: float = 145.0

    def read_light_level(
        self,
    ) -> float:

        return float(
            self.light_level
        )


# ==========================================================
# Dummy Vibration Sensor
# ==========================================================


@dataclass
class DummyVibrationSensor(
    VibrationSensor
):
    """
    Software vibration simulator.

    Production equivalent:
        SW-420
    """

    detected: bool = False

    def vibration_detected(
        self,
    ) -> bool:

        return bool(
            self.detected
        )


# ==========================================================
# Dummy GPS
# ==========================================================


@dataclass
class DummyGPSSensor(
    GPSSensor
):
    """
    Software GPS simulator.
    """

    latitude: float = 12.2958

    longitude: float = 76.6394

    altitude: float = 770.0

    accuracy: float = 4.5

    def read_location(
        self,
    ) -> LocationTelemetry:

        return LocationTelemetry(

            latitude=self.latitude,

            longitude=self.longitude,

            altitude=self.altitude,

            accuracy=self.accuracy,

        )