"""
Tests for CADIE.
"""

from types import SimpleNamespace

from edge.decision import (
    CADIE,
)


def create_prediction(
    confidence=0.95,
    label="Chainsaw",
):

    return SimpleNamespace(

        label=label,

        confidence=confidence,

        class_id=1,

    )


def create_profile(
    environment_type="Natural",
):

    return SimpleNamespace(

        environment_type=environment_type,

    )


def create_policy(
    sensitivity=1.30,
):

    return SimpleNamespace(

        sensitivity_for=lambda label: sensitivity,

    )


def create_event(
    detected=True,
    priority=5,
):

    return SimpleNamespace(

        detected=detected,

        priority=priority,

    )


def test_high_priority_natural_event_becomes_critical():

    cadie = CADIE()

    result = cadie.evaluate(

        prediction=create_prediction(
            confidence=0.95,
            label="Chainsaw",
        ),

        environment_profile=create_profile(
            "Natural"
        ),

        adaptive_policy=create_policy(
            1.30
        ),

        event=create_event(
            detected=True,
            priority=5,
        ),

        device_status={
            "battery_percent": 82.5,
        },

    )

    assert (
        result.risk_level
        == "CRITICAL"
    )

    assert (
        result.recommended_action
        == "TRANSMIT_IMMEDIATELY"
    )

    assert (
        result.requires_attention
        is True
    )

    assert (
        result.decision_score
        >= 0.90
    )


def test_undetected_event_is_not_critical():

    cadie = CADIE()

    result = cadie.evaluate(

        prediction=create_prediction(
            confidence=0.95,
            label="Bird",
        ),

        environment_profile=create_profile(
            "Natural"
        ),

        adaptive_policy=create_policy(
            1.20
        ),

        event=create_event(
            detected=False,
            priority=1,
        ),

    )

    assert (
        result.risk_level
        not in {
            "HIGH",
            "CRITICAL",
        }
    )

    assert (
        result.recommended_action
        == "MONITOR"
    )

    assert (
        result.requires_attention
        is False
    )


def test_weather_background_event_is_low_significance():

    cadie = CADIE()

    result = cadie.evaluate(

        prediction=create_prediction(
            confidence=0.80,
            label="Wind",
        ),

        environment_profile=create_profile(
            "WeatherDominant"
        ),

        adaptive_policy=create_policy(
            0.60
        ),

        event=create_event(
            detected=True,
            priority=1,
        ),

    )

    assert (
        result.risk_level
        in {
            "LOW",
            "MEDIUM",
        }
    )

    assert (
        result.recommended_action
        in {
            "MONITOR",
            "PRIORITIZE",
        }
    )


def test_low_battery_can_defer_low_risk_event():

    cadie = CADIE()

    result = cadie.evaluate(

        prediction=create_prediction(
            confidence=0.50,
            label="Bird",
        ),

        environment_profile=create_profile(
            "Natural"
        ),

        adaptive_policy=create_policy(
            1.0
        ),

        event=create_event(
            detected=True,
            priority=1,
        ),

        device_status={
            "battery_percent": 15.0,
        },

    )

    assert result.risk_level in {
        "MINIMAL",
        "LOW",
        "MEDIUM",
    }

    assert result.recommended_action in {
        "MONITOR",
        "DEFER",
        "PRIORITIZE",
    }


def test_decision_serialization():

    cadie = CADIE()

    result = cadie.evaluate(

        prediction=create_prediction(),

        environment_profile=create_profile(),

        adaptive_policy=create_policy(),

        event=create_event(),

    )

    data = result.to_dict()

    assert (
        data["risk_level"]
        == result.risk_level
    )

    assert (
        data["decision_score"]
        == result.decision_score
    )

    assert (
        data["recommended_action"]
        == result.recommended_action
    )

    assert isinstance(
        data["contributing_factors"],
        list,
    )


def test_invalid_prediction():

    cadie = CADIE()

    try:

        cadie.evaluate(

            prediction=None,

            environment_profile=create_profile(),

            adaptive_policy=create_policy(),

            event=create_event(),

        )

    except ValueError:

        return

    assert False