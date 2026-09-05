"""
Dashboard Runtime Data Source
=============================

Live dashboard data source.

The dashboard receives:

    Live telemetry
          +
    Latest inference event
          +
    Recent inference history

from RuntimeDatabase.

Telemetry and inference are intentionally separated.

Telemetry:
    device_telemetry table

Inference:
    edge_events table
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any
import json
import os
from urllib.error import URLError, HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen


class RuntimeDataSource:
    """
    Live FastAPI-backed dashboard data source.

    The dashboard receives:
        - live telemetry
        - latest inference event
        - recent inference history
        - backend health

    This version intentionally does NOT use RuntimeDatabase directly.
    It polls the FastAPI runtime endpoints so telemetry sent by the ESP32
    is visible immediately in the dashboard.
    """

    def __init__(
        self,
        api_url: str | None = None,
        device_id: str | None = None,
        event_history_limit: int = 50,
        timeout_seconds: float = 2.5,
    ) -> None:
        self.api_url = (
            api_url
            or os.getenv("AURAFOREST_API_URL")
            or "http://127.0.0.1:8000"
        ).rstrip("/")

        self.device_id = (
            device_id
            or os.getenv("AURAFOREST_DEVICE_ID")
            or "edge_node_telemetry_001"
        )

        self.event_history_limit = max(1, int(event_history_limit))
        self.timeout_seconds = max(0.5, float(timeout_seconds))
        self._last_state: dict[str, Any] | None = None
        self._last_error: str | None = None

    # ==========================================================
    # HTTP
    # ==========================================================

    def _get_json(self, path: str) -> dict[str, Any] | list[Any] | None:
        url = f"{self.api_url}{path}"

        request = Request(
            url,
            method="GET",
            headers={
                "Accept": "application/json",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
            },
        )

        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                payload = response.read().decode("utf-8")
                return json.loads(payload)

        except HTTPError as exc:
            self._last_error = f"HTTP {exc.code}: {exc.reason}"
        except URLError as exc:
            self._last_error = f"Connection error: {exc.reason}"
        except TimeoutError:
            self._last_error = "FastAPI request timed out."
        except json.JSONDecodeError:
            self._last_error = "FastAPI returned invalid JSON."
        except Exception as exc:
            self._last_error = str(exc)

        return None

    # ==========================================================
    # LIVE STATE
    # ==========================================================

    def tick(self) -> dict[str, Any]:
        """
        Fetch a completely fresh dashboard snapshot from FastAPI.
        """

        self._last_error = None

        health = self._get_json("/health")
        telemetry_response = self._get_json(
            f"/api/v1/edge/devices/{quote(self.device_id, safe='')}/telemetry"
        )
        latest_response = self._get_json("/api/v1/edge/events/latest")
        history_response = self._get_json(
            f"/api/v1/edge/events?limit={self.event_history_limit}"
        )

        # The API may temporarily fail. Keep the last valid UI state rather
        # than replacing the entire dashboard with empty values.
        if (
            health is None
            and telemetry_response is None
            and latest_response is None
            and history_response is None
        ):
            if self._last_state is not None:
                state = deepcopy(self._last_state)
                connection = state.setdefault("connection", {})
                connection["online"] = False
                connection["status"] = "BACKEND OFFLINE"
                connection["error"] = self._last_error
                connection["api_url"] = self.api_url
                connection["device_id"] = self.device_id
                return state

            state = self._build_empty_runtime_state()
            state["connection"] = {
                "online": False,
                "status": "BACKEND OFFLINE",
                "error": self._last_error,
                "api_url": self.api_url,
                "device_id": self.device_id,
            }
            self._last_state = deepcopy(state)
            return deepcopy(state)

        telemetry_record = self._extract_telemetry(telemetry_response)
        latest_event = self._extract_latest_event(latest_response)
        history_records = self._extract_history(history_response)

        state = self._build_state(
            latest_event=latest_event,
            telemetry_record=telemetry_record,
            history_records=history_records,
            health=health if isinstance(health, dict) else {},
        )

        state["connection"] = {
            "online": True,
            "status": "RUNTIME ONLINE",
            "error": None,
            "api_url": self.api_url,
            "device_id": self.device_id,
            "health": health if isinstance(health, dict) else {},
        }

        self._last_state = deepcopy(state)
        return deepcopy(state)

    # ==========================================================
    # API RESPONSE EXTRACTION
    # ==========================================================

    @staticmethod
    def _extract_telemetry(
        response: dict[str, Any] | list[Any] | None,
    ) -> dict[str, Any] | None:
        if not isinstance(response, dict):
            return None

        if response.get("success") is False:
            return None

        telemetry = response.get("telemetry")

        if isinstance(telemetry, dict):
            return telemetry

        # Backend may return the telemetry object directly.
        if any(
            key in response
            for key in ("device_status", "location", "hardware_health")
        ):
            return response

        return None

    @staticmethod
    def _extract_latest_event(
        response: dict[str, Any] | list[Any] | None,
    ) -> dict[str, Any] | None:
        """
        Extract the COMPLETE latest runtime record.

        Important:
        /api/v1/edge/events/latest returns a database record containing
        prediction, environment, adaptive_policy, event, decision,
        unknown_discovery and location.

        We must NOT return response["event"] alone because that would throw
        away environment/policy/CADIE/top-k data.
        """
        if isinstance(response, list):
            return response[0] if response else None

        if not isinstance(response, dict):
            return None

        if response.get("success") is False:
            return None

        # FastAPI's latest-event endpoint returns the complete record directly.
        if any(
            key in response
            for key in (
                "prediction",
                "environment",
                "adaptive_policy",
                "event",
                "decision",
                "unknown_discovery",
                "location",
            )
        ):
            return response

        # Support wrapped responses from alternate API versions.
        record = response.get("record")
        if isinstance(record, dict):
            return record

        data = response.get("data")
        if isinstance(data, dict):
            return data

        event = response.get("event")
        if isinstance(event, dict):
            return event

        return None

    @staticmethod
    def _extract_history(
        response: dict[str, Any] | list[Any] | None,
    ) -> list[dict[str, Any]]:
        if isinstance(response, list):
            return [item for item in response if isinstance(item, dict)]

        if not isinstance(response, dict):
            return []

        for key in ("events", "records", "data", "items"):
            value = response.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]

        return []

    # ==========================================================
    # STATE CONSTRUCTION
    # ==========================================================

    def _build_state(
        self,
        latest_event: dict[str, Any] | None,
        telemetry_record: dict[str, Any] | None,
        history_records: list[dict[str, Any]],
        health: dict[str, Any],
    ) -> dict[str, Any]:

        latest = latest_event or {}

        prediction = latest.get("prediction") or {}
        event = latest.get("event") or {}
        decision = latest.get("decision") or {}
        environment = (
            latest.get("environment")
            or latest.get("environment_profile")
            or {}
        )
        adaptive_policy = latest.get("adaptive_policy") or {}
        unknown_discovery = latest.get("unknown_discovery")

        if not isinstance(prediction, dict):
            prediction = {}
        if not isinstance(event, dict):
            event = {}
        if not isinstance(decision, dict):
            decision = {}
        if not isinstance(environment, dict):
            environment = {}
        if not isinstance(adaptive_policy, dict):
            adaptive_policy = {}

        # Support a flat event/prediction response as a fallback.
        if not event and any(
            key in latest
            for key in ("label", "class_id", "confidence", "detected")
        ):
            event = latest

        if not prediction and any(
            key in latest
            for key in (
                "label",
                "confidence",
                "class_id",
                "top_k",
                "inference_time_ms",
            )
        ):
            prediction = {
                "label": latest.get("label"),
                "class_id": latest.get("class_id"),
                "confidence": latest.get("confidence", 0.0),
                "inference_time_ms": latest.get(
                    "inference_time_ms",
                    0.0,
                ),
                "top_k": latest.get("top_k", []),
                "model": latest.get("model"),
            }

        telemetry = self._build_telemetry(telemetry_record)

        current_event = None
        if event or prediction:
            current_event = {
                "label": event.get(
                    "label",
                    prediction.get("label", "Unknown"),
                ),
                "class_id": event.get(
                    "class_id",
                    prediction.get("class_id"),
                ),
                "confidence": event.get(
                    "confidence",
                    prediction.get("confidence", 0.0),
                ),
                "adjusted_confidence": event.get(
                    "adjusted_confidence"
                ),
                "detection_threshold": event.get(
                    "detection_threshold"
                ),
                "detected": event.get("detected", True),
                "priority": event.get("priority", 0),
                "environment_type": event.get(
                    "environment_type",
                    environment.get("environment_type"),
                ),
                "reason": event.get("reason", ""),
                "inference_time_ms": event.get(
                    "inference_time_ms",
                    prediction.get("inference_time_ms", 0.0),
                ),
                "metadata": deepcopy(event.get("metadata", {})),
                "risk_level": decision.get("risk_level", "LOW"),
            }

        cadie = {
            "risk_level": decision.get("risk_level", "LOW"),
            "score": decision.get("decision_score", 0.0),
            "action": decision.get("recommended_action", "MONITOR"),
            "requires_attention": decision.get(
                "requires_attention",
                False,
            ),
            "confidence": decision.get("confidence", 0.0),
            "reason": decision.get("reason", ""),
            "contributing_factors": deepcopy(
                decision.get("contributing_factors", [])
            ),
            "signal": event.get(
                "label",
                prediction.get("label", "Unknown"),
            ),
            "baseline_delta": decision.get("baseline_delta"),
        }

        events = self._build_event_history(history_records)

        device_id = (
            latest.get("device_id")
            or (telemetry_record or {}).get("device_id")
            or self.device_id
        )

        timestamp = latest.get("timestamp")
        telemetry_timestamp = telemetry.get("telemetry_timestamp")

        return {
            "telemetry": telemetry,
            "event": current_event,
            "events": events,
            "recent_events": events,
            "cadie": cadie,
            "waveform": [],
            "device_id": device_id,
            "timestamp": timestamp,
            "telemetry_timestamp": telemetry_timestamp,
            "environment": deepcopy(environment),
            "adaptive_policy": deepcopy(adaptive_policy),
            "prediction": deepcopy(prediction),
            "unknown_discovery": deepcopy(unknown_discovery),
            "hardware_health": deepcopy(
                telemetry.get("hardware_health", {})
            ),
            "location": {
                "latitude": telemetry.get("latitude"),
                "longitude": telemetry.get("longitude"),
                "altitude": telemetry.get("altitude"),
                "accuracy": telemetry.get("accuracy"),
                "source": telemetry.get("location_source"),
                "city": telemetry.get("city"),
                "state": telemetry.get("state"),
                "country": telemetry.get("country"),
            },
            "health": deepcopy(health),
        }

    @staticmethod
    def _build_telemetry(
        telemetry_record: dict[str, Any] | None,
    ) -> dict[str, Any]:

        if not telemetry_record:
            return {
                "battery_percent": None,
                "battery_voltage": None,
                "temperature": None,
                "humidity": None,
                "pressure": None,
                "light_level": None,
                "vibration_detected": None,
                "charging": None,
                "latitude": None,
                "longitude": None,
                "altitude": None,
                "accuracy": None,
                "location_source": None,
                "city": None,
                "state": None,
                "country": None,
                "telemetry_timestamp": None,
                "hardware_health": {},
            }

        device_status = telemetry_record.get("device_status") or {}
        location = telemetry_record.get("location") or {}
        hardware_health = telemetry_record.get("hardware_health") or {}

        return {
            "battery_percent": device_status.get("battery_percent"),
            "battery_voltage": device_status.get("battery_voltage"),
            "temperature": device_status.get("temperature"),
            "humidity": device_status.get("humidity"),
            "pressure": device_status.get("pressure"),
            "light_level": device_status.get("light_level"),
            "vibration_detected": device_status.get(
                "vibration_detected"
            ),
            "charging": device_status.get("charging"),
            "latitude": location.get("latitude"),
            "longitude": location.get("longitude"),
            "altitude": location.get("altitude"),
            "accuracy": location.get("accuracy"),
            "location_source": location.get("source"),
            "city": location.get("city"),
            "state": location.get("state"),
            "country": location.get("country"),
            "telemetry_timestamp": telemetry_record.get(
                "timestamp",
                telemetry_record.get("updated_at"),
            ),
            "hardware_health": deepcopy(hardware_health),
        }

    # ==========================================================
    # EVENT HISTORY
    # ==========================================================

    @staticmethod
    def _build_event_history(
        records: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Normalize complete FastAPI runtime records for the dashboard."""
        result: list[dict[str, Any]] = []

        for record in records:
            if not isinstance(record, dict):
                continue

            prediction = record.get("prediction") or {}
            event = record.get("event") or {}
            decision = record.get("decision") or {}
            environment = (
                record.get("environment")
                or record.get("environment_profile")
                or {}
            )
            adaptive_policy = record.get("adaptive_policy") or {}
            location = record.get("location") or {}

            if not isinstance(prediction, dict):
                prediction = {}
            if not isinstance(event, dict):
                event = {}
            if not isinstance(decision, dict):
                decision = {}
            if not isinstance(environment, dict):
                environment = {}
            if not isinstance(adaptive_policy, dict):
                adaptive_policy = {}
            if not isinstance(location, dict):
                location = {}

            label = (
                prediction.get("label")
                or event.get("label")
                or record.get("label")
                or "Unknown"
            )

            confidence = prediction.get("confidence")
            if confidence is None:
                confidence = event.get("confidence")
            if confidence is None:
                confidence = record.get("confidence", 0.0)

            class_id = prediction.get("class_id")
            if class_id is None:
                class_id = event.get("class_id")
            if class_id is None:
                class_id = record.get("class_id")

            inference_time_ms = prediction.get("inference_time_ms")
            if inference_time_ms is None:
                inference_time_ms = event.get("inference_time_ms")
            if inference_time_ms is None:
                inference_time_ms = record.get("inference_time_ms", 0.0)

            risk_level = (
                decision.get("risk_level")
                or event.get("risk_level")
                or record.get("risk_level")
                or "LOW"
            )

            normalized_prediction = {
                **prediction,
                "label": label,
                "class_id": class_id,
                "confidence": confidence,
                "inference_time_ms": inference_time_ms,
                "top_k": prediction.get(
                    "top_k",
                    record.get("top_k", []),
                ),
            }

            normalized_event = {
                **event,
                "label": label,
                "class_id": class_id,
                "confidence": confidence,
                "detected": event.get(
                    "detected",
                    record.get("detected", True),
                ),
                "priority": event.get(
                    "priority",
                    record.get("priority", 0),
                ),
                "inference_time_ms": inference_time_ms,
            }

            normalized_decision = {
                **decision,
                "risk_level": risk_level,
                "recommended_action": decision.get(
                    "recommended_action",
                    decision.get(
                        "action",
                        record.get("recommended_action", "MONITOR"),
                    ),
                ),
            }

            result.append(
                {
                    "id": record.get("id"),
                    "device_id": record.get("device_id") or self_device_id(record),
                    "label": label,
                    "confidence": confidence,
                    "risk_level": risk_level,
                    "timestamp": record.get("timestamp"),
                    "latitude": location.get("latitude"),
                    "longitude": location.get("longitude"),
                    "priority": normalized_event.get("priority", 0),
                    "detected": normalized_event.get("detected", False),
                    "inference_time_ms": inference_time_ms,
                    "prediction": normalized_prediction,
                    "event": normalized_event,
                    "decision": normalized_decision,
                    "environment": environment,
                    "adaptive_policy": adaptive_policy,
                    "unknown_discovery": record.get("unknown_discovery"),
                    "location": location,
                }
            )

        return result


    # ==========================================================
    # DASHBOARD COMPATIBILITY
    # ==========================================================

    def get_recent_events(self, limit: int = 10) -> list[dict[str, Any]]:
        """Compatibility API for dashboards using get_recent_events()."""
        events = self._build_event_history(
            self._extract_history(
                self._get_json(
                    f"/api/v1/edge/events?limit={max(1, int(limit))}"
                )
            )
        )
        return events[: max(0, int(limit))]

    # ==========================================================
    # EMPTY STATE
    # ==========================================================

    def _build_empty_runtime_state(self) -> dict[str, Any]:
        return {
            "telemetry": self._build_telemetry(None),
            "event": None,
            "events": [],
            "recent_events": [],
            "cadie": {
                "risk_level": "LOW",
                "score": 0.0,
                "action": "WAITING",
                "requires_attention": False,
                "confidence": 0.0,
                "reason": "Waiting for runtime data.",
                "contributing_factors": [],
                "signal": "Waiting",
                "baseline_delta": None,
            },
            "waveform": [],
            "device_id": self.device_id,
            "timestamp": None,
            "telemetry_timestamp": None,
            "environment": {},
            "adaptive_policy": {},
            "prediction": {},
            "unknown_discovery": None,
            "hardware_health": {},
            "location": {},
            "health": {},
            "connection": {},
        }

    # ==========================================================
    # RESET / SOURCE INFORMATION
    # ==========================================================

    def reset(self) -> None:
        self._last_state = None
        self._last_error = None

    def source_name(self) -> str:
        return "LIVE FASTAPI"

    def is_simulator(self) -> bool:
        return False

    def get_last_state(self) -> dict[str, Any] | None:
        if self._last_state is None:
            return None
        return deepcopy(self._last_state)

    @property
    def last_error(self) -> str | None:
        return self._last_error


def self_device_id(record: dict[str, Any]) -> str:
    """Safely obtain a device ID from a history record."""
    return str(record.get("device_id") or "Unknown")

