from pathlib import Path
from uuid import uuid4

from inscription.domain.enums import CaptureMode, CaptureScope, ConfidenceLabel, EventKind, ResolvedBackend
from inscription.domain.models import DraftStep, ExportDocument, RawEvent, ResolvedElement, ScreenshotArtifact, Session
from inscription.storage.repository import InscriptionRepository
from inscription.storage.sqlite_store import SQLiteStore


def make_repo(tmp_path: Path) -> InscriptionRepository:
    store = SQLiteStore(tmp_path / "inscription.db")
    repo = InscriptionRepository(store)
    repo.initialize()
    return repo


def test_save_and_get_session(tmp_path):
    repo = make_repo(tmp_path)
    session = Session(app_version="0.1.0", title="Test Session")
    repo.save_session(session)

    loaded = repo.get_session(session.session_id)
    assert loaded is not None
    assert loaded.session_id == session.session_id
    assert loaded.title == "Test Session"


def test_save_and_list_raw_events(tmp_path):
    repo = make_repo(tmp_path)
    session = Session(app_version="0.1.0")
    repo.save_session(session)
    event = RawEvent(session_id=session.session_id, sequence_number=1, event_kind=EventKind.MOUSE_CLICK)
    repo.save_raw_event(event)

    events = repo.list_raw_events(session.session_id)
    assert len(events) == 1
    assert events[0].sequence_number == 1


def test_save_and_get_resolved_element(tmp_path):
    repo = make_repo(tmp_path)
    session = Session(app_version="0.1.0")
    repo.save_session(session)
    event = RawEvent(session_id=session.session_id, sequence_number=1, event_kind=EventKind.MOUSE_CLICK)
    repo.save_raw_event(event)
    resolved = ResolvedElement(
        event_id=event.event_id,
        backend=ResolvedBackend.UIA,
        control_name="Save",
        control_type="Button",
        confidence_score=0.95,
        confidence_label=ConfidenceLabel.HIGH,
    )
    repo.save_resolved_element(resolved)

    loaded = repo.get_resolved_element_by_event(event.event_id)
    assert loaded is not None
    assert loaded.control_name == "Save"


def test_save_screenshot_and_draft_step_and_export(tmp_path):
    repo = make_repo(tmp_path)
    session = Session(app_version="0.1.0")
    repo.save_session(session)
    event = RawEvent(session_id=session.session_id, sequence_number=1, event_kind=EventKind.MOUSE_CLICK)
    repo.save_raw_event(event)

    screenshot = ScreenshotArtifact(
        session_id=session.session_id,
        source_event_id=event.event_id,
        capture_mode=CaptureMode.AUTO,
        capture_scope=CaptureScope.WINDOW,
        file_path="shots/001.png",
        file_name="001.png",
        image_width=1280,
        image_height=720,
        image_format="png",
    )
    repo.save_screenshot(screenshot)

    step = DraftStep(
        session_id=session.session_id,
        ordinal=1,
        title="Click Save",
        primary_screenshot_id=screenshot.screenshot_id,
        source_event_ids_json=[event.event_id],
        confidence_score=0.95,
    )
    repo.save_draft_step(step)

    export = ExportDocument(
        session_id=session.session_id,
        format="html",
        title="Guide",
        output_path="exports/guide.html",
        step_snapshot_json=[{"ordinal": 1, "title": "Click Save"}],
    )
    repo.save_export_document(export)

    screenshots = repo.list_screenshots(session.session_id)
    steps = repo.list_draft_steps(session.session_id)
    exports = repo.list_export_documents(session.session_id)

    assert len(screenshots) == 1
    assert screenshots[0].file_name == "001.png"
    assert len(steps) == 1
    assert steps[0].title == "Click Save"
    assert len(exports) == 1
    assert exports[0].format == "html"


def test_foreign_keys_enforced(tmp_path):
    repo = make_repo(tmp_path)
    bogus_session_id = uuid4()
    event = RawEvent(session_id=bogus_session_id, sequence_number=1, event_kind=EventKind.MOUSE_CLICK)

    try:
        repo.save_raw_event(event)
        raised = False
    except Exception:
        raised = True

    assert raised is True
