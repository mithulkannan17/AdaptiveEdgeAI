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