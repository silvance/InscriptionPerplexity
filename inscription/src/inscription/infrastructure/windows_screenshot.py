from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import mss  # type: ignore[import-untyped]

from inscription.infrastructure.windows_adapters import ScreenshotProvider, ScreenshotResult


@dataclass(slots=True)
class WindowsMssScreenshotProvider(ScreenshotProvider):
    """
    Real screenshot provider for Windows using the mss library.

    - capture_screen: grabs the primary monitor (index 1 in mss.monitors).
    - capture_window: currently implemented as a screen capture; can be
      refined later to use a window bounding box if you pass coords in.
    - capture_region: grabs an arbitrary rectangle.
    """

    default_monitor_index: int = 1  # mss.monitors[1] is usually the primary monitor

    def capture_window(self, *, destination_dir: str | Path, stem: str) -> ScreenshotResult:
        # For now treat "window" as the primary monitor; later we can supply
        # a bounding rect based on the active window.
        return self._capture_monitor(
            monitors=[self.default_monitor_index],
            destination_dir=destination_dir,
            stem=stem,
        )

    def capture_screen(self, *, destination_dir: str | Path, stem: str) -> ScreenshotResult:
        # Screen = primary monitor for now; mss.monitors[0] is "all monitors".
        return self._capture_monitor(
            monitors=[self.default_monitor_index],
            destination_dir=destination_dir,
            stem=stem,
        )

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
        destination_dir = Path(destination_dir)
        destination_dir.mkdir(parents=True, exist_ok=True)
        file_name = f"{stem}.png"
        file_path = destination_dir / file_name

        with mss.mss() as sct:
            monitor = {"left": left, "top": top, "width": width, "height": height}
            sct_img = sct.grab(monitor)
            mss.tools.to_png(sct_img.rgb, sct_img.size, output=str(file_path))  # type: ignore[attr-defined]

        return ScreenshotResult(
            file_path=file_path.as_posix(),
            file_name=file_name,
            image_width=width,
            image_height=height,
            image_format="png",
        )

    def _capture_monitor(
        self,
        *,
        monitors: Iterable[int],
        destination_dir: str | Path,
        stem: str,
    ) -> ScreenshotResult:
        destination_dir = Path(destination_dir)
        destination_dir.mkdir(parents=True, exist_ok=True)

        with mss.mss() as sct:
            monitor_index = next(iter(monitors))
            monitor = sct.monitors[monitor_index]
            file_name = f"{stem}.png"
            file_path = destination_dir / file_name
            sct_img = sct.grab(monitor)
            mss.tools.to_png(sct_img.rgb, sct_img.size, output=str(file_path))  # type: ignore[attr-defined]

            width = monitor["width"]
            height = monitor["height"]

        return ScreenshotResult(
            file_path=file_path.as_posix(),
            file_name=file_name,
            image_width=width,
            image_height=height,
            image_format="png",
        )