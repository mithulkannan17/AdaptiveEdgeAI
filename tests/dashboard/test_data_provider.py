"""
Tests for dashboard.data_provider.

These tests verify the dashboard data-access boundary without
depending on Streamlit rendering or the real runtime database.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest


# ==========================================================
# Project Import Path
# ==========================================================

# File location:
#
# AdaptiveEdgeAI/
#     tests/
#         dashboard/
#             test_data_provider.py
#
# parents[0] -> tests/dashboard
# parents[1] -> tests
# parents[2] -> AdaptiveEdgeAI

PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)

if str(PROJECT_ROOT) not in sys.path:

    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )


# ==========================================================
# Dashboard Import
# ==========================================================

from dashboard.data_provider import (
    DashboardDataProvider,
)


# ==========================================================
# Fake Data Source
# ==========================================================

class FakeSource:
    """
    Deterministic fake dashboard source used for testing.
    """

    def __init__(self) -> None:

        self.calls = 0

        self.reset_calls = 0

    def tick(self) -> dict:

        self.calls += 1

        return {

            "telemetry": {

                "temperature": 24.5,

                "humidity": 68.2,

            },

            "event": {

                "label": "Bird",

                "confidence": 91.4,

            },

            "events": [

                {

                    "label": "Bird",

                    "confidence": 91.4,

                }

            ],

            "cadie": {

                "risk_level": "LOW",

                "score": 0.18,

            },

            "waveform": [

                0.1,

                -0.2,

                0.3,

            ],

        }

    def reset(self) -> None:

        self.reset_calls += 1


# ==========================================================
# State Retrieval
# ==========================================================

def test_provider_reads_state_from_source():

    source = FakeSource()

    provider = DashboardDataProvider(
        source=source
    )

    state = provider.get_state()

    assert source.calls == 1

    assert (
        state["telemetry"]["temperature"]
        == 24.5
    )

    assert (
        state["event"]["label"]
        == "Bird"
    )

    assert (
        state["events"][0]["label"]
        == "Bird"
    )

    assert (
        state["cadie"]["risk_level"]
        == "LOW"
    )

    assert state["waveform"] == [
        0.1,
        -0.2,
        0.3,
    ]


# ==========================================================
# Cached State
# ==========================================================

def test_provider_returns_copy_of_cached_state():

    source = FakeSource()

    provider = DashboardDataProvider(
        source=source
    )

    state = provider.get_state()

    state[
        "telemetry"
    ][
        "temperature"
    ] = 999

    cached = provider.get_last_state()

    assert cached is not None

    assert (
        cached[
            "telemetry"
        ][
            "temperature"
        ]
        == 24.5
    )


def test_provider_returns_copy_from_get_last_state():

    source = FakeSource()

    provider = DashboardDataProvider(
        source=source
    )

    provider.get_state()

    first = provider.get_last_state()

    assert first is not None

    first[
        "telemetry"
    ][
        "temperature"
    ] = 999

    second = provider.get_last_state()

    assert second is not None

    assert (
        second[
            "telemetry"
        ][
            "temperature"
        ]
        == 24.5
    )


# ==========================================================
# Convenience Accessors
# ==========================================================

def test_provider_convenience_accessors():

    provider = DashboardDataProvider(
        source=FakeSource()
    )

    provider.get_state()

    assert (
        provider.get_telemetry()[
            "humidity"
        ]
        == 68.2
    )

    assert (
        provider.get_current_event()[
            "label"
        ]
        == "Bird"
    )

    assert len(
        provider.get_events()
    ) == 1

    assert (
        provider.get_cadie()[
            "score"
        ]
        == 0.18
    )

    assert (
        provider.get_waveform()
        == [
            0.1,
            -0.2,
            0.3,
        ]
    )


# ==========================================================
# State Required
# ==========================================================

def test_provider_requires_state_for_accessors():

    provider = DashboardDataProvider(
        source=FakeSource()
    )

    with pytest.raises(RuntimeError):

        provider.get_telemetry()

    with pytest.raises(RuntimeError):

        provider.get_current_event()

    with pytest.raises(RuntimeError):

        provider.get_events()

    with pytest.raises(RuntimeError):

        provider.get_cadie()

    with pytest.raises(RuntimeError):

        provider.get_waveform()


# ==========================================================
# Invalid State
# ==========================================================

def test_provider_rejects_invalid_state():

    class InvalidSource:

        def tick(self):

            return []

    provider = DashboardDataProvider(
        source=InvalidSource()
    )

    with pytest.raises(TypeError):

        provider.get_state()


def test_provider_rejects_invalid_telemetry():

    class InvalidSource:

        def tick(self):

            return {

                "telemetry": "invalid",

                "event": None,

                "events": [],

                "cadie": {},

                "waveform": [],

            }

    provider = DashboardDataProvider(
        source=InvalidSource()
    )

    with pytest.raises(TypeError):

        provider.get_state()


def test_provider_rejects_invalid_event():

    class InvalidSource:

        def tick(self):

            return {

                "telemetry": {},

                "event": "invalid",

                "events": [],

                "cadie": {},

                "waveform": [],

            }

    provider = DashboardDataProvider(
        source=InvalidSource()
    )

    with pytest.raises(TypeError):

        provider.get_state()


def test_provider_rejects_invalid_events():

    class InvalidSource:

        def tick(self):

            return {

                "telemetry": {},

                "event": None,

                "events": "invalid",

                "cadie": {},

                "waveform": [],

            }

    provider = DashboardDataProvider(
        source=InvalidSource()
    )

    with pytest.raises(TypeError):

        provider.get_state()


def test_provider_rejects_invalid_cadie():

    class InvalidSource:

        def tick(self):

            return {

                "telemetry": {},

                "event": None,

                "events": [],

                "cadie": "invalid",

                "waveform": [],

            }

    provider = DashboardDataProvider(
        source=InvalidSource()
    )

    with pytest.raises(TypeError):

        provider.get_state()


def test_provider_rejects_invalid_waveform():

    class InvalidSource:

        def tick(self):

            return {

                "telemetry": {},

                "event": None,

                "events": [],

                "cadie": {},

                "waveform": "invalid",

            }

    provider = DashboardDataProvider(
        source=InvalidSource()
    )

    with pytest.raises(TypeError):

        provider.get_state()


# ==========================================================
# Reset
# ==========================================================

def test_provider_reset_clears_cache():

    source = FakeSource()

    provider = DashboardDataProvider(
        source=source
    )

    provider.get_state()

    assert (
        provider.get_last_state()
        is not None
    )

    provider.reset()

    assert (
        source.reset_calls
        == 1
    )

    assert (
        provider.get_last_state()
        is None
    )


def test_provider_reset_without_source_reset():

    class SourceWithoutReset:

        def tick(self):

            return {

                "telemetry": {},

                "event": None,

                "events": [],

                "cadie": {},

                "waveform": [],

            }

    provider = DashboardDataProvider(
        source=SourceWithoutReset()
    )

    provider.get_state()

    assert (
        provider.get_last_state()
        is not None
    )

    provider.reset()

    assert (
        provider.get_last_state()
        is None
    )


# ==========================================================
# Source Information
# ==========================================================

def test_provider_source_information():

    source = FakeSource()

    provider = DashboardDataProvider(
        source=source
    )

    assert (
        provider.source_name()
        == "FakeSource"
    )

    assert (
        provider.is_simulator()
        is False
    )


def test_default_provider_uses_simulator():

    provider = DashboardDataProvider()

    assert (
        provider.is_simulator()
        is True
    )

    assert (
        provider.source_name()
        == "DashboardSimulator"
    )


# ==========================================================
# State Refresh
# ==========================================================

def test_provider_refreshes_source_on_each_get_state():

    source = FakeSource()

    provider = DashboardDataProvider(
        source=source
    )

    first = provider.get_state()

    second = provider.get_state()

    assert source.calls == 2

    assert first == second