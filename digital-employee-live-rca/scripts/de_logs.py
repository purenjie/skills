#!/usr/bin/env python3
"""Collect target-environment Digital Employee Gateway and Worker Runner logs for RCA."""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import json
import os
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


GATEWAY_APP = "shopee.engineering_infra.infra_products.digital_employee.gateway"
RUNNER_APP = "shopee.engineering_infra.infra_products.digital_employee.worker_runner"
# Test Space can list these applications but currently cannot resolve either
# application to a LogDB. Bromo's service log endpoint is therefore the
# canonical test source, rather than a production LogDB fallback.
TEST_SERVICES = {
    "gateway": "digitalemployee-gateway-test-sg",
    "runner": "digitalemployee-workerrunner-test-sg",
}
LIVE_ENVIRONMENTS = {
    "gateway": "liveish",
    "runner": "live",
}
DEFAULT_OUT_DIR = Path("/tmp/digital-employee-live-rca")
RUN_TAG = f"{dt.datetime.now().strftime('%Y%m%d-%H%M%S')}-{os.getpid()}"
NOTE_DIR = Path("/Users/renjie.pu/Documents/知识库/03. 工作记录/数字员工/问题排查")
DEFAULT_HOURS = 1
LOGCLI_MAX_LIMIT = 100
# These events end one Gateway request/round. Some of them are intentionally
# non-terminal for a long-lived runner-backed execution.
TERMINAL_EVENTS = {
    "chat_response",
    "task_proposal",
    "plan_info_required",
    "plan_proposal",
    "knowledge_qa_completed",
    "plan_completed",
    "error",
}

def _id_pattern(*names: str) -> re.Pattern[str]:
    keys = "|".join(re.escape(name) for name in names)
    return re.compile(
        rf"(?:\\?[\"'])?(?:{keys})(?:\\?[\"'])?\s*[=:]\s*(?:\\?[\"'])?"
        r"([A-Za-z0-9_.:/-]+)(?![A-Za-z0-9_.:/-])(?!\s*=)",
        re.IGNORECASE,
    )


ID_PATTERNS = {
    "request_id": _id_pattern("request_id"),
    "thread_id": _id_pattern("thread_id", "thread"),
    "conversation_id": _id_pattern("conversation_id", "conversation"),
    "task_id": _id_pattern("task_id", "task"),
    "ticket_id": _id_pattern("ticket_id", "ticket"),
    "run_id": _id_pattern("run_id", "run"),
    "execution_request_id": _id_pattern("execution_request_id"),
}

LOG_LEVEL_MARKERS = "TRACE|DEBUG|INFO|WARN|WARNING|ERROR|FATAL|PANIC"
GATEWAY_MARKER = re.compile(
    rf"\[(?!(?:{LOG_LEVEL_MARKERS})\])[a-zA-Z0-9_ |]+\](?:\s+[a-zA-Z0-9_=.-]+)?"
    r"|event=(chat_response|task_proposal|plan_info_required|plan_proposal|knowledge_qa_completed|plan_completed|error)"
)
RUNNER_MARKER = re.compile(
    r"(?:runner_|qa_template_warm_pool_|gateway_execution_|gateway_task_|dems_startup_context_)[a-zA-Z0-9_]+"
    r"|\[startup_observation\](?:\s+[a-zA-Z0-9_=.-]+)?"
)
ANSI_ESCAPE_RE = re.compile(r"\x1B(?:\[[0-?]*[ -/]*[@-~]|\][^\x07]*(?:\x07|\x1B\\))")
TIME_PATTERN = re.compile(r"20\d\d-\d\d-\d\d[ T]\d\d:\d\d:\d\d(?:\.\d+)?")
MESSAGE_KEYS = ("message", "@message", "MESSAGE", "msg", "log", "content", "line")
GENERIC_QUERY_TERMS = {
    "intent",
    "task",
    "error",
    "failed",
    "rca",
    "classify",
    "classify_with_context",
}
TIME_KEYS = ("timestamp", "@timestamp", "time", "datetime", "date", "ts")


@dataclass(frozen=True)
class LogRecord:
    raw: str
    timestamp: dt.datetime | None
    source_index: int
    line_index: int


def strip_ansi(value: str) -> str:
    """Remove terminal color/control sequences emitted by Bromo and logcli."""
    return ANSI_ESCAPE_RE.sub("", value)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect target-environment Gateway/Runner logs and summarize IDs/markers for Digital Employee RCA."
    )
    sub = parser.add_subparsers(dest="mode", required=True)
    add_query_args(sub.add_parser("gateway", help="Query Gateway logs."), "gateway")
    add_query_args(sub.add_parser("runner", help="Query Worker Runner logs."), "runner")
    add_query_args(sub.add_parser("joint", help="Start with Gateway, then follow Runner/Gateway boundaries."), "joint")
    args = parser.parse_args()
    if args.limit > LOGCLI_MAX_LIMIT:
        print(
            f"[warn] applying RCA safety cap limit={LOGCLI_MAX_LIMIT} per production segment; "
            f"clamping --limit {args.limit} to {LOGCLI_MAX_LIMIT}",
            file=sys.stderr,
        )
        args.limit = LOGCLI_MAX_LIMIT
    return args


def add_query_args(parser: argparse.ArgumentParser, service: str) -> None:
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR), help="Directory for collected log outputs.")
    parser.add_argument(
        "--environment",
        choices=("live", "test"),
        default="live",
        help="live uses Space LogDB; test uses Bromo daemon.log for the active test service.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print collection commands without running them.")
    parser.add_argument(
        "--limit",
        type=int,
        default=LOGCLI_MAX_LIMIT,
        help=f"RCA safety cap per production segment ({LOGCLI_MAX_LIMIT}); larger values are clamped.",
    )
    parser.add_argument("--timeout", type=int, default=120, help="logcli --timeout for each query.")
    parser.add_argument("--segment-minutes", type=int, default=2, help="Segment explicit start/end windows.")
    parser.add_argument("--parallel", type=int, default=8, help="Max concurrent segment queries (1 = serial).")
    parser.add_argument("--start", help='Start time, e.g. "2026-07-07 18:34".')
    parser.add_argument("--end", help='End time, e.g. "2026-07-07 18:37".')
    parser.add_argument("--hours", type=int, help=f"Use logcli --hours when start/end are unknown. Default: {DEFAULT_HOURS}.")
    parser.add_argument("--task-id")
    parser.add_argument("--conversation-id")
    if service in ("gateway", "joint"):
        parser.add_argument("--thread-id")
        parser.add_argument("--request-id")
        parser.add_argument("--message-id")
        parser.add_argument("--execution-request-id")
    if service in ("runner", "joint"):
        parser.add_argument("--ticket-id")
        parser.add_argument("--run-id")
        if service == "runner":
            parser.add_argument("--execution-request-id")
    parser.add_argument("--keyword", action="append", default=[], help="Extra exact term to OR into PQL.")
    parser.add_argument("--write-note", action="store_true", help="Write a concise RCA note after log collection.")
    parser.add_argument("--note-id", help="Override the TASKID part of the note filename when no task_id exists.")
    parser.add_argument("--note-reason", help="Short Chinese root-cause phrase for the note filename and title.")
    parser.add_argument("--note-conclusion", help="One-line conclusion for the note body.")
    parser.add_argument("--note-boundary", help="Confirmed responsibility boundary for the note body.")
    parser.add_argument("--note-next-step", default="无", help="Next step for the note body.")
    parser.add_argument("--incident-date", help="Incident date as YYYY-MM-DD or MMDD for the note filename.")


def quote_term(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def build_pql(terms: list[str], *, service: str | None = None) -> str:
    clean = validate_terms(terms)
    # Reason: PQL tokenizes on dashes even inside quotes, so long IDs (UUIDs,
    # sandbox_ids with many `-`/`--`) routinely return ZERO hits as an exact
    # phrase. The empty JSON looks like "no log" and risks a false-negative
    # root cause. Automatically also OR the short tail substring (after the
    # last `-`), which PQL matches as a single token, so the query succeeds
    # without a manual retry. Keep the warning so the investigator sees what
    # was added.
    expanded: list[str] = []
    for term in clean:
        expanded.append(term)
        if "--" in term or term.count("-") >= 4:
            tail = term.rsplit("-", 1)[-1] or term[-8:]
            if tail and tail not in clean and tail not in expanded:
                expanded.append(tail)
                print(
                    f"[warn] term has many dashes, PQL may tokenize it and return empty: "
                    f"{term[:48]}... -> also querying short substring \"{tail}\"",
                    file=sys.stderr,
                )
    body = " OR ".join(quote_term(term) for term in expanded)
    environment = LIVE_ENVIRONMENTS.get(service or "")
    if environment:
        return f"@env = {environment} AND ({body})"
    return body


def validate_terms(terms: list[str]) -> list[str]:
    clean: list[str] = []
    for term in terms:
        if term and term not in clean:
            clean.append(term)
    if not clean:
        raise SystemExit("At least one ID or --keyword is required.")
    generic = [term for term in clean if term.strip().lower() in GENERIC_QUERY_TERMS]
    if generic:
        raise SystemExit(
            "Generic query terms are forbidden; use a correlated ID or rare marker: "
            + ", ".join(generic)
        )
    return clean


def arg_value(args: argparse.Namespace, name: str) -> str | None:
    return getattr(args, name.replace("-", "_"), None)


def service_terms(args: argparse.Namespace, service: str) -> list[str]:
    terms = list(args.keyword)
    names = (
        ("thread_id", "conversation_id", "request_id", "task_id", "message_id", "execution_request_id")
        if service == "gateway"
        else ("ticket_id", "conversation_id", "task_id", "run_id", "execution_request_id")
    )
    for name in names:
        value = arg_value(args, name)
        if value:
            terms.append(value)
    return terms


def parse_minute(value: str) -> dt.datetime:
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M"):
        try:
            return dt.datetime.strptime(value, fmt)
        except ValueError:
            pass
    raise SystemExit(f"Unsupported time format: {value!r}. Use YYYY-MM-DD HH:MM.")


def windows(args: argparse.Namespace) -> list[tuple[str | None, str | None]]:
    # Bromo service logs have no remote start/end predicate. Fetch once, then
    # apply the requested time window to parsed application timestamps locally.
    if args.start or args.end:
        if not (args.start and args.end):
            raise SystemExit("Provide both --start and --end, or use --hours.")
    if getattr(args, "environment", "live") == "test":
        return [(None, None)]
    if args.start or args.end:
        start = parse_minute(args.start)
        end = parse_minute(args.end)
        if end <= start:
            raise SystemExit("--end must be after --start.")
        step = dt.timedelta(minutes=max(1, args.segment_minutes))
        output = []
        cursor = start
        while cursor < end:
            segment_end = min(cursor + step, end)
            output.append((cursor.strftime("%Y-%m-%d %H:%M"), segment_end.strftime("%Y-%m-%d %H:%M")))
            cursor = segment_end
        return output
    return [(None, None)]


def build_command(
    app: str,
    pql: str,
    args: argparse.Namespace,
    start: str | None,
    end: str | None,
    service: str | None = None,
) -> list[str]:
    if getattr(args, "environment", "live") == "test":
        service_name = service if service in TEST_SERVICES else (
            "gateway" if app == GATEWAY_APP else "runner"
        )
        return [
            "smc",
            "services",
            "logs",
            TEST_SERVICES[service_name],
            "--env",
            "test",
            "--wide",
            "--show-table=false",
        ]
    command = ["smc", "logcli", "query", app, "--pql", pql, "--limit", str(args.limit), "--timeout", str(args.timeout), "--json"]
    if start and end:
        command.extend(["--start", start, "--end", end])
    else:
        command.extend(["--hours", str(args.hours or DEFAULT_HOURS)])
    return command


def record_window(args: argparse.Namespace) -> tuple[dt.datetime, dt.datetime] | None:
    """Return the local filter window required by Bromo test log collection."""
    if getattr(args, "environment", "live") != "test":
        return None
    if args.start or args.end:
        if not (args.start and args.end):
            raise SystemExit("Provide both --start and --end, or use --hours.")
        return parse_minute(args.start), parse_minute(args.end)
    end = dt.datetime.now()
    return end - dt.timedelta(hours=args.hours or DEFAULT_HOURS), end


def filter_records_by_window(
    records: list[LogRecord], window: tuple[dt.datetime, dt.datetime] | None
) -> list[LogRecord]:
    if window is None:
        return records
    start, end = window
    # The Bromo endpoint has no remote time-range filter. Excluding records
    # without a parseable application timestamp keeps task metadata and stale
    # container rows out of RCA evidence.
    return [
        record
        for record in records
        if record.timestamp is not None and start <= record.timestamp <= end
    ]


def print_empty_hint(args: argparse.Namespace, summary: dict[str, object]) -> None:
    """Warn when a query returned nothing and may have used the default 1h window."""
    if args.dry_run:
        return
    has_data = bool(summary.get("ids")) or bool(summary.get("timeline")) or bool(summary.get("signals"))
    if has_data:
        return
    if getattr(args, "environment", "live") == "test":
        print(
            "[hint] Test Bromo logs were filtered locally by timestamp and exact requested term. "
            "A miss is not proof of absence: verify the active instance retained the incident window.",
            file=sys.stderr,
        )
    elif not args.start and not args.hours:
        print(
            "[hint] empty result with the default 1h window. If the incident is older, "
            "pass --start/--end from the diagnostic created_at/updated_at.",
            file=sys.stderr,
        )

def run_query(app: str, service: str, terms: list[str], args: argparse.Namespace, label: str) -> list[Path]:
    environment = getattr(args, "environment", "live")
    validate_terms(terms)
    pql = build_pql(terms, service=service) if environment == "live" else ""
    out_dir = Path(args.out_dir).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)
    segs = windows(args)
    # Reason: segment queries are independent (disjoint output files via RUN_TAG
    # + index) and each is a multi-second `smc logcli` HTTP round-trip. Running
    # them serially makes a 30-min window take minutes. A bounded thread pool
    # collapses that to ~max_workers round-trips without changing output.
    workers = 1 if args.dry_run else max(1, min(args.parallel, len(segs))) if segs else 1

    def run_one(index: int, start: str | None, end: str | None) -> Path:
        suffix = f"{label}-{service}-{index:02d}-{RUN_TAG}.{'log' if environment == 'test' else 'json'}"
        out_file = out_dir / suffix
        command = build_command(app, pql, args, start, end, service=service)
        printable = " ".join(shlex.quote(part) for part in command)
        if args.dry_run:
            print(f"[dry-run] {printable} > {out_file}")
        else:
            source = "Bromo test daemon.log" if environment == "test" else "Space LogDB"
            print(f"[query] {service} ({source}) seg {index:02d}/{len(segs)} -> {out_file}")
            with out_file.open("w", encoding="utf-8") as handle:
                completed = subprocess.run(command, stdout=handle, stderr=subprocess.PIPE, text=True)
            if completed.returncode != 0:
                print(completed.stderr.strip(), file=sys.stderr)
                raise SystemExit(completed.returncode)
        return out_file

    if workers == 1:
        return [run_one(i, start, end) for i, (start, end) in enumerate(segs, start=1)]

    import concurrent.futures

    results: dict[int, Path] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        future_to_idx = {
            pool.submit(run_one, i, start, end): i
            for i, (start, end) in enumerate(segs, start=1)
        }
        for future in concurrent.futures.as_completed(future_to_idx):
            results[future_to_idx[future]] = future.result()
    return [results[i] for i in sorted(results)]


def _parse_timestamp(value: object) -> dt.datetime | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        seconds = float(value)
        if seconds > 10_000_000_000:
            seconds /= 1000
        try:
            return dt.datetime.fromtimestamp(seconds, tz=dt.timezone.utc).replace(
                tzinfo=None
            )
        except (OverflowError, OSError, ValueError):
            return None
    text = strip_ansi(str(value)).strip()
    if re.fullmatch(r"\d+(?:\.\d+)?", text):
        return _parse_timestamp(float(text))
    match = TIME_PATTERN.search(text)
    if match:
        text = match.group(0)
    text = text.replace(",", ".").replace("Z", "+00:00")
    try:
        parsed = dt.datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is not None:
        return parsed.astimezone(dt.timezone.utc).replace(tzinfo=None)
    return parsed


def _records_from_json(
    value: object,
    *,
    source_index: int,
    counter: list[int],
) -> list[LogRecord]:
    records: list[LogRecord] = []
    if isinstance(value, list):
        for item in value:
            records.extend(
                _records_from_json(item, source_index=source_index, counter=counter)
            )
        return records
    if not isinstance(value, dict):
        return records

    data = value.get("data")
    if isinstance(data, str):
        if value.get("base64Encoded") is True:
            try:
                data = base64.b64decode(data).decode("utf-8", errors="replace")
            except (ValueError, TypeError):
                pass
        try:
            nested = json.loads(data)
        except json.JSONDecodeError:
            nested = None
        if nested is not None:
            return _records_from_json(
                nested,
                source_index=source_index,
                counter=counter,
            )

    message_key = next(
        (key for key in MESSAGE_KEYS if key in value and value[key] is not None),
        None,
    )
    message = value.get(message_key) if message_key else data
    if message is not None and not isinstance(message, (dict, list)):
        timestamp_value = next(
            (value[key] for key in TIME_KEYS if key in value and value[key] is not None),
            None,
        )
        context = {
            key: item
            for key, item in value.items()
            if key != message_key and key != "data"
        }
        raw = strip_ansi(str(message))
        if context:
            raw += " " + json.dumps(
                context,
                ensure_ascii=False,
                separators=(",", ":"),
            )
        counter[0] += 1
        records.append(
            LogRecord(
                raw=raw,
                timestamp=_parse_timestamp(timestamp_value) or _parse_timestamp(raw),
                source_index=source_index,
                line_index=counter[0],
            )
        )
        return records

    for item in value.values():
        records.extend(
            _records_from_json(item, source_index=source_index, counter=counter)
        )
    return records


def read_records(files: list[Path]) -> list[LogRecord]:
    records: list[LogRecord] = []
    for source_index, path in enumerate(files):
        if not path.exists():
            continue
        content = path.read_text(encoding="utf-8", errors="replace")
        parsed_records: list[LogRecord] = []
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            parsed = None
        if parsed is not None:
            parsed_records = _records_from_json(
                parsed,
                source_index=source_index,
                counter=[0],
            )
        if not parsed_records:
            for line_index, line in enumerate(content.splitlines()):
                if not line.strip():
                    continue
                parsed_records.append(
                    LogRecord(
                        raw=strip_ansi(line),
                        timestamp=_parse_timestamp(line),
                        source_index=source_index,
                        line_index=line_index,
                    )
                )
        records.extend(parsed_records)

    return sorted(
        records,
        key=lambda record: (
            record.timestamp is None,
            record.timestamp or dt.datetime.max,
            record.source_index,
            record.line_index,
        ),
    )


def filter_records(records: list[LogRecord], exact_terms: list[str] | None) -> list[LogRecord]:
    terms = [term for term in (exact_terms or []) if term]
    if not terms:
        return records
    return [record for record in records if any(term in record.raw for term in terms)]


def read_text(files: list[Path], exact_terms: list[str] | None = None) -> str:
    records = filter_records(read_records(files), exact_terms)
    return "\n".join(record.raw for record in records)


def extract_ids(text: str) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for name, pattern in ID_PATTERNS.items():
        values = []
        for match in pattern.finditer(text):
            value = match.group(1).strip('",}])')
            if value and value not in values:
                values.append(value)
        if values:
            found[name] = values[:10]
    return found


def extract_reason(line: str) -> str | None:
    match = re.search(
        r"(?:\\?[\"'])?reason(?:\\?[\"'])?\s*[=:]\s*(?:\\?[\"'])?"
        r"(.*?)(?=(?:\\?[\"'])?\s+[a-zA-Z_][a-zA-Z0-9_]*(?:\\?[\"'])?\s*=|[,}\]]|$)",
        line,
        re.IGNORECASE,
    )
    if not match:
        return None
    return match.group(1).strip().rstrip("\"'")


def extract_field(line: str, key: str) -> str | None:
    """Extract a compact key=value or JSON key from a structured log line."""
    pattern = re.compile(
        rf"(?<![A-Za-z0-9_])(?:\\?[\"'])?{re.escape(key)}(?:\\?[\"'])?"
        r"\s*[=:]\s*(?:\\?[\"'])?([A-Za-z0-9_.:/-]+)"
        r"(?![A-Za-z0-9_.:/-])(?!\s*=)",
        re.IGNORECASE,
    )
    match = pattern.search(line)
    return match.group(1).strip("\"'") if match else None


def marker_field_summary(
    text: str,
    marker: str,
    fields: tuple[str, ...],
) -> str | None:
    """Return only safe, bounded fields from the first matching marker line."""
    fallback: str | None = None
    for line in text.splitlines():
        if marker not in line:
            continue
        values = [
            f"{key}={value}"
            for key in fields
            if (value := extract_field(line, key))
        ]
        summary = marker + (" " + " ".join(values) if values else "")
        if fallback is None:
            fallback = summary
        if extract_field(line, "record_kind") == "summary":
            return summary
    return fallback


def extract_log_environments(text: str) -> list[str]:
    values: list[str] = []
    pattern = re.compile(
        r'(?:\\?["\'])?@env(?:\\?["\'])?\s*[=:]\s*(?:\\?["\'])?([A-Za-z0-9_.-]+)',
        re.IGNORECASE,
    )
    for match in pattern.finditer(text):
        value = match.group(1).strip().rstrip("\"'")
        if value and value not in values:
            values.append(value)
    return values


def extract_timeline(text: str, service: str, limit: int = 80) -> list[str]:
    marker_re = GATEWAY_MARKER if service == "gateway" else RUNNER_MARKER
    lines: list[str] = []
    for raw_line in text.splitlines():
        marker = marker_re.search(raw_line)
        if not marker:
            continue
        timestamp = TIME_PATTERN.search(raw_line)
        marker_text = marker.group(0)
        reason = ""
        if "reason" in raw_line:
            reason_value = extract_reason(raw_line)
            if reason_value:
                reason = f" reason={reason_value}"
        event = ""
        event_match = re.search(r"event=([a-zA-Z0-9_]+)", raw_line)
        if event_match and "event=" not in marker_text:
            event = f" event={event_match.group(1)}"
        prefix = timestamp.group(0) if timestamp else "time_unknown"
        entry = f"{prefix} {marker_text}{event}{reason}"
        if entry not in lines:
            lines.append(entry)
        if len(lines) >= limit:
            break
    return lines


def first_matching_line(text: str, pattern: str) -> str | None:
    compiled = re.compile(pattern)
    for line in text.splitlines():
        if compiled.search(line):
            timestamp = TIME_PATTERN.search(line)
            prefix = timestamp.group(0) if timestamp else "time_unknown"
            return f"{prefix} {line.strip()[:500]}"
    return None


def last_matching_line(text: str, pattern: str) -> str | None:
    compiled = re.compile(pattern)
    result = None
    for line in text.splitlines():
        if compiled.search(line):
            timestamp = TIME_PATTERN.search(line)
            prefix = timestamp.group(0) if timestamp else "time_unknown"
            result = f"{prefix} {line.strip()[:500]}"
    return result


def _regex_first(text: str, pattern: str) -> str | None:
    """Return the first capture group of `pattern` in `text`, or None."""
    match = re.search(pattern, text)
    return match.group(1) if match else None


def extract_first_terminal(text: str) -> str | None:
    for line in text.splitlines():
        event_match = re.search(r"event=([a-zA-Z0-9_]+)", line)
        if event_match and event_match.group(1) in TERMINAL_EVENTS:
            timestamp = TIME_PATTERN.search(line)
            prefix = timestamp.group(0) if timestamp else "time_unknown"
            return f"{prefix} event={event_match.group(1)}"
    return None


def analyze_signals(
    text: str,
    service: str,
    *,
    environment: str = "live",
) -> dict[str, str]:
    signals: dict[str, str] = {}
    if not text.strip():
        return signals
    environments = extract_log_environments(text)
    service_key = "gateway" if service.startswith("gateway") else "runner"
    expected_environment = LIVE_ENVIRONMENTS[service_key]
    if environment == "live":
        unexpected_environments = [
            value for value in environments if value != expected_environment
        ]
        if unexpected_environments:
            signals["environment_warning"] = (
                f"expected {expected_environment}; also found "
                + ",".join(unexpected_environments)
            )
    if service.startswith("gateway"):
        terminal = extract_first_terminal(text)
        if terminal:
            signals["first_round_terminal_event"] = terminal
        blocked = marker_field_summary(
            text,
            "[de_execution_blocked]",
            ("record_kind", "diagnostic_id", "stage", "reason_code"),
        )
        if blocked:
            signals["execution_blocked"] = blocked
        startup = marker_field_summary(
            text,
            "[startup_observation]",
            (
                "kind",
                "action",
                "milestone",
                "stage",
                "result",
                "reason_code",
                "first_worker_event_type",
                "first_visible_event_type",
            ),
        )
        if startup:
            signals["startup_observation"] = startup
        if "kafka_wait" in text:
            signals["gateway_handoff"] = "found [runner_business_prepare] kafka_wait; switch to Runner by ticket_id"
            signals["boundary_hint"] = "Gateway -> Runner handoff"
        elif "[stream] send2agent" in text and "[stream] agent_event" not in text:
            signals["boundary_hint"] = "Gateway sent to sandbox/agent; no agent_event found in current window"
        elif "[stream] agent_event" in text and re.search(r"\[seatalk_api\].*(rejected|failed|request_failed)", text):
            signals["boundary_hint"] = "Gateway received agent_event; SeaTalk rendering/API needs focus"
        elif "[stream] agent_event" in text:
            signals["boundary_hint"] = "Gateway event handling after agent_event"

        # Scenario flip: a follow-up bound as one scenario (e.g. QNA) gets scrubbed and
        # re-routed to another (e.g. OPERATION) via inherited_task_context_scrubbed.
        # Reason: this scrub/flip is an EXPECTED fallback on context degrade (e.g.
        # GetGroupChatThreadByThreadID failure), NOT a fault by itself. Surfacing it as
        # "expected" prevents the common误判 of mistaking the flip for the root cause and
        # pushes the investigator toward the real question: did the new card get written?
        slot_scenario = _regex_first(text, r"direct_execution_slot_bound.*?scenario=(\w+)")
        scrub_target = _regex_first(text, r"inherited_task_context_scrubbed.*?target_scenario=(\w+)")
        if scrub_target:
            if slot_scenario and slot_scenario != scrub_target:
                signals["scenario_flip"] = (
                    f"{slot_scenario}->{scrub_target} via inherited_task_context_scrubbed "
                    "(expected fallback on context degrade, NOT a fault by itself; "
                    "check whether the newly init'd stream card actually gets written)"
                )
            else:
                signals["scenario_flip"] = (
                    f"->{scrub_target} via inherited_task_context_scrubbed "
                    "(expected fallback on context degrade, NOT a fault by itself)"
                )

        # Orphan stream card suspect: init_interactive_stream_group builds a streaming card
        # that is normally filled by a [stream] terminal_agent_event (QNA/RCA path). If more
        # cards are init'd than terminal fills occur, a card may be left empty.
        # Reason: this is only a SUSPECT — terminal_agent_event can fall outside the window.
        # When an OPERATION route is present, note that OPERATION updates the OLD anchor card
        # via update_decision (reason=update_existing_policy), NOT the newly init'd stream
        # card, which is exactly the orphan/empty-card pattern.
        init_cards = len(re.findall(r"init_interactive_stream_group_success", text))
        terminal_fills = len(re.findall(r"\[stream\] terminal_agent_event", text))
        if init_cards > terminal_fills:
            note = f"{init_cards} init_interactive_stream_group vs {terminal_fills} terminal_agent_event"
            if re.search(r"(\[route\]|\[runner_conversation\]).*#OPERATION", text):
                note += (
                    "; OPERATION route updates the old anchor card via update_decision, "
                    "not the newly init'd stream card — suspect orphan/empty card"
                )
            signals["orphan_card_suspect"] = note
    else:
        outcome = last_matching_line(
            text,
            r"runner_kafka_ticket_(started|provisioning_error|dependency_error|non_actionable|inflight|duplicate_active|ignored|parse_error)",
        )
        if outcome and "runner_kafka_ticket_provisioning_error" in outcome:
            reason = extract_reason(outcome) or "reason_not_extracted"
            signals["runner_result"] = f"provisioning_error reason={reason}"
            if "Sandbox.create" in reason or "sandbox" in reason.lower():
                signals["boundary_hint"] = "Sandbox API / sandbox provisioning"
            elif "startup_context" in reason or "startup context" in reason.lower():
                signals["boundary_hint"] = "Runner startup context / DEMS"
            elif "gateway" in reason.lower():
                signals["boundary_hint"] = "Runner -> Gateway notification"
        elif outcome and "runner_kafka_ticket_started" in outcome:
            signals["runner_result"] = "started"
            if "runner_gateway_execution_registered" in text:
                signals["boundary_hint"] = "Runner registered execution; switch back to Gateway by execution_request_id"
            else:
                signals["boundary_hint"] = "Runner started; check Gateway execution registration"
        elif outcome:
            outcome_match = re.search(
                r"runner_kafka_ticket_([a-zA-Z0-9_]+)",
                outcome,
            )
            status = outcome_match.group(1) if outcome_match else "unknown"
            reason = extract_reason(outcome) or "reason_not_extracted"
            signals["runner_result"] = f"{status} reason={reason}"
            if status == "dependency_error":
                signals["boundary_hint"] = "Runner dependency before successful provisioning"
            elif status == "non_actionable":
                signals["boundary_hint"] = "Runner eligibility/context/route decision"
            elif status in {"inflight", "duplicate_active"}:
                signals["boundary_hint"] = "Runner lifecycle dedupe/inflight guard"
        if "runner_ticket_execution_environment_mismatch" in text and "boundary_hint" not in signals:
            signals["boundary_hint"] = "Runner payload/runtime environment guard"
        elif "runner_ticket_execution_provisioning_skipped" in text and "boundary_hint" not in signals:
            signals["boundary_hint"] = "Runner provisioning eligibility/skip decision"
        elif "runner_kafka_message_payload" not in text:
            if re.search(r"runner_kafka_worker_started|runner_ticket_execution_|runner_sandbox_|runner_gateway_", text):
                signals["payload_logging_note"] = (
                    "runner_kafka_message_payload is conditional; its absence does not prove "
                    "the Kafka event was not consumed"
                )
            else:
                signals["boundary_hint"] = "Runner/Kafka before message consumption"

    failure = first_matching_line(
        text,
        r"(?:event=error\b|\[(?:ERROR|FATAL|PANIC)\]|"
        r"(?:^|[_\s])(?:failed|failure|rejected|invalid_signature|"
        r"provisioning_error|dependency_error)\b|"
        r"\b(?:result|status)=(?:failed|missing|error)\b|"
        r"\[de_execution_blocked\])",
    )
    if failure:
        signals["failure_like_hint"] = failure
    return signals


def summarize(
    service: str,
    files: list[Path],
    *,
    exact_terms: list[str] | None = None,
    query_limit: int | None = None,
    time_window: tuple[dt.datetime, dt.datetime] | None = None,
    environment: str = "live",
) -> dict[str, object]:
    all_records = read_records(files)
    windowed_records = filter_records_by_window(all_records, time_window)
    records = filter_records(windowed_records, exact_terms)
    text = "\n".join(record.raw for record in records)
    ids = extract_ids(text)
    timeline = extract_timeline(text, service)
    signals = analyze_signals(text, service, environment=environment)
    saturated_files = []
    if query_limit:
        record_counts: dict[int, int] = {}
        for record in all_records:
            record_counts[record.source_index] = (
                record_counts.get(record.source_index, 0) + 1
            )
        for source_index, path in enumerate(files):
            if record_counts.get(source_index, 0) >= query_limit:
                saturated_files.append(path.name)
        if saturated_files:
            signals["query_saturation_warning"] = (
                f"{len(saturated_files)} segment(s) reached limit={query_limit}; "
                "reduce --segment-minutes before concluding absence"
            )
    print(f"\n[{service}] files")
    for path in files:
        print(f"- {path}")
    print(f"\n[{service}] extracted IDs")
    if ids:
        for name, values in ids.items():
            print(f"- {name}: {', '.join(values)}")
    else:
        print("- none")
    print(f"\n[{service}] marker timeline")
    if timeline:
        for entry in timeline:
            print(f"- {entry}")
    else:
        print("- none")
    print(f"\n[{service}] signals")
    if signals:
        for name, value in signals.items():
            print(f"- {name}: {value}")
    else:
        print("- none")
    if all_records and exact_terms and not records:
        source = "collected test logs" if time_window is not None else "broad PQL"
        print(
            f"\n[{service}] warning\n- {source} returned records, but none contained the full requested ID; "
            f"\n[{service}] warning\n- {source} returned records, but none contained the full requested term; "
            "short-tail matches were excluded from RCA analysis"
        )
    return {
        "ids": ids,
        "timeline": timeline,
        "signals": signals,
        "files": [str(path) for path in files],
        "_text": text,
    }


def summarize_query(
    service: str, files: list[Path], terms: list[str], args: argparse.Namespace
) -> dict[str, object]:
    return summarize(
        service,
        files,
        exact_terms=terms,
        query_limit=args.limit if getattr(args, "environment", "live") == "live" else None,
        time_window=record_window(args),
        environment=getattr(args, "environment", "live"),
    )


def first(values: dict[str, list[str]], key: str) -> str | None:
    items = values.get(key) or []
    return items[0] if items else None


def unique(values: dict[str, list[str]], key: str) -> str | None:
    items = values.get(key) or []
    return items[0] if len(items) == 1 else None


def correlated_ids(
    summary: dict[str, object],
    *,
    marker_pattern: str,
    id_key: str,
    required_term: str | None = None,
) -> list[str]:
    text = summary.get("_text", "")
    if not isinstance(text, str):
        return []
    marker = re.compile(marker_pattern)
    pattern = ID_PATTERNS[id_key]
    values: list[str] = []
    for line in text.splitlines():
        if not marker.search(line):
            continue
        if required_term and required_term not in line:
            continue
        for match in pattern.finditer(line):
            value = match.group(1).strip('",}])')
            if value and value not in values:
                values.append(value)
    return values


def merged_ids(summaries: list[dict[str, object]]) -> dict[str, list[str]]:
    output: dict[str, list[str]] = {}
    for summary in summaries:
        ids = summary.get("ids", {})
        if not isinstance(ids, dict):
            continue
        for key, values in ids.items():
            if not isinstance(values, list):
                continue
            bucket = output.setdefault(key, [])
            for value in values:
                if isinstance(value, str) and value not in bucket:
                    bucket.append(value)
    return output


def incident_mmdd(args: argparse.Namespace) -> str:
    if args.incident_date:
        value = args.incident_date.strip()
        if re.fullmatch(r"\d{4}", value):
            return value
        match = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", value)
        if match:
            return f"{match.group(2)}{match.group(3)}"
        raise SystemExit("--incident-date must be YYYY-MM-DD or MMDD.")
    if args.start:
        parsed = parse_minute(args.start)
        return parsed.strftime("%m%d")
    return dt.datetime.now().strftime("%m%d")


def sanitize_filename_part(value: str) -> str:
    value = re.sub(r"[\\/:*?\"<>|\n\r\t]", "", value).strip()
    value = re.sub(r"\s+", "", value)
    return value[:48] or "原因待补充"


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    for index in range(2, 100):
        candidate = path.with_name(f"{stem}-{index}{suffix}")
        if not candidate.exists():
            return candidate
    raise SystemExit(f"Too many existing note files for {path.name}")


def compact_lines(items: list[str], limit: int) -> list[str]:
    return items[:limit] if items else ["待补充"]


def redact_text(value: str) -> str:
    patterns = (
        r"(?i)(authorization\s*[=:]\s*)(?:bearer\s+)?[^\s,}\]]+",
        r"(?i)((?:access_token|api_key|secret|connect_token|personal_token)\s*[=:]\s*)[^\s,}\]]+",
        r'(?i)("(?:authorization|access_token|api_key|secret|connect_token|personal_token)"\s*:\s*")[^"]+',
    )
    redacted = value
    for pattern in patterns:
        redacted = re.sub(pattern, r"\1<redacted>", redacted)
    return redacted


def write_note(args: argparse.Namespace, summaries: list[dict[str, object]]) -> Path | None:
    if not args.write_note:
        return None
    if args.dry_run:
        raise SystemExit("--write-note cannot be used with --dry-run.")
    missing_note_fields = [
        flag
        for flag, value in (
            ("--note-reason", args.note_reason),
            ("--note-conclusion", args.note_conclusion),
            ("--note-boundary", args.note_boundary),
        )
        if not value
    ]
    if missing_note_fields:
        raise SystemExit(
            "--write-note requires confirmed RCA fields: " + ", ".join(missing_note_fields)
        )

    ids = merged_ids(summaries)
    note_id = args.note_id or arg_value(args, "task_id") or first(ids, "task_id")
    if not note_id:
        raise SystemExit("Cannot write note without task_id. Provide --task-id or --note-id.")

    reason = sanitize_filename_part(args.note_reason)
    mmdd = incident_mmdd(args)
    NOTE_DIR.mkdir(parents=True, exist_ok=True)
    path = unique_path(NOTE_DIR / f"{mmdd}-{note_id}-{reason}.md")

    timeline: list[str] = []
    signal_lines: list[str] = []
    for summary in summaries:
        service = "unknown"
        files = summary.get("files", [])
        if isinstance(files, list) and files:
            filename = str(files[0])
            if "runner" in filename:
                service = "runner"
            elif "gateway" in filename:
                service = "gateway"
        for item in summary.get("timeline", []):
            if isinstance(item, str):
                timeline.append(f"{service}: {item}")
        signals = summary.get("signals", {})
        if isinstance(signals, dict):
            for key, value in signals.items():
                if key == "failure_like_hint":
                    continue
                signal_lines.append(redact_text(f"{service}: {key}={value}"))

    timeline = [redact_text(line) for line in timeline]
    conclusion = redact_text(args.note_conclusion)
    boundary = redact_text(args.note_boundary)
    next_step = args.note_next_step or "无"
    query_terms = ", ".join(
        value
        for value in [
            arg_value(args, "thread_id"),
            arg_value(args, "request_id"),
            arg_value(args, "task_id"),
            arg_value(args, "ticket_id"),
            arg_value(args, "run_id"),
            arg_value(args, "execution_request_id"),
        ]
        if value
    ) or "见证据链"

    body = [
        f"# {note_id} {reason}",
        "",
        f"结论：{conclusion}",
        "",
        "根因：",
        f"- 直接原因：{redact_text(args.note_reason)}",
        f"- 责任边界：{boundary}",
        "",
        "证据链：",
    ]
    body.extend(f"- {line}" for line in compact_lines(signal_lines, 6))
    body.extend(f"- {line}" for line in compact_lines(timeline, 8))
    body.extend(
        [
            "",
            "排查流程：",
            f"- 起手 ID 和时间窗：{query_terms}; {args.start or 'hours'} -> {args.end or args.hours or DEFAULT_HOURS}",
            "- 关键分流点：见 signals 和 marker timeline。",
            f"- 最终收敛到的失败点：{boundary}",
            "",
            "后续：",
            f"- {next_step}",
            "",
        ]
    )
    path.write_text("\n".join(body), encoding="utf-8")
    print(f"\n[note] wrote {path}")
    return path


def write_run_summary(run_dir: Path, summaries: list[dict[str, object]]) -> Path:
    """Write a bounded, redacted artifact for agent-independent follow-up."""
    public_summaries = []
    for summary in summaries:
        signals = summary.get("signals", {})
        public_summaries.append(
            {
                "ids": summary.get("ids", {}),
                "timeline": [
                    redact_text(str(item))
                    for item in summary.get("timeline", [])
                    if isinstance(item, str)
                ],
                "signals": {
                    str(key): redact_text(str(value))
                    for key, value in signals.items()
                }
                if isinstance(signals, dict)
                else {},
                "files": summary.get("files", []),
            }
        )
    path = run_dir / "summary.json"
    payload = {
        "schema_version": 1,
        "identifiers": merged_ids(summaries),
        "summaries": public_summaries,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[summary] wrote {path}")
    return path


def prepare_run_dir(args: argparse.Namespace) -> Path:
    run_dir = Path(args.out_dir).expanduser() / RUN_TAG
    args.out_dir = str(run_dir)
    print(f"[run] output directory: {run_dir}")
    return run_dir


def _explicit_runner_ids(args: argparse.Namespace) -> bool:
    return any(
        arg_value(args, name)
        for name in ("ticket_id", "conversation_id", "task_id", "run_id", "execution_request_id")
    )


def main() -> None:
    args = parse_args()
    run_dir = prepare_run_dir(args)

    if args.mode == "gateway":
        terms = service_terms(args, "gateway")
        files = run_query(GATEWAY_APP, "gateway", terms, args, "manual")
        summary = summarize_query("gateway", files, terms, args)
        print_empty_hint(args, summary)
        write_run_summary(run_dir, [summary])
        write_note(args, [summary])
        return

    if args.mode == "runner":
        terms = service_terms(args, "runner")
        files = run_query(RUNNER_APP, "runner", terms, args, "manual")
        summary = summarize_query("runner", files, terms, args)
        print_empty_hint(args, summary)
        write_run_summary(run_dir, [summary])
        write_note(args, [summary])
        return

    summaries: list[dict[str, object]] = []
    gateway_terms = service_terms(args, "gateway")
    runner_terms = service_terms(args, "runner")
    if not gateway_terms and runner_terms:
        gateway_terms = list(runner_terms)
    runner_summary: dict[str, object] | None = None

    if _explicit_runner_ids(args):
        # Gateway and Runner queries are independent when both sides already
        # have a usable ID. Run them concurrently; boundary follow-ups remain
        # sequential because their IDs come from the preceding result.
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            gateway_future = pool.submit(
                run_query,
                GATEWAY_APP,
                "gateway",
                gateway_terms,
                args,
                "joint",
            )
            runner_future = pool.submit(
                run_query,
                RUNNER_APP,
                "runner",
                runner_terms,
                args,
                "joint",
            )
            gateway_files = gateway_future.result()
            runner_files = runner_future.result()
        gateway_summary = summarize_query("gateway", gateway_files, gateway_terms, args)
        runner_summary = summarize_query("runner", runner_files, runner_terms, args)
        print_empty_hint(args, runner_summary)
    else:
        gateway_files = run_query(
            GATEWAY_APP,
            "gateway",
            gateway_terms,
            args,
            "joint",
        )
        gateway_summary = summarize_query("gateway", gateway_files, gateway_terms, args)

    summaries.append(gateway_summary)
    print_empty_hint(args, gateway_summary)

    boundary_tickets = correlated_ids(
        gateway_summary,
        marker_pattern=r"\[runner_business_prepare\]\s+kafka_wait",
        id_key="ticket_id",
    )
    ticket_id = boundary_tickets[0] if len(boundary_tickets) == 1 else None
    if len(boundary_tickets) > 1:
        print(
            "\n[joint] Multiple ticket_id values were found on kafka_wait boundaries; "
            "automatic Runner follow-up stopped to avoid cross-task attribution.",
            file=sys.stderr,
        )

    if runner_summary is not None:
        summaries.append(runner_summary)
        if ticket_id is None:
            runner_ids = (
                runner_summary["ids"]
                if isinstance(runner_summary.get("ids"), dict)
                else {}
            )
            ticket_id = unique(runner_ids, "ticket_id")

    # A task_id query can reveal ticket_id but still miss ticket-only Kafka and
    # provisioning logs. Re-query narrowly by the correlated ticket_id.
    if ticket_id and ticket_id not in runner_terms:
        runner_terms = [ticket_id]
        runner_files = run_query(
            RUNNER_APP,
            "runner",
            runner_terms,
            args,
            "joint-correlated",
        )
        runner_summary = summarize_query("runner-correlated", runner_files, runner_terms, args)
        print_empty_hint(args, runner_summary)
        summaries.append(runner_summary)

    if runner_summary is None:
        print("\n[joint] No Runner boundary ID found. Check Gateway timeline before querying Runner.")

    execution_ids = (
        correlated_ids(
            runner_summary,
            marker_pattern=r"runner_gateway_execution_registered",
            id_key="execution_request_id",
            required_term=ticket_id,
        )
        if runner_summary is not None
        else []
    )
    execution_request_id = execution_ids[0] if len(execution_ids) == 1 else None
    if len(execution_ids) > 1:
        print(
            "\n[joint] Multiple execution_request_id values matched the Runner registration boundary; "
            "automatic Gateway follow-up stopped.",
            file=sys.stderr,
        )
    if execution_request_id:
        followup_args = argparse.Namespace(**vars(args))
        followup_args.keyword = [execution_request_id]
        followup_files = run_query(
            GATEWAY_APP,
            "gateway",
            [execution_request_id],
            followup_args,
            "joint-followup",
        )
        followup_summary = summarize_query(
            "gateway-followup", followup_files, [execution_request_id], followup_args
        )
        print_empty_hint(args, followup_summary)
        summaries.append(followup_summary)

    write_run_summary(run_dir, summaries)
    write_note(args, summaries)


if __name__ == "__main__":
    main()
