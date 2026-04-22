from __future__ import annotations

import sys
import time
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


def build_repository(db_path: Path) -> InscriptionRepository:
    store = SQLiteStore(db_path)
    repo = InscriptionRepository(store)
    repo.initialize()
    return repo


def build_coordinator(base_dir: Path) -> CaptureCoordinator:
    db_path = base_dir / "inscription.db"
    sessions_root = base_dir / "sessions"

    repo = build_repository(db_path)
    controller = SessionController(repository=repo, config=CaptureRuntimeConfig())

    # For now, we wire only the null/stub providers so this script is safe
    # to run on any platform. We will introduce platform-aware real providers
    # (pynput + Windows adapters) in a Windows-specific harness.
    mouse_provider = NullMouseEventProvider()
    keyboard_provider = NullKeyboardEventProvider()
    window_provider = NullWindowFocusProvider()
    screenshot_provider = StubScreenshotProvider()

    coordinator = CaptureCoordinator(
        controller=controller,
        mouse_provider=mouse_provider,
        keyboard_provider=keyboard_provider,
        window_provider=window_provider,
        screenshot_provider=screenshot_provider,
        screenshot_root=sessions_root,
    )
    return coordinator


def main() -> None:
    """
    Minimal interactive harness for Inscription capture.

    - Starts a new session.
    - Waits until the user presses Enter in this console.
    - Stops the session and prints a brief summary.

    On Windows you will later swap in real providers for mouse/keyboard,
    active window, and screenshots. This script focuses on wiring and flow.
    """
    base_dir = Path.cwd()
    coordinator = build_coordinator(base_dir)

    print("Inscription recorder")
    print("====================")
    print(f"Working directory: {base_dir}")
    print()
    print("Starting capture session...")
    coordinator.start_capture(app_version="0.1.0", title="Interactive Session")

    print("Capture is running with null/stub providers.")
    print("Press Enter in this console to stop the session.")
    print()

    try:
        # Simple blocking wait; real UI will replace this later.
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
    print(f"Session ID: {session.session_id}")
    print(f"Title:      {session.title or '(none)'}")
    print(f"Events:     {len(events)}")
    print(f"Screenshots:{len(screenshots)}")
    print()
    print("Done.")


if __name__ == "__main__":
    if sys.platform.startswith("linux") or sys.platform.startswith("win"):
        main()
    else:
        print("Inscription recorder harness is not supported on this platform yet.")