#!/usr/bin/env python3
"""Deterministic Digital Employee target-environment RCA orchestrator.

The first supported vertical slice is intent classification. It correlates a task or
Kafka ticket to conversation_id, then finds the matching Runner
classify_with_context marker without asking the LLM to manage query loops.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol
from zoneinfo import ZoneInfo

import de_logs

RUNNER_APP = de_logs.RUNNER_APP
DEFAULT_OUT_DIR = Path("/tmp/de-live-rca")
SHANGHAI = ZoneInfo("Asia/Shanghai")
INTENT_MARKER = "runner_classification_with_context_created"
MAX_QUERY_BUDGET = 5
GENERIC_QUERY_TERMS = de_logs.GENERIC_QUERY_TERMS


class QueryFailure(RuntimeError):
    pass


@dataclass(frozen=True)
class QueryResult:
    service: str
    term: str
    start: str
    end: str
    file: Path
    duration_ms: int
    records: list[de_logs.LogRecord]


class QueryClient(Protocol):
    def query(self, *, service: str, term: str, start: str, end: str, label: str) -> QueryResult: ...


class RealLogClient:
    def __init__(
        self,
        out_dir: Path,
        *,
        timeout_seconds: int = 45,
        limit: int = 100,
        environment: str = "live",
    ) -> None:
        self.out_dir = out_dir
        self.timeout_seconds = timeout_seconds
        self.limit = min(max(1, limit), de_logs.LOGCLI_MAX_LIMIT)
        self.environment = environment
        self.query_index = 0
        self.out_dir.mkdir(parents=True, exist_ok=True)

    def query(self, *, service: str, term: str, start: str, end: str, label: str) -> QueryResult:
        normalized = term.strip()
        if not normalized:
            raise QueryFailure("empty query term")
        if normalized.lower() in GENERIC_QUERY_TERMS:
            raise QueryFailure(f"generic query term is forbidden: {normalized}")
        if service != "runner":
            raise QueryFailure(f"unsupported service in current orchestrator: {service}")

        self.query_index += 1
        output_file = self.out_dir / f"{self.query_index:02d}-{label}.{'log' if self.environment == 'test' else 'json'}"
        de_logs.validate_terms([normalized])
        pql = (
            de_logs.build_pql([normalized], service=service)
            if self.environment == "live"
            else ""
        )
        if self.environment == "test":
            command = [
                "smc",
                "services",
                "logs",
                de_logs.TEST_SERVICES["runner"],
                "--env",
                "test",
                "--wide",
                "--show-table=false",
            ]
        else:
            command = [
                "smc",
                "logcli",
                "query",
                RUNNER_APP,
                "--pql",
                pql,
                "--limit",
                str(self.limit),
                "--timeout",
                str(self.timeout_seconds),
                "--json",
                "--start",
                start,
                "--end",
                end,
            ]
        print(
            f"[de_rca] query {self.query_index}: service={service} term={normalized} "
            f"window={start}->{end}",
            file=sys.stderr,
            flush=True,
        )
        started = time.monotonic()
        try:
            with output_file.open("w", encoding="utf-8") as handle:
                completed = subprocess.run(
                    command,
                    stdout=handle,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=self.timeout_seconds + 5,
                )
        except subprocess.TimeoutExpired as error:
            raise QueryFailure(f"query timed out after {self.timeout_seconds + 5}s: {normalized}") from error
        duration_ms = int((time.monotonic() - started) * 1000)
        if completed.returncode != 0:
            stderr = de_logs.redact_text((completed.stderr or "").strip())
            raise QueryFailure(f"query failed code={completed.returncode}: {stderr or 'no stderr'}")

        all_records = de_logs.read_records([output_file])
        if self.environment == "test":
            all_records = de_logs.filter_records_by_window(
                all_records,
                (de_logs.parse_minute(start), de_logs.parse_minute(end)),
            )
        records = de_logs.filter_records(all_records, [normalized])
        return QueryResult(
            service=service,
            term=normalized,
            start=start,
            end=end,
            file=output_file,
            duration_ms=duration_ms,
            records=records,
        )


def parse_incident_time(value: str) -> dt.datetime:
    text = value.strip().replace("Z", "+00:00")
    try:
        parsed = dt.datetime.fromisoformat(text)
    except ValueError as error:
        raise ValueError(f"createdAt must be ISO-8601: {value}") from error
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=SHANGHAI)
    return parsed.astimezone(SHANGHAI)


def minute_window(center: dt.datetime, before: int, after: int) -> tuple[str, str]:
    minute = center.replace(second=0, microsecond=0)
    start = minute - dt.timedelta(minutes=before)
    end = minute + dt.timedelta(minutes=after)
    return start.strftime("%Y-%m-%d %H:%M"), end.strftime("%Y-%m-%d %H:%M")


def extract_json_after(text: str, marker: str) -> dict[str, Any] | None:
    marker_index = text.find(marker)
    if marker_index < 0:
        return None
    start = text.find("{", marker_index + len(marker))
    if start < 0:
        return None
    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                try:
                    value = json.loads(text[start : index + 1])
                except json.JSONDecodeError:
                    return None
                return value if isinstance(value, dict) else None
    return None


def first_nested(value: Any, key: str) -> Any:
    if isinstance(value, dict):
        if key in value:
            return value[key]
        for child in value.values():
            result = first_nested(child, key)
            if result is not None:
                return result
    elif isinstance(value, list):
        for child in value:
            result = first_nested(child, key)
            if result is not None:
                return result
    return None


def startup_context(records: list[de_logs.LogRecord], primary_term: str) -> dict[str, Any]:
    candidates: list[dict[str, Any]] = []
    for record in records:
        if primary_term not in record.raw:
            continue
        marker = next(
            (
                value
                for value in (
                    "runner_kafka_message_payload",
                    "runner_ticket_execution_task_context_resolved",
                    "runner_gateway_task_upsert_succeeded",
                    "runner_kafka_ticket_started",
                )
                if value in record.raw
            ),
            "runner_context",
        )
        payload = extract_json_after(record.raw, "payload=")
        if payload:
            current_process = first_nested(payload, "current_process")
            if isinstance(current_process, dict):
                handling = current_process.get("handling_payload")
                if isinstance(handling, dict):
                    candidates.append(
                        {
                            "timestamp": timestamp_text(record),
                            "conversation_id": handling.get("conversation_id"),
                            "digital_employee_id": handling.get("digital_employee_id"),
                            "task_id": handling.get("task_id"),
                            "ticket_id": handling.get("ticket_id") or current_process.get("ticket_id"),
                            "message": handling.get("req_message") or handling.get("content"),
                            "upstream_scenario_type": handling.get("scenario_type"),
                            "upstream_task_type": handling.get("task_type"),
                            "agent_identifier": handling.get("agent_identifier"),
                            "source_platform": handling.get("source_platform"),
                            "marker": marker,
                        }
                    )
        ids = de_logs.extract_ids(record.raw)
        for conversation_id in ids.get("conversation_id", []):
            candidates.append(
                {
                    "timestamp": timestamp_text(record),
                    "conversation_id": conversation_id,
                    "digital_employee_id": regex_field(record.raw, "digital_employee_id"),
                    "task_id": regex_field(record.raw, "task_id"),
                    "ticket_id": regex_field(record.raw, "ticket_id"),
                    "message": None,
                    "upstream_scenario_type": None,
                    "upstream_task_type": regex_field(record.raw, "task_type"),
                    "agent_identifier": regex_field(record.raw, "agent_identifier"),
                    "source_platform": regex_field(record.raw, "source_platform"),
                    "marker": marker,
                }
            )

    by_conversation: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        conversation_id = candidate.get("conversation_id")
        if not isinstance(conversation_id, str) or not conversation_id:
            continue
        existing = by_conversation.get(conversation_id)
        if existing is None or candidate.get("message"):
            by_conversation[conversation_id] = candidate
    if not by_conversation:
        return {}
    if len(by_conversation) > 1:
        return {"ambiguous_conversation_ids": sorted(by_conversation)}
    return next(iter(by_conversation.values()))


def regex_field(text: str, key: str) -> str | None:
    match = re.search(
        rf'(?:\\?["\'])?{re.escape(key)}(?:\\?["\'])?\s*[=:]\s*'
        rf'(?:\\?["\'])?([^\s,}}\]]+)(?![A-Za-z0-9_.:/-])(?!\s*=)',
        text,
    )
    return match.group(1).strip('"\'') if match else None


def timestamp_text(record: de_logs.LogRecord) -> str:
    # Prefer the application timestamp embedded in @message. The outer log wrapper
    # timestamp is normalized to UTC by de_logs and would otherwise display 8h early.
    match = de_logs.TIME_PATTERN.search(record.raw)
    if match:
        return match.group(0)
    if record.timestamp is not None:
        return record.timestamp.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    return "time_unknown"


def parse_llm_reason(line: str) -> str | None:
    match = re.search(r"\bllm_reason=(.*?)(?=\s+final_rationale=|\s+catalog_resolve_ms=|$)", line)
    return match.group(1).strip() if match else None


def classification_from_record(record: de_logs.LogRecord) -> dict[str, Any] | None:
    if INTENT_MARKER not in record.raw:
        return None
    request = extract_json_after(record.raw, "request=") or {}
    response = extract_json_after(record.raw, "response=") or {}
    response_data = response.get("data") if isinstance(response, dict) else None
    response_data = response_data if isinstance(response_data, dict) else {}
    task = response_data.get("task")
    task = task if isinstance(task, dict) else None
    return {
        "timestamp": timestamp_text(record),
        "marker": INTENT_MARKER,
        "endpoint": "/v1/intents/classify_with_context",
        "request_id": request.get("request_id") or response_data.get("request_id"),
        "classification_id": response_data.get("classification_id"),
        "conversation_id": request.get("conversation_id"),
        "digital_employee_id": request.get("digital_employee_id"),
        "team_name": request.get("team_name"),
        "message": request.get("message"),
        "sender_email": request.get("sender_email"),
        "scenario_type": task.get("scenario_type") if task else regex_field(record.raw, "scenario_type"),
        "task_type_id": task.get("task_type_id") if task else None,
        "task_type": task.get("task_type") if task else None,
        "language": task.get("language") if task else None,
        "direct_response": response_data.get("direct_response"),
        "llm_reason": parse_llm_reason(record.raw),
        "llm_engine": regex_field(record.raw, "llm_engine"),
        "llm_model": regex_field(record.raw, "llm_model"),
        "total_latency_ms": int(value) if (value := regex_field(record.raw, "total_latency_ms")) and value.isdigit() else None,
    }


def choose_classification(
    records: list[de_logs.LogRecord],
    *,
    conversation_id: str,
    digital_employee_id: str | None,
    incident_time: dt.datetime,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    parsed = [classification_from_record(record) for record in records]
    candidates = [item for item in parsed if item and item.get("conversation_id") == conversation_id]
    if digital_employee_id:
        matching_de = [item for item in candidates if item.get("digital_employee_id") == digital_employee_id]
        if matching_de:
            candidates = matching_de
    if not candidates:
        return None, []

    def distance(item: dict[str, Any]) -> float:
        try:
            parsed_time = dt.datetime.fromisoformat(str(item["timestamp"]).replace(" ", "T")).replace(tzinfo=SHANGHAI)
        except ValueError:
            return float("inf")
        return abs((parsed_time - incident_time).total_seconds())

    candidates.sort(key=distance)
    return candidates[0], candidates


def evidence_item(
    *,
    time_value: str,
    marker: str,
    correlation: dict[str, Any],
    fields: dict[str, Any],
    judgement: str,
    source_file: str,
) -> dict[str, Any]:
    return {
        "time": time_value,
        "service": "runner",
        "marker": marker,
        "correlation": {key: value for key, value in correlation.items() if value not in (None, "")},
        "fields": {key: value for key, value in fields.items() if value not in (None, "")},
        "judgement": judgement,
        "source_file": source_file,
    }


def bundle_checksum(bundle: dict[str, Any]) -> str:
    payload = {key: value for key, value in bundle.items() if key != "integrity"}
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def write_bundle(bundle: dict[str, Any], run_dir: Path) -> Path:
    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / "evidence-bundle.json"
    bundle["bundle_path"] = str(path)
    bundle["integrity"] = bundle_checksum(bundle)
    path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def unconfirmed_bundle(
    *,
    target: str,
    reason: str,
    identifiers: dict[str, Any],
    created_at: str,
    question: str,
    queries: list[dict[str, Any]],
    started: float,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "status": "unconfirmed",
        "target": target,
        "reason": reason,
        "identifiers": identifiers,
        "created_at": created_at,
        "question": question,
        "queries": queries,
        "evidence": [],
        "timings": {"total_ms": int((time.monotonic() - started) * 1000)},
    }


def query_metadata(result: QueryResult) -> dict[str, Any]:
    return {
        "service": result.service,
        "term": result.term,
        "start": result.start,
        "end": result.end,
        "duration_ms": result.duration_ms,
        "exact_record_count": len(result.records),
        "file": str(result.file),
    }


def diagnose_intent(
    *,
    client: QueryClient,
    task_id: str | None,
    ticket_id: str | None,
    conversation_id: str | None,
    created_at: str,
    question: str,
    max_queries: int = 3,
    max_wall_seconds: int = 90,
) -> dict[str, Any]:
    started = time.monotonic()
    incident_time = parse_incident_time(created_at)
    identifiers: dict[str, Any] = {
        "task_id": task_id,
        "ticket_id": ticket_id,
        "conversation_id": conversation_id,
    }
    queries: list[dict[str, Any]] = []
    startup: dict[str, Any] = {}
    initial_start, initial_end = minute_window(incident_time, before=1, after=4)

    def budget_available() -> bool:
        return len(queries) < min(max(1, max_queries), MAX_QUERY_BUDGET) and time.monotonic() - started < max_wall_seconds

    primary_term = ticket_id or task_id
    if primary_term:
        if not budget_available():
            return unconfirmed_bundle(
                target="intent_classification",
                reason="query_budget_exhausted",
                identifiers=identifiers,
                created_at=created_at,
                question=question,
                queries=queries,
                started=started,
            )
        result = client.query(
            service="runner",
            term=primary_term,
            start=initial_start,
            end=initial_end,
            label="startup",
        )
        queries.append(query_metadata(result))
        startup = startup_context(result.records, primary_term)
        ambiguous = startup.get("ambiguous_conversation_ids")
        if ambiguous:
            bundle = unconfirmed_bundle(
                target="intent_classification",
                reason="ambiguous_conversation_id",
                identifiers={**identifiers, "conversation_candidates": ambiguous},
                created_at=created_at,
                question=question,
                queries=queries,
                started=started,
            )
            bundle["status"] = "ambiguous"
            return bundle
        conversation_id = conversation_id or startup.get("conversation_id")
        identifiers.update(
            {
                "conversation_id": conversation_id,
                "digital_employee_id": startup.get("digital_employee_id"),
                "task_id": task_id or startup.get("task_id"),
                "ticket_id": ticket_id or startup.get("ticket_id"),
            }
        )

    if not conversation_id:
        return unconfirmed_bundle(
            target="intent_classification",
            reason="conversation_id_not_found",
            identifiers=identifiers,
            created_at=created_at,
            question=question,
            queries=queries,
            started=started,
        )

    if not budget_available():
        return unconfirmed_bundle(
            target="intent_classification",
            reason="query_budget_exhausted",
            identifiers=identifiers,
            created_at=created_at,
            question=question,
            queries=queries,
            started=started,
        )

    classification_result = client.query(
        service="runner",
        term=conversation_id,
        start=initial_start,
        end=initial_end,
        label="classification",
    )
    queries.append(query_metadata(classification_result))
    classification, candidates = choose_classification(
        classification_result.records,
        conversation_id=conversation_id,
        digital_employee_id=identifiers.get("digital_employee_id"),
        incident_time=incident_time,
    )

    if classification is None and budget_available():
        wide_start, wide_end = minute_window(incident_time, before=5, after=10)
        expanded = client.query(
            service="runner",
            term=conversation_id,
            start=wide_start,
            end=wide_end,
            label="classification-expanded",
        )
        queries.append(query_metadata(expanded))
        classification, candidates = choose_classification(
            expanded.records,
            conversation_id=conversation_id,
            digital_employee_id=identifiers.get("digital_employee_id"),
            incident_time=incident_time,
        )
        classification_result = expanded

    if classification is None:
        return unconfirmed_bundle(
            target="intent_classification",
            reason="classification_marker_not_found",
            identifiers=identifiers,
            created_at=created_at,
            question=question,
            queries=queries,
            started=started,
        )

    scenario_type = classification.get("scenario_type")
    task_type = classification.get("task_type")
    llm_reason = classification.get("llm_reason")
    if not scenario_type or scenario_type == "UNKNOWN":
        return unconfirmed_bundle(
            target="intent_classification",
            reason="classification_result_not_actionable",
            identifiers=identifiers,
            created_at=created_at,
            question=question,
            queries=queries,
            started=started,
        )

    evidence: list[dict[str, Any]] = []
    if startup:
        evidence.append(
            evidence_item(
                time_value=str(startup.get("timestamp") or "time_unknown"),
                marker=str(startup.get("marker") or "runner_context"),
                correlation={
                    "task_id": identifiers.get("task_id"),
                    "ticket_id": identifiers.get("ticket_id"),
                    "conversation_id": conversation_id,
                    "digital_employee_id": identifiers.get("digital_employee_id"),
                },
                fields={
                    "message": startup.get("message"),
                    "upstream_scenario_type": startup.get("upstream_scenario_type"),
                    "upstream_task_type": startup.get("upstream_task_type"),
                    "agent_identifier": startup.get("agent_identifier"),
                },
                judgement="The Runner task/context marker correlates the ticket/task to the target conversation.",
                source_file=queries[0]["file"],
            )
        )
    evidence.append(
        evidence_item(
            time_value=str(classification.get("timestamp")),
            marker=INTENT_MARKER,
            correlation={
                "conversation_id": conversation_id,
                "digital_employee_id": classification.get("digital_employee_id"),
                "request_id": classification.get("request_id"),
            },
            fields={
                "message": classification.get("message"),
                "scenario_type": scenario_type,
                "task_type_id": classification.get("task_type_id"),
                "task_type": task_type,
                "llm_reason": llm_reason,
                "llm_engine": classification.get("llm_engine"),
                "llm_model": classification.get("llm_model"),
                "total_latency_ms": classification.get("total_latency_ms"),
            },
            judgement=f"Runner intent classification returned scenario_type={scenario_type}, task_type={task_type}.",
            source_file=str(classification_result.file),
        )
    )

    reason_for_summary = (llm_reason or "not logged").rstrip(".")
    return {
        "schema_version": 1,
        "status": "confirmed",
        "target": "intent_classification",
        "identifiers": identifiers,
        "created_at": created_at,
        "question": question,
        "classification": classification,
        "root_cause_candidate": (
            f"Runner /v1/intents/classify_with_context classified the message as "
            f"scenario_type={scenario_type}, task_type={task_type}; llm_reason={reason_for_summary}."
        ),
        "responsibility_boundary": "Runner admission intent classification (/v1/intents/classify_with_context)",
        "queries": queries,
        "query_count": len(queries),
        "candidate_count": len(candidates),
        "evidence": evidence,
        "timings": {
            "query_ms": sum(int(query["duration_ms"]) for query in queries),
            "total_ms": int((time.monotonic() - started) * 1000),
        },
    }


def verify_bundle(bundle: dict[str, Any]) -> None:
    expected = bundle.get("integrity")
    if not isinstance(expected, str) or expected != bundle_checksum(bundle):
        raise ValueError("evidence bundle integrity check failed")
    if bundle.get("status") != "confirmed":
        raise ValueError("knowledge note requires a confirmed evidence bundle")
    identifiers = bundle.get("identifiers")
    if not isinstance(identifiers, dict) or not identifiers.get("task_id"):
        raise ValueError("knowledge note requires task_id in evidence bundle")
    evidence = bundle.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        raise ValueError("knowledge note requires online evidence")


def write_note_from_bundle(
    *,
    bundle_path: Path,
    reason: str,
    conclusion: str,
    boundary: str,
    next_step: str,
) -> Path:
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    verify_bundle(bundle)
    identifiers = bundle["identifiers"]
    task_id = str(identifiers["task_id"])
    incident_time = parse_incident_time(str(bundle["created_at"]))
    mmdd = incident_time.strftime("%m%d")
    safe_reason = de_logs.sanitize_filename_part(reason)
    de_logs.NOTE_DIR.mkdir(parents=True, exist_ok=True)
    path = de_logs.unique_path(de_logs.NOTE_DIR / f"{mmdd}-{task_id}-{safe_reason}.md")

    lines = [
        f"# {task_id} {safe_reason}",
        "",
        f"结论：{de_logs.redact_text(conclusion)}",
        "",
        "根因：",
        f"- 直接原因：{de_logs.redact_text(reason)}",
        f"- 责任边界：{de_logs.redact_text(boundary)}",
        "",
        "证据链：",
    ]
    for item in bundle["evidence"]:
        fields = item.get("fields", {})
        compact_fields = ", ".join(
            f"{key}={de_logs.redact_text(str(value))}"
            for key, value in fields.items()
            if value not in (None, "")
        )
        lines.append(
            f"- {item.get('time')} / {item.get('service')} / {item.get('marker')} / "
            f"{compact_fields} / {item.get('judgement')}"
        )
    lines.extend(
        [
            "",
            "查询统计：",
            f"- query_count：{bundle.get('query_count')}",
            f"- query_ms：{bundle.get('timings', {}).get('query_ms')}",
            f"- evidence_bundle：{bundle_path}",
            "",
            "后续：",
            f"- {de_logs.redact_text(next_step)}",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Deterministic Digital Employee live RCA orchestrator")
    sub = parser.add_subparsers(dest="action", required=True)

    diagnose = sub.add_parser("diagnose")
    diagnose.add_argument("--target", choices=("auto", "intent_classification"), default="auto")
    diagnose.add_argument("--task-id")
    diagnose.add_argument("--ticket-id")
    diagnose.add_argument("--conversation-id")
    diagnose.add_argument("--created-at", required=True)
    diagnose.add_argument("--question", required=True)
    diagnose.add_argument("--environment", choices=("live", "test"), default="live")
    diagnose.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    diagnose.add_argument("--query-timeout", type=int, default=45)
    diagnose.add_argument("--max-queries", type=int, default=3)
    diagnose.add_argument("--max-wall-seconds", type=int, default=90)

    note = sub.add_parser("write-note")
    note.add_argument("--evidence-bundle", required=True)
    note.add_argument("--reason", required=True)
    note.add_argument("--conclusion", required=True)
    note.add_argument("--boundary", required=True)
    note.add_argument("--next-step", default="无")
    return parser


def infer_target(target: str, question: str) -> str:
    if target != "auto":
        return target
    lowered = question.lower()
    terms = ("意图", "识别为", "为什么是rca", "classify", "scenario_type", "task_type")
    if any(term in lowered for term in terms):
        return "intent_classification"
    raise ValueError("auto target is ambiguous; specify --target")


def main() -> None:
    args = build_parser().parse_args()
    if args.action == "write-note":
        path = write_note_from_bundle(
            bundle_path=Path(args.evidence_bundle).expanduser(),
            reason=args.reason,
            conclusion=args.conclusion,
            boundary=args.boundary,
            next_step=args.next_step,
        )
        print(json.dumps({"status": "written", "note_path": str(path)}, ensure_ascii=False))
        return

    target = infer_target(args.target, args.question)
    run_tag = f"{dt.datetime.now().strftime('%Y%m%d-%H%M%S')}-{os.getpid()}"
    run_dir = Path(args.out_dir).expanduser() / run_tag
    client = RealLogClient(
        run_dir / "queries",
        timeout_seconds=max(5, min(args.query_timeout, 120)),
        environment=args.environment,
    )
    started = time.monotonic()
    try:
        if target != "intent_classification":
            raise ValueError(f"unsupported target: {target}")
        bundle = diagnose_intent(
            client=client,
            task_id=args.task_id,
            ticket_id=args.ticket_id,
            conversation_id=args.conversation_id,
            created_at=args.created_at,
            question=args.question,
            max_queries=args.max_queries,
            max_wall_seconds=args.max_wall_seconds,
        )
    except (QueryFailure, ValueError) as error:
        bundle = {
            "schema_version": 1,
            "status": "unconfirmed",
            "target": target,
            "reason": str(error),
            "identifiers": {
                "task_id": args.task_id,
                "ticket_id": args.ticket_id,
                "conversation_id": args.conversation_id,
            },
            "created_at": args.created_at,
            "question": args.question,
            "queries": [],
            "evidence": [],
            "timings": {"total_ms": int((time.monotonic() - started) * 1000)},
        }
    path = write_bundle(bundle, run_dir)
    bundle["bundle_path"] = str(path)
    print(json.dumps(bundle, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
