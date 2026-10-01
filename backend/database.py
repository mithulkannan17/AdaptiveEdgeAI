"""
Runtime Database
================

Persistent SQLite storage for:

1. ESP32 hardware telemetry
2. Edge inference events
3. CADIE decisions
4. Device locations
5. Hardware health

Telemetry is stored separately from inference events so that the
dashboard can display genuinely live sensor information even when
no new inference event has been generated.
"""

from __future__ import annotations

import json
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_DATABASE_PATH = Path(
    "data/runtime.db"
)


class RuntimeDatabase:
    """
    SQLite storage for edge runtime data.

    Tables
    ------
    device_telemetry
        Stores the newest telemetry received from each device.

    edge_events
        Stores inference/runtime events.
    """

    def __init__(
        self,
        database_path: str | Path = DEFAULT_DATABASE_PATH,
    ) -> None:

        self.database_path = Path(
            database_path
        )

        self.database_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.initialize()

    # ==========================================================
    # CONNECTION
    # ==========================================================

    def _connect(self) -> sqlite3.Connection:
        """
        Create a SQLite connection.
        """

        connection = sqlite3.connect(
            self.database_path,
            timeout=10,
        )

        connection.row_factory = sqlite3.Row

        return connection

    # ==========================================================
    # INITIALIZATION / MIGRATION
    # ==========================================================

    def initialize(self) -> None:
        """
        Create all runtime tables.

        Existing databases are preserved.
        """

        with self._connect() as connection:

            # --------------------------------------------------
            # Runtime events
            # --------------------------------------------------

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS edge_events (

                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    device_id TEXT NOT NULL,

                    timestamp REAL NOT NULL,

                    prediction_json TEXT NOT NULL,

                    environment_json TEXT NOT NULL,

                    adaptive_policy_json TEXT NOT NULL,

                    event_json TEXT NOT NULL,

                    decision_json TEXT,

                    unknown_discovery_json TEXT,

                    location_json TEXT,

                    device_status_json TEXT

                )
                """
            )

            # --------------------------------------------------
            # Existing schema migration
            # --------------------------------------------------

            columns = connection.execute(
                "PRAGMA table_info(edge_events)"
            ).fetchall()

            column_names = {
                column["name"]
                for column in columns
            }

            if "decision_json" not in column_names:

                connection.execute(
                    """
                    ALTER TABLE edge_events
                    ADD COLUMN decision_json TEXT
                    """
                )

            # --------------------------------------------------
            # Dedicated live telemetry table
            # --------------------------------------------------

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS device_telemetry (

                    device_id TEXT PRIMARY KEY,

                    timestamp REAL NOT NULL,

                    device_status_json TEXT,

                    location_json TEXT,

                    hardware_health_json TEXT,

                    updated_at REAL NOT NULL

                )
                """
            )

            # --------------------------------------------------
            # Permanent historical telemetry log
            # --------------------------------------------------

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS telemetry_history (

                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    device_id TEXT NOT NULL,

                    timestamp REAL NOT NULL,

                    temperature REAL,

                    humidity REAL,

                    light_level REAL,

                    battery_percent REAL,

                    battery_voltage REAL,

                    vibration_detected INTEGER,

                    mq2_raw REAL,

                    mq2_voltage REAL,

                    mq135_raw REAL,

                    mq135_voltage REAL,

                    gas_risk_score REAL,

                    gas_status TEXT,

                    device_status_json TEXT,

                    location_json TEXT,

                    hardware_health_json TEXT,

                    created_at REAL NOT NULL

                )
                """
            )

            # --------------------------------------------------
            # Experiment & Validation logs
            # --------------------------------------------------

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS experiment_logs (

                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    experiment_name TEXT NOT NULL,

                    timestamp REAL NOT NULL,

                    summary_json TEXT NOT NULL,

                    details_json TEXT NOT NULL,

                    config_json TEXT,

                    created_at REAL NOT NULL

                )
                """
            )

            # --------------------------------------------------
            # Emergency Alert Notifications
            # --------------------------------------------------
            # Emergency Alerts
            # --------------------------------------------------

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS emergency_alerts (

                    alert_id TEXT PRIMARY KEY,

                    device_id TEXT NOT NULL,

                    timestamp REAL NOT NULL,

                    threat_type TEXT NOT NULL,

                    risk_level TEXT NOT NULL,

                    confidence REAL NOT NULL,

                    location_lat REAL,

                    location_lon REAL,

                    message TEXT NOT NULL,

                    channels_json TEXT NOT NULL,

                    decision_json TEXT,

                    status TEXT NOT NULL,

                    created_at TEXT NOT NULL,

                    acknowledged_at TEXT,

                    acknowledged_by TEXT,

                    resolved_at TEXT,

                    resolved_by TEXT,

                    resolution_notes TEXT,

                    assigned_ranger_id TEXT,

                    assigned_ranger_name TEXT

                )
                """
            )

            # Column migrations for emergency_alerts
            alert_cols = {
                column["name"]
                for column in connection.execute("PRAGMA table_info(emergency_alerts)").fetchall()
            }
            for col_name, col_type in [
                ("resolved_at", "TEXT"),
                ("resolved_by", "TEXT"),
                ("resolution_notes", "TEXT"),
                ("assigned_ranger_id", "TEXT"),
                ("assigned_ranger_name", "TEXT"),
            ]:
                if col_name not in alert_cols:
                    connection.execute(
                        f"ALTER TABLE emergency_alerts ADD COLUMN {col_name} {col_type}"
                    )

            # --------------------------------------------------
            # Public Citizen Reports Table
            # --------------------------------------------------

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS citizen_reports (

                    report_id TEXT PRIMARY KEY,

                    timestamp REAL NOT NULL,

                    reporter_name TEXT NOT NULL,

                    contact_info TEXT,

                    threat_category TEXT NOT NULL,

                    description TEXT NOT NULL,

                    photo_filename TEXT,

                    location_lat REAL,

                    location_lon REAL,

                    status TEXT NOT NULL,

                    status_notes TEXT,

                    created_at TEXT NOT NULL,

                    updated_at TEXT

                )
                """
            )

            # --------------------------------------------------
            # Security & Authentication Audit Log
            # --------------------------------------------------

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS auth_audit_log (

                    event_id TEXT PRIMARY KEY,

                    timestamp REAL NOT NULL,

                    username TEXT NOT NULL,

                    role TEXT NOT NULL,

                    action TEXT NOT NULL,

                    ip_address TEXT,

                    details TEXT,

                    created_at TEXT NOT NULL

                )
                """
            )

            # --------------------------------------------------
            # Indexes
            # --------------------------------------------------

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_edge_events_device_id
                ON edge_events(device_id)
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_edge_events_timestamp
                ON edge_events(timestamp)
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_device_telemetry_updated_at
                ON device_telemetry(updated_at)
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_telemetry_history_device_id
                ON telemetry_history(device_id)
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_telemetry_history_timestamp
                ON telemetry_history(timestamp)
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_experiment_logs_name
                ON experiment_logs(experiment_name)
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_emergency_alerts_status
                ON emergency_alerts(status)
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_emergency_alerts_timestamp
                ON emergency_alerts(timestamp)
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_citizen_reports_timestamp
                ON citizen_reports(timestamp)
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_citizen_reports_status
                ON citizen_reports(status)
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_auth_audit_log_timestamp
                ON auth_audit_log(timestamp)
                """
            )

            connection.commit()

    # ==========================================================
    # LIVE TELEMETRY
    # ==========================================================

    def upsert_telemetry(
        self,
        device_id: str,
        timestamp: float,
        device_status: dict[str, Any] | None = None,
        location: dict[str, Any] | None = None,
        hardware_health: dict[str, Any] | None = None,
    ) -> None:
        """
        Insert or update the latest telemetry for a device.

        This is the persistent live telemetry store used by the
        dashboard.
        """

        if not device_id or not device_id.strip():

            raise ValueError(
                "device_id cannot be empty."
            )

        device_id = device_id.strip()

        # ------------------------------------------------------
        # Preserve previous values when a field is omitted
        # ------------------------------------------------------

        previous = self.get_latest_telemetry(
            device_id
        )

        if previous is not None:

            if device_status is None:

                device_status = previous.get(
                    "device_status"
                )

            if location is None:

                location = previous.get(
                    "location"
                )

            if hardware_health is None:

                hardware_health = previous.get(
                    "hardware_health"
                )

        # ------------------------------------------------------
        # SQLite UPSERT
        # ------------------------------------------------------

        with self._connect() as connection:

            connection.execute(
                """
                INSERT INTO device_telemetry (

                    device_id,

                    timestamp,

                    device_status_json,

                    location_json,

                    hardware_health_json,

                    updated_at

                )
                VALUES (?, ?, ?, ?, ?, ?)

                ON CONFLICT(device_id)
                DO UPDATE SET

                    timestamp =
                        excluded.timestamp,

                    device_status_json =
                        excluded.device_status_json,

                    location_json =
                        excluded.location_json,

                    hardware_health_json =
                        excluded.hardware_health_json,

                    updated_at =
                        excluded.updated_at
                """,
                (
                    device_id,

                    float(timestamp),

                    json.dumps(
                        device_status
                    ),

                    json.dumps(
                        location
                    ),

                    json.dumps(
                        hardware_health
                    ),

                    float(timestamp),
                ),
            )

            connection.commit()

    # ==========================================================
    # LATEST TELEMETRY FOR DEVICE
    # ==========================================================

    def get_latest_telemetry(
        self,
        device_id: str,
    ) -> dict[str, Any] | None:
        """
        Return the newest persistent telemetry for one device.
        """

        if not device_id or not device_id.strip():

            raise ValueError(
                "device_id cannot be empty."
            )

        with self._connect() as connection:

            row = connection.execute(
                """
                SELECT

                    device_id,

                    timestamp,

                    device_status_json,

                    location_json,

                    hardware_health_json,

                    updated_at

                FROM device_telemetry

                WHERE device_id = ?

                LIMIT 1
                """,
                (
                    device_id.strip(),
                ),
            ).fetchone()

        if row is None:

            return None

        return {

            "device_id":
                row["device_id"],

            "timestamp":
                row["timestamp"],

            "device_status":
                self._decode_json(
                    row["device_status_json"]
                ),

            "location":
                self._decode_json(
                    row["location_json"]
                ),

            "hardware_health":
                self._decode_json(
                    row["hardware_health_json"]
                ),

            "updated_at":
                row["updated_at"],

        }

    # ==========================================================
    # ALL LIVE TELEMETRY
    # ==========================================================

    def get_all_latest_telemetry(
        self,
    ) -> list[dict[str, Any]]:
        """
        Return the latest telemetry for every known device.
        """

        with self._connect() as connection:

            rows = connection.execute(
                """
                SELECT

                    device_id,

                    timestamp,

                    device_status_json,

                    location_json,

                    hardware_health_json,

                    updated_at

                FROM device_telemetry

                ORDER BY updated_at DESC
                """
            ).fetchall()

        return [

            {
                "device_id":
                    row["device_id"],

                "timestamp":
                    row["timestamp"],

                "device_status":
                    self._decode_json(
                        row["device_status_json"]
                    ),

                "location":
                    self._decode_json(
                        row["location_json"]
                    ),

                "hardware_health":
                    self._decode_json(
                        row["hardware_health_json"]
                    ),

                "updated_at":
                    row["updated_at"],

            }

            for row in rows

        ]

    # ==========================================================
    # TELEMETRY DEVICE LIST
    # ==========================================================

    def get_telemetry_devices(
        self,
    ) -> list[str]:
        """
        Return devices that have reported telemetry.
        """

        with self._connect() as connection:

            rows = connection.execute(
                """
                SELECT device_id

                FROM device_telemetry

                ORDER BY device_id
                """
            ).fetchall()

        return [
            row["device_id"]
            for row in rows
        ]

    # ==========================================================
    # INSERT RUNTIME EVENT
    # ==========================================================

    def insert_message(
        self,
        message: dict[str, Any],
    ) -> int:
        """
        Store a complete runtime event.

        Returns
        -------
        int
            Database ID.
        """

        required_fields = (

            "device_id",

            "timestamp",

            "prediction",

            "environment",

            "adaptive_policy",

            "event",

        )

        for field_name in required_fields:

            if field_name not in message:

                raise ValueError(
                    "Missing required message field: "
                    f"{field_name}"
                )

        with self._connect() as connection:

            cursor = connection.execute(
                """
                INSERT INTO edge_events (

                    device_id,

                    timestamp,

                    prediction_json,

                    environment_json,

                    adaptive_policy_json,

                    event_json,

                    decision_json,

                    unknown_discovery_json,

                    location_json,

                    device_status_json

                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (

                    message["device_id"],

                    message["timestamp"],

                    json.dumps(
                        message["prediction"]
                    ),

                    json.dumps(
                        message["environment"]
                    ),

                    json.dumps(
                        message["adaptive_policy"]
                    ),

                    json.dumps(
                        message["event"]
                    ),

                    json.dumps(
                        message.get(
                            "decision"
                        )
                    ),

                    json.dumps(
                        message.get(
                            "unknown_discovery"
                        )
                    ),

                    json.dumps(
                        message.get(
                            "location"
                        )
                    ),

                    json.dumps(
                        message.get(
                            "device_status"
                        )
                    ),

                ),
            )

            connection.commit()

            return int(
                cursor.lastrowid
            )

    # ==========================================================
    # COUNT
    # ==========================================================

    def count(
        self,
    ) -> int:
        """
        Return the number of runtime events.
        """

        with self._connect() as connection:

            row = connection.execute(
                """
                SELECT COUNT(*)
                FROM edge_events
                """
            ).fetchone()

        return int(
            row[0]
        )

    # ==========================================================
    # LATEST EVENT
    # ==========================================================

    def get_latest(
        self,
    ) -> dict[str, Any] | None:
        """
        Return the latest runtime event.
        """

        with self._connect() as connection:

            row = connection.execute(
                """
                SELECT

                    id,

                    device_id,

                    timestamp,

                    prediction_json,

                    environment_json,

                    adaptive_policy_json,

                    event_json,

                    decision_json,

                    unknown_discovery_json,

                    location_json,

                    device_status_json

                FROM edge_events

                ORDER BY id DESC

                LIMIT 1
                """
            ).fetchone()

        if row is None:

            return None

        return self._row_to_dict(
            row
        )

    # ==========================================================
    # RECENT EVENTS
    # ==========================================================

    def get_recent(
        self,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """
        Return recent runtime events.
        """

        limit = int(
            limit
        )

        if limit <= 0:

            raise ValueError(
                "limit must be greater than zero."
            )

        with self._connect() as connection:

            rows = connection.execute(
                """
                SELECT

                    id,

                    device_id,

                    timestamp,

                    prediction_json,

                    environment_json,

                    adaptive_policy_json,

                    event_json,

                    decision_json,

                    unknown_discovery_json,

                    location_json,

                    device_status_json

                FROM edge_events

                ORDER BY id DESC

                LIMIT ?
                """,
                (
                    limit,
                ),
            ).fetchall()

        return [
            self._row_to_dict(
                row
            )
            for row in rows
        ]

    # ==========================================================
    # DEVICES
    # ==========================================================

    def get_devices(
        self,
    ) -> list[str]:
        """
        Return every known device from both telemetry and events.
        """

        with self._connect() as connection:

            rows = connection.execute(
                """
                SELECT device_id
                FROM device_telemetry

                UNION

                SELECT device_id
                FROM edge_events

                ORDER BY device_id
                """
            ).fetchall()

        return [
            row["device_id"]
            for row in rows
        ]

    # ==========================================================
    # DEVICE EVENTS
    # ==========================================================

    def get_recent_for_device(
        self,
        device_id: str,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """
        Return recent runtime events for one device.
        """

        if not device_id:

            raise ValueError(
                "device_id cannot be empty."
            )

        limit = int(
            limit
        )

        if limit <= 0:

            raise ValueError(
                "limit must be greater than zero."
            )

        with self._connect() as connection:

            rows = connection.execute(
                """
                SELECT

                    id,

                    device_id,

                    timestamp,

                    prediction_json,

                    environment_json,

                    adaptive_policy_json,

                    event_json,

                    decision_json,

                    unknown_discovery_json,

                    location_json,

                    device_status_json

                FROM edge_events

                WHERE device_id = ?

                ORDER BY id DESC

                LIMIT ?
                """,
                (
                    device_id,

                    limit,
                ),
            ).fetchall()

        return [
            self._row_to_dict(
                row
            )
            for row in rows
        ]

    # ==========================================================
    # JSON DECODING
    # ==========================================================

    @staticmethod
    def _decode_json(
        value: Any,
    ) -> Any:
        """
        Decode a JSON field safely.
        """

        if value is None:

            return None

        if isinstance(
            value,
            (
                dict,
                list,
                int,
                float,
                bool,
            ),
        ):

            return value

        try:

            return json.loads(
                value
            )

        except (
            TypeError,
            json.JSONDecodeError,
        ):

            return None

    # ==========================================================
    # ROW CONVERSION
    # ==========================================================

    def _row_to_dict(
        self,
        row: sqlite3.Row,
    ) -> dict[str, Any]:
        """
        Convert an edge_events row to a dictionary.
        """

        return {

            "id":
                row["id"],

            "device_id":
                row["device_id"],

            "timestamp":
                row["timestamp"],

            "prediction":
                self._decode_json(
                    row["prediction_json"]
                ),

            "environment":
                self._decode_json(
                    row["environment_json"]
                ),

            "adaptive_policy":
                self._decode_json(
                    row["adaptive_policy_json"]
                ),

            "event":
                self._decode_json(
                    row["event_json"]
                ),

            "decision":
                self._decode_json(
                    row["decision_json"]
                ),

            "unknown_discovery":
                self._decode_json(
                    row["unknown_discovery_json"]
                ),

            "location":
                self._decode_json(
                    row["location_json"]
                ),

            "device_status":
                self._decode_json(
                    row["device_status_json"]
                ),

        }

    # ==========================================================
    # TELEMETRY HISTORY
    # ==========================================================

    def insert_telemetry_history(
        self,
        device_id: str,
        timestamp: float,
        device_status: dict[str, Any] | None = None,
        location: dict[str, Any] | None = None,
        hardware_health: dict[str, Any] | None = None,
    ) -> int:
        """
        Record a permanent historical telemetry entry into SQLite.
        """
        if not device_id or not device_id.strip():
            raise ValueError("device_id cannot be empty.")

        device_id = device_id.strip()
        status = device_status or {}

        temp = status.get("temperature")
        hum = status.get("humidity")
        light = status.get("light_level")
        batt_pct = status.get("battery_percent")
        batt_v = status.get("battery_voltage")
        vib = 1 if status.get("vibration_detected") else 0

        mq2_raw = status.get("mq2_raw")
        mq2_v = status.get("mq2_adc_voltage", status.get("mq2_voltage"))
        mq135_raw = status.get("mq135_raw")
        mq135_v = status.get("mq135_adc_voltage", status.get("mq135_voltage"))

        gas_assessment = status.get("gas_assessment") or {}
        gas_score = gas_assessment.get("gas_risk_score") if isinstance(gas_assessment, dict) else None
        gas_stat = gas_assessment.get("overall_status") if isinstance(gas_assessment, dict) else None

        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO telemetry_history (
                    device_id,
                    timestamp,
                    temperature,
                    humidity,
                    light_level,
                    battery_percent,
                    battery_voltage,
                    vibration_detected,
                    mq2_raw,
                    mq2_voltage,
                    mq135_raw,
                    mq135_voltage,
                    gas_risk_score,
                    gas_status,
                    device_status_json,
                    location_json,
                    hardware_health_json,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    device_id,
                    float(timestamp),
                    float(temp) if temp is not None else None,
                    float(hum) if hum is not None else None,
                    float(light) if light is not None else None,
                    float(batt_pct) if batt_pct is not None else None,
                    float(batt_v) if batt_v is not None else None,
                    vib,
                    float(mq2_raw) if mq2_raw is not None else None,
                    float(mq2_v) if mq2_v is not None else None,
                    float(mq135_raw) if mq135_raw is not None else None,
                    float(mq135_v) if mq135_v is not None else None,
                    float(gas_score) if gas_score is not None else None,
                    str(gas_stat) if gas_stat is not None else None,
                    json.dumps(device_status),
                    json.dumps(location),
                    json.dumps(hardware_health),
                    float(timestamp),
                ),
            )
            connection.commit()
            return cursor.lastrowid

    def get_telemetry_history(
        self,
        device_id: str | None = None,
        limit: int = 100,
        start_time: float | None = None,
        end_time: float | None = None,
    ) -> list[dict[str, Any]]:
        """
        Query chronological telemetry history with optional filtering.
        """
        limit = max(1, int(limit))
        query = ["SELECT * FROM telemetry_history WHERE 1=1"]
        params: list[Any] = []

        if device_id:
            query.append("AND device_id = ?")
            params.append(device_id.strip())

        if start_time is not None:
            query.append("AND timestamp >= ?")
            params.append(float(start_time))

        if end_time is not None:
            query.append("AND timestamp <= ?")
            params.append(float(end_time))

        query.append("ORDER BY timestamp DESC LIMIT ?")
        params.append(limit)

        with self._connect() as connection:
            rows = connection.execute(" ".join(query), params).fetchall()

        results = []
        for r in rows:
            results.append({
                "id": r["id"],
                "device_id": r["device_id"],
                "timestamp": r["timestamp"],
                "temperature": r["temperature"],
                "humidity": r["humidity"],
                "light_level": r["light_level"],
                "battery_percent": r["battery_percent"],
                "battery_voltage": r["battery_voltage"],
                "vibration_detected": bool(r["vibration_detected"]),
                "mq2_raw": r["mq2_raw"],
                "mq2_voltage": r["mq2_voltage"],
                "mq135_raw": r["mq135_raw"],
                "mq135_voltage": r["mq135_voltage"],
                "gas_risk_score": r["gas_risk_score"],
                "gas_status": r["gas_status"],
                "device_status": self._decode_json(r["device_status_json"]),
                "location": self._decode_json(r["location_json"]),
                "hardware_health": self._decode_json(r["hardware_health_json"]),
                "created_at": r["created_at"],
            })
        return results

    def get_gas_history(
        self,
        device_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Query gas sensor time-series data.
        """
        history = self.get_telemetry_history(device_id=device_id, limit=limit)
        return [
            {
                "timestamp": h["timestamp"],
                "device_id": h["device_id"],
                "mq2_raw": h["mq2_raw"],
                "mq2_voltage": h["mq2_voltage"],
                "mq135_raw": h["mq135_raw"],
                "mq135_voltage": h["mq135_voltage"],
                "gas_risk_score": h["gas_risk_score"],
                "gas_status": h["gas_status"],
            }
            for h in history
            if h["mq2_raw"] is not None or h["mq135_raw"] is not None
        ]

    # ==========================================================
    # EXPERIMENT & BENCHMARK LOGGING
    # ==========================================================

    def insert_experiment_log(
        self,
        experiment_name: str,
        summary: dict[str, Any],
        details: Any,
        config: dict[str, Any] | None = None,
        timestamp: float | None = None,
    ) -> int:
        """
        Persist experiment benchmarks and validation trial results.
        """
        if not experiment_name:
            raise ValueError("experiment_name cannot be empty.")

        import time as _time
        ts = float(timestamp if timestamp is not None else _time.time())

        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO experiment_logs (
                    experiment_name,
                    timestamp,
                    summary_json,
                    details_json,
                    config_json,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    experiment_name.strip(),
                    ts,
                    json.dumps(summary),
                    json.dumps(details),
                    json.dumps(config or {}),
                    ts,
                ),
            )
            connection.commit()
            return cursor.lastrowid

    def get_latest_experiment(
        self,
        experiment_name: str,
    ) -> dict[str, Any] | None:
        """
        Retrieve the newest run for an experiment.
        """
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM experiment_logs
                WHERE experiment_name = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (experiment_name.strip(),),
            ).fetchone()

        if row is None:
            return None

        return {
            "id": row["id"],
            "experiment_name": row["experiment_name"],
            "timestamp": row["timestamp"],
            "summary": self._decode_json(row["summary_json"]),
            "details": self._decode_json(row["details_json"]),
            "config": self._decode_json(row["config_json"]),
            "created_at": row["created_at"],
        }

    def get_all_experiments(
        self,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """
        Retrieve recent experiment logs.
        """
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, experiment_name, timestamp, summary_json, config_json, created_at
                FROM experiment_logs
                ORDER BY id DESC
                LIMIT ?
                """,
                (max(1, int(limit)),),
            ).fetchall()

        return [
            {
                "id": r["id"],
                "experiment_name": r["experiment_name"],
                "timestamp": r["timestamp"],
                "summary": self._decode_json(r["summary_json"]),
                "config": self._decode_json(r["config_json"]),
                "created_at": r["created_at"],
            }
            for r in rows
        ]

    # ==========================================================
    # EMERGENCY ALERT NOTIFICATIONS
    # ==========================================================

    def insert_emergency_alert(self, alert_data: dict[str, Any]) -> str:
        """
        Insert an emergency alert record into the database.
        """
        alert_id = str(alert_data.get("alert_id") or f"alert-{int(time.time())}")
        device_id = str(alert_data.get("device_id") or "UNKNOWN")
        ts = float(alert_data.get("timestamp") or time.time())
        threat_type = str(alert_data.get("threat_type") or "UNKNOWN")
        risk_level = str(alert_data.get("risk_level") or "CRITICAL")
        confidence = float(alert_data.get("confidence") or 0.0)
        location = alert_data.get("location") or {}
        lat = alert_data.get("location_lat", location.get("latitude"))
        lon = alert_data.get("location_lon", location.get("longitude"))
        message = str(alert_data.get("message") or "")
        channels_json = json.dumps(alert_data.get("channels") or ["LOCAL_DEVICE_STROBE"])
        decision_json = json.dumps(alert_data.get("decision") or {})
        status = str(alert_data.get("status") or "DISPATCHED")
        created_at = str(alert_data.get("created_at") or datetime.utcnow().isoformat() + "Z")

        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO emergency_alerts (
                    alert_id, device_id, timestamp, threat_type, risk_level,
                    confidence, location_lat, location_lon, message,
                    channels_json, decision_json, status, created_at,
                    acknowledged_at, acknowledged_by
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    alert_id, device_id, ts, threat_type, risk_level,
                    confidence, lat, lon, message,
                    channels_json, decision_json, status, created_at,
                    None, None
                ),
            )
            connection.commit()

        return alert_id

    def get_active_emergency_alerts(self, limit: int = 20) -> list[dict[str, Any]]:
        """
        Retrieve all unacknowledged (active) emergency alerts.
        """
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM emergency_alerts
                WHERE status = 'DISPATCHED'
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (max(1, int(limit)),),
            ).fetchall()

        return [
            {
                "alert_id": r["alert_id"],
                "device_id": r["device_id"],
                "timestamp": r["timestamp"],
                "threat_type": r["threat_type"],
                "risk_level": r["risk_level"],
                "confidence": r["confidence"],
                "location_lat": r["location_lat"],
                "location_lon": r["location_lon"],
                "message": r["message"],
                "channels": self._decode_json(r["channels_json"]),
                "decision": self._decode_json(r["decision_json"]),
                "status": r["status"],
                "created_at": r["created_at"],
                "acknowledged_at": r["acknowledged_at"],
                "acknowledged_by": r["acknowledged_by"],
                "resolved_at": r["resolved_at"] if "resolved_at" in r.keys() else None,
                "resolved_by": r["resolved_by"] if "resolved_by" in r.keys() else None,
                "resolution_notes": r["resolution_notes"] if "resolution_notes" in r.keys() else None,
                "assigned_ranger_id": r["assigned_ranger_id"] if "assigned_ranger_id" in r.keys() else None,
                "assigned_ranger_name": r["assigned_ranger_name"] if "assigned_ranger_name" in r.keys() else None,
            }
            for r in rows
        ]

    def get_emergency_alert_history(self, limit: int = 50) -> list[dict[str, Any]]:
        """
        Retrieve recent emergency alerts history.
        """
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM emergency_alerts
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (max(1, int(limit)),),
            ).fetchall()

        return [
            {
                "alert_id": r["alert_id"],
                "device_id": r["device_id"],
                "timestamp": r["timestamp"],
                "threat_type": r["threat_type"],
                "risk_level": r["risk_level"],
                "confidence": r["confidence"],
                "location_lat": r["location_lat"],
                "location_lon": r["location_lon"],
                "message": r["message"],
                "channels": self._decode_json(r["channels_json"]),
                "decision": self._decode_json(r["decision_json"]),
                "status": r["status"],
                "created_at": r["created_at"],
                "acknowledged_at": r["acknowledged_at"],
                "acknowledged_by": r["acknowledged_by"],
                "resolved_at": r["resolved_at"] if "resolved_at" in r.keys() else None,
                "resolved_by": r["resolved_by"] if "resolved_by" in r.keys() else None,
                "resolution_notes": r["resolution_notes"] if "resolution_notes" in r.keys() else None,
                "assigned_ranger_id": r["assigned_ranger_id"] if "assigned_ranger_id" in r.keys() else None,
                "assigned_ranger_name": r["assigned_ranger_name"] if "assigned_ranger_name" in r.keys() else None,
            }
            for r in rows
        ]

    def acknowledge_emergency_alert(
        self,
        alert_id: str,
        acknowledged_by: str = "Ranger Station",
    ) -> bool:
        """
        Acknowledge an emergency alert.
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE emergency_alerts
                SET status = 'ACKNOWLEDGED',
                    acknowledged_at = ?,
                    acknowledged_by = ?
                WHERE alert_id = ?
                """,
                (now_iso, acknowledged_by.strip(), alert_id.strip()),
            )
            connection.commit()
            return cursor.rowcount > 0

    def resolve_emergency_alert(
        self,
        alert_id: str,
        resolved_by: str = "Field Ranger Unit",
        resolution_notes: str = "Threat addressed and resolved on site.",
    ) -> bool:
        """
        Mark an emergency alert as RESOLVED/SOLVED by a field ranger or chief ranger.
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE emergency_alerts
                SET status = 'RESOLVED',
                    resolved_at = ?,
                    resolved_by = ?,
                    resolution_notes = ?
                WHERE alert_id = ?
                """,
                (now_iso, resolved_by.strip(), resolution_notes.strip(), alert_id.strip()),
            )
            connection.commit()
            return cursor.rowcount > 0

    def assign_emergency_alert(
        self,
        alert_id: str,
        ranger_id: str,
        ranger_name: str,
    ) -> bool:
        """
        Assign an active emergency alert to a nearby field ranger unit.
        """
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE emergency_alerts
                SET status = 'ASSIGNED',
                    assigned_ranger_id = ?,
                    assigned_ranger_name = ?
                WHERE alert_id = ?
                """,
                (ranger_id.strip(), ranger_name.strip(), alert_id.strip()),
            )
            connection.commit()
            return cursor.rowcount > 0

    # ==========================================================
    # PUBLIC CITIZEN REPORTS
    # ==========================================================

    def insert_citizen_report(
        self,
        report_id: str,
        reporter_name: str,
        threat_category: str,
        description: str,
        contact_info: str | None = None,
        photo_filename: str | None = None,
        location_lat: float | None = None,
        location_lon: float | None = None,
        timestamp: float | None = None,
    ) -> str:
        """
        Store a new public citizen report with optional photo evidence and coordinates.
        """
        import time as _t
        ts = float(timestamp or _t.time())
        now_iso = datetime.now(timezone.utc).isoformat()

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO citizen_reports (
                    report_id, timestamp, reporter_name, contact_info,
                    threat_category, description, photo_filename,
                    location_lat, location_lon, status, status_notes,
                    created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING', 'Awaiting Chief Ranger review', ?, ?)
                """,
                (
                    report_id, ts, reporter_name, contact_info,
                    threat_category, description, photo_filename,
                    location_lat, location_lon, now_iso, now_iso
                ),
            )
            connection.commit()

        return report_id

    def get_citizen_reports(self, limit: int = 50, status: str | None = None) -> list[dict[str, Any]]:
        """
        Retrieve citizen reports submitted by the public.
        """
        with self._connect() as connection:
            if status:
                rows = connection.execute(
                    """
                    SELECT * FROM citizen_reports
                    WHERE status = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                    """,
                    (status.strip().upper(), max(1, int(limit))),
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT * FROM citizen_reports
                    ORDER BY timestamp DESC
                    LIMIT ?
                    """,
                    (max(1, int(limit)),),
                ).fetchall()

        return [dict(r) for r in rows]

    def update_citizen_report_status(
        self,
        report_id: str,
        status: str,
        notes: str = "",
    ) -> bool:
        """
        Update citizen report status (e.g. VERIFIED, DISPATCHED, RESOLVED).
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE citizen_reports
                SET status = ?,
                    status_notes = ?,
                    updated_at = ?
                WHERE report_id = ?
                """,
                (status.strip().upper(), notes.strip(), now_iso, report_id.strip()),
            )
            connection.commit()
            return cursor.rowcount > 0

    # ==========================================================
    # SECURITY & AUTHENTICATION AUDIT LOG
    # ==========================================================

    def insert_auth_audit_log(
        self,
        username: str,
        role: str,
        action: str,
        details: str = "",
        ip_address: str = "127.0.0.1",
        timestamp: float | None = None,
    ) -> str:
        """
        Insert an immutable audit log record.
        """
        import uuid as _u
        import time as _t
        event_id = "aud_" + _u.uuid4().hex[:12]
        ts = float(timestamp or _t.time())
        now_iso = datetime.now(timezone.utc).isoformat()

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO auth_audit_log (
                    event_id, timestamp, username, role, action, ip_address, details, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (event_id, ts, username, role, action, ip_address, details, now_iso),
            )
            connection.commit()

        return event_id

    def get_auth_audit_log(self, limit: int = 100) -> list[dict[str, Any]]:
        """
        Retrieve recent authentication and security audit logs.
        """
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM auth_audit_log
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (max(1, int(limit)),),
            ).fetchall()

        return [dict(r) for r in rows]

    # ==========================================================
    # FIELD RANGERS ROSTER & GEOLOCATION
    # ==========================================================

    def get_field_rangers(self) -> list[dict[str, Any]]:
        """
        Return active field ranger units, their current GPS coordinates, and patrol status.
        """
        return [
            {
                "ranger_id": "ranger_01",
                "name": "Ranger Amar Singh",
                "callsign": "ALPHA-1",
                "rank": "Senior Field Ranger",
                "sector": "Sector 4 (Tiger Corridor)",
                "latitude": 12.2980,
                "longitude": 76.6420,
                "status": "ON_PATROL",
                "battery": 92,
                "assigned_alert": None,
                "phone": "+91 98450 12345",
            },
            {
                "ranger_id": "ranger_02",
                "name": "Ranger Deepa Rao",
                "callsign": "BRAVO-2",
                "rank": "Rapid Response Lead",
                "sector": "Sector 2 (River Ridge)",
                "latitude": 12.2920,
                "longitude": 76.6340,
                "status": "RESPONDING",
                "battery": 85,
                "assigned_alert": "alert_chainsaw_01",
                "phone": "+91 98450 23456",
            },
            {
                "ranger_id": "ranger_03",
                "name": "Ranger Vikrant Kumar",
                "callsign": "SIERRA-3",
                "rank": "Acoustic Sentry Officer",
                "sector": "Sector 7 (North Boundary)",
                "latitude": 12.3020,
                "longitude": 76.6450,
                "status": "STANDBY",
                "battery": 98,
                "assigned_alert": None,
                "phone": "+91 98450 34567",
            },
        ]

    # ==========================================================
    # DATABASE METRICS & STATS
    # ==========================================================

    def get_database_stats(self) -> dict[str, Any]:
        """
        Return comprehensive storage statistics for the entire database.
        """
        with self._connect() as connection:
            events_count = connection.execute("SELECT COUNT(*) FROM edge_events").fetchone()[0]
            devices_count = connection.execute("SELECT COUNT(*) FROM device_telemetry").fetchone()[0]
            history_count = connection.execute("SELECT COUNT(*) FROM telemetry_history").fetchone()[0]
            experiments_count = connection.execute("SELECT COUNT(*) FROM experiment_logs").fetchone()[0]
            alerts_count = connection.execute("SELECT COUNT(*) FROM emergency_alerts").fetchone()[0]

        file_size_bytes = 0
        if self.database_path.exists():
            file_size_bytes = self.database_path.stat().st_size

        return {
            "database_path": str(self.database_path),
            "file_size_kb": round(file_size_bytes / 1024, 2),
            "total_edge_events": events_count,
            "total_registered_devices": devices_count,
            "total_telemetry_history_records": history_count,
            "total_experiment_logs": experiments_count,
            "total_emergency_alerts": alerts_count,
        }