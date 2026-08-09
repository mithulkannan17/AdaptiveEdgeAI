"""
Tests for the backend communication client.
"""

import httpx
import pytest

from communication import (
    CommunicationClient,
    CommunicationError,
)


def test_health(
    monkeypatch,
):

    def mock_get(
        url,
        timeout,
    ):

        return httpx.Response(

            200,

            json={
                "status": "healthy",
                "stored_records": 5,
            },

        )

    monkeypatch.setattr(
        httpx,
        "get",
        mock_get,
    )

    client = CommunicationClient()

    result = client.health()

    assert (
        result["status"]
        == "healthy"
    )

    assert (
        result["stored_records"]
        == 5
    )


def test_send_message(
    monkeypatch,
):

    captured = {}

    def mock_post(
        url,
        json,
        timeout,
    ):

        captured["url"] = url

        captured["json"] = json

        return httpx.Response(

            200,

            json={
                "success": True,
                "record_id": 7,
            },

        )

    monkeypatch.setattr(
        httpx,
        "post",
        mock_post,
    )

    from communication import (
        EdgeMessage,
        PredictionMessage,
        EnvironmentMessage,
        AdaptivePolicyMessage,
        EventMessage,
    )

    message = EdgeMessage(

        device_id="edge_node_001",

        timestamp=1234567890.0,

        prediction=PredictionMessage(

            label="Bird",

            class_id=0,

            confidence=0.91,

        ),

        environment=EnvironmentMessage(

            environment_type="Natural",

            observation_count=3,

            observation_duration_seconds=10.0,

        ),

        adaptive_policy=AdaptivePolicyMessage(

            environment_type="Natural",

            detection_threshold=0.55,

            transmission_mode="selective",

            sampling_mode="active",

        ),

        event=EventMessage(

            label="Bird",

            class_id=0,

            confidence=0.91,

            adjusted_confidence=1.0,

            detection_threshold=0.55,

            detected=True,

            priority=1,

            environment_type="Natural",

        ),

    )

    client = CommunicationClient()

    result = client.send(
        message
    )

    assert (
        result["success"]
        is True
    )

    assert (
        result["record_id"]
        == 7
    )

    assert (
        captured["url"]
        == "http://127.0.0.1:8000/api/v1/edge/events"
    )

    assert (
        captured["json"]["device_id"]
        == "edge_node_001"
    )


def test_invalid_message():

    client = CommunicationClient()

    with pytest.raises(
        TypeError
    ):

        client.send(
            {"invalid": "message"}
        )


def test_backend_error(
    monkeypatch,
):

    def mock_post(
        url,
        json,
        timeout,
    ):

        return httpx.Response(

            500,

            text="Internal Server Error",

        )

    monkeypatch.setattr(
        httpx,
        "post",
        mock_post,
    )

    from communication import (
        EdgeMessage,
        PredictionMessage,
        EnvironmentMessage,
        AdaptivePolicyMessage,
        EventMessage,
    )

    message = EdgeMessage(

        device_id="edge_node_001",

        timestamp=1234567890.0,

        prediction=PredictionMessage(
            label="Bird",
            class_id=0,
            confidence=0.9,
        ),

        environment=EnvironmentMessage(
            environment_type="Natural",
            observation_count=1,
            observation_duration_seconds=1.0,
        ),

        adaptive_policy=AdaptivePolicyMessage(
            environment_type="Natural",
            detection_threshold=0.55,
            transmission_mode="selective",
            sampling_mode="active",
        ),

        event=EventMessage(
            label="Bird",
            class_id=0,
            confidence=0.9,
            adjusted_confidence=0.9,
            detection_threshold=0.55,
            detected=True,
            priority=1,
            environment_type="Natural",
        ),

    )

    client = CommunicationClient()

    with pytest.raises(
        CommunicationError
    ):

        client.send(message)