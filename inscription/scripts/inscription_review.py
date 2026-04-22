from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from typing import Iterable

from inscription.storage.repository import InscriptionRepository
from inscription.storage.sqlite_store import SQLiteStore


def build_repository(db_path: Path) -> InscriptionRepository:
    store = SQLiteStore(db_path)
    repo = InscriptionRepository(store)
    repo.initialize()
    return repo


def format_dt(value) -> str:
    if value is None:
        return "-"
    if isinstance(value, datetime):
        return value.isoformat(timespec="seconds")
    return str(value)


def print_table(headers: list[str], rows: Iterable[list[object]]) -> None:
    rows = [list(map(lambda v: "" if v is None else str(v), row)) for row in rows]
    widths = [len(h) for h in headers]

    for row in rows:
        for idx, value in enumerate(row):
            widths[idx] = max(widths[idx], len(value))

    header_line = "  ".join(h.ljust(widths[idx]) for idx, h in enumerate(headers))
    divider_line = "  ".join("-" * widths[idx] for idx in range(len(headers)))

    print(header_line)
    print(divider_line)

    for row in rows:
        print("  ".join(value.ljust(widths[idx]) for idx, value in enumerate(row)))


def cmd_sessions(args: argparse.Namespace) -> int:
    repo = build_repository(Path(args.db))
    sessions = repo.list_sessions(limit=args.limit)

    if not sessions:
        print("No sessions found.")
        return 0

    rows = []
    for session in sessions:
        rows.append(
            [
                str(session.session_id),
                session.title or "-",
                session.status,
                session.raw_event_count,
                session.screenshot_count,
                format_dt(session.recording_started_at_utc),
                format_dt(session.recording_stopped_at_utc),
            ]
        )

    print_table(
        [
            "session_id",
            "title",
            "status",
            "events",
            "screenshots",
            "started",
            "stopped",
        ],
        rows,
    )
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    repo = build_repository(Path(args.db))
    session_id = args.session_id

    session = repo.get_session(session_id)
    if session is None:
        print(f"Session not found: {session_id}")
        return 1

    print("Session")
    print("-------")
    print(f"Session ID:   {session.session_id}")
    print(f"Title:        {session.title or '-'}")
    print(f"Status:       {session.status}")
    print(f"Started:      {format_dt(session.recording_started_at_utc)}")
    print(f"Stopped:      {format_dt(session.recording_stopped_at_utc)}")
    print(f"Raw events:   {session.raw_event_count}")
    print(f"Screenshots:  {session.screenshot_count}")
    print()

    events = repo.list_raw_events(session.session_id)
    screenshots = repo.list_screenshots(session.session_id)

    if args.include_events:
        print("Events")
        print("------")
        if not events:
            print("No events.")
        else:
            rows = []
            for event in events[: args.event_limit]:
                rows.append(
                    [
                        event.sequence_number,
                        event.event_kind,
                        event.input_subtype or "-",
                        event.active_window_title or "-",
                        format_dt(event.timestamp_utc),
                        f"{event.cursor_x},{event.cursor_y}"
                        if event.cursor_x is not None and event.cursor_y is not None
                        else "-",
                    ]
                )
            print_table(
                ["seq", "kind", "subtype", "window", "timestamp", "cursor"],
                rows,
            )
        print()

    if args.include_screenshots:
        print("Screenshots")
        print("-----------")
        if not screenshots:
            print("No screenshots.")
        else:
            rows = []
            for shot in screenshots[: args.screenshot_limit]:
                rows.append(
                    [
                        str(shot.screenshot_id),
                        shot.capture_mode,
                        shot.capture_scope,
                        shot.file_name,
                        shot.file_path,
                        format_dt(shot.captured_at_utc),
                    ]
                )
            print_table(
                ["screenshot_id", "mode", "scope", "file_name", "file_path", "captured"],
                rows,
            )

    return 0


def cmd_events(args: argparse.Namespace) -> int:
    repo = build_repository(Path(args.db))
    session = repo.get_session(args.session_id)
    if session is None:
        print(f"Session not found: {args.session_id}")
        return 1

    events = repo.list_raw_events(session.session_id)
    if not events:
        print("No events found.")
        return 0

    rows = []
    for event in events[: args.limit]:
        rows.append(
            [
                event.sequence_number,
                event.event_kind,
                event.input_subtype or "-",
                event.active_window_title or "-",
                event.process_name or "-",
                format_dt(event.timestamp_utc),
            ]
        )

    print_table(
        ["seq", "kind", "subtype", "window", "process", "timestamp"],
        rows,
    )
    return 0


def cmd_screenshots(args: argparse.Namespace) -> int:
    repo = build_repository(Path(args.db))
    session = repo.get_session(args.session_id)
    if session is None:
        print(f"Session not found: {args.session_id}")
        return 1

    screenshots = repo.list_screenshots(session.session_id)
    if not screenshots:
        print("No screenshots found.")
        return 0

    rows = []
    for shot in screenshots[: args.limit]:
        rows.append(
            [
                str(shot.screenshot_id),
                shot.capture_mode,
                shot.capture_scope,
                shot.file_name,
                shot.file_path,
                format_dt(shot.captured_at_utc),
            ]
        )

    print_table(
        ["screenshot_id", "mode", "scope", "file_name", "file_path", "captured"],
        rows,
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="inscription-review",
        description="Review Inscription capture sessions from the command line.",
    )
    parser.add_argument(
        "--db",
        default="inscription.db",
        help="Path to the Inscription SQLite database (default: inscription.db)",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    sessions_parser = subparsers.add_parser("sessions", help="List recent sessions")
    sessions_parser.add_argument("--limit", type=int, default=10, help="Max sessions to show")
    sessions_parser.set_defaults(func=cmd_sessions)

    show_parser = subparsers.add_parser("show", help="Show a session summary")
    show_parser.add_argument("session_id", help="Session UUID")
    show_parser.add_argument("--include-events", action="store_true", help="Show session events")
    show_parser.add_argument(
        "--include-screenshots",
        action="store_true",
        help="Show screenshot records for the session",
    )
    show_parser.add_argument("--event-limit", type=int, default=25, help="Max events to show")
    show_parser.add_argument(
        "--screenshot-limit",
        type=int,
        default=25,
        help="Max screenshots to show",
    )
    show_parser.set_defaults(func=cmd_show)

    events_parser = subparsers.add_parser("events", help="List events for a session")
    events_parser.add_argument("session_id", help="Session UUID")
    events_parser.add_argument("--limit", type=int, default=100, help="Max events to show")
    events_parser.set_defaults(func=cmd_events)

    screenshots_parser = subparsers.add_parser("screenshots", help="List screenshots for a session")
    screenshots_parser.add_argument("session_id", help="Session UUID")
    screenshots_parser.add_argument("--limit", type=int, default=100, help="Max screenshots to show")
    screenshots_parser.set_defaults(func=cmd_screenshots)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return 