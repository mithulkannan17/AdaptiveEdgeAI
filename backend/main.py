"""
FastAPI Backend

Receives:
    1. Hardware telemetry from ESP32 edge nodes
    2. PCM16 audio from ESP32 edge nodes

Telemetry is cached per device and supplied as environmental
context to the adaptive audio-intelligence pipeline.
"""

from __future__ import annotations

from typing import Any
import struct
import uuid

from fastapi import Body
from fastapi import FastAPI
from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict
from pathlib import Path
from fastapi.responses import FileResponse

from backend.audio_service import AudioInferenceService
from backend.database import RuntimeDatabase


# ==========================================================
# UNKNOWN AUDIO EVIDENCE STORAGE
# ==========================================================

UNKNOWN_AUDIO_ROOT = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "unknown_audio"
)
UNKNOWN_AUDIO_ROOT.mkdir(
    parents=True,
    exist_ok=True,
)


def _detect_audio_extension(audio_bytes: bytes) -> str:
    """Best-effort detection of common audio container formats."""
    if len(audio_bytes) >= 12:
        if audio_bytes[0:4] == b"RIFF" and audio_bytes[8:12] == b"WAVE":
            return "wav"

    if audio_bytes.startswith(b"ID3"):
        return "mp3"

    if len(audio_bytes) >= 2 and audio_bytes[0] == 0xFF:
        # MPEG Layer III frame sync. Keep this conservative so raw
        # PCM is not accidentally classified as MP3.
        b1 = audio_bytes[1]
        if (b1 & 0xE0) == 0xE0 and (b1 & 0x06) in (0x00, 0x02, 0x04, 0x06):
            return "mp3"

    if audio_bytes.startswith(b"fLaC"):
        return "flac"

    if audio_bytes.startswith(b"OggS"):
        return "ogg"

    if audio_bytes.startswith(b"FORM") and len(audio_bytes) >= 12:
        return "aiff"

    if len(audio_bytes) >= 12 and audio_bytes[4:8] == b"ftyp":
        return "m4a"

    # AAC ADTS commonly starts with 0xFFF sync.
    if len(audio_bytes) >= 2 and audio_bytes[0] == 0xFF:
        if (audio_bytes[1] & 0xF6) == 0xF0:
            return "aac"

    return "pcm16"


def _pcm16_to_wav(
    pcm_bytes: bytes,
    sample_rate: int,
) -> bytes:
    """Wrap mono PCM16 bytes in a standard WAV container."""
    if len(pcm_bytes) % 2 != 0:
        raise ValueError(
            "Raw PCM16 audio must contain an even number of bytes."
        )

    sample_rate = int(sample_rate)
    if sample_rate <= 0:
        raise ValueError(
            "sample_rate must be greater than zero."
        )

    data_size = len(pcm_bytes)
    byte_rate = sample_rate * 2
    block_align = 2

    header = struct.pack(
        "<4sI4s"
        "4sIHHIIHH"
        "4sI",
        b"RIFF",
        36 + data_size,
        b"WAVE",
        b"fmt ",
        16,
        1,
        1,
        sample_rate,
        byte_rate,
        block_align,
        16,
        b"data",
        data_size,
    )
    return header + pcm_bytes


def _save_audio_evidence(
    audio_bytes: bytes,
    sample_rate: int,
) -> Path:
    """
    Persist the incoming audio in data/unknown_audio.

    WAV/compressed formats are retained as received.
    Raw PCM16 is wrapped as a playable WAV file.
    """
    extension = _detect_audio_extension(audio_bytes)
    sample_id = uuid.uuid4().hex

    if extension == "pcm16":
        filename = f"incoming_{sample_id}.wav"
        payload = _pcm16_to_wav(
            audio_bytes,
            sample_rate,
        )
    else:
        filename = f"incoming_{sample_id}.{extension}"
        payload = audio_bytes

    path = (
        UNKNOWN_AUDIO_ROOT
        / filename
    )

    path.write_bytes(payload)
    return path


def _safe_audio_path(
    raw_path: str | None,
) -> Path | None:
    """
    Resolve an evidence path and require it to remain inside
    data/unknown_audio.
    """
    if not raw_path:
        return None

    try:
        root = UNKNOWN_AUDIO_ROOT.resolve()
        path = Path(raw_path).resolve()

        path.relative_to(root)

        if not path.is_file():
            return None

        return path

    except (
        OSError,
        RuntimeError,
        ValueError,
    ):
        return None


def _unknown_evidence_required(
    inference_result: dict[str, Any],
) -> bool:
    """
    Decide whether the temporary audio evidence must be retained.

    The open-set discovery result is authoritative when present.
    A final Unknown prediction is also retained as a safe fallback.
    """
    discovery = (
        inference_result.get("unknown_discovery")
        or {}
    )

    if isinstance(discovery, dict):
        if bool(discovery.get("is_unknown")):
            return True

        if bool(discovery.get("buffered")):
            return True

        decision = discovery.get("decision")
        if isinstance(decision, dict):
            if bool(decision.get("is_unknown")):
                return True

    runtime = (
        inference_result.get("edge_runtime")
        or {}
    )

    runtime_discovery = (
        runtime.get("unknown_discovery")
        or runtime.get("discovery_result")
        or {}
    )

    if isinstance(runtime_discovery, dict):
        if bool(runtime_discovery.get("is_unknown")):
            return True

    prediction = (
        inference_result.get("prediction")
        or {}
    )

    if isinstance(prediction, dict):
        return str(
            prediction.get("label", "")
        ).strip().lower() == "unknown"

    return False


# ==========================================================
# FASTAPI APPLICATION
# ==========================================================

app = FastAPI(
    title="Adaptive Edge Intelligence API",
    description=(
        "Backend API for the Adaptive Edge Intelligence "
        "Platform."
    ),
    version="1.0.0",
)


# ==========================================================
# SERVICES
# ==========================================================

database = RuntimeDatabase()

audio_service = AudioInferenceService(
    sample_rate=16000
)


# ==========================================================
# LATEST TELEMETRY CACHE
# ==========================================================

latest_device_telemetry: dict[
    str,
    dict[str, Any],
] = {}


# ==========================================================
# REQUEST SCHEMAS
# ==========================================================

class TelemetryRequest(BaseModel):
    """
    Hardware telemetry received from an ESP32 edge node.
    """

    model_config = ConfigDict(
        extra="allow"
    )

    device_id: str

    timestamp: float

    device_status: dict

    location: dict | None = None

    hardware_health: dict | None = None


class EdgeMessageRequest(BaseModel):
    """
    Complete runtime intelligence message.

    This is produced by the Python edge-runtime pipeline,
    not directly by the ESP32 hardware.
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

    decision: dict | None = None

    unknown_discovery: dict | None = None

    location: dict | None = None

    device_status: dict | None = None


class MessageResponse(BaseModel):

    success: bool

    record_id: int


class UnknownClusterLabelRequest(BaseModel):
    """Human label applied to a discovered unknown-sound cluster."""

    label: str
    notes: str = ""


# ==========================================================
# ROOT
# ==========================================================

@app.get("/")
def root():

    return {
        "service":
            "Adaptive Edge Intelligence API",

        "status":
            "online",
    }


# ==========================================================
# HEALTH
# ==========================================================

@app.get("/health")
def health():

    return {

        "status":
            "healthy",

        "stored_records":
            database.count(),

        "tracked_devices":
            len(latest_device_telemetry),

        "inference_model":
            "mobilenet_v3_small",

    }


# ==========================================================
# ESP32 HARDWARE TELEMETRY
# ==========================================================

@app.post(
    "/api/v1/edge/telemetry"
)
def receive_telemetry(
    telemetry: TelemetryRequest,
):
    """
    Receive live hardware telemetry from an ESP32.

    Telemetry is stored in two places:

    1. In-memory cache
       Used immediately by audio inference.

    2. Persistent SQLite telemetry table
       Used by the dashboard and other consumers.
    """

    # ------------------------------------------------------
    # Validation
    # ------------------------------------------------------

    if not telemetry.device_id.strip():

        raise HTTPException(
            status_code=400,
            detail="device_id cannot be empty.",
        )

    # ------------------------------------------------------
    # Normalize values
    # ------------------------------------------------------

    device_id = (
        telemetry.device_id.strip()
    )

    timestamp = float(
        telemetry.timestamp
    )

    device_status = (
        telemetry.device_status
    )

    location = (
        telemetry.location
    )

    hardware_health = (
        telemetry.hardware_health
    )

    # ------------------------------------------------------
    # Update in-memory cache
    # ------------------------------------------------------

    latest_device_telemetry[
        device_id
    ] = {

        "device_status":
            device_status,

        "location":
            location,

        "hardware_health":
            hardware_health,

        "timestamp":
            timestamp,

    }

    # ------------------------------------------------------
    # Persist latest telemetry
    # ------------------------------------------------------

    try:

        database.upsert_telemetry(

            device_id=device_id,

            timestamp=timestamp,

            device_status=device_status,

            location=location,

            hardware_health=hardware_health,

        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to store telemetry: "
                f"{exc}"
            ),
        ) from exc

    # ------------------------------------------------------
    # Response
    # ------------------------------------------------------

    return {

        "success":
            True,

        "device_id":
            device_id,

        "timestamp":
            timestamp,

        "telemetry_cached":
            True,

        "telemetry_persisted":
            True,

    }


# ==========================================================
# GET LATEST TELEMETRY
# ==========================================================

@app.get(
    "/api/v1/edge/devices/{device_id}/telemetry"
)
def device_telemetry(
    device_id: str,
):
    """
    Return the latest telemetry for a device.

    Persistent SQLite storage is the source of truth.
    The memory cache is used only as a fallback.
    """

    if not device_id.strip():

        raise HTTPException(
            status_code=400,
            detail="device_id cannot be empty.",
        )

    device_id = (
        device_id.strip()
    )

    # ------------------------------------------------------
    # Persistent telemetry first
    # ------------------------------------------------------

    telemetry = (
        database.get_latest_telemetry(
            device_id
        )
    )

    # ------------------------------------------------------
    # Memory fallback
    # ------------------------------------------------------

    if telemetry is None:

        telemetry = (
            latest_device_telemetry.get(
                device_id
            )
        )

    # ------------------------------------------------------
    # No telemetry
    # ------------------------------------------------------

    if telemetry is None:

        raise HTTPException(
            status_code=404,
            detail=(
                "No telemetry available for "
                f"device '{device_id}'."
            ),
        )

    # ------------------------------------------------------
    # Response
    # ------------------------------------------------------

    return {

        "success":
            True,

        "device_id":
            device_id,

        **telemetry,

    }

# ==========================================================
# EDGE RUNTIME EVENTS
# ==========================================================

@app.post(
    "/api/v1/edge/events",
    response_model=MessageResponse,
)
def receive_edge_event(
    message: EdgeMessageRequest,
):

    payload = message.model_dump()

    # ------------------------------------------------------
    # Update telemetry cache if available
    # ------------------------------------------------------

    if (
        message.device_status is not None
        or message.location is not None
    ):

        previous = (
            latest_device_telemetry.get(
                message.device_id,
                {}
            )
        )

        latest_device_telemetry[
            message.device_id
        ] = {

            "device_status":
                (
                    message.device_status
                    if message.device_status is not None
                    else previous.get(
                        "device_status"
                    )
                ),

            "location":
                (
                    message.location
                    if message.location is not None
                    else previous.get(
                        "location"
                    )
                ),

            "hardware_health":
                previous.get(
                    "hardware_health"
                ),

            "timestamp":
                message.timestamp,

        }

    # ------------------------------------------------------
    # Store runtime event
    # ------------------------------------------------------

    try:

        record_id = (
            database.insert_message(
                payload
            )
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to store edge event: "
                f"{exc}"
            ),
        ) from exc

    return MessageResponse(

        success=True,

        record_id=record_id,

    )


# ==========================================================
# AUDIO INGESTION
# ==========================================================

@app.post(
    "/api/v1/edge/audio"
)
async def receive_edge_audio(

    device_id: str,

    timestamp: float,

    sample_rate: int = 16000,

    audio: bytes = Body(
        ...,
        media_type="application/octet-stream",
    ),

):

    # ------------------------------------------------------
    # Validation
    # ------------------------------------------------------

    if not device_id.strip():

        raise HTTPException(
            status_code=400,
            detail="device_id cannot be empty.",
        )

    if sample_rate <= 0:

        raise HTTPException(
            status_code=400,
            detail=(
                "sample_rate must be greater "
                "than zero."
            ),
        )

    if not audio:

        raise HTTPException(
            status_code=400,
            detail="Audio payload is empty.",
        )

    # ------------------------------------------------------
    # Retrieve latest telemetry
    # ------------------------------------------------------

    cached = (
        latest_device_telemetry.get(
            device_id
        )
    )

    device_status = None

    location = None

    hardware_health = None

    telemetry_timestamp = None

    if cached is not None:

        device_status = (
            cached.get(
                "device_status"
            )
        )

        location = (
            cached.get(
                "location"
            )
        )

        hardware_health = (
            cached.get(
                "hardware_health"
            )
        )

        telemetry_timestamp = (
            cached.get(
                "timestamp"
            )
        )

    # ------------------------------------------------------
    # Persist temporary audio evidence
    # ------------------------------------------------------
    #
    # The predictor/unknown-discovery pipeline needs a stable
    # audio_path at the moment it creates an UnknownSample.
    #
    # Known audio is deleted immediately after successful
    # inference. Unknown candidates are retained for human
    # review and later cluster playback.
    # ------------------------------------------------------

    audio_evidence_path: Path | None = None

    try:
        audio_evidence_path = _save_audio_evidence(
            audio_bytes=audio,
            sample_rate=sample_rate,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to persist audio evidence: "
                f"{exc}"
            ),
        ) from exc

    # ------------------------------------------------------
    # Run complete inference pipeline
    # ------------------------------------------------------

    try:

        inference_result = (
            audio_service.infer_pcm16(

                audio_bytes=audio,

                sample_rate=sample_rate,

                top_k=5,

                device_status=device_status,

                audio_path=str(audio_evidence_path),

            )
        )

    except ValueError as exc:

        if audio_evidence_path is not None:
            try:
                audio_evidence_path.unlink(missing_ok=True)
            except OSError:
                pass

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:

        if audio_evidence_path is not None:
            try:
                audio_evidence_path.unlink(missing_ok=True)
            except OSError:
                pass

        raise HTTPException(
            status_code=500,
            detail=(
                "Audio inference failed: "
                f"{exc}"
            ),
        ) from exc

    # ------------------------------------------------------
    # Build complete runtime event
    # ------------------------------------------------------
    #
    # AudioInferenceService may return the runtime pipeline
    # under "edge_runtime". We preserve the complete result
    # while also supporting direct top-level fields.
    # ------------------------------------------------------

    runtime = (
        inference_result.get("edge_runtime")
        or {}
    )

    prediction = (
        runtime.get("prediction")
        or inference_result.get("prediction")
        or {}
    )

    environment = (
        runtime.get("environment")
        or runtime.get("environment_profile")
        or inference_result.get("environment")
        or {}
    )

    adaptive_policy = (
        runtime.get("adaptive_policy")
        or inference_result.get("adaptive_policy")
        or {}
    )

    event = (
        runtime.get("event")
        or inference_result.get("event")
        or {}
    )

    decision = (
        runtime.get("decision")
        or inference_result.get("decision")
    )

    unknown_discovery = (
        runtime.get("unknown_discovery")
        or runtime.get("discovery_result")
        or inference_result.get("unknown_discovery")
    )

    # ------------------------------------------------------
    # Ensure event has useful fallback information
    # ------------------------------------------------------

    if not event and prediction:
        event = {
            "label":
                prediction.get("label", "Unknown"),

            "class_id":
                prediction.get("class_id"),

            "confidence":
                prediction.get("confidence", 0.0),

            "inference_time_ms":
                prediction.get(
                    "inference_time_ms",
                    0.0,
                ),

            "detected":
                True,
        }

    # ------------------------------------------------------
    # Location fallback
    # ------------------------------------------------------

    if location is None:
        location = {
            "latitude": 12.2958,
            "longitude": 76.6394,
            "name": "Mysore",
            "source": "FALLBACK",
        }

    # ------------------------------------------------------
    # Persist audio inference as a runtime event
    # ------------------------------------------------------

    runtime_message = {
        "device_id":
            device_id,

        "timestamp":
            timestamp,

        "prediction":
            prediction,

        "environment":
            environment,

        "adaptive_policy":
            adaptive_policy,

        "event":
            event,

        "decision":
            decision,

        "unknown_discovery":
            unknown_discovery,

        "location":
            location,

        "device_status":
            device_status,
    }

    try:
        record_id = database.insert_message(
            runtime_message
        )

    except Exception as exc:
        if audio_evidence_path is not None:
            try:
                audio_evidence_path.unlink(missing_ok=True)
            except OSError:
                pass

        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to store audio runtime "
                f"event: {exc}"
            ),
        ) from exc

    # ------------------------------------------------------
    # Retain evidence only for unknown candidates
    # ------------------------------------------------------

    evidence_retained = _unknown_evidence_required(
        inference_result
    )

    if not evidence_retained and audio_evidence_path is not None:
        try:
            audio_evidence_path.unlink(
                missing_ok=True
            )
            audio_evidence_path = None
        except OSError:
            pass

    # ------------------------------------------------------
    # Refresh telemetry cache
    # ------------------------------------------------------

    latest_device_telemetry[
        device_id
    ] = {
        "device_status":
            device_status,

        "location":
            location,

        "hardware_health":
            hardware_health,

        "timestamp":
            timestamp,
    }

    # ------------------------------------------------------
    # Return complete result
    # ------------------------------------------------------

    return {
        "success":
            True,

        "record_id":
            record_id,

        "device_id":
            device_id,

        "timestamp":
            timestamp,

        "telemetry_context":
            {
                "available":
                    cached is not None,

                "telemetry_timestamp":
                    telemetry_timestamp,

                "device_status":
                    device_status,

                "location":
                    location,

                "hardware_health":
                    hardware_health,
            },

        "runtime":
            {
                "prediction":
                    prediction,

                "environment":
                    environment,

                "adaptive_policy":
                    adaptive_policy,

                "event":
                    event,

                "decision":
                    decision,

                "unknown_discovery":
                    unknown_discovery,

                "audio_evidence":
                    {
                        "retained":
                            evidence_retained,

                        "audio_url":
                            (
                                f"/api/v1/edge/unknown/samples/audio/{audio_evidence_path.name}"
                                if audio_evidence_path is not None
                                and evidence_retained
                                else None
                            ),
                    },
            },

        "inference":
            inference_result,
    }


# ==========================================================
# LATEST EVENT
# ==========================================================

@app.get(
    "/api/v1/edge/events/latest"
)
def latest_event():

    result = (
        database.get_latest()
    )

    if result is None:

        raise HTTPException(
            status_code=404,
            detail=(
                "No edge events available."
            ),
        )

    return result


# ==========================================================
# RECENT EVENTS
# ==========================================================

@app.get(
    "/api/v1/edge/events"
)
def recent_events(
    limit: int = 50,
):

    if limit <= 0:

        raise HTTPException(
            status_code=400,
            detail=(
                "limit must be greater than zero."
            ),
        )

    if limit > 500:

        raise HTTPException(
            status_code=400,
            detail=(
                "limit cannot exceed 500."
            ),
        )

    return database.get_recent(
        limit=limit
    )


# ==========================================================
# UNKNOWN SOUND DISCOVERY
# ==========================================================


def _get_discovery_predictor():
    """Return the singleton predictor used by the live audio service."""

    predictor = getattr(audio_service, "predictor", None)

    if predictor is None:
        raise HTTPException(
            status_code=503,
            detail="Unknown discovery is unavailable because the predictor is not initialized.",
        )

    return predictor


@app.get(
    "/api/v1/edge/unknown/status"
)
def unknown_discovery_status():
    """Return live open-set detection and clustering status."""

    predictor = _get_discovery_predictor()

    try:
        return {
            "success": True,
            "discovery": predictor.get_unknown_discovery_status(),
            "last_raw_prediction": predictor.get_last_raw_prediction(),
            "last_discovery_result": predictor.get_last_discovery_result(),
        }
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to read unknown discovery status: {exc}",
        ) from exc


@app.get(
    "/api/v1/edge/unknown/clusters"
)
def unknown_discovery_clusters():
    """Return all persistent discovered unknown-sound clusters."""

    predictor = _get_discovery_predictor()

    try:
        return {
            "success": True,
            "clusters": predictor.get_unknown_clusters(),
        }
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to read unknown clusters: {exc}",
        ) from exc


@app.post(
    "/api/v1/edge/unknown/clusters/{cluster_id}/label"
)
def label_unknown_cluster(
    cluster_id: str,
    request: UnknownClusterLabelRequest,
):
    """Apply a human-readable label to a discovered cluster."""

    if not cluster_id.strip():
        raise HTTPException(
            status_code=400,
            detail="cluster_id cannot be empty.",
        )

    if not request.label.strip():
        raise HTTPException(
            status_code=400,
            detail="label cannot be empty.",
        )

    predictor = _get_discovery_predictor()

    try:
        cluster = predictor.label_unknown_cluster(
            cluster_id=cluster_id,
            label=request.label,
            notes=request.notes,
        )

        return {
            "success": True,
            "cluster": cluster,
        }

    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to label unknown cluster: {exc}",
        ) from exc


@app.post(
    "/api/v1/edge/unknown/clusters/{cluster_id}/unlabel"
)
def unlabel_unknown_cluster(
    cluster_id: str,
):
    """Remove a human label while retaining the discovered cluster."""

    if not cluster_id.strip():
        raise HTTPException(
            status_code=400,
            detail="cluster_id cannot be empty.",
        )

    predictor = _get_discovery_predictor()

    try:
        cluster = predictor.unlabel_unknown_cluster(
            cluster_id=cluster_id,
        )

        return {
            "success": True,
            "cluster": cluster,
        }

    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to unlabel unknown cluster: {exc}",
        ) from exc


@app.post(
    "/api/v1/edge/unknown/buffer/clear"
)
def clear_unknown_buffer():
    """Clear buffered unknown samples without deleting discovered clusters."""

    predictor = _get_discovery_predictor()

    try:
        predictor.clear_unknown_buffer()
        return {
            "success": True,
            "message": "Unknown-sound buffer cleared.",
            "discovery": predictor.get_unknown_discovery_status(),
        }
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear unknown buffer: {exc}",
        ) from exc


# ==========================================================
# UNKNOWN AUDIO HUMAN-REVIEW API
# ==========================================================


@app.get(
    "/api/v1/edge/unknown/clusters/{cluster_id}/samples"
)
def unknown_cluster_samples(
    cluster_id: str,
):
    """Return sample metadata for a discovered unknown cluster."""
    if not cluster_id.strip():
        raise HTTPException(
            status_code=400,
            detail="cluster_id cannot be empty.",
        )

    predictor = _get_discovery_predictor()
    manager = getattr(
        predictor,
        "discovery_manager",
        None,
    )

    if manager is None:
        manager = getattr(
            predictor,
            "unknown_discovery_manager",
            None,
        )

    if manager is None:
        manager = getattr(
            predictor,
            "unknown_manager",
            None,
        )

    if manager is None:
        raise HTTPException(
            status_code=503,
            detail="Unknown discovery manager is unavailable.",
        )

    try:
        samples = manager.get_samples(
            cluster_id
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to read cluster samples: "
                f"{exc}"
            ),
        ) from exc

    result = []

    for sample in samples:
        if hasattr(sample, "to_dict"):
            item = sample.to_dict()
        elif isinstance(sample, dict):
            item = dict(sample)
        else:
            item = {
                "sample_id": str(
                    getattr(
                        sample,
                        "sample_id",
                        "",
                    )
                ),
                "cluster_id": str(
                    getattr(
                        sample,
                        "cluster_id",
                        cluster_id,
                    )
                ),
                "captured_at": getattr(
                    sample,
                    "captured_at",
                    None,
                ),
                "predicted_class": getattr(
                    sample,
                    "predicted_class",
                    None,
                ),
                "confidence": getattr(
                    sample,
                    "confidence",
                    None,
                ),
                "audio_path": getattr(
                    sample,
                    "audio_path",
                    None,
                ),
            }

        raw_path = item.pop(
            "audio_path",
            None,
        )

        safe_path = _safe_audio_path(
            raw_path
        )

        item["audio_available"] = (
            safe_path is not None
        )

        item["audio_url"] = (
            f"/api/v1/edge/unknown/samples/{item.get('sample_id')}/audio"
            if safe_path is not None
            else None
        )

        result.append(item)

    return {
        "success": True,
        "cluster_id": cluster_id,
        "samples": result,
        "count": len(result),
    }


@app.get(
    "/api/v1/edge/unknown/samples/{sample_id}"
)
def unknown_sample(
    sample_id: str,
):
    """Return one unknown sample's review metadata."""
    if not sample_id.strip():
        raise HTTPException(
            status_code=400,
            detail="sample_id cannot be empty.",
        )

    predictor = _get_discovery_predictor()
    manager = getattr(
        predictor,
        "discovery_manager",
        None,
    )

    if manager is None:
        manager = getattr(
            predictor,
            "unknown_discovery_manager",
            None,
        )

    if manager is None:
        manager = getattr(
            predictor,
            "unknown_manager",
            None,
        )

    if manager is None:
        raise HTTPException(
            status_code=503,
            detail="Unknown discovery manager is unavailable.",
        )

    try:
        sample = manager.get_sample(
            sample_id
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to read unknown sample: "
                f"{exc}"
            ),
        ) from exc

    if hasattr(sample, "to_dict"):
        item = sample.to_dict()
    elif isinstance(sample, dict):
        item = dict(sample)
    else:
        item = {
            "sample_id": str(
                getattr(
                    sample,
                    "sample_id",
                    sample_id,
                )
            ),
            "cluster_id": getattr(
                sample,
                "cluster_id",
                None,
            ),
            "captured_at": getattr(
                sample,
                "captured_at",
                None,
            ),
            "predicted_class": getattr(
                sample,
                "predicted_class",
                None,
            ),
            "confidence": getattr(
                sample,
                "confidence",
                None,
            ),
            "audio_path": getattr(
                sample,
                "audio_path",
                None,
            ),
        }

    raw_path = item.pop(
        "audio_path",
        None,
    )

    safe_path = _safe_audio_path(
        raw_path
    )

    item["audio_available"] = (
        safe_path is not None
    )

    item["audio_url"] = (
        f"/api/v1/edge/unknown/samples/{sample_id}/audio"
        if safe_path is not None
        else None
    )

    return {
        "success": True,
        "sample": item,
    }


@app.get(
    "/api/v1/edge/unknown/samples/{sample_id}/audio"
)
def unknown_sample_audio(
    sample_id: str,
):
    """Stream a retained unknown-sample audio file."""
    if not sample_id.strip():
        raise HTTPException(
            status_code=400,
            detail="sample_id cannot be empty.",
        )

    predictor = _get_discovery_predictor()
    manager = getattr(
        predictor,
        "discovery_manager",
        None,
    )

    if manager is None:
        manager = getattr(
            predictor,
            "unknown_discovery_manager",
            None,
        )

    if manager is None:
        manager = getattr(
            predictor,
            "unknown_manager",
            None,
        )

    if manager is None:
        raise HTTPException(
            status_code=503,
            detail="Unknown discovery manager is unavailable.",
        )

    try:
        raw_path = manager.get_sample_audio_path(
            sample_id
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to locate unknown sample audio: "
                f"{exc}"
            ),
        ) from exc

    path = _safe_audio_path(
        raw_path
    )

    if path is None:
        raise HTTPException(
            status_code=404,
            detail="Audio evidence is not available for this sample.",
        )

    media_types = {
        ".wav": "audio/wav",
        ".mp3": "audio/mpeg",
        ".flac": "audio/flac",
        ".ogg": "audio/ogg",
        ".oga": "audio/ogg",
        ".m4a": "audio/mp4",
        ".aac": "audio/aac",
        ".aiff": "audio/aiff",
        ".aif": "audio/aiff",
    }

    media_type = media_types.get(
        path.suffix.lower(),
        "application/octet-stream",
    )

    return FileResponse(
        path=path,
        media_type=media_type,
        filename=path.name,
    )


# Backward-friendly endpoint for the evidence URL returned by
# the audio-ingestion response. It resolves the stored filename
# only after validating it is inside UNKNOWN_AUDIO_ROOT.
@app.get(
    "/api/v1/edge/unknown/samples/audio/{filename}"
)
def unknown_audio_by_filename(
    filename: str,
):
    """Stream retained evidence by its generated filename."""
    if not filename.strip():
        raise HTTPException(
            status_code=400,
            detail="filename cannot be empty.",
        )

    path = _safe_audio_path(
        str(
            UNKNOWN_AUDIO_ROOT
            / filename
        )
    )

    if path is None:
        raise HTTPException(
            status_code=404,
            detail="Audio evidence is not available.",
        )

    media_types = {
        ".wav": "audio/wav",
        ".mp3": "audio/mpeg",
        ".flac": "audio/flac",
        ".ogg": "audio/ogg",
        ".oga": "audio/ogg",
        ".m4a": "audio/mp4",
        ".aac": "audio/aac",
        ".aiff": "audio/aiff",
        ".aif": "audio/aiff",
    }

    return FileResponse(
        path=path,
        media_type=media_types.get(
            path.suffix.lower(),
            "application/octet-stream",
        ),
        filename=path.name,
    )


# ==========================================================
# DEVICES
# ==========================================================

@app.get(
    "/api/v1/edge/devices"
)
def devices():

    return {

        "devices":
            database.get_devices()

    }