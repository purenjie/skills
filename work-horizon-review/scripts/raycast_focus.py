#!/usr/bin/env python3
"""Read and start Raycast Focus sessions for the work-horizon-review skill.

The Unified Log parser is based on the MIT-licensed Raycast Focus Stats extension:
https://github.com/raycast/extensions/tree/dc8eb2b1efb00f6d5e1e65981801a44225ac88af/extensions/raycast-focus-stats
"""

from __future__ import annotations

import argparse
import json
import plistlib
import re
import sqlite3
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable, Sequence
from urllib.parse import urlencode

RAYCAST_APP = Path("/Applications/Raycast.app")
RAYCAST_EXTENSIONS_DIR = (
    Path.home() / "Library" / "Application Support" / "com.raycast.macos" / "extensions"
)
COLLECTOR_SUPPORT_DIR = Path.home() / "Library" / "Application Support" / "work-horizon-review"
COLLECTOR_DB_PATH = COLLECTOR_SUPPORT_DIR / "raycast-focus-sessions.db"
DEFAULT_WEEKLY_ROOT = Path.home() / "Documents" / "KnowledgeBase" / "03-work-records"
LOG_COMMAND = "/usr/bin/log"
LOG_PREDICATE = 'subsystem == "com.raycast.macos" AND category == "focus"'
TIMESTAMP_RE = re.compile(
    r"^(?P<stamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(?:\.\d+)?(?:[+-]\d{4})?)"
)


@dataclass(frozen=True)
class FocusSession:
    goal: str
    duration_minutes: int
    started_at: datetime
    backend: str
    planned_seconds: int | None = None
    pause_count: int | None = None
    block_count: int | None = None
    snooze_count: int | None = None
    source: str | None = None

    def as_json(self) -> dict[str, object]:
        data = asdict(self)
        data["started_at"] = self.started_at.astimezone().isoformat()
        return data


@dataclass(frozen=True)
class PendingFocusLaunch:
    goal: str
    duration_minutes: int
    launched_at: datetime

def parse_cli_datetime(value: str) -> datetime:
    """Parse a local YYYY-MM-DD or YYYY-MM-DD HH:MM:SS value."""
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S"):
        try:
            parsed = datetime.strptime(value, fmt)
            return parsed.astimezone()
        except ValueError:
            continue
    raise argparse.ArgumentTypeError(f"Unsupported date: {value}")


def parse_log_timestamp(line: str) -> datetime | None:
    match = TIMESTAMP_RE.match(line)
    if not match:
        return None
    stamp = match.group("stamp")
    formats = (
        "%Y-%m-%d %H:%M:%S.%f%z",
        "%Y-%m-%d %H:%M:%S%z",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
    )
    for fmt in formats:
        try:
            parsed = datetime.strptime(stamp, fmt)
            return parsed.astimezone() if parsed.tzinfo else parsed.astimezone()
        except ValueError:
            continue
    return None


def parse_summary_start(value: str) -> datetime | None:
    value = value.strip()
    for fmt in ("%Y-%m-%d %H:%M:%S %z", "%Y-%m-%d %H:%M:%S"):
        try:
            parsed = datetime.strptime(value, fmt)
            return parsed.astimezone() if parsed.tzinfo else parsed.astimezone()
        except ValueError:
            continue
    return None


def parse_duration_minutes(value: str) -> int | None:
    """Parse Raycast summary durations such as 10m, 2 minutes, or 1h 5m."""
    value = value.strip().lower()
    if not value:
        return 0

    hours = re.search(r"(\d+)\s*(?:h|hour|hours)\b", value)
    minutes = re.search(r"(\d+)\s*(?:m|min|mins|minute|minutes)\b", value)
    if hours or minutes:
        return (int(hours.group(1)) * 60 if hours else 0) + (int(minutes.group(1)) if minutes else 0)

    plain_number = re.fullmatch(r"\d+", value)
    return int(value) if plain_number else None


def parse_int_field(value: str) -> int | None:
    match = re.search(r"-?\d+", value)
    return int(match.group()) if match else None


def _nearest_unused_start(
    starts: list[dict[str, object]], summary_start: datetime | None, used: set[int]
) -> int | None:
    candidates = [index for index in range(len(starts)) if index not in used]
    if not candidates:
        return None
    if summary_start is None:
        return candidates[0]

    def distance(index: int) -> float:
        started_at = starts[index]["started_at"]
        assert isinstance(started_at, datetime)
        return abs((started_at - summary_start).total_seconds())

    nearest = min(candidates, key=distance)
    return nearest if distance(nearest) <= 5 else candidates[0]


def parse_focus_log(
    text: str, fallback_goal: str | None = None, now: datetime | None = None
) -> list[FocusSession]:
    """Parse Raycast Focus events, recovering the latest goal from preferences when needed."""
    starts: list[dict[str, object]] = []
    summaries: list[dict[str, object]] = []
    current_start: dict[str, object] | None = None
    current_summary: dict[str, object] | None = None

    def flush_start() -> None:
        nonlocal current_start
        if current_start and current_start.get("goal"):
            starts.append(current_start)
        current_start = None

    def flush_summary() -> None:
        nonlocal current_summary
        if current_summary and "duration_minutes" in current_summary:
            summaries.append(current_summary)
        current_summary = None

    for line in text.splitlines():
        stripped = line.strip()
        timestamp = parse_log_timestamp(line)

        if "Start focus session" in line:
            flush_start()
            flush_summary()
            current_start = {
                "started_at": timestamp or datetime.now().astimezone(),
                "goal": "",
                "planned_seconds": None,
            }
            continue

        if "Focus session activity summary" in line:
            flush_start()
            flush_summary()
            current_summary = {
                "event_at": timestamp,
                "started_at": None,
                "duration_minutes": 0,
                "pause_count": None,
                "block_count": None,
                "snooze_count": None,
                "source": None,
            }
            continue

        if timestamp and (current_start or current_summary):
            flush_start()
            flush_summary()

        if current_start is not None:
            if stripped.startswith("Goal:"):
                current_start["goal"] = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("Duration:"):
                current_start["planned_seconds"] = parse_int_field(stripped.split(":", 1)[1])
            continue

        if current_summary is not None:
            if stripped.startswith("Start date:"):
                current_summary["started_at"] = parse_summary_start(stripped.split(":", 1)[1])
            elif stripped.startswith("Source:"):
                current_summary["source"] = stripped.split(":", 1)[1].strip() or None
            elif stripped.startswith("Duration:"):
                duration = parse_duration_minutes(stripped.split(":", 1)[1])
                current_summary["duration_minutes"] = duration if duration is not None else 0
            elif stripped.startswith("Pauses Count:"):
                current_summary["pause_count"] = parse_int_field(stripped.split(":", 1)[1])
            elif stripped.startswith("Block Events Count:"):
                current_summary["block_count"] = parse_int_field(stripped.split(":", 1)[1])
            elif stripped.startswith("Snooze Events Count:"):
                current_summary["snooze_count"] = parse_int_field(stripped.split(":", 1)[1])

    flush_start()
    flush_summary()

    sessions: list[FocusSession] = []
    used_starts: set[int] = set()
    now = now or datetime.now().astimezone()
    summary_event_times = [
        value
        for summary in summaries
        if isinstance((value := summary.get("event_at")), datetime)
    ]
    latest_summary_event = max(summary_event_times) if summary_event_times else None

    for summary in summaries:
        summary_start = summary.get("started_at")
        index = _nearest_unused_start(
            starts,
            summary_start if isinstance(summary_start, datetime) else None,
            used_starts,
        )

        planned_seconds: int | None = None
        if index is not None:
            used_starts.add(index)
            start = starts[index]
            goal = str(start["goal"]).strip()
            started_at = start["started_at"]
            planned_seconds = start.get("planned_seconds")  # type: ignore[assignment]
        else:
            event_at = summary.get("event_at")
            started_at = summary_start if isinstance(summary_start, datetime) else event_at
            if not isinstance(started_at, datetime):
                continue
            is_latest_recent_summary = (
                fallback_goal is not None
                and isinstance(event_at, datetime)
                and event_at == latest_summary_event
                and abs((now - event_at).total_seconds()) <= 15 * 60
            )
            goal = fallback_goal.strip() if is_latest_recent_summary else "Focus（目标不可用）"

        if not goal or not isinstance(started_at, datetime):
            continue
        sessions.append(
            FocusSession(
                goal=goal,
                duration_minutes=int(summary.get("duration_minutes") or 0),
                started_at=started_at,
                planned_seconds=planned_seconds,
                pause_count=summary.get("pause_count"),  # type: ignore[arg-type]
                block_count=summary.get("block_count"),  # type: ignore[arg-type]
                snooze_count=summary.get("snooze_count"),  # type: ignore[arg-type]
                source=summary.get("source"),  # type: ignore[arg-type]
                backend="unified-log",
            )
        )
    return sessions


def initialize_collector_db(path: Path = COLLECTOR_DB_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                started_at_ms INTEGER PRIMARY KEY,
                goal TEXT NOT NULL,
                duration INTEGER NOT NULL,
                pause_count INTEGER,
                block_count INTEGER,
                snooze_count INTEGER,
                source TEXT,
                captured_at_ms INTEGER NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS pending_launches (
                launched_at_ms INTEGER PRIMARY KEY,
                goal TEXT NOT NULL,
                duration INTEGER NOT NULL,
                expires_at_ms INTEGER NOT NULL
            )
            """
        )
    return path


def validate_collector_db(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        with sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=2) as connection:
            columns = {row[1] for row in connection.execute("PRAGMA table_info(sessions)").fetchall()}
        return {
            "started_at_ms",
            "goal",
            "duration",
            "pause_count",
            "block_count",
            "snooze_count",
            "source",
            "captured_at_ms",
        }.issubset(columns)
    except (sqlite3.Error, OSError):
        return False


def save_collected_session(session: FocusSession, path: Path = COLLECTOR_DB_PATH) -> None:
    initialize_collector_db(path)
    with sqlite3.connect(path, timeout=5) as connection:
        connection.execute(
            """
            INSERT INTO sessions(
                started_at_ms, goal, duration, pause_count, block_count, snooze_count, source, captured_at_ms
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(started_at_ms) DO UPDATE SET
                goal = excluded.goal,
                duration = excluded.duration,
                pause_count = excluded.pause_count,
                block_count = excluded.block_count,
                snooze_count = excluded.snooze_count,
                source = excluded.source,
                captured_at_ms = excluded.captured_at_ms
            """,
            (
                int(session.started_at.timestamp() * 1000),
                session.goal,
                session.duration_minutes,
                session.pause_count,
                session.block_count,
                session.snooze_count,
                session.source,
                int(datetime.now().astimezone().timestamp() * 1000),
            ),
        )

def record_pending_focus_launch(
    goal: str,
    duration_minutes: int,
    started_at: datetime | None = None,
    path: Path = COLLECTOR_DB_PATH,
 ) -> PendingFocusLaunch:
    """Persist a launch so a summary-only Raycast event retains its intended goal."""
    launched_at = (started_at or datetime.now().astimezone()).astimezone()
    launched_at_ms = int(launched_at.timestamp() * 1000)
    expires_at_ms = launched_at_ms + (duration_minutes + 15) * 60 * 1000
    initialize_collector_db(path)
    with sqlite3.connect(path, timeout=5) as connection:
        connection.execute(
            "DELETE FROM pending_launches WHERE expires_at_ms < ?",
            (launched_at_ms,),
        )
        connection.execute(
            """
            INSERT INTO pending_launches(launched_at_ms, goal, duration, expires_at_ms)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(launched_at_ms) DO UPDATE SET
                goal = excluded.goal,
                duration = excluded.duration,
                expires_at_ms = excluded.expires_at_ms
            """,
            (launched_at_ms, goal, duration_minutes, expires_at_ms),
        )
    return PendingFocusLaunch(goal, duration_minutes, launched_at)


def find_pending_focus_launch(
    started_at: datetime,
    path: Path = COLLECTOR_DB_PATH,
    now: datetime | None = None,
    tolerance: timedelta = timedelta(minutes=5),
 ) -> PendingFocusLaunch | None:
    """Return the nearest unexpired CLI launch whose start time matches a Raycast summary."""
    if not path.exists():
        return None
    reference_ms = int(started_at.timestamp() * 1000)
    now_ms = int((now or datetime.now().astimezone()).timestamp() * 1000)
    tolerance_ms = int(tolerance.total_seconds() * 1000)
    try:
        with sqlite3.connect(path, timeout=5) as connection:
            connection.execute(
                "DELETE FROM pending_launches WHERE expires_at_ms < ?",
                (now_ms,),
            )
            rows = connection.execute(
                """
                SELECT launched_at_ms, goal, duration
                FROM pending_launches
                WHERE launched_at_ms BETWEEN ? AND ?
                ORDER BY ABS(launched_at_ms - ?)
                LIMIT 1
                """,
                (reference_ms - tolerance_ms, reference_ms + tolerance_ms, reference_ms),
            ).fetchall()
    except sqlite3.Error:
        return None
    if not rows:
        return None
    launched_at_ms, goal, duration = rows[0]
    return PendingFocusLaunch(
        goal=str(goal),
        duration_minutes=int(duration),
        launched_at=datetime.fromtimestamp(int(launched_at_ms) / 1000).astimezone(),
    )


def discard_pending_focus_launch(
    launch: PendingFocusLaunch, path: Path = COLLECTOR_DB_PATH
 ) -> None:
    if not path.exists():
        return
    launched_at_ms = int(launch.launched_at.timestamp() * 1000)
    with sqlite3.connect(path, timeout=5) as connection:
        connection.execute(
            "DELETE FROM pending_launches WHERE launched_at_ms = ?",
            (launched_at_ms,),
        )

def read_collector_sessions(path: Path, start: datetime, end: datetime) -> list[FocusSession]:
    start_ms = int(start.timestamp() * 1000)
    end_ms = int(end.timestamp() * 1000)
    with sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=5) as connection:
        rows = connection.execute(
            """
            SELECT goal, duration, started_at_ms, pause_count, block_count, snooze_count, source
            FROM sessions
            WHERE started_at_ms >= ? AND started_at_ms < ?
            ORDER BY started_at_ms
            """,
            (start_ms, end_ms),
        ).fetchall()
    return [
        FocusSession(
            goal=str(goal),
            duration_minutes=int(duration),
            started_at=datetime.fromtimestamp(int(started_at_ms) / 1000).astimezone(),
            pause_count=pause_count,
            block_count=block_count,
            snooze_count=snooze_count,
            source=source,
            backend="local-collector",
        )
        for goal, duration, started_at_ms, pause_count, block_count, snooze_count, source in rows
    ]


def validate_focus_stats_db(path: Path) -> bool:
    try:
        uri = f"file:{path}?mode=ro"
        with sqlite3.connect(uri, uri=True, timeout=2) as connection:
            columns = {
                row[1]
                for row in connection.execute("PRAGMA table_info(sessions)").fetchall()
            }
        return {"goal", "duration", "timestamp"}.issubset(columns)
    except (sqlite3.Error, OSError):
        return False


def find_focus_stats_db() -> Path | None:
    if not RAYCAST_EXTENSIONS_DIR.exists():
        return None
    candidates = sorted(
        RAYCAST_EXTENSIONS_DIR.glob("**/sessions.db"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    return next((path for path in candidates if validate_focus_stats_db(path)), None)


def read_database_sessions(path: Path, start: datetime, end: datetime) -> list[FocusSession]:
    start_ms = int(start.timestamp() * 1000)
    end_ms = int(end.timestamp() * 1000)
    uri = f"file:{path}?mode=ro"
    with sqlite3.connect(uri, uri=True, timeout=5) as connection:
        rows = connection.execute(
            """
            SELECT goal, duration, timestamp
            FROM sessions
            WHERE timestamp >= ? AND timestamp < ?
            ORDER BY timestamp
            """,
            (start_ms, end_ms),
        ).fetchall()
    return [
        FocusSession(
            goal=str(goal),
            duration_minutes=int(duration),
            started_at=datetime.fromtimestamp(int(timestamp) / 1000).astimezone(),
            backend="focus-stats-db",
        )
        for goal, duration, timestamp in rows
    ]


def read_unified_log(start: datetime, end: datetime, timeout: int = 20) -> str:
    command = [
        LOG_COMMAND,
        "show",
        "--predicate",
        LOG_PREDICATE,
        "--info",
        "--start",
        start.strftime("%Y-%m-%d %H:%M:%S"),
        "--end",
        end.strftime("%Y-%m-%d %H:%M:%S"),
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
    except subprocess.TimeoutExpired as error:
        raise RuntimeError(f"log show timed out after {timeout} seconds") from error
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"log show exited with {result.returncode}")
    return result.stdout


def read_last_focus_goal() -> str | None:
    """Read the latest Focus title saved by Raycast Preferences."""
    result = subprocess.run(
        ["defaults", "export", "com.raycast.macos", "-"],
        capture_output=True,
        timeout=5,
        check=False,
    )
    if result.returncode != 0 or not result.stdout:
        return None
    try:
        preferences = plistlib.loads(result.stdout)
    except (plistlib.InvalidFileException, ValueError):
        return None
    goal = preferences.get("raycast-startFocusSession-title")
    return goal.strip() if isinstance(goal, str) and goal.strip() else None


def load_sessions(start: datetime, end: datetime) -> tuple[list[FocusSession], str, str | None]:
    if validate_collector_db(COLLECTOR_DB_PATH):
        return (
            read_collector_sessions(COLLECTOR_DB_PATH, start, end),
            "local-collector",
            str(COLLECTOR_DB_PATH),
        )
    database = find_focus_stats_db()
    if database:
        return read_database_sessions(database, start, end), "focus-stats-db", str(database)
    log_end = min(end, datetime.now().astimezone())
    log_text = read_unified_log(start, log_end)
    fallback_goal = read_last_focus_goal()
    sessions = [
        session
        for session in parse_focus_log(log_text, fallback_goal=fallback_goal)
        if start <= session.started_at < end
    ]
    return sessions, "unified-log", None


def date_range_from_args(args: argparse.Namespace) -> tuple[datetime, datetime, str]:
    now = datetime.now().astimezone()
    if args.today:
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return start, start + timedelta(days=1), "今日"
    if args.week:
        start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        return start, start + timedelta(days=7), "本周"
    if args.from_date:
        start = args.from_date
        end = args.to_date or now
        if len(getattr(args, "to_raw", "") or "") == 10:
            end += timedelta(days=1)
        if end <= start:
            raise ValueError("--to must be after --from")
        return start, end, f"{start.date()}～{end.date()}"
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return start, start + timedelta(days=1), "今日"


def markdown_report(sessions: Sequence[FocusSession], title: str, backend: str) -> str:
    total = sum(session.duration_minutes for session in sessions)
    by_goal: dict[str, list[FocusSession]] = {}
    for session in sessions:
        by_goal.setdefault(session.goal, []).append(session)

    lines = [f"## {title} Focus", "", f"- 数据源：{backend}"]
    if not sessions:
        lines.extend(
            [
                "- 状态：没有读取到 Focus Session",
                "- 注意：数据为空不代表没有投入，可能是插件未同步或系统日志已被清理。",
            ]
        )
        return "\n".join(lines)

    lines.extend([f"- 总时长：{total} 分钟", f"- Session：{len(sessions)} 次", "", "### 按目标", ""])
    for goal, grouped in sorted(
        by_goal.items(), key=lambda item: sum(session.duration_minutes for session in item[1]), reverse=True
    ):
        duration = sum(session.duration_minutes for session in grouped)
        lines.append(f"- {goal}：{duration} 分钟 / {len(grouped)} 次")
    return "\n".join(lines)


def command_report(args: argparse.Namespace) -> int:
    try:
        start, end, title = date_range_from_args(args)
        sessions, backend, database = load_sessions(start, end)
    except (RuntimeError, sqlite3.Error, ValueError) as error:
        print(f"Failed to read Raycast Focus sessions: {error}", file=sys.stderr)
        return 1

    if args.format == "json":
        payload = {
            "period": {"start": start.isoformat(), "end": end.isoformat(), "title": title},
            "backend": backend,
            "database": database,
            "total_minutes": sum(session.duration_minutes for session in sessions),
            "session_count": len(sessions),
            "sessions": [session.as_json() for session in sessions],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(markdown_report(sessions, title, backend))
    return 0


def weekly_note_path_for(date: datetime, weekly_root: Path = DEFAULT_WEEKLY_ROOT) -> Path:
    iso_year, iso_week, iso_weekday = date.isocalendar()
    monday = date - timedelta(days=iso_weekday - 1)
    sunday = monday + timedelta(days=6)
    filename = f"{iso_year}-W{iso_week:02d}｜{monday:%m-%d}～{sunday:%m-%d}.md"
    return weekly_root / str(iso_year) / "周复盘" / filename


def read_active_anchor(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Weekly note not found: {path}")
    anchors: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^\s*-\s*主动推进：\s*(.+?)\s*$", line)
        if match and match.group(1).strip():
            anchors.append(match.group(1).strip())
    if anchors:
        return anchors[-1]
    raise ValueError(f"No non-empty 主动推进 item found in {path}")


def focus_deeplink(goal: str, minutes: int, mode: str) -> str:
    query = urlencode({"goal": goal, "duration": minutes * 60, "mode": mode})
    return f"raycast://focus/start?{query}"


def launch_focus(goal: str, minutes: int, mode: str, dry_run: bool) -> int:
    if minutes < 1 or minutes > 24 * 60:
        print("Focus duration must be between 1 and 1440 minutes", file=sys.stderr)
        return 2
    url = focus_deeplink(goal, minutes, mode)
    print(f"Goal: {goal}")
    print(f"Duration: {minutes} minutes")
    print(f"Deeplink: {url}")
    if dry_run:
        return 0
    pending_launch = record_pending_focus_launch(goal, minutes)
    result = subprocess.run(["open", url], check=False)
    if result.returncode != 0:
        discard_pending_focus_launch(pending_launch)
    return result.returncode


def command_start(args: argparse.Namespace) -> int:
    return launch_focus(args.goal, args.minutes, args.mode, args.dry_run)


def command_start_from_journal(args: argparse.Namespace) -> int:
    path = (
        Path(args.journal).expanduser()
        if args.journal
        else weekly_note_path_for(datetime.now().astimezone())
    )
    try:
        goal = read_active_anchor(path)
    except (FileNotFoundError, ValueError, OSError) as error:
        print(str(error), file=sys.stderr)
        return 1
    print(f"Weekly note: {path}")
    return launch_focus(goal, args.minutes, args.mode, args.dry_run)


def command_doctor(_: argparse.Namespace) -> int:
    print(f"Raycast: {'installed' if RAYCAST_APP.exists() else 'not found'}")
    print(f"Unified Log: {'available' if Path(LOG_COMMAND).exists() else 'not found'}")
    if validate_collector_db(COLLECTOR_DB_PATH):
        try:
            with sqlite3.connect(f"file:{COLLECTOR_DB_PATH}?mode=ro", uri=True, timeout=5) as connection:
                count = int(connection.execute("SELECT COUNT(*) FROM sessions").fetchone()[0])
                latest = connection.execute(
                    "SELECT goal, duration, started_at_ms FROM sessions ORDER BY started_at_ms DESC LIMIT 1"
                ).fetchone()
            print(f"Local Collector DB: {COLLECTOR_DB_PATH}")
            print(f"Collected sessions: {count}")
            if latest:
                goal, duration, started_at_ms = latest
                started = datetime.fromtimestamp(int(started_at_ms) / 1000).astimezone()
                print(f"Latest session: {started.isoformat()} | {goal} | {duration} minutes")
            print("Backend: local-collector")
            return 0
        except sqlite3.Error as error:
            print(f"Local Collector DB: unreadable ({error})")
    else:
        print("Local Collector DB: not found")
    database = find_focus_stats_db()
    if database:
        try:
            uri = f"file:{database}?mode=ro"
            with sqlite3.connect(uri, uri=True, timeout=5) as connection:
                count = int(connection.execute("SELECT COUNT(*) FROM sessions").fetchone()[0])
                latest = connection.execute(
                    "SELECT goal, duration, timestamp FROM sessions ORDER BY timestamp DESC LIMIT 1"
                ).fetchone()
            print(f"Focus Stats DB: {database}")
            print("Schema: valid")
            print(f"Sessions: {count}")
            if latest:
                goal, duration, timestamp = latest
                started = datetime.fromtimestamp(int(timestamp) / 1000).astimezone()
                print(f"Latest session: {started.isoformat()} | {goal} | {duration} minutes")
            print("Backend: focus-stats-db")
            return 0
        except sqlite3.Error as error:
            print(f"Focus Stats DB: unreadable ({error})")

    print("Focus Stats DB: not found")
    if not Path(LOG_COMMAND).exists():
        print("Backend: unavailable")
        return 1
    try:
        end = datetime.now().astimezone()
        start = end - timedelta(hours=24)
        sessions = parse_focus_log(read_unified_log(start, end))
        print(f"Recent completed sessions: {len(sessions)}")
        print("Backend: unified-log")
        print("History warning: only retained system logs can be read")
        return 0
    except RuntimeError as error:
        print(f"Unified Log read failed: {error}")
        print("Backend: unavailable")
        return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read and start Raycast Focus sessions")
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor = subparsers.add_parser("doctor", help="Check Raycast Focus data sources")
    doctor.set_defaults(func=command_doctor)

    report = subparsers.add_parser("report", help="Report Focus sessions")
    period = report.add_mutually_exclusive_group()
    period.add_argument("--today", action="store_true", help="Report today's sessions")
    period.add_argument("--week", action="store_true", help="Report the current ISO week's sessions")
    period.add_argument("--from", dest="from_raw", help="Start date (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)")
    report.add_argument("--to", dest="to_raw", help="End date (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)")
    report.add_argument("--format", choices=("markdown", "json"), default="markdown")
    report.set_defaults(func=command_report)

    start = subparsers.add_parser("start", help="Start a Raycast Focus session")
    start.add_argument("--goal", required=True)
    start.add_argument("--minutes", type=int, default=50)
    start.add_argument("--mode", choices=("block", "allow"), default="block")
    start.add_argument("--dry-run", action="store_true")
    start.set_defaults(func=command_start)

    journal = subparsers.add_parser("start-from-journal", help="Start Focus using the latest weekly-note 主动推进 item")
    journal.add_argument("--journal", help="Override weekly note path")
    journal.add_argument("--minutes", type=int, default=50)
    journal.add_argument("--mode", choices=("block", "allow"), default="block")
    journal.add_argument("--dry-run", action="store_true")
    journal.set_defaults(func=command_start_from_journal)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "from_raw", None):
        args.from_date = parse_cli_datetime(args.from_raw)
        args.to_date = parse_cli_datetime(args.to_raw) if args.to_raw else None
    elif getattr(args, "to_raw", None):
        parser.error("--to requires --from")
    else:
        args.from_date = None
        args.to_date = None
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
