"""
Communication Client

Sends serialized edge-runtime messages to the backend API.
"""

from __future__ import annotations

from typing import Any

import httpx

from communication.schemas import EdgeMessage


class CommunicationError(
    RuntimeError
):
    """
    Raised when communication with the backend fails.
    """


class CommunicationClient:
    """
    HTTP client used by an edge node to communicate
    with the backend service.
    """

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8000",
        timeout: float = 10.0,
    ):
        self.base_url = (
            base_url.rstrip("/")
        )

        self.timeout = float(
            timeout
        )

        if self.timeout <= 0:

            raise ValueError(
                "timeout must be greater than zero."
            )

    def _events_url(self) -> str:
        """
        Return the edge-event API endpoint.
        """

        return (
            f"{self.base_url}"
            "/api/v1/edge/events"
        )

    def send(
        self,
        message: EdgeMessage,
    ) -> dict[str, Any]:
        """
        Send an EdgeMessage to the backend.

        Parameters
        ----------
        message:
            Serialized edge runtime message.

        Returns
        -------
        dict
            Backend response.

        Raises
        ------
        TypeError
            If message is not an EdgeMessage.

        CommunicationError
            If the request fails.
        """

        if not isinstance(
            message,
            EdgeMessage,
        ):

            raise TypeError(
                "message must be an EdgeMessage."
            )

        payload = message.to_dict()

        try:

            response = httpx.post(

                self._events_url(),

                json=payload,

                timeout=self.timeout,

            )

        except (
            httpx.ConnectError,
            httpx.TimeoutException,
            httpx.NetworkError,
            httpx.RequestError,
        ) as exc:

            raise CommunicationError(
                f"Unable to communicate with backend: {exc}"
            ) from exc

        if response.status_code >= 400:

            raise CommunicationError(

                "Backend rejected edge message: "
                f"{response.status_code} "
                f"{response.text}"

            )

        try:

            return response.json()

        except ValueError as exc:

            raise CommunicationError(
                "Backend returned invalid JSON."
            ) from exc

    def health(
        self,
    ) -> dict[str, Any]:
        """
        Check backend availability.
        """

        try:

            response = httpx.get(

                f"{self.base_url}/health",

                timeout=self.timeout,

            )

        except (
            httpx.ConnectError,
            httpx.TimeoutException,
            httpx.NetworkError,
            httpx.RequestError,
        ) as exc:

            raise CommunicationError(
                f"Unable to reach backend: {exc}"
            ) from exc

        if response.status_code >= 400:

            raise CommunicationError(

                "Backend health check failed: "
                f"{response.status_code}"

            )

        try:

            return response.json()

        except ValueError as exc:

            raise CommunicationError(
                "Backend returned invalid health response."
            ) from exc