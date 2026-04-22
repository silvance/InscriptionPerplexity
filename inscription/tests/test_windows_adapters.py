from inscription.infrastructure.windows_adapters import (
    NullKeyboardEventProvider,
    NullMouseEventProvider,
    NullWindowFocusProvider,
    StubScreenshotProvider,
)


def test_null_providers_toggle_running_state():
    mouse = NullMouseEventProvider()
    keyboard = NullKeyboardEventProvider()
    window = NullWindowFocusProvider()

    assert mouse.is_running() is False
    assert keyboard.is_running() is False
    assert window.is_running() is False

    mouse.start()
    keyboard.start()
    window.start()

    assert mouse.is_running() is True
    assert keyboard.is_running() is True
    assert window.is_running() is True

    mouse.stop()
    keyboard.stop()
    window.stop()

    assert mouse.is_running() is False
    assert keyboard.is_running() is False
    assert window.is_running() is False


def test_null_window_focus_provider_returns_window_payload():
    provider = NullWindowFocusProvider(active_window={
        "window_title": "Inscription",
        "process_name": "inscription.exe",
        "process_id": 4242,
    })
    payload = provider.get_active_window()

    assert payload["window_title"] == "Inscription"
    assert payload["process_name"] == "inscription.exe"
    assert payload["process_id"] == 4242


def test_stub_screenshot_provider_creates_placeholder_file(tmp_path):
    provider = StubScreenshotProvider(default_width=1440, default_height=900)
    result = provider.capture_window(destination_dir=tmp_path / "shots", stem="shot-0001")

    assert result.file_name == "shot-0001.png"
    assert result.image_width == 1440
    assert result.image_height == 900
    assert (tmp_path / "shots" / "shot-0001.png").exists()


def test_stub_screenshot_provider_region_uses_requested_dimensions(tmp_path):
    provider = StubScreenshotProvider()
    result = provider.capture_region(
        destination_dir=tmp_path / "shots",
        stem="region-0001",
        left=10,
        top=20,
        width=320,
        height=240,
    )

    assert result.image_width == 320
    assert result.image_height == 240
