from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


@dataclass(slots=True, frozen=True)
class ScreenshotResult:
    file_path: str
    file_name: str
    image_width: int
    image_height: int
    image_format: str = "png"


class MouseEventProvider(Protocol):
    def start(self) -> None: ...
    def stop(self) -> None: ...
    def is_running(self) -> bool: ...


class KeyboardEventProvider(Protocol):
    def start(self) -> None: ...
    def stop(self) -> None: ...
    def is_running(self) -> bool: ...


class WindowFocusProvider(Protocol):
    def start(self) -> None: ...
    def stop(self) -> None: ...
    def is_running(self) -> bool: ...
    def get_active_window(self) -> dict[str, Any] | None: ...


class ScreenshotProvider(Protocol):
    def capture_window(self, *, destination_dir: str | Path, stem: str) -> ScreenshotResult: ...
    def capture_screen(self, *, destination_dir: str | Path, stem: str) -> ScreenshotResult: ...
    def capture_region(
        self,
        *,
        destination_dir: str | Path,
        stem: str,
        left: int,
        top: int,
        width: int,
        height: int,
    ) -> ScreenshotResult: ...


@dataclass(slots=True)
class _BaseProvider:
    _running: bool = False

    def start(self) -> None:
        self._running = True

    def stop(self) -> None:
        self._running = False

    def is_running(self) -> bool:
        return self._running


class NullMouseEventProvider(_BaseProvider):
    pass


class NullKeyboardEventProvider(_BaseProvider):
    pass


class NullWindowFocusProvider(_BaseProvider):
    def __init__(self, active_window: dict[str, Any] | None = None) -> None:
        super().__init__()
        self._active_window = active_window or {
            "window_title": None,
            "process_name": None,
            "process_id": None,
        }

    def get_active_window(self) -> dict[str, Any] | None:
        return self._active_window

    def set_active_window(
        self,
        *,
        window_title: str | None,
        process_name: str | None = None,
        process_id: int | None = None,
    ) -> None:
        self._active_window = {
            "window_title": window_title,
            "process_name": process_name,
            "process_id": process_id,
        }


@dataclass(slots=True)
class StubScreenshotProvider:
    default_width: int = 1280
    default_height: int = 720
    default_format: str = "png"

    def capture_window(self, *, destination_dir: str | Path, stem: str) -> ScreenshotResult:
        return self._make_result(destination_dir=destination_dir, stem=stem)

    def capture_screen(self, *, destination_dir: str | Path, stem: str) -> ScreenshotResult:
        return self._make_result(destination_dir=destination_dir, stem=stem)

    def capture_region(
        self,
        *,
        destination_dir: str | Path,
        stem: str,
        left: int,
        top: int,
        width: int,
        height: int,
    ) -> ScreenshotResult:
        return self._make_result(destination_dir=destination_dir, stem=stem, width=width, height=height)

    def _make_result(
        self,
        *,
        destination_dir: str | Path,
        stem: str,
        width: int | None = None,
        height: int | None = None,
    ) -> ScreenshotResult:
        destination_path = Path(destination_dir)
        destination_path.mkdir(parents=True, exist_ok=True)
        file_name = f"{stem}.{self.default_format}"
        file_path = destination_path / file_name
        file_path.write_bytes(b"stub-image")
        return ScreenshotResult(
            file_path=file_path.as_posix(),
            file_name=file_name,
            image_width=width or self.default_width,
            image_height=height or self.default_height,
            image_format=self.default_format,
        )