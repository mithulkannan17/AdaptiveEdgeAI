"""
Edge Runtime Communication Service

Connects the edge runtime controller with the backend
communication layer.

The service coordinates:

    EdgeController
        ↓
    TransmissionPolicy
        ↓
    HardwareSensorManager
        ↓
    EdgeMessageSerializer
        ↓
    CommunicationClient

Hardware telemetry can be supplied explicitly through
HardwareTelemetry or automatically collected from a
HardwareSensorManager.

The same interface works with both dummy sensors and
future real ESP32-S3 sensor drivers.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from communication.client import CommunicationClient
from communication.serializer import EdgeMessageSerializer
from communication.transmission_policy import (
    TransmissionPolicy,
)

from hardware.sensors import (
    HardwareSensorManager,
)

from hardware.telemetry import (
    HardwareTelemetry,
)


class EdgeRuntimeService:
    """
    Coordinates EdgeController execution and backend
    communication.

    HardwareSensorManager is optional.

    When configured:

        HardwareSensorManager
                ↓
        HardwareTelemetry
                ↓
        EdgeMessageSerializer

    When not configured, the service continues to support
    explicitly supplied telemetry and legacy location /
    device_status dictionaries.
    """

    def __init__(
        self,
        controller,
        device_id: str,
        communication_client: Optional[
            CommunicationClient
        ] = None,
        transmission_policy: Optional[
            TransmissionPolicy
        ] = None,
        sensor_manager: Optional[
            HardwareSensorManager
        ] = None,
    ):

        if controller is None:

            raise ValueError(
                "controller cannot be None."
            )

        self.controller = controller

        self.serializer = (
            EdgeMessageSerializer(
                device_id=device_id
            )
        )

        self.client = (

            communication_client

            if communication_client is not None

            else CommunicationClient()

        )

        self.transmission_policy = (

            transmission_policy

            if transmission_policy is not None

            else TransmissionPolicy()

        )

        # --------------------------------------------------
        # Hardware Sensor Manager
        # --------------------------------------------------

        if sensor_manager is not None:

            if not isinstance(
                sensor_manager,
                HardwareSensorManager,
            ):

                raise TypeError(
                    "sensor_manager must be a "
                    "HardwareSensorManager instance."
                )

        self.sensor_manager = (
            sensor_manager
        )

        # --------------------------------------------------
        # Runtime state
        # --------------------------------------------------

        self.last_runtime_result = None

        self.last_message = None

        self.last_response = None

        self.last_telemetry = None

        self.last_transmitted = False

    # ======================================================
    # Hardware Telemetry
    # ======================================================

    def read_hardware_telemetry(
        self,
    ) -> HardwareTelemetry | None:
        """
        Read a complete hardware telemetry snapshot.

        Returns None when no HardwareSensorManager has
        been configured.

        This method is intentionally independent of whether
        the configured sensors are dummy implementations
        or real ESP32-S3 hardware drivers.
        """

        if self.sensor_manager is None:

            return None

        telemetry = (
            self.sensor_manager.read_all()
        )

        if not isinstance(
            telemetry,
            HardwareTelemetry,
        ):

            raise TypeError(
                "HardwareSensorManager.read_all() "
                "must return HardwareTelemetry."
            )

        self.last_telemetry = telemetry

        return telemetry

    # ======================================================
    # Telemetry Normalization
    # ======================================================

    @staticmethod
    def _normalize_telemetry(
        telemetry: HardwareTelemetry | None,
        location: dict | None,
        device_status: dict | None,
    ) -> tuple[dict | None, dict | None]:
        """
        Normalize structured HardwareTelemetry into the
        dictionaries expected by the communication serializer.

        Legacy location/device_status arguments remain
        supported for backward compatibility.

        Explicit telemetry takes precedence over legacy
        dictionary arguments.
        """

        if telemetry is not None:

            if not isinstance(
                telemetry,
                HardwareTelemetry,
            ):

                raise TypeError(
                    "telemetry must be a HardwareTelemetry "
                    "instance."
                )

            telemetry_data = (
                telemetry.to_dict()
            )

            telemetry_location = (
                telemetry_data["location"]
            )

            telemetry_status = (
                telemetry_data["device_status"]
            )

            # Structured telemetry takes precedence.
            if telemetry_location is not None:

                location = telemetry_location

            if telemetry_status is not None:

                device_status = telemetry_status

        return (
            location,
            device_status,
        )

    # ======================================================
    # Transmission
    # ======================================================

    def _transmit(
        self,
        runtime_result,
        telemetry: HardwareTelemetry | None = None,
        location: dict | None = None,
        device_status: dict | None = None,
    ):
        """
        Serialize and transmit a runtime result when
        permitted by the transmission policy.

        If telemetry is not explicitly supplied and a
        HardwareSensorManager is configured, telemetry is
        collected automatically.
        """

        should_transmit = (
            self.transmission_policy.should_transmit(
                runtime_result
            )
        )

        self.last_transmitted = (
            should_transmit
        )

        # --------------------------------------------------
        # Transmission suppressed
        # --------------------------------------------------

        if not should_transmit:

            self.last_message = None

            self.last_response = None

            return None

        # --------------------------------------------------
        # Automatic hardware telemetry
        # --------------------------------------------------

        if (
            telemetry is None
            and self.sensor_manager is not None
        ):

            telemetry = (
                self.read_hardware_telemetry()
            )

        # --------------------------------------------------
        # Normalize hardware telemetry
        # --------------------------------------------------

        (
            location,
            device_status,
        ) = self._normalize_telemetry(

            telemetry,

            location,

            device_status,

        )

        # --------------------------------------------------
        # Serialize
        # --------------------------------------------------

        message = (
            self.serializer.serialize(

                runtime_result,

                location=location,

                device_status=device_status,

            )
        )

        self.last_message = message

        # --------------------------------------------------
        # Send
        # --------------------------------------------------

        response = (
            self.client.send(
                message
            )
        )

        self.last_response = response

        return response

    # ======================================================
    # Process Spectrogram
    # ======================================================

    def process_spectrogram(
        self,
        spectrogram,
        top_k: int = 5,
        audio_path: str | Path | None = None,
        telemetry: HardwareTelemetry | None = None,
        location: dict | None = None,
        device_status: dict | None = None,
    ):
        """
        Run the complete edge pipeline and transmit
        the resulting intelligence when permitted.

        Parameters
        ----------
        telemetry:
            Structured hardware telemetry snapshot.

            If omitted and sensor_manager is configured,
            telemetry is automatically collected.

        location:
            Legacy location dictionary.

        device_status:
            Legacy device-status dictionary.
        """

        runtime_result = (
            self.controller.process_spectrogram(

                spectrogram,

                top_k=top_k,

                audio_path=audio_path,

            )
        )

        self.last_runtime_result = (
            runtime_result
        )

        return self._transmit(

            runtime_result,

            telemetry=telemetry,

            location=location,

            device_status=device_status,

        )

    # ======================================================
    # Process Prediction
    # ======================================================

    def process_prediction(
        self,
        prediction,
        telemetry: HardwareTelemetry | None = None,
        location: dict | None = None,
        device_status: dict | None = None,
    ):
        """
        Process an existing prediction through the
        edge pipeline and transmit the result when
        permitted.

        Hardware telemetry is automatically collected
        when a sensor manager is configured and explicit
        telemetry is not supplied.
        """

        runtime_result = (
            self.controller.process_prediction(
                prediction
            )
        )

        self.last_runtime_result = (
            runtime_result
        )

        return self._transmit(

            runtime_result,

            telemetry=telemetry,

            location=location,

            device_status=device_status,

        )

    # ======================================================
    # State
    # ======================================================

    def get_last_runtime_result(
        self,
    ):
        """
        Return the most recent edge runtime result.
        """

        return self.last_runtime_result

    def get_last_message(
        self,
    ):
        """
        Return the most recently serialized message.

        Returns None when the latest result was not
        transmitted.
        """

        return self.last_message

    def get_last_response(
        self,
    ):
        """
        Return the most recent backend response.

        Returns None when the latest result was not
        transmitted.
        """

        return self.last_response

    def get_last_telemetry(
        self,
    ) -> HardwareTelemetry | None:
        """
        Return the most recently collected hardware
        telemetry snapshot.
        """

        return self.last_telemetry

    def was_last_transmitted(
        self,
    ) -> bool:
        """
        Return whether the latest runtime result was
        transmitted to the backend.
        """

        return self.last_transmitted