from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from inscription.capture.capture_models import CaptureRuntimeConfig
from inscription.capture.session_controller import SessionController
from inscription.domain.enums import CaptureMode, CaptureScope
from inscription.infrastructure.windows_adapters import (
    KeyboardEventProvider,
    MouseEventProvider,
    ScreenshotProvider,
    WindowFocusProvider,
)


@dataclass(slots=True)
class CaptureCoordinator:
    controller: SessionController
    mouse_provider: MouseEventProvider
    keyboard_provider: KeyboardEventProvider
    window_provider: WindowFocusProvider
    screenshot_provider: ScreenshotProvider
    screenshot_root: str | Path = "sessions"
    _providers_started: bool = field(init=False, default=False)

    def start_capture(self, *, app_version: str, title: str | None = None) -> None:
        self.controller.start_session(app_version=app_version, title=title)
        self.mouse_provider.start()
        self.keyboard_provider.start()
        self.window_provider.start()
        self._providers_started = True

    def stop_capture(self):
        self._stop_providers()
        return self.controller.stop_session()

    def pause_capture(self) -> None:
        self.controller.pause_session()

    def resume_capture(self) -> None:
        self.controller.resume_session()

    def ingest_click(
        self,
        *,
        cursor_x: int,
        cursor_y: int,
        button: str = "left_click",
    ):
        active_window = self.window_provider.get_active_window() or {}
        return self.controller.record_click(
            window_title=active_window.get("window_title"),
            cursor_x=cursor_x,
            cursor_y=cursor_y,
            button=button,
            process_name=active_window.get("process_name"),
            process_id=active_window.get("process_id"),
        )

    def ingest_window_change(self) -> None:
        active_window = self.window_provider.get_active_window() or {}
        window_title = active_window.get("window_title")
        if not window_title:
            return
        self.controller.record_window_change(
            window_title=window_title,
            process_name=active_window.get("process_name"),
            process_id=active_window.get("process_id"),
        )

    def ingest_keyboard_milestone(self, *, input_subtype: str) -> None:
        active_window = self.window_provider.get_active_window() or {}
        self.controller.record_keyboard_milestone(
            input_subtype=input_subtype,
            window_title=active_window.get("window_title"),
        )

    def capture_manual_window_screenshot(self):
        session = self.controller.current_session
        if session is None:
            raise RuntimeError("no active session")
        destination_dir = self._session_screenshot_dir(session_id=str(session.session_id))
        stem = f"shot-{self.controller.snapshot.screenshot_count + 1:04d}"
        result = self.screenshot_provider.capture_window(
            destination_dir=destination_dir,
            stem=stem,
        )
        return self.controller.record_screenshot(
            capture_mode=CaptureMode.MANUAL,
            capture_scope=CaptureScope.WINDOW,
            file_path=result.file_path,
            file_name=result.file_name,
            image_width=result.image_width,
            image_height=result.image_height,
            image_format=result.image_format,
        )

    def capture_manual_screen_screenshot(self):
        session = self.controller.current_session
        if session is None:
            raise RuntimeError("no active session")
        destination_dir = self._session_screenshot_dir(session_id=str(session.session_id))
        stem = f"shot-{self.controller.snapshot.screenshot_count + 1:04d}"
        result = self.screenshot_provider.capture_screen(
            destination_dir=destination_dir,
            stem=stem,
        )
        return self.controller.record_screenshot(
            capture_mode=CaptureMode.MANUAL,
            capture_scope=CaptureScope.SCREEN,
            file_path=result.file_path,
            file_name=result.file_name,
            image_width=result.image_width,
            image_height=result.image_height,
            image_format=result.image_format,
        )

    def _session_screenshot_dir(self, *, session_id: str) -> Path:
        return Path(self.screenshot_root) / session_id / "screenshots"

    def _stop_providers(self) -> None:
        if not self._providers_started:
            return
        self.mouse_provider.stop()
        self.keyboard_provider.stop()
        self.window_provider.stop()
        self._providers_started = False