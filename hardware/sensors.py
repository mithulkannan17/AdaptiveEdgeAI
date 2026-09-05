"""
Hardware Sensor Interfaces

Defines the hardware abstraction used by the edge runtime
to obtain sensor telemetry and acoustic input.

The implementations are intentionally hardware-independent.

Actual ESP32-S3 sensor drivers can later implement these
interfaces for:

    - INMP441
    - MAX17048
    - BME280
    - BH1750
    - SW420
    - GPS
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np

from hardware.telemetry import (
    DeviceTelemetry,
    HardwareTelemetry,
    LocationTelemetry,
)

from hardware.microphone import (
    MicrophoneSensor,
)


# ==========================================================
# Microphone
# ==========================================================


class MicrophoneSensor(ABC):
    """
    Interface for the environmental microphone.

    The production implementation will obtain PCM audio
    samples from the INMP441 microphone connected to the
    ESP32-S3.

    The edge inference pipeline can consume the returned
    samples without knowing how the microphone is connected.
    """

    @abstractmethod
    def read_audio(
        self,
        duration_seconds: float,
        sample_rate: int,
    ) -> np.ndarray:
        """
        Capture PCM audio samples.

        Parameters
        ----------
        duration_seconds:
            Duration of audio to capture.

        sample_rate:
            Target sampling rate in Hz.

        Returns
        -------
        numpy.ndarray
            Mono floating-point PCM samples.
        """


# ==========================================================
# Battery
# ==========================================================


class BatterySensor(ABC):
    """
    Interface for a battery/fuel-gauge sensor.

    Production implementation:
        MAX17048
    """

    @abstractmethod
    def read_battery_percent(self) -> float:
        """Return battery charge percentage."""

    @abstractmethod
    def read_battery_voltage(self) -> float:
        """Return battery voltage."""


# ==========================================================
# Environmental Sensor
# ==========================================================


class EnvironmentalSensor(ABC):
    """
    Interface for temperature/humidity sensing.

    Production implementation:
        BME280
    """

    @abstractmethod
    def read_temperature(self) -> float:
        """Return temperature in degrees Celsius."""

    @abstractmethod
    def read_humidity(self) -> float:
        """Return relative humidity percentage."""


# ==========================================================
# Light Sensor
# ==========================================================


class LightSensor(ABC):
    """
    Interface for ambient-light sensing.

    Production implementation:
        BH1750
    """

    @abstractmethod
    def read_light_level(self) -> float:
        """Return ambient light level."""


# ==========================================================
# Vibration Sensor
# ==========================================================


class VibrationSensor(ABC):
    """
    Interface for vibration detection.

    Production implementation:
        SW-420
    """

    @abstractmethod
    def vibration_detected(self) -> bool:
        """Return whether vibration is currently detected."""


# ==========================================================
# GPS
# ==========================================================


class GPSSensor(ABC):
    """
    Interface for GPS/location sensing.
    """

    @abstractmethod
    def read_location(self) -> LocationTelemetry:
        """Return the current GPS location."""


# ==========================================================
# Hardware Sensor Manager
# ==========================================================


class HardwareSensorManager:
    """
    Aggregates individual hardware sensors into a single
    HardwareTelemetry snapshot.

    The manager deliberately does not know whether a sensor
    is real hardware or a dummy implementation.

    This allows the complete software stack to be tested
    before the ESP32-S3 hardware is available.
    """

    def __init__(
        self,
        microphone_sensor: MicrophoneSensor | None = None,
        battery_sensor: BatterySensor | None = None,
        environmental_sensor: EnvironmentalSensor | None = None,
        light_sensor: LightSensor | None = None,
        vibration_sensor: VibrationSensor | None = None,
        gps_sensor: GPSSensor | None = None,
    ):

        self.microphone_sensor = (
            microphone_sensor
        )

        self.battery_sensor = (
            battery_sensor
        )

        self.environmental_sensor = (
            environmental_sensor
        )

        self.light_sensor = (
            light_sensor
        )

        self.vibration_sensor = (
            vibration_sensor
        )

        self.gps_sensor = (
            gps_sensor
        )

    # ======================================================
    # Audio
    # ======================================================

    def read_audio(
        self,
        duration_seconds: float,
        sample_rate: int,
    ) -> np.ndarray:
        """
        Capture audio using the configured microphone.

        Raises
        ------
        RuntimeError
            If no microphone is configured.
        """

        if self.microphone_sensor is None:

            raise RuntimeError(
                "No microphone sensor is configured."
            )

        if duration_seconds <= 0:

            raise ValueError(
                "duration_seconds must be greater than zero."
            )

        if sample_rate <= 0:

            raise ValueError(
                "sample_rate must be greater than zero."
            )

        audio = self.microphone_sensor.read_audio(

            duration_seconds=duration_seconds,

            sample_rate=sample_rate,

        )

        audio = np.asarray(
            audio,
            dtype=np.float32,
        )

        if audio.ndim != 1:

            raise ValueError(
                "Microphone audio must be a mono "
                "one-dimensional array."
            )

        return audio

    # ======================================================
    # Device Status
    # ======================================================

    def read_device_status(
        self,
    ) -> DeviceTelemetry:
        """
        Read all available device/environment sensors.

        Missing sensors remain represented as None.
        """

        battery_percent = None

        battery_voltage = None

        temperature = None

        humidity = None

        light_level = None

        vibration_detected = None

        # --------------------------------------------------
        # Battery
        # --------------------------------------------------

        if self.battery_sensor is not None:

            battery_percent = (
                self.battery_sensor
                .read_battery_percent()
            )

            battery_voltage = (
                self.battery_sensor
                .read_battery_voltage()
            )

        # --------------------------------------------------
        # Environment
        # --------------------------------------------------

        if self.environmental_sensor is not None:

            temperature = (
                self.environmental_sensor
                .read_temperature()
            )

            humidity = (
                self.environmental_sensor
                .read_humidity()
            )

        # --------------------------------------------------
        # Light
        # --------------------------------------------------

        if self.light_sensor is not None:

            light_level = (
                self.light_sensor
                .read_light_level()
            )

        # --------------------------------------------------
        # Vibration
        # --------------------------------------------------

        if self.vibration_sensor is not None:

            vibration_detected = (
                self.vibration_sensor
                .vibration_detected()
            )

        return DeviceTelemetry(

            battery_percent=battery_percent,

            battery_voltage=battery_voltage,

            temperature=temperature,

            humidity=humidity,

            light_level=light_level,

            vibration_detected=vibration_detected,

        )

    # ======================================================
    # GPS
    # ======================================================

    def read_location(
        self,
    ) -> LocationTelemetry | None:
        """
        Read the current GPS location.

        Returns None when no GPS sensor is configured.
        """

        if self.gps_sensor is None:

            return None

        return self.gps_sensor.read_location()

    # ======================================================
    # Complete Telemetry
    # ======================================================

    def read_all(
        self,
    ) -> HardwareTelemetry:
        """
        Read all configured hardware sensors.

        Returns
        -------
        HardwareTelemetry
            Complete hardware telemetry snapshot.
        """

        location = (
            self.read_location()
        )

        device_status = (
            self.read_device_status()
        )

        return HardwareTelemetry(

            location=location,

            device_status=device_status,

        )