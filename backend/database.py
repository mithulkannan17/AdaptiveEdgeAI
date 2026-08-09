"""
Runtime Database

Stores telemetry and event information received from
adaptive edge nodes.

This database is separate from the training dataset
metadata stored in the project's database/ directory.
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
    SQLite storage for edge runtime messages.
    """

    def __init__(
        self,
        database_path: str | Path = DEFAULT_DATABASE_PATH,
    ):
        self.database_path = Path(
            database_path
        )

        self.database_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.initialize()

    def _connect(self):
        """
        Create a SQLite connection.
        """

        return sqlite3.connect(
            self.database_path
        )

    def initialize(self) -> None:
        """
        Create the runtime telemetry table if it
        does not already exist.
        """

        with self._connect() as connection:

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

                    unknown_discovery_json TEXT,

                    location_json TEXT,

                    device_status_json TEXT

                )
                """
            )

            connection.commit()

    def insert_message(
        self,
        message: dict[str, Any],
    ) -> int:
        """
        Store an EdgeMessage.

        Returns
        -------
        int
            Database ID assigned to the record.
        """

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

                    unknown_discovery_json,

                    location_json,

                    device_status_json

                )

                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
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

    def count(self) -> int:
        """
        Return the number of stored runtime records.
        """

        with self._connect() as connection:

            cursor = connection.execute(
                "SELECT COUNT(*) FROM edge_events"
            )

            return int(
                cursor.fetchone()[0]
            )

    def get_latest(
        self,
    ) -> dict | None:
        """
        Return the latest runtime record.
        """

        with self._connect() as connection:

            cursor = connection.execute(

                """
                SELECT

                    id,

                    device_id,

                    timestamp,

                    prediction_json,

                    environment_json,

                    adaptive_policy_json,

                    event_json,

                    unknown_discovery_json,

                    location_json,

                    device_status_json

                FROM edge_events

                ORDER BY id DESC

                LIMIT 1
                """

            )

            row = cursor.fetchone()

        if row is None:

            return None

        return self._row_to_dict(
            row
        )

    @staticmethod
    def _decode_json(
        value,
    ):
        """
        Decode a JSON database field.
        """

        if value is None:
            return None

        return json.loads(value)

    def _row_to_dict(
        self,
        row,
    ) -> dict:

        return {

            "id": row[0],

            "device_id": row[1],

            "timestamp": row[2],

            "prediction":
                self._decode_json(row[3]),

            "environment":
                self._decode_json(row[4]),

            "adaptive_policy":
                self._decode_json(row[5]),

            "event":
                self._decode_json(row[6]),

            "unknown_discovery":
                self._decode_json(row[7]),

            "location":
                self._decode_json(row[8]),

            "device_status":
                self._decode_json(row[9]),

        }