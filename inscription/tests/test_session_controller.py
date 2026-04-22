from pathlib import Path

import pytest

from inscription.capture.capture_models import CaptureRuntimeConfig, RecorderStatus
from inscription.capture.session_controller import SessionController
from inscription.domain.enums import CaptureMode, CaptureScope, EventKind, SessionStatus
from inscription.storage.repository import InscriptionRepository
from inscription.storage.sqlite_store import SQLiteStore


def make_controller(tmp_path: Path, config: CaptureRuntimeConfig | None = None) -> SessionController:
    store = SQLiteStore(tmp_path / "inscription.db")
    repo = InscriptionRepository(store)
    repo.initialize()
    return SessionController(repository=repo, config=config or CaptureRuntimeConfig())


def test_start_pause_resume_stop_session(tmp_path):
    controller = make_controller(tmp_path)

    session = controller.start_session(app_version="0.1.0", title="Capture A")
    assert session.status == SessionStatus.RECORDING
    assert controller.snapshot.status == RecorderStatus.RECORDING

    controller.pause_session()
    assert controller.snapshot.status == RecorderStatus.PAUSED

    controller.resume_session()
    assert controller.snapshot.status == RecorderStatus.RECORDING

    final_session = controller.stop_session()
    assert final_session.status == SessionStatus.STOPPED
    assert controller.snapshot.status == RecorderStatus.STOPPED


def test_record_click_window_change_and_keyboard_event(tmp_path):
    controller = make_controller(tmp_path)
    controller.start_session(app_version="0.1.0")

    window_event = controller.record_window_change(window_title="Evidence Explorer", process_name="explorer.exe")
    click_event = controller.record_click(window_title="Evidence Explorer", cursor_x=100, cursor_y=200)
    key_event = controller.record_keyboard_milestone(input_subtype="ctrl_s", window_title="Evidence Explorer")
    controller.stop_session()

    repo = controller.repository
    events = repo.list_raw_events(controller.current_session.session_id)
    event_kinds = [event.event_kind for event in events]

    assert window_event.event_kind == EventKind.WINDOW_CHANGE
    assert click_event.event_kind == EventKind.MOUSE_CLICK
    assert key_event.event_kind == EventKind.KEYBOARD_MILESTONE
    assert EventKind.SESSION_START in event_kinds
    assert EventKind.SESSION_STOP in event_kinds
    assert controller.snapshot.event_count == len(events)


def test_record_manual_screenshot(tmp_path):
    controller = make_controller(tmp_path)
    controller.start_session(app_version="0.1.0")
    screenshot = controller.record_screenshot(capture_mode=CaptureMode.MANUAL, capture_scope=CaptureScope.WINDOW)

    assert screenshot.file_name.endswith(".png")
    assert controller.snapshot.screenshot_count == 1


def test_cannot_record_when_paused(tmp_path):
    controller = make_controller(tmp_path)
    controller.start_session(app_version="0.1.0")
    controller.pause_session()

    with pytest.raises(RuntimeError):
        controller.record_click(window_title="Paused Window", cursor_x=1, cursor_y=1)


def test_event_limit_enforced(tmp_path):
    config = CaptureRuntimeConfig(max_events_per_session=2)
    controller = make_controller(tmp_path, config=config)
    controller.start_session(app_version="0.1.0")

    controller.record_click(window_title="A", cursor_x=1, cursor_y=1)
    with pytest.raises(RuntimeError):
        controller.record_click(window_title="B", cursor_x=2, cursor_y=2)


def test_auto_screenshot_on_left_click(tmp_path):
    config = CaptureRuntimeConfig(auto_screenshots=True, screenshot_on_left_click=True)
    controller = make_controller(tmp_path, config=config)
    controller.start_session(app_version="0.1.0")
    click_event = controller.record_click(window_title="Auto Shot", cursor_x=10, cursor_y=10)

    screenshots = controller.repository.list_screenshots(controller.current_session.session_id)
    assert len(screenshots) == 1
    assert screenshots[0].source_event_id == click_event.event_id
