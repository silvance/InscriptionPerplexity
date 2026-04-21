from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from inscription.domain.enums import (
    CaptureMode,
    CaptureScope,
    ConfidenceLabel,
    CreatedBy,
    DraftStepReviewStatus,
    EventKind,
    ResolvedBackend,
    ScreenshotReviewStatus,
    SessionStatus,
)
from inscription.utils.time import utc_now


class InscriptionModel(BaseModel):
    model_config = ConfigDict(validate_assignment=True, extra='forbid')


class Session(InscriptionModel):
    session_id: UUID = Field(default_factory=uuid4)
    created_at_utc: datetime = Field(default_factory=utc_now)
    updated_at_utc: datetime = Field(default_factory=utc_now)
    recording_started_at_utc: datetime | None = None
    recording_stopped_at_utc: datetime | None = None
    status: SessionStatus = SessionStatus.NEW
    title: str | None = None
    guide_title: str | None = None
    source_machine_name: str | None = None
    source_user_name: str | None = None
    os_version: str | None = None
    app_version: str
    notes: str | None = None
    step_count: int = 0
    raw_event_count: int = 0
    screenshot_count: int = 0
    primary_export_document_id: UUID | None = None
    settings_snapshot_json: dict[str, Any] | None = None

    @field_validator('step_count', 'raw_event_count', 'screenshot_count')
    @classmethod
    def non_negative_counts(cls, value: int) -> int:
        if value < 0:
            raise ValueError('counts must be non-negative')
        return value

    @model_validator(mode='after')
    def validate_recording_order(self) -> 'Session':
        if self.recording_started_at_utc and self.recording_stopped_at_utc:
            if self.recording_stopped_at_utc < self.recording_started_at_utc:
                raise ValueError('recording_stopped_at_utc cannot be before recording_started_at_utc')
        if self.updated_at_utc < self.created_at_utc:
            raise ValueError('updated_at_utc cannot be before created_at_utc')
        return self


class RawEvent(InscriptionModel):
    event_id: UUID = Field(default_factory=uuid4)
    session_id: UUID
    sequence_number: int
    timestamp_utc: datetime = Field(default_factory=utc_now)
    event_kind: EventKind
    input_subtype: str | None = None
    cursor_x: int | None = None
    cursor_y: int | None = None
    screen_index: int | None = None
    active_window_title: str | None = None
    active_window_handle: str | None = None
    process_name: str | None = None
    process_id: int | None = None
    executable_path: str | None = None
    correlation_id: UUID | None = None
    resolution_id: UUID | None = None
    screenshot_id: UUID | None = None
    is_noise_candidate: bool = False
    raw_payload_json: dict[str, Any] | None = None

    @field_validator('sequence_number')
    @classmethod
    def positive_sequence(cls, value: int) -> int:
        if value < 1:
            raise ValueError('sequence_number must be >= 1')
        return value

    @field_validator('process_id', 'screen_index')
    @classmethod
    def optional_non_negative(cls, value: int | None) -> int | None:
        if value is not None and value < 0:
            raise ValueError('value must be non-negative')
        return value


class ResolvedElement(InscriptionModel):
    resolution_id: UUID = Field(default_factory=uuid4)
    event_id: UUID
    resolved_at_utc: datetime = Field(default_factory=utc_now)
    backend: ResolvedBackend
    window_title: str | None = None
    window_class_name: str | None = None
    control_name: str | None = None
    control_type: str | None = None
    localized_control_type: str | None = None
    automation_id: str | None = None
    framework_id: str | None = None
    runtime_id: list[int] | None = None
    bounding_rect_json: dict[str, int] | None = None
    parent_chain_summary: str | None = None
    supported_patterns_json: list[str] | None = None
    confidence_score: float = 0.0
    confidence_label: ConfidenceLabel = ConfidenceLabel.FAILED
    failure_reason: str | None = None
    diagnostic_payload_json: dict[str, Any] | None = None

    @field_validator('confidence_score')
    @classmethod
    def confidence_range(cls, value: float) -> float:
        if not 0.0 <= value <= 1.0:
            raise ValueError('confidence_score must be between 0.0 and 1.0')
        return value

    @model_validator(mode='after')
    def validate_confidence(self) -> 'ResolvedElement':
        if self.confidence_label == ConfidenceLabel.FAILED and not self.failure_reason:
            raise ValueError('failure_reason is required when confidence_label is failed')
        return self


class ScreenshotArtifact(InscriptionModel):
    screenshot_id: UUID = Field(default_factory=uuid4)
    session_id: UUID
    captured_at_utc: datetime = Field(default_factory=utc_now)
    capture_mode: CaptureMode
    capture_scope: CaptureScope
    source_event_id: UUID | None = None
    file_path: str
    file_name: str
    image_width: int
    image_height: int
    image_format: str
    sha256: str | None = None
    review_status: ScreenshotReviewStatus = ScreenshotReviewStatus.OK
    replacement_screenshot_id: UUID | None = None
    crop_rect_json: dict[str, int] | None = None
    notes: str | None = None

    @field_validator('image_width', 'image_height')
    @classmethod
    def positive_dimensions(cls, value: int) -> int:
        if value <= 0:
            raise ValueError('image dimensions must be > 0')
        return value

    @field_validator('file_path')
    @classmethod
    def non_empty_path(cls, value: str) -> str:
        if not value.strip():
            raise ValueError('file_path cannot be empty')
        return value

    @model_validator(mode='after')
    def validate_replacement(self) -> 'ScreenshotArtifact':
        if self.review_status == ScreenshotReviewStatus.REPLACED and not self.replacement_screenshot_id:
            raise ValueError('replacement_screenshot_id is required when review_status is replaced')
        if Path(self.file_name).name != self.file_name:
            raise ValueError('file_name must not include directory separators')
        return self


class DraftStep(InscriptionModel):
    step_id: UUID = Field(default_factory=uuid4)
    session_id: UUID
    ordinal: int
    title: str
    body: str | None = None
    primary_screenshot_id: UUID | None = None
    source_event_ids_json: list[UUID] = Field(default_factory=list)
    source_resolution_ids_json: list[UUID] | None = None
    generation_strategy: str | None = None
    confidence_score: float = 0.0
    review_status: DraftStepReviewStatus = DraftStepReviewStatus.DRAFT
    created_by: CreatedBy = CreatedBy.SYSTEM
    edited_by_user: bool = False
    is_user_inserted: bool = False
    is_deleted: bool = False
    annotation_json: dict[str, Any] | None = None
    created_at_utc: datetime = Field(default_factory=utc_now)
    updated_at_utc: datetime = Field(default_factory=utc_now)

    @field_validator('ordinal')
    @classmethod
    def positive_ordinal(cls, value: int) -> int:
        if value < 1:
            raise ValueError('ordinal must be >= 1')
        return value

    @field_validator('title')
    @classmethod
    def non_blank_title(cls, value: str) -> str:
        if not value.strip():
            raise ValueError('title cannot be blank')
        return value.strip()

    @field_validator('confidence_score')
    @classmethod
    def step_confidence_range(cls, value: float) -> float:
        if not 0.0 <= value <= 1.0:
            raise ValueError('confidence_score must be between 0.0 and 1.0')
        return value

    @model_validator(mode='after')
    def validate_step_state(self) -> 'DraftStep':
        if self.updated_at_utc < self.created_at_utc:
            raise ValueError('updated_at_utc cannot be before created_at_utc')
        if self.created_by == CreatedBy.USER and not self.is_user_inserted and not self.edited_by_user:
            self.is_user_inserted = True
        return self


class ExportDocument(InscriptionModel):
    export_document_id: UUID = Field(default_factory=uuid4)
    session_id: UUID
    format: str
    created_at_utc: datetime = Field(default_factory=utc_now)
    title: str
    output_path: str
    template_version: str | None = None
    export_options_json: dict[str, Any] | None = None
    step_snapshot_json: list[dict[str, Any]]
    sha256: str | None = None

    @field_validator('format', 'title', 'output_path')
    @classmethod
    def non_blank_strings(cls, value: str) -> str:
        if not value.strip():
            raise ValueError('field cannot be blank')
        return value.strip()
