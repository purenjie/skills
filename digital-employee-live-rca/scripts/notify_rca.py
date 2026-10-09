#!/usr/bin/env python3
"""Render and immediately send one Digital Employee RCA notification."""

from __future__ import annotations

import argparse
import os
import hashlib
import json
import re
import subprocess
from pathlib import Path

import de_logs

RECIPIENT = os.environ.get("SEATALK_RCA_RECIPIENT", "")
MAX_EVIDENCE = 3
MAX_MESSAGE_CHARS = 6000
STATUS_LABELS = {
    "confirmed": "✅ 已确认",
    "unconfirmed": "⚠️ 未确认",
    "ambiguous": "❓ 存在歧义",
    "query_failed": "⛔ 查询失败",
}


def digest(message: str) -> str:
    return hashlib.sha256(message.encode("utf-8")).hexdigest()


def safe_text(value: str, *, limit: int) -> str:
    text = de_logs.redact_text(value)
    text = text.replace("<", "‹").replace(">", "›")
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > limit:
        return text[: max(0, limit - 1)].rstrip() + "…"
    return text or "未提供"


def render_message(args: argparse.Namespace) -> str:
    identifiers = [safe_text(value, limit=160) for value in args.identifier]
    evidence = [safe_text(value, limit=700) for value in args.evidence[:MAX_EVIDENCE]]
    lines = [
        f"## DE Live RCA · {STATUS_LABELS[args.status]}",
        "",
        f"**问题**：{safe_text(args.question, limit=500)}",
    ]
    if identifiers:
        lines.append(f"**关键 ID**：{' · '.join(identifiers)}")
    lines.extend(
        [
            f"**结论**：{safe_text(args.conclusion, limit=800)}",
            f"**根因 / 未确认原因**：{safe_text(args.reason, limit=1000)}",
            f"**责任边界**：{safe_text(args.boundary, limit=500)}",
            "",
            "**关键证据**：",
        ]
    )
    if evidence:
        lines.extend(f"{index}. {item}" for index, item in enumerate(evidence, start=1))
    else:
        lines.append("1. 无可确认的在线证据")
    lines.extend(
        [
            "",
            f"**耗时**：{safe_text(args.duration, limit=120)}",
            f"**下一步**：{safe_text(args.next_step, limit=800)}",
        ]
    )
    message = "\n".join(lines).strip() + "\n"
    if len(message) > MAX_MESSAGE_CHARS:
        raise ValueError(f"notification exceeds {MAX_MESSAGE_CHARS} characters")
    return message


def notify(args: argparse.Namespace) -> None:
    message = render_message(args)
    path = Path(args.output).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(message, encoding="utf-8")
    completed = subprocess.run(
        [
            "smc",
            "seatalk",
            "message",
            "send-user",
            RECIPIENT,
            "--format",
            "markdown",
            "--text",
            message,
            "--json",
        ],
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        error = de_logs.redact_text((completed.stderr or completed.stdout or "unknown error").strip())
        raise SystemExit(f"SeaTalk notification failed: {error}")
    print(
        json.dumps(
            {
                "status": "sent",
                "recipient": RECIPIENT,
                "message_file": str(path),
                "sha256": digest(message),
            },
            ensure_ascii=False,
        )
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Render and send one Digital Employee RCA notification")
    parser.add_argument("--output", required=True)
    parser.add_argument("--status", choices=tuple(STATUS_LABELS), required=True)
    parser.add_argument("--question", required=True)
    parser.add_argument("--identifier", action="append", default=[])
    parser.add_argument("--conclusion", required=True)
    parser.add_argument("--reason", required=True)
    parser.add_argument("--boundary", required=True)
    parser.add_argument("--evidence", action="append", default=[])
    parser.add_argument("--duration", default="未知")
    parser.add_argument("--next-step", required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    notify(args)


if __name__ == "__main__":
    main()
