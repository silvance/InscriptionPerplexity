from __future__ import annotations

from sqlite3 import Row
from typing import Any
from uuid import UUID

from inscription.domain.models import DraftStep, ExportDocument, RawEvent, ResolvedElement, ScreenshotArtifact, Session
from inscription.storage.sqlite_store import SQLiteStore


class InscriptionRepository:
    def __init__(self, store: SQLiteStore) -> None:
        self.store = store

    def initialize(self) -> None:
        self.store.initialize()

    def save_session(self, session: Session) -> None:
        with self.store.transaction() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO sessions (
                    session_id, created_at_utc, updated_at_utc, recording_started_at_utc,
                    recording_stopped_at_utc, status, title, guide_title, source_machine_name,
                    source_user_name, os_version, app_version, notes, step_count,
                    raw_event_count, screenshot_count, primary_export_document_id, settings_snapshot_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(session.session_id),
                    session.created_at_utc,
                    session.updated_at_utc,
                    session.recording_started_at_utc,
                    session.recording_stopped_at_utc,
                    session.status,
                    session.title,
                    session.guide_title,
                    session.source_machine_name,
                    session.source_user_name,
                    session.os_version,
                    session.app_version,
                    session.notes,
                    session.step_count,
                    session.raw_event_count,
                    session.screenshot_count,
                    str(session.primary_export_document_id) if session.primary_export_document_id else None,
                    self.store.dump_json(session.settings_snapshot_json),
                ),
            )

    def get_session(self, session_id: UUID | str) -> Session | None:
        with self.store.transaction() as conn:
            row = conn.execute("SELECT * FROM sessions WHERE session_id = ?", (str(session_id),)).fetchone()
        if not row:
            return None
        return Session(**self._session_dict(row))

    def save_raw_event(self, event: RawEvent) -> None:
        with self.store.transaction() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO raw_events (
                    event_id, session_id, sequence_number, timestamp_utc, event_kind, input_subtype,
                    cursor_x, cursor_y, screen_index, active_window_title, active_window_handle,
                    process_name, process_id, executable_path, correlation_id, resolution_id,
                    screenshot_id, is_noise_candidate, raw_payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(event.event_id),
                    str(event.session_id),
                    event.sequence_number,
                    event.timestamp_utc,
                    event.event_kind,
                    event.input_subtype,
                    event.cursor_x,
                    event.cursor_y,
                    event.screen_index,
                    event.active_window_title,
                    event.active_window_handle,
                    event.process_name,
                    event.process_id,
                    event.executable_path,
                    str(event.correlation_id) if event.correlation_id else None,
                    str(event.resolution_id) if event.resolution_id else None,
                    str(event.screenshot_id) if event.screenshot_id else None,
                    int(event.is_noise_candidate),
                    self.store.dump_json(event.raw_payload_json),
                ),
            )

    def list_raw_events(self, session_id: UUID | str) -> list[RawEvent]:
        with self.store.transaction() as conn:
            rows = conn.execute(
                "SELECT * FROM raw_events WHERE session_id = ? ORDER BY sequence_number", (str(session_id),)
            ).fetchall()
        return [RawEvent(**self._raw_event_dict(row)) for row in rows]

    def save_resolved_element(self, resolved: ResolvedElement) -> None:
        with self.store.transaction() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO resolved_elements (
                    resolution_id, event_id, resolved_at_utc, backend, window_title, window_class_name,
                    control_name, control_type, localized_control_type, automation_id, framework_id,
                    runtime_id, bounding_rect_json, parent_chain_summary, supported_patterns_json,
                    confidence_score, confidence_label, failure_reason, diagnostic_payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(resolved.resolution_id),
                    str(resolved.event_id),
                    resolved.resolved_at_utc,
                    resolved.backend,
                    resolved.window_title,
                    resolved.window_class_name,
                    resolved.control_name,
                    resolved.control_type,
                    resolved.localized_control_type,
                    resolved.automation_id,
                    resolved.framework_id,
                    self.store.dump_json(resolved.runtime_id),
                    self.store.dump_json(resolved.bounding_rect_json),
                    resolved.parent_chain_summary,
                    self.store.dump_json(resolved.supported_patterns_json),
                    resolved.confidence_score,
                    resolved.confidence_label,
                    resolved.failure_reason,
                    self.store.dump_json(resolved.diagnostic_payload_json),
                ),
            )

    def get_resolved_element_by_event(self, event_id: UUID | str) -> ResolvedElement | None:
        with self.store.transaction() as conn:
            row = conn.execute("SELECT * FROM resolved_elements WHERE event_id = ?", (str(event_id),)).fetchone()
        if not row:
            return None
        return ResolvedElement(**self._resolved_element_dict(row))

    def save_screenshot(self, screenshot: ScreenshotArtifact) -> None:
        with self.store.transaction() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO screenshot_artifacts (
                    screenshot_id, session_id, captured_at_utc, capture_mode, capture_scope, source_event_id,
                    file_path, file_name, image_width, image_height, image_format, sha256,
                    review_status, replacement_screenshot_id, crop_rect_json, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(screenshot.screenshot_id),
                    str(screenshot.session_id),
                    screenshot.captured_at_utc,
                    screenshot.capture_mode,
                    screenshot.capture_scope,
                    str(screenshot.source_event_id) if screenshot.source_event_id else None,
                    screenshot.file_path,
                    screenshot.file_name,
                    screenshot.image_width,
                    screenshot.image_height,
                    screenshot.image_format,
                    screenshot.sha256,
                    screenshot.review_status,
                    str(screenshot.replacement_screenshot_id) if screenshot.replacement_screenshot_id else None,
                    self.store.dump_json(screenshot.crop_rect_json),
                    screenshot.notes,
                ),
            )

    def list_screenshots(self, session_id: UUID | str) -> list[ScreenshotArtifact]:
        with self.store.transaction() as conn:
            rows = conn.execute(
                "SELECT * FROM screenshot_artifacts WHERE session_id = ? ORDER BY captured_at_utc", (str(session_id),)
            ).fetchall()
        return [ScreenshotArtifact(**self._screenshot_dict(row)) for row in rows]

    def save_draft_step(self, step: DraftStep) -> None:
        with self.store.transaction() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO draft_steps (
                    step_id, session_id, ordinal, title, body, primary_screenshot_id, source_event_ids_json,
                    source_resolution_ids_json, generation_strategy, confidence_score, review_status,
                    created_by, edited_by_user, is_user_inserted, is_deleted, annotation_json,
                    created_at_utc, updated_at_utc
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(step.step_id),
                    str(step.session_id),
                    step.ordinal,
                    step.title,
                    step.body,
                    str(step.primary_screenshot_id) if step.primary_screenshot_id else None,
                    self.store.dump_json([str(x) for x in step.source_event_ids_json]),
                    self.store.dump_json([str(x) for x in step.source_resolution_ids_json]) if step.source_resolution_ids_json else None,
                    step.generation_strategy,
                    step.confidence_score,
                    step.review_status,
                    step.created_by,
                    int(step.edited_by_user),
                    int(step.is_user_inserted),
                    int(step.is_deleted),
                    self.store.dump_json(step.annotation_json),
                    step.created_at_utc,
                    step.updated_at_utc,
                ),
            )

    def list_draft_steps(self, session_id: UUID | str) -> list[DraftStep]:
        with self.store.transaction() as conn:
            rows = conn.execute(
                "SELECT * FROM draft_steps WHERE session_id = ? ORDER BY ordinal", (str(session_id),)
            ).fetchall()
        return [DraftStep(**self._draft_step_dict(row)) for row in rows]

    def save_export_document(self, export_document: ExportDocument) -> None:
        with self.store.transaction() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO export_documents (
                    export_document_id, session_id, format, created_at_utc, title, output_path,
                    template_version, export_options_json, step_snapshot_json, sha256
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(export_document.export_document_id),
                    str(export_document.session_id),
                    export_document.format,
                    export_document.created_at_utc,
                    export_document.title,
                    export_document.output_path,
                    export_document.template_version,
                    self.store.dump_json(export_document.export_options_json),
                    self.store.dump_json(export_document.step_snapshot_json),
                    export_document.sha256,
                ),
            )

    def list_export_documents(self, session_id: UUID | str) -> list[ExportDocument]:
        with self.store.transaction() as conn:
            rows = conn.execute(
                "SELECT * FROM export_documents WHERE session_id = ? ORDER BY created_at_utc", (str(session_id),)
            ).fetchall()
        return [ExportDocument(**self._export_document_dict(row)) for row in rows]

    def _session_dict(self, row: Row) -> dict[str, Any]:
        return {
            **dict(row),
            "settings_snapshot_json": self.store.load_json(row["settings_snapshot_json"]),
        }

    def _raw_event_dict(self, row: Row) -> dict[str, Any]:
        return {
            **dict(row),
            "is_noise_candidate": bool(row["is_noise_candidate"]),
            "raw_payload_json": self.store.load_json(row["raw_payload_json"]),
        }

    def _resolved_element_dict(self, row: Row) -> dict[str, Any]:
        return {
            **dict(row),
            "runtime_id": self.store.load_json(row["runtime_id"]),
            "bounding_rect_json": self.store.load_json(row["bounding_rect_json"]),
            "supported_patterns_json": self.store.load_json(row["supported_patterns_json"]),
            "diagnostic_payload_json": self.store.load_json(row["diagnostic_payload_json"]),
        }

    def _screenshot_dict(self, row: Row) -> dict[str, Any]:
        return {
            **dict(row),
            "crop_rect_json": self.store.load_json(row["crop_rect_json"]),
        }

    def _draft_step_dict(self, row: Row) -> dict[str, Any]:
        source_event_ids = self.store.load_json(row["source_event_ids_json"]) or []
        source_resolution_ids = self.store.load_json(row["source_resolution_ids_json"])
        return {
            **dict(row),
            "source_event_ids_json": [UUID(x) for x in source_event_ids],
            "source_resolution_ids_json": [UUID(x) for x in source_resolution_ids] if source_resolution_ids else None,
            "edited_by_user": bool(row["edited_by_user"]),
            "is_user_inserted": bool(row["is_user_inserted"]),
            "is_deleted": bool(row["is_deleted"]),
            "annotation_json": self.store.load_json(row["annotation_json"]),
        }

    def _export_document_dict(self, row: Row) -> dict[str, Any]:
        return {
            **dict(row),
            "export_options_json": self.store.load_json(row["export_options_json"]),
            "step_snapshot_json": self.store.load_json(row["step_snapshot_json"]),
        }
