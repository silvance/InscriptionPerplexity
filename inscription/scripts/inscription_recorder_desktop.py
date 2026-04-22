from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from inscription.capture import CaptureCoordinator, CaptureRuntimeConfig, SessionController
from inscription.infrastructure import (
    NullKeyboardEventProvider,
    NullMouseEventProvider,
    NullWindowFocusProvider,
    StubScreenshotProvider,
)
from inscription.storage.repository import InscriptionRepository
from inscription.storage.sqlite_store import SQLiteStore


def has_module(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def build_repository(db_path: Path) -> InscriptionRepository:
    store = SQLiteStore(db_path)
    repo = InscriptionRepository(store)
    repo.initialize()
    return repo


def build_controller(base_dir: Path) -> SessionController:
    repo = build_repository(base_dir / "inscription.db")
    config = CaptureRuntimeConfig(
        auto_screenshots=True,
        screenshot_on_left_click=True,
        screenshot_scope_window=True,
        screenshot_scope_screen=False,
    )
    return SessionController(repository=repo, config=config)


def build_desktop_coordinator(base_dir: Path) -> CaptureCoordinator:
    controller = build_controller(base_dir)
    sessions_root = base_dir / "sessions"

    window_provider = NullWindowFocusProvider()
    screenshot_provider = StubScreenshotProvider()
    mouse_provider = NullMouseEventProvider()
    keyboard_provider = NullKeyboardEventProvider()

    coordinator = CaptureCoordinator(
        controller=controller,
        mouse_provider=mouse_provider,
        keyboard_provider=keyboard_provider,
        window_provider=window_provider,
        screenshot_provider=screenshot_provider,
        screenshot_root=sessions_root,
    )

    if has_module("pynput"):
        from inscription.infrastructure.keyboard_pynput import PynputKeyboardEventProvider
        from inscription.infrastructure.mouse_pynput import PynputMouseEventProvider

        def handle_click(x: int, y: int, button_name: str, pressed: bool) -> None:
            if not pressed:
                return
            if button_name != "left":
                return
            try:
                coordinator.ingest_click(cursor_x=x, cursor_y=y, button="left_click")
                coordinator.maybe_auto_screenshot_after_click()
            except Exception:
                pass

        def handle_keyboard_milestone(name: str) -> None:
            try:
                coordinator.ingest_keyboard_milestone(input_subtype=name)
            except Exception:
                pass

        coordinator.mouse_provider = PynputMouseEventProvider(click_handler=handle_click)
        coordinator.keyboard_provider = PynputKeyboardEventProvider(
            milestone_handler=handle_keyboard_milestone
        )

    if sys.platform.startswith("win"):
        if has_module("mss"):
            from inscription.infrastructure.windows_screenshot import WindowsMssScreenshotProvider

            coordinator.screenshot_provider = WindowsMssScreenshotProvider()

        if has_module("win32gui") and has_module("win32process") and has_module("psutil"):
            from inscription.infrastructure.windows_window_focus import (
                WindowsForegroundWindowFocusProvider,
            )

            coordinator.window_provider = WindowsForegroundWindowFocusProvider()

    return coordinator


def main() -> None:
    base_dir = Path.cwd()
    coordinator = build_desktop_coordinator(base_dir)

    print("Inscription desktop recorder")
    print("============================")
    print(f"Working directory: {base_dir}")
    print()

    using_real_mouse = coordinator.mouse_provider.__class__.__name__ != "NullMouseEventProvider"
    using_real_keyboard = coordinator.keyboard_provider.__class__.__name__ != "NullKeyboardEventProvider"
    using_real_window = coordinator.window_provider.__class__.__name__ != "NullWindowFocusProvider"
    using_real_screenshot = coordinator.screenshot_provider.__class__.__name__ != "StubScreenshotProvider"

    print(f"Mouse provider:      {coordinator.mouse_provider.__class__.__name__}")
    print(f"Keyboard provider:   {coordinator.keyboard_provider.__class__.__name__}")
    print(f"Window provider:     {coordinator.window_provider.__class__.__name__}")
    print(f"Screenshot provider: {coordinator.screenshot_provider.__class__.__name__}")
    print()

    if not using_real_mouse and not using_real_keyboard:
        print("pynput not available, so desktop input capture is running in fallback mode.")
    if sys.platform.startswith("win") and not using_real_window:
        print("Windows window-focus integrations are unavailable; using fallback provider.")
    if sys.platform.startswith("win") and not using_real_screenshot:
        print("Windows screenshot integrations are unavailable; using stub screenshots.")

    print()
    print("Starting capture session...")
    coordinator.start_capture(app_version="0.1.0", title="Desktop Session")
    print("Capture is running.")
    print("Use the desktop normally, then press Enter in this console to stop.")
    print()

    try:
        input(">> ")
    except KeyboardInterrupt:
        print("\nInterrupted by user (Ctrl+C).")
    finally:
        print("Stopping capture session...")
        session = coordinator.stop_capture()

    if session is None:
        print("No session was active.")
        return

    repo = coordinator.controller.repository
    events = repo.list_raw_events(session.session_id)
    screenshots = repo.list_screenshots(session.session_id)

    print()
    print(f"Session ID:   {session.session_id}")
    print(f"Title:        {session.title or '(none)'}")
    print(f"Raw events:   {len(events)}")
    print(f"Screenshots:  {len(screenshots)}")
    print()
    print("Done.")


if __name__ == "__main__":
    main()