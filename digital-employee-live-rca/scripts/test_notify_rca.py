#!/usr/bin/env python3

import argparse
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import notify_rca


def render_args(**overrides):
    values = {
        "status": "confirmed",
        "question": "为什么任务失败？",
        "identifier": ["task_id=TASK-1", "run_id=RUN-1"],
        "conclusion": "Runner 启动失败。",
        "reason": "sandbox bootstrap timeout",
        "boundary": "Runner worker bootstrap",
        "evidence": [
            "10:00 / runner / marker-a / task_id=TASK-1 / started",
            "10:01 / runner / marker-b / reason=timeout / rejected",
            "10:02 / gateway / marker-c / status=failed / visible failure",
            "10:03 / runner / marker-d / unrelated / ignored",
        ],
        "duration": "42s",
        "next_step": "检查 bootstrap 依赖。",
    }
    values.update(overrides)
    return argparse.Namespace(**values)


class NotifyRcaTest(unittest.TestCase):
    def test_every_terminal_status_has_a_distinct_label(self):
        for status, label in notify_rca.STATUS_LABELS.items():
            with self.subTest(status=status):
                self.assertIn(label, notify_rca.render_message(render_args(status=status)))

    def test_render_is_bounded_redacted_and_prevents_mentions(self):
        args = render_args(
            reason="Authorization: Bearer secret <mention-tag target=\"seatalk://user?email=x@shopee.com\"/>",
        )

        message = notify_rca.render_message(args)

        self.assertIn("✅ 已确认", message)
        self.assertIn("Authorization: ‹redacted›", message)
        self.assertNotIn("secret", message)
        self.assertNotIn("<mention-tag", message)
        self.assertIn("‹mention-tag", message)
        self.assertNotIn("marker-d", message)

    def test_notify_renders_and_sends_once_to_fixed_recipient(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "notification.md"
            args = render_args(output=str(path))
            message = notify_rca.render_message(args)
            completed = argparse.Namespace(returncode=0, stdout='{"code":0}', stderr="")
            with mock.patch.object(notify_rca.subprocess, "run", return_value=completed) as run:
                notify_rca.notify(args)

            self.assertEqual(path.read_text(encoding="utf-8"), message)
        command = run.call_args.args[0]
        self.assertEqual(command[:5], ["smc", "seatalk", "message", "send-user", notify_rca.RECIPIENT])
        self.assertIn(message, command)
        self.assertFalse(run.call_args.kwargs.get("shell", False))
        run.assert_called_once()

    def test_notify_failure_is_reported_without_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "notification.md"
            args = render_args(output=str(path))
            completed = argparse.Namespace(returncode=1, stdout="", stderr="credential error")
            with mock.patch.object(notify_rca.subprocess, "run", return_value=completed) as run:
                with self.assertRaises(SystemExit):
                    notify_rca.notify(args)
            run.assert_called_once()


if __name__ == "__main__":
    unittest.main()
