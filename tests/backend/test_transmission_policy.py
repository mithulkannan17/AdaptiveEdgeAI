"""
Tests for adaptive transmission policy.
"""

from types import SimpleNamespace

import pytest

from communication import (
    TransmissionPolicy,
)


def create_result(
    mode,
    detected=False,
    priority=0,
):

    return SimpleNamespace(

        adaptive_policy=SimpleNamespace(

            transmission_mode=mode,

        ),

        event=SimpleNamespace(

            detected=detected,

            priority=priority,

        ),

    )


def test_continuous_always_transmits():

    policy = TransmissionPolicy()

    result = create_result(
        "continuous",
        detected=False,
        priority=0,
    )

    assert (
        policy.should_transmit(result)
        is True
    )


def test_event_driven_detected_event():

    policy = TransmissionPolicy()

    result = create_result(
        "event_driven",
        detected=True,
        priority=1,
    )

    assert (
        policy.should_transmit(result)
        is True
    )


def test_event_driven_undetected_event():

    policy = TransmissionPolicy()

    result = create_result(
        "event_driven",
        detected=False,
        priority=0,
    )

    assert (
        policy.should_transmit(result)
        is False
    )


def test_selective_detected_event():

    policy = TransmissionPolicy()

    result = create_result(
        "selective",
        detected=True,
        priority=1,
    )

    assert (
        policy.should_transmit(result)
        is True
    )


def test_selective_low_priority_undetected():

    policy = TransmissionPolicy()

    result = create_result(
        "selective",
        detected=False,
        priority=1,
    )

    assert (
        policy.should_transmit(result)
        is False
    )


def test_selective_high_priority():

    policy = TransmissionPolicy()

    result = create_result(
        "selective",
        detected=False,
        priority=4,
    )

    assert (
        policy.should_transmit(result)
        is True
    )


def test_invalid_mode_is_safe():

    policy = TransmissionPolicy()

    result = create_result(
        "invalid_mode",
        detected=True,
        priority=5,
    )

    assert (
        policy.should_transmit(result)
        is False
    )


def test_none_result():

    policy = TransmissionPolicy()

    with pytest.raises(
        ValueError
    ):

        policy.should_transmit(
            None
        )