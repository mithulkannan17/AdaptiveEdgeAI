"""
Dashboard Data Provider
=======================

Provides a stable data interface between the Streamlit dashboard
and the edge/runtime data source.

The provider supports two data sources:

    1. DashboardSimulator
    2. RuntimeDataSource

The simulator remains the default source so the dashboard can
operate without hardware or runtime database data.

The runtime source can be selected explicitly through:

    create_runtime_dashboard_data_provider()

This keeps data acquisition separate from Streamlit rendering.

Supported imports
-----------------

Package execution:

    from dashboard.data_provider import DashboardDataProvider

Direct Streamlit execution:

    streamlit run dashboard/app.py
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Protocol


# ==========================================================
# Simulator Import Compatibility
# ==========================================================

try:

    from .simulator import DashboardSimulator

except ImportError:

    from simulator import DashboardSimulator


# ==========================================================
# Runtime Data Source Import Compatibility
# ==========================================================

try:

    from .runtime_data_source import RuntimeDataSource

except ImportError:

    from runtime_data_source import RuntimeDataSource


# ==========================================================
# Data Source Protocol
# ==========================================================

class DashboardDataSource(Protocol):
    """
    Interface required by DashboardDataProvider.

    Any dashboard data source must provide a tick() method
    returning a dictionary containing the dashboard state.
    """

    def tick(
        self,
    ) -> dict[str, Any]:
        """
        Return the latest dashboard state.
        """
        ...


# ==========================================================
# Dashboard Data Provider
# ==========================================================

class DashboardDataProvider:
    """
    Stable data-access layer for the dashboard.

    The provider separates data acquisition from UI rendering.

    When no source is supplied:

        DashboardSimulator

    is used.

    A RuntimeDataSource or another compatible source can be
    injected without changing the dashboard rendering layer.
    """

    def __init__(
        self,
        source: DashboardDataSource | None = None,
    ) -> None:

        self.source = (

            source

            if source is not None

            else DashboardSimulator()

        )

        self._last_state: dict[str, Any] | None = None

    # ======================================================
    # State
    # ======================================================

    def get_state(
        self,
    ) -> dict[str, Any]:
        """
        Retrieve and normalize the latest dashboard state.

        A deep copy is returned so dashboard code cannot
        accidentally mutate the provider's cached state.
        """

        raw_state = self.source.tick()

        if not isinstance(
            raw_state,
            dict,
        ):

            raise TypeError(
                "Dashboard data source must return "
                "a dictionary."
            )

        state = self._normalize_state(
            raw_state
        )

        self._last_state = deepcopy(
            state
        )

        return deepcopy(
            state
        )

    # ======================================================
    # Cached State
    # ======================================================

    def get_last_state(
        self,
    ) -> dict[str, Any] | None:
        """
        Return the most recently retrieved dashboard state.

        Returns None before the first call to get_state().
        """

        if self._last_state is None:

            return None

        return deepcopy(
            self._last_state
        )

    # ======================================================
    # Normalization
    # ======================================================

    @staticmethod
    def _normalize_state(
        state: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Normalize a source state into the contract expected
        by the dashboard.

        Missing optional sections receive safe empty values.
        """

        # --------------------------------------------------
        # Telemetry
        # --------------------------------------------------

        telemetry = state.get(
            "telemetry"
        )

        if telemetry is None:

            telemetry = {}

        if not isinstance(
            telemetry,
            dict,
        ):

            raise TypeError(
                "Dashboard state 'telemetry' "
                "must be a dictionary."
            )

        # --------------------------------------------------
        # Current Event
        # --------------------------------------------------

        event = state.get(
            "event"
        )

        if (

            event is not None

            and not isinstance(
                event,
                dict,
            )

        ):

            raise TypeError(
                "Dashboard state 'event' "
                "must be a dictionary or None."
            )

        # --------------------------------------------------
        # Event History
        # --------------------------------------------------

        events = state.get(
            "events",
            [],
        )

        if events is None:

            events = []

        if not isinstance(
            events,
            list,
        ):

            raise TypeError(
                "Dashboard state 'events' "
                "must be a list."
            )

        # --------------------------------------------------
        # CADIE
        # --------------------------------------------------

        cadie = state.get(
            "cadie"
        )

        if cadie is None:

            cadie = {}

        if not isinstance(
            cadie,
            dict,
        ):

            raise TypeError(
                "Dashboard state 'cadie' "
                "must be a dictionary."
            )

        # --------------------------------------------------
        # Waveform
        # --------------------------------------------------

        waveform = state.get(
            "waveform",
            [],
        )

        if waveform is None:

            waveform = []

        if not isinstance(
            waveform,
            (list, tuple),
        ):

            raise TypeError(
                "Dashboard state 'waveform' "
                "must be a list or tuple."
            )

        # --------------------------------------------------
        # Normalized State
        # --------------------------------------------------

        return {

            "telemetry":
                dict(
                    telemetry
                ),

            "event":
                deepcopy(
                    event
                ),

            "events":
                deepcopy(
                    events
                ),

            "cadie":
                dict(
                    cadie
                ),

            "waveform":
                list(
                    waveform
                ),

        }

    # ======================================================
    # Convenience Accessors
    # ======================================================

    def get_telemetry(
        self,
    ) -> dict[str, Any]:
        """
        Return the latest telemetry.

        Raises RuntimeError when no state has been retrieved.
        """

        state = self._require_state()

        return deepcopy(
            state[
                "telemetry"
            ]
        )

    def get_current_event(
        self,
    ) -> dict[str, Any] | None:
        """
        Return the latest detected event.
        """

        state = self._require_state()

        return deepcopy(
            state[
                "event"
            ]
        )

    def get_events(
        self,
    ) -> list[dict[str, Any]]:
        """
        Return the event history.
        """

        state = self._require_state()

        return deepcopy(
            state[
                "events"
            ]
        )

    def get_cadie(
        self,
    ) -> dict[str, Any]:
        """
        Return the latest CADIE decision.
        """

        state = self._require_state()

        return deepcopy(
            state[
                "cadie"
            ]
        )

    def get_waveform(
        self,
    ) -> list[Any]:
        """
        Return the latest acoustic waveform representation.
        """

        state = self._require_state()

        return list(
            state[
                "waveform"
            ]
        )

    # ======================================================
    # Runtime Control
    # ======================================================

    def reset(
        self,
    ) -> None:
        """
        Reset the underlying source when it exposes reset().

        The provider cache is always cleared.
        """

        reset_method = getattr(
            self.source,
            "reset",
            None,
        )

        if callable(
            reset_method
        ):

            reset_method()

        self._last_state = None

    # ======================================================
    # Source Information
    # ======================================================

    def source_name(
        self,
    ) -> str:
        """
        Return the class name of the active data source.
        """

        return self.source.__class__.__name__

    def is_simulator(
        self,
    ) -> bool:
        """
        Return True when the active source is DashboardSimulator.
        """

        return isinstance(
            self.source,
            DashboardSimulator,
        )

    # ======================================================
    # Internal Helpers
    # ======================================================

    def _require_state(
        self,
    ) -> dict[str, Any]:
        """
        Return cached state.

        Raises RuntimeError when get_state() has not yet
        been called.
        """

        if self._last_state is None:

            raise RuntimeError(
                "No dashboard state is available. "
                "Call get_state() first."
            )

        return self._last_state


# ==========================================================
# Simulator Factory
# ==========================================================

def create_dashboard_data_provider(
) -> DashboardDataProvider:
    """
    Create the default dashboard data provider.

    The default source remains DashboardSimulator.

    This preserves the existing dashboard behavior and
    allows development without hardware.
    """

    return DashboardDataProvider(
        source=DashboardSimulator()
    )


# ==========================================================
# Runtime Factory
# ==========================================================

def create_runtime_dashboard_data_provider(
) -> DashboardDataProvider:
    """
    Create a dashboard data provider backed by the real
    runtime database.

    Data flow:

        RuntimeDatabase
              ↓
        RuntimeDataSource
              ↓
        DashboardDataProvider
              ↓
        Streamlit
    """

    return DashboardDataProvider(
        source=RuntimeDataSource()
    )