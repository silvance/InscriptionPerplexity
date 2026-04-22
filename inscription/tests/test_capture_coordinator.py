from pathlib import Path

from inscription.capture.coordinator import CaptureCoordinator
from inscription.capture.session_controller import SessionController
from inscription.infrastructure.windows_adapters import (
    NullKeyboardEventProvider,
    NullMouseEventProvider,
    NullWindowFocusProvider,
    StubScreenshotProvider,
)
from inscription.storage.repository import InscriptionRepository
from inscription.storage.sqlite_store import SQLiteStore


def make_coordinator(tmp_path: Path) -> CaptureCoordinator:
    store = SQLiteStore(tmp_path / "inscription.db")
    repo = InscriptionRepository(store)
    repo.initialize()

    controller = SessionController(repository=repo)
    return CaptureCoordinator(
        controller=controller,
        mouse_provider=NullMouseEventProvider(),
        keyboard_provider=NullKeyboardEventProvider(),
        window_provider=NullWindowFocusProvider(
            active_window={
                "window_title": "Inscription",
                "process_name": "inscription.exe",
                "process_id": 4444,
            }
        ),
        screenshot_provider=StubScreenshotProvider(),
        screenshot_root=tmp_path / "sessions",
    )


def test_start_and_stop_capture_toggles_providers(tmp_path):
    coordinator = make_coordinator(tmp_path)

    coordinator.start_capture(app_version="0.1.0", title="Coordinator Test")
    assert coordinator.mouse_provider.is_running() is True
    assert coordinator.keyboard_provider.is_running() is True
    assert coordinator.window_provider.is_running() is True

    session = coordinator.stop_capture()
    assert session is not None
    assert coordinator.mouse_provider.is_running() is False
    assert coordinator.keyboard_provider.is_running() is False
    assert coordinator.window_provider.is_running() is False


def test_ingest_click_and_window_change_persist_events(tmp_path):
    coordinator = make_coordinator(tmp_path)
    coordinator.start_capture(app_version="0.1.0")

    coordinator.ingest_window_change()
    coordinator.ingest_click(cursor_x=50, cursor_y=80)
    coordinator.ingest_keyboard_milestone(input_subtype="ctrl_s")
    coordinator.stop_capture()

    events = coordinator.controller.repository.list_raw_events(
        coordinator.controller.current_session.session_id
    )
    assert len(events) >= 5


def test_manual_window_screenshot_uses_stub_provider(tmp_path):
    coordinator = make_coordinator(tmp_path)
    coordinator.start_capture(app_version="0.1.0")

    screenshot = coordinator.capture_manual_window_screenshot()

    assert screenshot.file_name.endswith(".png")
    assert "screenshots" in screenshot.file_path