"""
Dashboard API Client

Provides a small HTTP client used by the Streamlit
dashboard to communicate with the FastAPI backend.

The dashboard never accesses SQLite directly.
"""

from __future__ import annotations

from typing import Any

import httpx


class DashboardAPIError(
    RuntimeError
):
    """Raised when the dashboard cannot communicate
    with the backend."""


class DashboardAPIClient:
    """
    HTTP client for dashboard-facing backend endpoints.
    """

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8000",
        timeout: float = 5.0,
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

    # ======================================================
    # Request Helper
    # ======================================================

    def _get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> Any:
        """
        Perform a GET request against the backend.
        """

        try:

            response = httpx.get(

                f"{self.base_url}{path}",

                params=params,

                timeout=self.timeout,

            )

        except httpx.RequestError as exc:

            raise DashboardAPIError(
                f"Unable to reach backend: {exc}"
            ) from exc

        if response.status_code >= 400:

            raise DashboardAPIError(

                "Backend request failed: "
                f"{response.status_code} "
                f"{response.text}"

            )

        try:

            return response.json()

        except ValueError as exc:

            raise DashboardAPIError(
                "Backend returned invalid JSON."
            ) from exc

    # ======================================================
    # Health
    # ======================================================

    def health(
        self,
    ) -> dict:
        """
        Return backend health information.
        """

        return self._get(
            "/health"
        )

    # ======================================================
    # Latest Event
    # ======================================================

    def latest_event(
        self,
    ) -> dict | None:
        """
        Return the latest runtime event.
        """

        try:

            return self._get(
                "/api/v1/edge/events/latest"
            )

        except DashboardAPIError as exc:

            if "404" in str(exc):

                return None

            raise

    # ======================================================
    # Recent Events
    # ======================================================

    def recent_events(
        self,
        limit: int = 50,
        device_id: str | None = None,
    ) -> list[dict]:
        """
        Return recent runtime events.
        """

        params = {
            "limit": limit,
        }

        if device_id:

            params["device_id"] = (
                device_id
            )

        result = self._get(

            "/api/v1/dashboard/events",

            params=params,

        )

        return list(
            result
        )

    # ======================================================
    # Devices
    # ======================================================

    def devices(
        self,
    ) -> list[str]:
        """
        Return available edge devices.
        """

        result = self._get(
            "/api/v1/edge/devices"
        )

        return list(
            result.get(
                "devices",
                [],
            )
        )

    # ======================================================
    # Dashboard Summary
    # ======================================================

    def summary(
        self,
    ) -> dict:
        """
        Return dashboard summary information.
        """

        return self._get(
            "/api/v1/dashboard/summary"
        )