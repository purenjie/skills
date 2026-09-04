#!/usr/bin/env python3
"""Continuously collect Raycast Focus summaries from macOS Unified Log."""

from __future__ import annotations

import argparse
import json
import signal
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import IO, Sequence

import raycast_focus

STREAM_COMMAND = [
    raycast_focus.LOG_COMMAND,
    "stream",
    "--predicate",
    raycast_focus.LOG_PREDICATE,
    "--level",
    "info",
    "--style",
    "ndjson",
    "--type",
    "log",
]


def session_from_record(
    record: dict[str, object], fallback_goal: str | None = None
 ) -> raycast_focus.FocusSession | None:
    message = record.get("eventMessage")
    timestamp = record.get("timestamp")
    if not isinstance(message, str) or "Focus session activity summary" not in message:
        return None
    if not isinstance(timestamp, str):
        return None

    event_at = raycast_focus.parse_log_timestamp(timestamp)
    if event_at is None:
        return None
    synthetic_log = f"{timestamp} Raycast: [com.raycast.macos:focus] {message}"
    sessions = raycast_focus.parse_focus_log(
        synthetic_log,
        fallback_goal=fallback_goal if fallback_goal is not None else raycast_focus.read_last_focus_goal(),
        now=event_at,
    )
    return sessions[0] if sessions else None


def process_line(line: str, database: Path) -> bool:
    try:
        record = json.loads(line)
    except json.JSONDecodeError:
        return False
    if not isinstance(record, dict):
        return False

    summary = session_from_record(record)
    if summary is None:
        return False
    event_timestamp = record.get("timestamp")
    event_at = (
        raycast_focus.parse_log_timestamp(event_timestamp)
        if isinstance(event_timestamp, str)
        else None
    )
    pending_launch = raycast_focus.find_pending_focus_launch(
        summary.started_at, database, now=event_at
    )
    session = (
        session_from_record(record, fallback_goal=pending_launch.goal)
        if pending_launch
        else summary
    )
    assert session is not None
    raycast_focus.save_collected_session(session, database)
    if pending_launch:
        raycast_focus.discard_pending_focus_launch(pending_launch, database)
    print(
        f"captured {session.started_at.isoformat()} | {session.goal} | "
        f"{session.duration_minutes} minutes",
        flush=True,
    )
    return True


def process_stream(stream: IO[str], database: Path) -> int:
    captured = 0
    for line in stream:
        if process_line(line, database):
            captured += 1
    return captured


def backfill_recent(database: Path, minutes: int = 10) -> int:
    end = datetime.now().astimezone()
    start = end - timedelta(minutes=minutes)
    try:
        text = raycast_focus.read_unified_log(start, end, timeout=5)
    except RuntimeError as error:
        print(f"recent-log backfill failed: {error}", file=sys.stderr, flush=True)
        return 0
    sessions = raycast_focus.parse_focus_log(
        text,
        fallback_goal=raycast_focus.read_last_focus_goal(),
        now=end,
    )
    for session in sessions:
        raycast_focus.save_collected_session(session, database)
    if sessions:
        print(f"backfilled {len(sessions)} recent sessions", flush=True)
    return len(sessions)


def run_collector(database: Path) -> int:
    raycast_focus.initialize_collector_db(database)
    print(f"collector started | database={database}", flush=True)

    process: subprocess.Popen[str] | None = None

    def stop_collector(signum: int, _frame: object) -> None:
        print(f"collector stopping | signal={signum}", flush=True)
        if process and process.poll() is None:
            process.terminate()

    signal.signal(signal.SIGTERM, stop_collector)
    signal.signal(signal.SIGINT, stop_collector)

    process = subprocess.Popen(
        STREAM_COMMAND,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
    assert process.stdout is not None
    try:
        process_stream(process.stdout, database)
    finally:
        if process.poll() is None:
            process.terminate()
        try:
            _, stderr = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            _, stderr = process.communicate()
        if stderr.strip():
            print(stderr.strip(), file=sys.stderr, flush=True)
    return process.returncode or 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Continuously collect Raycast Focus sessions")
    parser.add_argument(
        "--database",
        type=Path,
        default=raycast_focus.COLLECTOR_DB_PATH,
        help="Collector SQLite database path",
    )
    parser.add_argument(
        "--stdin",
        action="store_true",
        help="Read NDJSON records from stdin instead of starting log stream",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    database = args.database.expanduser()
    raycast_focus.initialize_collector_db(database)
    if args.stdin:
        process_stream(sys.stdin, database)
        return 0
    return run_collector(database)


if __name__ == "__main__":
    raise SystemExit(main())
