"""
Communication Package.

Defines the data contracts and communication client used
between the adaptive edge node and backend services.
"""

from communication.schemas import (
    PredictionMessage,
    EnvironmentMessage,
    AdaptivePolicyMessage,
    EventMessage,
    EdgeMessage,
)

from communication.serializer import (
    EdgeMessageSerializer,
)

from communication.client import (
    CommunicationClient,
    CommunicationError,
)


__all__ = [
    "PredictionMessage",
    "EnvironmentMessage",
    "AdaptivePolicyMessage",
    "EventMessage",
    "EdgeMessage",
    "EdgeMessageSerializer",
    "CommunicationClient",
    "CommunicationError",
]