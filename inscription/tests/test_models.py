from uuid import uuid4

import pytest
from pydantic import ValidationError

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
from inscription.domain.models import DraftStep, ExportDocument, RawEvent, ResolvedElement, ScreenshotArtifact, Session


def test_session_defaults():
    session = Session(app_version='0.1.0')
    assert session.status == SessionStatus.NEW
    assert session.step_count == 0


def test_raw_event_requires_positive_sequence():
    with pytest.raises(ValidationError):
        RawEvent(session_id=uuid4(), sequence_number=0, event_kind=EventKind.MOUSE_CLICK)


def test_resolved_element_failed_requires_reason():
    with pytest.raises(ValidationError):
        ResolvedElement(event_id=uuid4(), backend=ResolvedBackend.UIA, confidence_score=0.0, confidence_label=ConfidenceLabel.FAILED)


def test_screenshot_replaced_requires_replacement_id():
    with pytest.raises(ValidationError):
        ScreenshotArtifact(
            session_id=uuid4(),
            capture_mode=CaptureMode.AUTO,
            capture_scope=CaptureScope.WINDOW,
            file_path='shots/001.png',
            file_name='001.png',
            image_width=100,
            image_height=100,
            image_format='png',
            review_status=ScreenshotReviewStatus.REPLACED,
        )


def test_draft_step_user_created_sets_inserted_flag():
    step = DraftStep(
        session_id=uuid4(),
        ordinal=1,
        title='Add note',
        confidence_score=1.0,
        review_status=DraftStepReviewStatus.EDITED,
        created_by=CreatedBy.USER,
    )
    assert step.is_user_inserted is True


def test_export_document_requires_non_blank_fields():
    with pytest.raises(ValidationError):
        ExportDocument(session_id=uuid4(), format=' ', title='x', output_path='out.html', step_snapshot_json=[])
