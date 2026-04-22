from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RecorderStatus(StrEnum):
    IDLE = "idle"
    RECORDING = "recording"
    PAUSED = "paused"
    STOPPED = "stopped"


class CaptureRuntimeConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    auto_screenshots: bool = True
    allow_manual_screenshots: bool = True
    capture_keyboard_milestones: bool = True
    capture_window_changes: bool = True
    suppress_mouse_move_noise: bool = True
    screenshot_on_left_click: bool = False
    max_events_per_session: int = 100_000


class RecordingSessionSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    session_id: UUID
    status: RecorderStatus
    started_at_utc: datetime | None = None
    stopped_at_utc: datetime | None = None
    paused_at_utc: datetime | None = None
    resumed_at_utc: datetime | None = None
    event_count: int = 0
    screenshot_count: int = 0
    draft_step_count: int = 0
    title: str | None = None
    current_window_title: str | None = None
