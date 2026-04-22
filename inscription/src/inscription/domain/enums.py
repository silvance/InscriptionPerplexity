from enum import StrEnum


class SessionStatus(StrEnum):
    NEW = "new"
    RECORDING = "recording"
    PAUSED = "paused"
    STOPPED = "stopped"
    PROCESSED = "processed"
    EDITED = "edited"
    EXPORTED = "exported"


class EventKind(StrEnum):
    SESSION_START = "session_start"
    SESSION_PAUSE = "session_pause"
    SESSION_RESUME = "session_resume"
    SESSION_STOP = "session_stop"
    WINDOW_CHANGE = "window_change"
    MOUSE_CLICK = "mouse_click"
    KEYBOARD_MILESTONE = "keyboard_milestone"
    SCREENSHOT_TRIGGER = "screenshot_trigger"


class ResolvedBackend(StrEnum):
    UIA = "uia"
    WIN32 = "win32"
    FALLBACK = "fallback"


class ConfidenceLabel(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    FAILED = "failed"


class CaptureMode(StrEnum):
    AUTO = "auto"
    MANUAL = "manual"


class CaptureScope(StrEnum):
    WINDOW = "window"
    SCREEN = "screen"
    REGION = "region"


class ScreenshotReviewStatus(StrEnum):
    OK = "ok"
    NEEDS_REVIEW = "needs_review"
    REPLACED = "replaced"
    REMOVED = "removed"


class DraftStepReviewStatus(StrEnum):
    DRAFT = "draft"
    NEEDS_REVIEW = "needs_review"
    APPROVED = "approved"
    EDITED = "edited"


class CreatedBy(StrEnum):
    SYSTEM = "system"
    USER = "user"
