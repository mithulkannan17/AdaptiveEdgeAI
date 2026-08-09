"""
FastAPI Backend

Receives runtime intelligence messages from adaptive
edge nodes and stores them in the runtime database.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict

from backend.database import RuntimeDatabase


app = FastAPI(

    title="Adaptive Edge Intelligence API",

    description=(
        "Backend API for the Adaptive Edge Intelligence "
        "Platform."
    ),

    version="1.0.0",

)


database = RuntimeDatabase()


class EdgeMessageRequest(BaseModel):
    """
    API representation of an edge runtime message.
    """

    model_config = ConfigDict(
        extra="forbid"
    )

    device_id: str

    timestamp: float

    prediction: dict

    environment: dict

    adaptive_policy: dict

    event: dict

    unknown_discovery: dict | None = None

    location: dict | None = None

    device_status: dict | None = None


class MessageResponse(BaseModel):
    """
    Response returned after storing a message.
    """

    success: bool

    record_id: int


@app.get("/")
def root():
    """
    Backend health endpoint.
    """

    return {

        "service":
            "Adaptive Edge Intelligence API",

        "status":
            "online",

    }


@app.get("/health")
def health():
    """
    Health-check endpoint.
    """

    return {

        "status":
            "healthy",

        "stored_records":
            database.count(),

    }


@app.post(
    "/api/v1/edge/events",
    response_model=MessageResponse,
)
def receive_edge_event(
    message: EdgeMessageRequest,
):
    """
    Receive and store an edge runtime event.
    """

    try:

        record_id = (
            database.insert_message(
                message.model_dump()
            )
        )

    except Exception as exc:

        raise HTTPException(

            status_code=500,

            detail=(
                f"Failed to store edge event: {exc}"
            ),

        ) from exc

    return MessageResponse(

        success=True,

        record_id=record_id,

    )


@app.get(
    "/api/v1/edge/events/latest"
)
def latest_event():
    """
    Return the most recently received edge event.
    """

    result = (
        database.get_latest()
    )

    if result is None:

        raise HTTPException(

            status_code=404,

            detail="No edge events available.",

        )

    return result