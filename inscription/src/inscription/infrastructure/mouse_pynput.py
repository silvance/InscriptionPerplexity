from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

from pynput import mouse  # type: ignore[import-untyped]

from inscription.infrastructure.windows_adapters import MouseEventProvider


MouseClickHandler = Callable[[int, int, str, bool], None]
"""
Signature: (x, y, button_name, pressed)

- x, y: cursor coordinates
- button_name: 'left', 'right', or 'middle'
- pressed: True on press, False on release
"""


@dataclass(slots=True)
class PynputMouseEventProvider(MouseEventProvider):
    """
    Cross-platform mouse event provider using pynput.

    This provider:
    - Starts a pynput.mouse.Listener in a background thread.
    - Invokes the configured handler on each click.
    - Tracks running state for coordination with CaptureCoordinator.
    """

    click_handler: MouseClickHandler
    _listener: Optional[mouse.Listener] = field(init=False, default=None)
    _running: bool = field(init=False, default=False)

    def start(self) -> None:
        if self._running:
            return

        def on_click(x: int, y: int, button, pressed: bool):
            # Map pynput button to a simple string
            if button == mouse.Button.left:
                name = "left"
            elif button == mouse.Button.right:
                name = "right"
            elif button == mouse.Button.middle:
                name = "middle"
            else:
                name = str(button)

            try:
                self.click_handler(x, y, name, pressed)
            except Exception:
                # Never let handler exceptions kill the listener thread
                pass

        self._listener = mouse.Listener(on_click=on_click)
        self._listener.start()
        self._running = True

    def stop(self) -> None:
        if not self._running:
            return
        if self._listener is not None:
            self._listener.stop()
            self._listener = None
        self._running = False

    def is_running(self) -> bool:
        return self._running