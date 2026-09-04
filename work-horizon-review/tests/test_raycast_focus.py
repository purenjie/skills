from __future__ import annotations

import importlib.util
import json
import sqlite3
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import parse_qs, urlparse

SCRIPT_PATH = Path(__file__).parents[1] / "scripts" / "raycast_focus.py"
FIXTURE_PATH = Path(__file__).parent / "fixtures" / "raycast-focus.log"

spec = importlib.util.spec_from_file_location("raycast_focus", SCRIPT_PATH)
assert spec and spec.loader
raycast_focus = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = raycast_focus
spec.loader.exec_module(raycast_focus)

COLLECTOR_PATH = Path(__file__).parents[1] / "scripts" / "raycast_focus_collector.py"
collector_spec = importlib.util.spec_from_file_location("raycast_focus_collector", COLLECTOR_PATH)
assert collector_spec and collector_spec.loader
raycast_focus_collector = importlib.util.module_from_spec(collector_spec)
sys.modules[collector_spec.name] = raycast_focus_collector
collector_spec.loader.exec_module(raycast_focus_collector)


class ParseFocusLogTests(unittest.TestCase):
    def test_parses_completed_sessions_and_ignores_incomplete_session(self) -> None:
        sessions = raycast_focus.parse_focus_log(FIXTURE_PATH.read_text(encoding="utf-8"))

        self.assertEqual(len(sessions), 2)
        first, second = sessions
        self.assertEqual(first.goal, "完成 SpaceToken API：正常路径, 异常路径")
        self.assertEqual(first.duration_minutes, 50)
        self.assertEqual(first.planned_seconds, 3000)
        self.assertEqual(first.pause_count, 1)
        self.assertEqual(first.block_count, 2)
        self.assertEqual(first.snooze_count, 0)
        self.assertEqual(first.source, "command")

        self.assertEqual(second.goal, "Ready Latency 假设验证")
        self.assertEqual(second.duration_minutes, 65)
        self.assertEqual(second.source, "deeplink")

    def test_summary_without_start_uses_unknown_goal(self) -> None:
        text = """2026-08-10 09:50:00.100000+0800 Raycast: [com.raycast.macos:focus] Focus session activity summary
	Start date: 2026-08-10 01:00:00 +0000
	Duration: 10m
"""
        sessions = raycast_focus.parse_focus_log(text)
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0].goal, "Focus（目标不可用）")
        self.assertEqual(sessions[0].duration_minutes, 10)

    def test_recent_summary_recovers_latest_goal_from_preferences(self) -> None:
        text = """2026-08-10 10:53:49.153037+0800 Raycast: [com.raycast.macos:focus] Focus session activity summary
	Start date: 2026-08-10 02:28:03 +0000
	Source: command
	Duration: 25 minutes
	Pauses Count: 0
	Block Events Count: 0
	Snooze Events Count: 0
"""
        now = datetime.fromisoformat("2026-08-10T10:55:00+08:00")
        sessions = raycast_focus.parse_focus_log(
            text, fallback_goal="tool_use 展示更多信息 + 时间", now=now
        )
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0].goal, "tool_use 展示更多信息 + 时间")
        self.assertEqual(sessions[0].duration_minutes, 25)
        self.assertEqual(sessions[0].pause_count, 0)

    def test_duration_formats(self) -> None:
        self.assertEqual(raycast_focus.parse_duration_minutes("10m"), 10)
        self.assertEqual(raycast_focus.parse_duration_minutes("2 minutes"), 2)
        self.assertEqual(raycast_focus.parse_duration_minutes("1h 5m"), 65)
        self.assertEqual(raycast_focus.parse_duration_minutes(""), 0)
        self.assertIsNone(raycast_focus.parse_duration_minutes("unknown"))


class DatabaseTests(unittest.TestCase):
    def test_validates_and_reads_focus_stats_database(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sessions.db"
            with sqlite3.connect(path) as connection:
                connection.execute(
                    "CREATE TABLE sessions (id INTEGER PRIMARY KEY, goal TEXT, duration INTEGER, timestamp INTEGER)"
                )
                started = datetime.now().astimezone().replace(microsecond=0)
                connection.execute(
                    "INSERT INTO sessions(goal, duration, timestamp) VALUES (?, ?, ?)",
                    ("战略下注", 50, int(started.timestamp() * 1000)),
                )

            self.assertTrue(raycast_focus.validate_focus_stats_db(path))
            sessions = raycast_focus.read_database_sessions(
                path, started - timedelta(minutes=1), started + timedelta(minutes=1)
            )
            self.assertEqual(len(sessions), 1)
            self.assertEqual(sessions[0].goal, "战略下注")
            self.assertEqual(sessions[0].duration_minutes, 50)
            self.assertEqual(sessions[0].backend, "focus-stats-db")

    def test_rejects_incompatible_database(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sessions.db"
            with sqlite3.connect(path) as connection:
                connection.execute("CREATE TABLE sessions (id INTEGER PRIMARY KEY, title TEXT)")
            self.assertFalse(raycast_focus.validate_focus_stats_db(path))


class JournalAndReportTests(unittest.TestCase):
    def test_reads_active_anchor(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "journal.md"
            path.write_text(
                "# 今日锚点\n\n- 主动推进：完成 SpaceToken API 的端到端闭环。\n",
                encoding="utf-8",
            )
            self.assertEqual(
                raycast_focus.read_active_anchor(path),
                "完成 SpaceToken API 的端到端闭环。",
            )

    def test_rejects_empty_anchor(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "journal.md"
            path.write_text("- 主动推进：\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                raycast_focus.read_active_anchor(path)

    def test_reads_latest_weekly_anchor(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "weekly.md"
            path.write_text(
                "### 周一\n- 主动推进：旧目标\n\n### 周二\n- 主动推进：当前目标\n",
                encoding="utf-8",
            )
            self.assertEqual(raycast_focus.read_active_anchor(path), "当前目标")

    def test_resolves_current_iso_week_note(self) -> None:
        date = datetime.fromisoformat("2026-09-04T09:00:00+08:00")
        with tempfile.TemporaryDirectory() as directory:
            path = raycast_focus.weekly_note_path_for(date, Path(directory))
            self.assertEqual(
                path,
                Path(directory) / "2026" / "周复盘" / "2026-W36｜08-31～09-06.md",
            )

    def test_deeplink_encodes_goal_and_duration(self) -> None:
        url = raycast_focus.focus_deeplink("Ready Latency 假设", 50, "block")
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        self.assertEqual(parsed.scheme, "raycast")
        self.assertEqual(parsed.netloc, "focus")
        self.assertEqual(parsed.path, "/start")
        self.assertEqual(query["goal"], ["Ready Latency 假设"])
        self.assertEqual(query["duration"], ["3000"])
        self.assertEqual(query["mode"], ["block"])

    def test_markdown_report_groups_goals(self) -> None:
        now = datetime.now().astimezone()
        sessions = [
            raycast_focus.FocusSession("A", 25, now, "fixture"),
            raycast_focus.FocusSession("A", 50, now, "fixture"),
            raycast_focus.FocusSession("B", 30, now, "fixture"),
        ]
        report = raycast_focus.markdown_report(sessions, "今日", "fixture")
        self.assertIn("总时长：105 分钟", report)
        self.assertIn("A：75 分钟 / 2 次", report)
        self.assertIn("B：30 分钟 / 1 次", report)

    def test_empty_report_does_not_claim_no_work(self) -> None:
        report = raycast_focus.markdown_report([], "本周", "unified-log")
        self.assertIn("数据为空不代表没有投入", report)


class CollectorTests(unittest.TestCase):
    def test_summary_record_is_persisted_and_deduplicated(self) -> None:
        record = {
            "timestamp": "2026-08-10 11:31:02.102199+0800",
            "eventMessage": (
                "Focus session activity summary\n"
                "\tStart date: 2026-08-10 03:05:59 +0000\n"
                "\tSource: command\n"
                "\tDuration: 25 minutes\n"
                "\tPauses Count: 0\n"
                "\tBlock Events Count: 0\n"
                "\tSnooze Events Count: 0"
            ),
        }
        original = raycast_focus.read_last_focus_goal
        raycast_focus.read_last_focus_goal = lambda: "tool_use 展示更多信息 + 时间"
        try:
            session = raycast_focus_collector.session_from_record(record)
        finally:
            raycast_focus.read_last_focus_goal = original
        self.assertIsNotNone(session)
        assert session is not None
        self.assertEqual(session.goal, "tool_use 展示更多信息 + 时间")
        self.assertEqual(session.duration_minutes, 25)

        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "collector.db"
            raycast_focus.save_collected_session(session, database)
            raycast_focus.save_collected_session(session, database)
            sessions = raycast_focus.read_collector_sessions(
                database,
                datetime.fromisoformat("2026-08-10T11:00:00+08:00"),
                datetime.fromisoformat("2026-08-10T12:00:00+08:00"),
            )
            self.assertEqual(len(sessions), 1)
            self.assertEqual(sessions[0].backend, "local-collector")
            self.assertEqual(sessions[0].pause_count, 0)

class PendingLaunchTests(unittest.TestCase):
    def test_collector_prefers_matching_pending_launch_goal(self) -> None:
        started = datetime.fromisoformat("2026-08-10T11:05:59+08:00")
        record = {
            "timestamp": "2026-08-10 11:31:02.102199+0800",
            "eventMessage": (
                "Focus session activity summary\n"
                "\tStart date: 2026-08-10 03:05:59 +0000\n"
                "\tSource: deeplink\n"
                "\tDuration: 25 minutes\n"
                "\tPauses Count: 0\n"
                "\tBlock Events Count: 0\n"
                "\tSnooze Events Count: 0"
            ),
        }
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "collector.db"
            raycast_focus.record_pending_focus_launch(
                "验证 Sandbox Ready Latency 瓶颈", 25, started, database
            )
            self.assertTrue(raycast_focus_collector.process_line(json.dumps(record), database))

            sessions = raycast_focus.read_collector_sessions(
                database,
                started - timedelta(minutes=1),
                started + timedelta(minutes=1),
            )
            self.assertEqual(len(sessions), 1)
            self.assertEqual(sessions[0].goal, "验证 Sandbox Ready Latency 瓶颈")
            self.assertIsNone(raycast_focus.find_pending_focus_launch(started, database))

    def test_pending_launch_only_matches_a_nearby_start_time(self) -> None:
        started = datetime.fromisoformat("2026-08-10T11:05:59+08:00")
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "collector.db"
            launch = raycast_focus.record_pending_focus_launch(
                "SeaTalk 限流", 25, started, database
            )
            matched = raycast_focus.find_pending_focus_launch(
                started + timedelta(minutes=4), database, now=started + timedelta(minutes=25)
            )
            self.assertEqual(matched, launch)
            self.assertIsNone(
                raycast_focus.find_pending_focus_launch(
                started + timedelta(minutes=6), database, now=started + timedelta(minutes=25)
                )
            )

if __name__ == "__main__":
    unittest.main()
