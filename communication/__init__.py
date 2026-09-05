"""
Communication Package

Provides the communication contract, telemetry structures,
backend client, transmission policy, serializer, and
edge runtime communication service.
"""

from communication.schemas import (
    AdaptivePolicyMessage,
    DecisionMessage,
    EdgeMessage,
    EnvironmentMessage,
    EventMessage,
    PredictionMessage,
)

from communication.telemetry import (
    DeviceTelemetry,
    LocationTelemetry,
)

from communication.client import (
    CommunicationClient,
    CommunicationError,
)

from communication.serializer import (
    EdgeMessageSerializer,
)

from communication.transmission_policy import (
    TransmissionPolicy,
)

from communication.runtime_service import (
    EdgeRuntimeService,
)


__all__ = [

    # --------------------------------------------------
    # Message schemas
    # --------------------------------------------------

    "PredictionMessage",

    "EnvironmentMessage",

    "AdaptivePolicyMessage",

    "EventMessage",

    "DecisionMessage",

    "EdgeMessage",

    # --------------------------------------------------
    # Telemetry
    # --------------------------------------------------

    "DeviceTelemetry",

    "LocationTelemetry",

    # --------------------------------------------------
    # Communication
    # --------------------------------------------------

    "CommunicationClient",

    "CommunicationError",

    "EdgeMessageSerializer",

    "TransmissionPolicy",

    "EdgeRuntimeService",

]