from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from inscription.capture.capture_models import CaptureRuntimeConfig, RecorderStatus, RecordingSessionSnapshot
from inscription.domain.enums import CaptureMode, CaptureScope, EventKind, SessionStatus
from inscription.domain.models import RawEvent, ScreenshotArtifact, Session
from inscription.storage.repository import InscriptionRepository
from inscription.utils.time import utc_now


@dataclass(slots=True)
class SessionController:
    repository: InscriptionRepository
    config: CaptureRuntimeConfig = field(default_factory=CaptureRuntimeConfig)
    _snapshot: RecordingSessionSnapshot | None = field(init=False, default=None)
    _current_session: Session | None = field(init=False, default=None)
    _sequence_number: int = field(init=False, default=0)

    def __post_init__(self) -> None:
        self._snapshot = None
        self._current_session = None
        self._sequence_number = 0

    @property
    def snapshot(self) -> RecordingSessionSnapshot | None:
        return self._snapshot

    @property
    def current_session(self) -> Session | None:
        return self._current_session

    def start_session(self, *, app_version: str, title: str | None = None) -> Session:
        if self._snapshot and self._snapshot.status in {RecorderStatus.RECORDING, RecorderStatus.PAUSED}:
            raise RuntimeError("a recording session is already active")

        now = utc_now()
        session = Session(
            app_version=app_version,
            title=title,
            status=SessionStatus.RECORDING,
            created_at_utc=now,
            recording_started_at_utc=now,
            updated_at_utc=now,
        )
        self.repository.save_session(session)

        self._current_session = session
        self._sequence_number = 0
        self._snapshot = RecordingSessionSnapshot(
            session_id=session.session_id,
            status=RecorderStatus.RECORDING,
            started_at_utc=now,
            title=title,
        )
        self._record_system_event(EventKind.SESSION_START)
        return self._current_session

    def pause_session(self) -> None:
        snapshot = self._require_active_snapshot()
        if snapshot.status != RecorderStatus.RECORDING:
            raise RuntimeError("session must be recording to pause")
        now = utc_now()
        snapshot.status = RecorderStatus.PAUSED
        snapshot.paused_at_utc = now
        self._current_session.status = SessionStatus.PAUSED
        self._current_session.updated_at_utc = now
        self.repository.save_session(self._current_session)
        self._record_system_event(EventKind.SESSION_PAUSE)

    def resume_session(self) -> None:
        snapshot = self._require_active_snapshot()
        if snapshot.status != RecorderStatus.PAUSED:
            raise RuntimeError("session must be paused to resume")
        now = utc_now()
        snapshot.status = RecorderStatus.RECORDING
        snapshot.resumed_at_utc = now
        self._current_session.status = SessionStatus.RECORDING
        self._current_session.updated_at_utc = now
        self.repository.save_session(self._current_session)
        self._record_system_event(EventKind.SESSION_RESUME)

    def stop_session(self) -> Session:
        snapshot = self._require_active_snapshot()
        if snapshot.status not in {RecorderStatus.RECORDING, RecorderStatus.PAUSED}:
            raise RuntimeError("session is not active")
        now = utc_now()
        self._record_system_event(EventKind.SESSION_STOP)
        snapshot.status = RecorderStatus.STOPPED
        snapshot.stopped_at_utc = now
        self._current_session.status = SessionStatus.STOPPED
        self._current_session.recording_stopped_at_utc = now
        self._current_session.updated_at_utc = now
        self._current_session.raw_event_count = snapshot.event_count
        self._current_session.screenshot_count = snapshot.screenshot_count
        self.repository.save_session(self._current_session)
        return self._current_session

    def record_click(
        self,
        *,
        window_title: str | None,
        cursor_x: int,
        cursor_y: int,
        button: str = "left_click",
        process_name: str | None = None,
        process_id: int | None = None,
        executable_path: str | None = None,
        raw_payload: dict[str, Any] | None = None,
    ) -> RawEvent:
        self._ensure_recording()
        event = self._build_event(
            event_kind=EventKind.MOUSE_CLICK,
            input_subtype=button,
            active_window_title=window_title,
            cursor_x=cursor_x,
            cursor_y=cursor_y,
            process_name=process_name,
            process_id=process_id,
            executable_path=executable_path,
            raw_payload_json=raw_payload,
        )
        self.repository.save_raw_event(event)
        self._after_event(event, window_title=window_title)
        if self.config.auto_screenshots and self.config.screenshot_on_left_click and button == "left_click":
            self.record_screenshot(capture_mode=CaptureMode.AUTO, capture_scope=CaptureScope.WINDOW, source_event_id=event.event_id)
        return event

    def record_window_change(
        self,
        *,
        window_title: str,
        process_name: str | None = None,
        process_id: int | None = None,
    ) -> RawEvent:
        self._ensure_recording()
        if not self.config.capture_window_changes:
            raise RuntimeError("window-change capture is disabled in config")
        event = self._build_event(
            event_kind=EventKind.WINDOW_CHANGE,
            active_window_title=window_title,
            process_name=process_name,
            process_id=process_id,
        )
        self.repository.save_raw_event(event)
        self._after_event(event, window_title=window_title)
        return event

    def record_keyboard_milestone(
        self,
        *,
        input_subtype: str,
        window_title: str | None = None,
        raw_payload: dict[str, Any] | None = None,
    ) -> RawEvent:
        self._ensure_recording()
        if not self.config.capture_keyboard_milestones:
            raise RuntimeError("keyboard milestone capture is disabled in config")
        event = self._build_event(
            event_kind=EventKind.KEYBOARD_MILESTONE,
            input_subtype=input_subtype,
            active_window_title=window_title,
            raw_payload_json=raw_payload,
        )
        self.repository.save_raw_event(event)
        self._after_event(event, window_title=window_title)
        return event

    def record_screenshot(
        self,
        *,
        capture_mode: CaptureMode,
        capture_scope: CaptureScope,
        source_event_id=None,
        file_path: str | None = None,
        file_name: str | None = None,
        image_width: int = 0,
        image_height: int = 0,
        image_format: str = "png",
    ) -> ScreenshotArtifact:
        self._ensure_active_session()
        now = utc_now()
        screenshot = ScreenshotArtifact(
            session_id=self._current_session.session_id,
            captured_at_utc=now,
            capture_mode=capture_mode,
            capture_scope=capture_scope,
            source_event_id=source_event_id,
            file_path=file_path or self._default_screenshot_path(),
            file_name=file_name or self._default_screenshot_name(),
            image_width=image_width or 1,
            image_height=image_height or 1,
            image_format=image_format,
        )
        self.repository.save_screenshot(screenshot)
        self._snapshot.screenshot_count += 1
        self._current_session.screenshot_count = self._snapshot.screenshot_count
        self._current_session.updated_at_utc = now
        self.repository.save_session(self._current_session)
        return screenshot

    def _record_system_event(self, event_kind: EventKind) -> RawEvent:
        event = self._build_event(event_kind=event_kind, active_window_title=self._snapshot.current_window_title if self._snapshot else None)
        self.repository.save_raw_event(event)
        self._after_event(event, window_title=event.active_window_title)
        return event

    def _build_event(self, *, event_kind: EventKind, **kwargs: Any) -> RawEvent:
        self._ensure_active_session()
        self._sequence_number += 1
        return RawEvent(
            session_id=self._current_session.session_id,
            sequence_number=self._sequence_number,
            event_kind=event_kind,
            **kwargs,
        )

    def _after_event(self, event: RawEvent, *, window_title: str | None) -> None:
        self._snapshot.event_count += 1
        self._snapshot.current_window_title = window_title or self._snapshot.current_window_title
        self._current_session.raw_event_count = self._snapshot.event_count
        self._current_session.updated_at_utc = utc_now()
        self.repository.save_session(self._current_session)

    def _default_screenshot_name(self) -> str:
        return f"shot-{self._snapshot.screenshot_count + 1:04d}.png"

    def _default_screenshot_path(self) -> str:
        return f"sessions/{self._current_session.session_id}/screenshots/{self._default_screenshot_name()}"

    def _ensure_recording(self) -> None:
        snapshot = self._require_active_snapshot()
        if snapshot.status != RecorderStatus.RECORDING:
            raise RuntimeError("session must be actively recording")
        if snapshot.event_count >= self.config.max_events_per_session:
            raise RuntimeError("session event limit reached")

    def _ensure_active_session(self) -> None:
        if self._current_session is None or self._snapshot is None:
            raise RuntimeError("no active session")

    def _require_active_snapshot(self) -> RecordingSessionSnapshot:
        self._ensure_active_session()
        return self._snapshot
