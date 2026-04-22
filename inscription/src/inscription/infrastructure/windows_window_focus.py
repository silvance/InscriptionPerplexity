from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import sys

from inscription.infrastructure.windows_adapters import WindowFocusProvider

if sys.platform.startswith("win"):
    import psutil  # type: ignore[import-untyped]
    import win32gui  # type: ignore[import-untyped]
    import win32process  # type: ignore[import-untyped]
else:  # pragma: no cover
    psutil = None  # type: ignore[assignment]
    win32gui = None  # type: ignore[assignment]
    win32process = None  # type: ignore[assignment]


@dataclass(slots=True)
class WindowsForegroundWindowFocusProvider(WindowFocusProvider):
    """
    WindowFocusProvider for Windows using pywin32 and psutil.

    On non-Windows platforms this provider will start but get_active_window()
    will always return None.
    """

    _running: bool = False

    def start(self) -> None:
        self._running = True

    def stop(self) -> None:
        self._running = False

    def is_running(self) -> bool:
        return self._running

    def get_active_window(self) -> dict[str, Any] | None:
        if not self._running:
            return None
        if not sys.platform.startswith("win") or win32gui is None:
            return None

        try:
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                return None

            title = win32gui.GetWindowText(hwnd) or None
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            proc_name: str | None = None
            if pid and psutil is not None:
                try:
                    proc = psutil.Process(pid)
                    proc_name = proc.name()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    proc_name = None

            return {
                "window_title": title,
                "process_name": proc_name,
                "process_id": int(pid) if pid else None,
            }
        except Exception:
            return None