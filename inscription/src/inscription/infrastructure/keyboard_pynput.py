from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

from pynput import keyboard  # type: ignore[import-untyped]

from inscription.infrastructure.windows_adapters import KeyboardEventProvider


KeyboardMilestoneHandler = Callable[[str], None]


@dataclass(slots=True)
class PynputKeyboardEventProvider(KeyboardEventProvider):
    """
    Cross-platform keyboard event provider using pynput.

    This provider tracks modifier state and emits a constrained set of
    workflow-oriented milestone names instead of logging ordinary typing.
    """

    milestone_handler: KeyboardMilestoneHandler
    _listener: Optional[keyboard.Listener] = field(init=False, default=None)
    _running: bool = field(init=False, default=False)
    _pressed_keys: set[object] = field(init=False, default_factory=set)

    def start(self) -> None:
        if self._running:
            return

        def for_canonical(callback):
            return lambda key: callback(self._canonical(key))

        self._listener = keyboard.Listener(
            on_press=for_canonical(self._on_press),
            on_release=for_canonical(self._on_release),
        )
        self._listener.start()
        self._running = True

    def stop(self) -> None:
        if not self._running:
            return
        if self._listener is not None:
            self._listener.stop()
            self._listener = None
        self._pressed_keys.clear()
        self._running = False

    def is_running(self) -> bool:
        return self._running

    def _canonical(self, key):
        if self._listener is None:
            return key
        try:
            return self._listener.canonical(key)
        except Exception:
            return key

    def _on_press(self, key) -> None:
        if key in self._pressed_keys:
            return

        self._pressed_keys.add(key)
        milestone = self._map_pressed_key_to_milestone(key)
        if milestone is None:
            return

        try:
            self.milestone_handler(milestone)
        except Exception:
            pass

    def _on_release(self, key) -> None:
        self._pressed_keys.discard(key)

    def _map_pressed_key_to_milestone(self, key) -> str | None:
        ctrl = self._is_ctrl_pressed()
        alt = self._is_alt_pressed()
        shift = self._is_shift_pressed()

        if key == keyboard.Key.tab and alt:
            return "alt_tab"

        if key == keyboard.Key.enter:
            return "enter"
        if key == keyboard.Key.esc:
            return "escape"
        if key == keyboard.Key.delete:
            return "delete"
        if key == keyboard.Key.backspace:
            return "backspace"
        if key == keyboard.Key.tab:
            return "shift_tab" if shift else "tab"
        if key == keyboard.Key.f5:
            return "f5"

        char = self._key_char(key)
        if char is None:
            return None

        if ctrl:
            ctrl_map = {
                "a": "ctrl_a",
                "c": "ctrl_c",
                "f": "ctrl_f",
                "n": "ctrl_n",
                "o": "ctrl_o",
                "p": "ctrl_p",
                "s": "ctrl_s",
                "v": "ctrl_v",
                "x": "ctrl_x",
                "y": "ctrl_y",
                "z": "ctrl_z",
            }
            return ctrl_map.get(char)

        return None

    def _key_char(self, key) -> str | None:
        if isinstance(key, keyboard.KeyCode):
            try:
                if key.char is None:
                    return None
                return key.char.lower()
            except Exception:
                return None
        return None

    def _is_ctrl_pressed(self) -> bool:
        return any(
            key in self._pressed_keys
            for key in (keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r)
        )

    def _is_alt_pressed(self) -> bool:
        return any(
            key in self._pressed_keys
            for key in (keyboard.Key.alt, keyboard.Key.alt_l, keyboard.Key.alt_r)
        )

    def _is_shift_pressed(self) -> bool:
        return any(
            key in self._pressed_keys
            for key in (keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r)
        )