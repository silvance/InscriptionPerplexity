from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterator


def adapt_datetime(dt: datetime) -> str:
    return dt.isoformat()


def convert_datetime(value: bytes) -> datetime:
    return datetime.fromisoformat(value.decode())


sqlite3.register_adapter(datetime, adapt_datetime)
sqlite3.register_converter("timestamp", convert_datetime)


class SQLiteStore:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(
            self.db_path,
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        conn = self.connect()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def initialize(self) -> None:
        with self.transaction() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    created_at_utc timestamp NOT NULL,
                    updated_at_utc timestamp NOT NULL,
                    recording_started_at_utc timestamp,
                    recording_stopped_at_utc timestamp,
                    status TEXT NOT NULL,
                    title TEXT,
                    guide_title TEXT,
                    source_machine_name TEXT,
                    source_user_name TEXT,
                    os_version TEXT,
                    app_version TEXT NOT NULL,
                    notes TEXT,
                    step_count INTEGER NOT NULL DEFAULT 0,
                    raw_event_count INTEGER NOT NULL DEFAULT 0,
                    screenshot_count INTEGER NOT NULL DEFAULT 0,
                    primary_export_document_id TEXT,
                    settings_snapshot_json TEXT
                );

                CREATE TABLE IF NOT EXISTS raw_events (
                    event_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    sequence_number INTEGER NOT NULL,
                    timestamp_utc timestamp NOT NULL,
                    event_kind TEXT NOT NULL,
                    input_subtype TEXT,
                    cursor_x INTEGER,
                    cursor_y INTEGER,
                    screen_index INTEGER,
                    active_window_title TEXT,
                    active_window_handle TEXT,
                    process_name TEXT,
                    process_id INTEGER,
                    executable_path TEXT,
                    correlation_id TEXT,
                    resolution_id TEXT,
                    screenshot_id TEXT,
                    is_noise_candidate INTEGER NOT NULL DEFAULT 0,
                    raw_payload_json TEXT,
                    FOREIGN KEY(session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_raw_events_session_sequence ON raw_events(session_id, sequence_number);

                CREATE TABLE IF NOT EXISTS resolved_elements (
                    resolution_id TEXT PRIMARY KEY,
                    event_id TEXT NOT NULL UNIQUE,
                    resolved_at_utc timestamp NOT NULL,
                    backend TEXT NOT NULL,
                    window_title TEXT,
                    window_class_name TEXT,
                    control_name TEXT,
                    control_type TEXT,
                    localized_control_type TEXT,
                    automation_id TEXT,
                    framework_id TEXT,
                    runtime_id TEXT,
                    bounding_rect_json TEXT,
                    parent_chain_summary TEXT,
                    supported_patterns_json TEXT,
                    confidence_score REAL NOT NULL,
                    confidence_label TEXT NOT NULL,
                    failure_reason TEXT,
                    diagnostic_payload_json TEXT,
                    FOREIGN KEY(event_id) REFERENCES raw_events(event_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS screenshot_artifacts (
                    screenshot_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    captured_at_utc timestamp NOT NULL,
                    capture_mode TEXT NOT NULL,
                    capture_scope TEXT NOT NULL,
                    source_event_id TEXT,
                    file_path TEXT NOT NULL,
                    file_name TEXT NOT NULL,
                    image_width INTEGER NOT NULL,
                    image_height INTEGER NOT NULL,
                    image_format TEXT NOT NULL,
                    sha256 TEXT,
                    review_status TEXT NOT NULL,
                    replacement_screenshot_id TEXT,
                    crop_rect_json TEXT,
                    notes TEXT,
                    FOREIGN KEY(session_id) REFERENCES sessions(session_id) ON DELETE CASCADE,
                    FOREIGN KEY(source_event_id) REFERENCES raw_events(event_id) ON DELETE SET NULL,
                    FOREIGN KEY(replacement_screenshot_id) REFERENCES screenshot_artifacts(screenshot_id) ON DELETE SET NULL
                );

                CREATE TABLE IF NOT EXISTS draft_steps (
                    step_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    ordinal INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    body TEXT,
                    primary_screenshot_id TEXT,
                    source_event_ids_json TEXT NOT NULL,
                    source_resolution_ids_json TEXT,
                    generation_strategy TEXT,
                    confidence_score REAL NOT NULL,
                    review_status TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    edited_by_user INTEGER NOT NULL DEFAULT 0,
                    is_user_inserted INTEGER NOT NULL DEFAULT 0,
                    is_deleted INTEGER NOT NULL DEFAULT 0,
                    annotation_json TEXT,
                    created_at_utc timestamp NOT NULL,
                    updated_at_utc timestamp NOT NULL,
                    FOREIGN KEY(session_id) REFERENCES sessions(session_id) ON DELETE CASCADE,
                    FOREIGN KEY(primary_screenshot_id) REFERENCES screenshot_artifacts(screenshot_id) ON DELETE SET NULL
                );
                CREATE INDEX IF NOT EXISTS idx_draft_steps_session_ordinal ON draft_steps(session_id, ordinal);

                CREATE TABLE IF NOT EXISTS export_documents (
                    export_document_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    format TEXT NOT NULL,
                    created_at_utc timestamp NOT NULL,
                    title TEXT NOT NULL,
                    output_path TEXT NOT NULL,
                    template_version TEXT,
                    export_options_json TEXT,
                    step_snapshot_json TEXT NOT NULL,
                    sha256 TEXT,
                    FOREIGN KEY(session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
                );
                """
            )

    @staticmethod
    def dump_json(value: object | None) -> str | None:
        if value is None:
            return None
        return json.dumps(value)

    @staticmethod
    def load_json(value: str | None):
        if value is None:
            return None
        return json.loads(value)
