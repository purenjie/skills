#!/usr/bin/env python3
"""Export a read-only weekly SRE startup scorecard from Prometheus and logs.

The exporter deliberately keeps Prometheus aggregates and log evidence
separate. Prometheus is the source for trend/quantile values; logs are the
execution-level drill-down source. An incomplete or empty upstream response is
reported as incomplete instead of being converted into a misleading zero.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import subprocess
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
from urllib import error as urlerror
from urllib import parse as urlparse
from urllib import request as urlrequest


DEFAULT_PROMETHEUS_URL = os.environ.get("PROMETHEUS_URL", "")
DEFAULT_GATEWAY_LOG_APP = os.environ.get("GATEWAY_LOG_APP", "")
DEFAULT_RUNNER_LOG_APP = os.environ.get("RUNNER_LOG_APP", "")
DEFAULT_OUTPUT_DIR = Path("dems-sre-startup-weekly-output")
METRIC_PREFIX = "digital_employee_task_startup_milestone_v3"
STAGE_METRIC_PREFIX = "digital_employee_task_startup_stage_v3_latency_seconds"
LOG_MARKER = "[startup_observation]"
LOG_LIMIT = 10_000
LABEL_KEYS = ("de_id", "team_id_l1", "team_id_l3", "scenario", "source", "task_type")
GROUP_KEYS = ("scenario", "de_id", "task_type")
STAGE_GROUP_KEYS = ("scenario", "de_id", "task_type", "service", "stage")


class IncompleteDataError(RuntimeError):
    pass


def parse_datetime(value: str) -> datetime:
    candidate = value.strip()
    if candidate.endswith("Z"):
        candidate = candidate[:-1] + "+00:00"
    parsed = datetime.fromisoformat(candidate)
    if parsed.tzinfo is None:
        raise ValueError(f"timestamp must include timezone: {value}")
    return parsed


def parse_team_filter(value: str) -> list[str]:
    teams = [item.strip() for item in value.split(",") if item.strip()]
    if not teams:
        raise ValueError("team filter cannot be empty")
    return teams


def promql_escape(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def label_matchers(args: argparse.Namespace) -> str:
    matchers = [f'team_id_l1=~{promql_escape("|".join(args.team_id_l1))}']
    for key in ("scenario", "de_id", "task_type", "source"):
        value = getattr(args, key, None)
        if value:
            matchers.append(f"{key}={promql_escape(value)}")
    return ",".join(matchers)


def query_prometheus(
    base_url: str,
    query: str,
    *,
    timestamp: datetime,
    opener=urlrequest.urlopen,
    retries: int = 3,
) -> list[dict[str, Any]]:
    endpoint = base_url.rstrip("/") + "/api/v1/query"
    params = urlparse.urlencode({"query": query, "time": str(timestamp.timestamp())})
    url = endpoint + "?" + params
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            with opener(url, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))
            if payload.get("status") != "success":
                raise IncompleteDataError(f"Prometheus returned status={payload.get('status')!r}")
            data = payload.get("data") or {}
            if any(container.get(key) is True for container in (payload, data) for key in ("partial", "isPartial")):
                raise IncompleteDataError("Prometheus returned partial data")
            if data.get("resultType") != "vector":
                raise IncompleteDataError("Prometheus response resultType must be vector")
            result = data.get("result")
            if not isinstance(result, list):
                raise IncompleteDataError("Prometheus response result is not a list")
            if not result:
                raise IncompleteDataError("Prometheus response result is empty; coverage is unknown")
            return result
        except (OSError, ValueError, KeyError, TypeError, IncompleteDataError, urlerror.URLError) as exc:
            last_error = exc
            if attempt + 1 < retries:
                time.sleep(0.2 * (attempt + 1))
    raise IncompleteDataError(f"Prometheus query failed after {retries} attempts: {last_error}")


def result_value(item: Mapping[str, Any]) -> float:
    value = item.get("value")
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or len(value) < 2:
        raise IncompleteDataError("Prometheus vector item has no value")
    try:
        parsed = float(value[1])
    except (TypeError, ValueError) as exc:
        raise IncompleteDataError("Prometheus vector item has an invalid value") from exc
    if not math.isfinite(parsed):
        raise IncompleteDataError("Prometheus vector item has a non-finite value")
    return parsed


def result_labels(item: Mapping[str, Any], group_keys: Sequence[str] = GROUP_KEYS) -> dict[str, str]:
    metric = item.get("metric")
    if not isinstance(metric, Mapping):
        raise IncompleteDataError("Prometheus vector item has no metric labels")
    labels: dict[str, str] = {}
    for key in group_keys:
        value = metric.get(key)
        if value is None or str(value) == "":
            raise IncompleteDataError(f"Prometheus result is missing label {key}")
        labels[key] = str(value)
    return labels


def aggregate_vector(result: Iterable[Mapping[str, Any]], group_keys: Sequence[str] = GROUP_KEYS) -> dict[tuple[str, ...], float]:
    values: dict[tuple[str, ...], float] = defaultdict(float)
    for item in result:
        value = result_value(item)
        labels = result_labels(item, group_keys)
        values[tuple(labels[key] for key in group_keys)] += value
    return dict(values)


def build_stage_rows(
    args: argparse.Namespace,
    *,
    end: datetime,
    window: str,
    metric_prefix: str,
    selector: str,
    group_keys: Sequence[str],
    metric_family: str,
    scope: str,
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    queries = {
        "success_count": f'sum by ({",".join(group_keys)}) (increase({metric_prefix}_count{{{selector},result="success"}}[{window}]))',
        "success_sum": f'sum by ({",".join(group_keys)}) (increase({metric_prefix}_sum{{{selector},result="success"}}[{window}]))',
        "success_p50": f'histogram_quantile(0.50, sum by (le,{",".join(group_keys)}) (increase({metric_prefix}_bucket{{{selector},result="success"}}[{window}])))',
        "success_p95": f'histogram_quantile(0.95, sum by (le,{",".join(group_keys)}) (increase({metric_prefix}_bucket{{{selector},result="success"}}[{window}])))',
    }
    values: dict[str, dict[tuple[str, ...], float]] = {}
    for name, query in queries.items():
        result = query_prometheus(args.prometheus_url, query, timestamp=end)
        values[name] = aggregate_vector(result, group_keys)
    groups = sorted(set().union(*(set(value) for value in values.values())))
    rows: list[dict[str, Any]] = []
    for group in groups:
        row = dict(zip(group_keys, group))
        for name, data in values.items():
            value = data.get(group, math.nan)
            row[name] = None if math.isnan(value) else value
        row["metric_family"] = metric_family
        row["scope"] = scope
        rows.append(row)
    return rows, queries


def build_prometheus_report(args: argparse.Namespace, start: datetime, end: datetime) -> dict[str, Any]:
    window = f"{(end - start).total_seconds():g}s"
    selector = label_matchers(args)
    base = f"{METRIC_PREFIX}_total"
    common = {"time": end.isoformat(), "window": window, "selector": selector}
    queries = {
        "started": f'sum by ({",".join(GROUP_KEYS)}) (increase({base}{{{selector},milestone="gateway_route_ready",result="started"}}[{window}]))',
        "route_ready_success": f'sum by ({",".join(GROUP_KEYS)}) (increase({base}{{{selector},milestone="gateway_route_ready",result="success"}}[{window}]))',
        "visible_success_count": f'sum by ({",".join(GROUP_KEYS)}) (increase({METRIC_PREFIX}_duration_seconds_count{{{selector},milestone="first_worker_result_visible",result="success"}}[{window}]))',
        "visible_success_sum": f'sum by ({",".join(GROUP_KEYS)}) (increase({METRIC_PREFIX}_duration_seconds_sum{{{selector},milestone="first_worker_result_visible",result="success"}}[{window}]))',
        "visible_success_p50": f'histogram_quantile(0.50, sum by (le,{",".join(GROUP_KEYS)}) (increase({METRIC_PREFIX}_duration_seconds_bucket{{{selector},milestone="first_worker_result_visible",result="success"}}[{window}])))',
        "visible_success_p95": f'histogram_quantile(0.95, sum by (le,{",".join(GROUP_KEYS)}) (increase({METRIC_PREFIX}_duration_seconds_bucket{{{selector},milestone="first_worker_result_visible",result="success"}}[{window}])))',
    }
    values: dict[str, dict[tuple[str, ...], float]] = {}
    for name, query in queries.items():
        result = query_prometheus(args.prometheus_url, query, timestamp=end)
        values[name] = aggregate_vector(result, GROUP_KEYS)
    groups = sorted(set().union(*(set(value) for value in values.values())))
    rows = []
    for group in groups:
        row = dict(zip(GROUP_KEYS, group))
        for name, data in values.items():
            value = data.get(group, math.nan)
            row[name] = None if math.isnan(value) else value
        rows.append(row)
    gateway_stage_rows, gateway_stage_queries = build_stage_rows(
        args,
        end=end,
        window=window,
        metric_prefix=STAGE_METRIC_PREFIX,
        selector=f'{selector},service="gateway"',
        group_keys=STAGE_GROUP_KEYS,
        metric_family="gateway_v3",
        scope=selector,
    )
    runner_selector = f'{selector},service="runner"'
    runner_stage_rows, runner_stage_queries = build_stage_rows(
        args,
        end=end,
        window=window,
        metric_prefix=STAGE_METRIC_PREFIX,
        selector=runner_selector,
        group_keys=STAGE_GROUP_KEYS,
        metric_family="runner_v3",
        scope=selector,
    )
    stage_rows = gateway_stage_rows + runner_stage_rows
    gateway_stage_overall_rows, gateway_stage_overall_queries = build_stage_rows(
        args,
        end=end,
        window=window,
        metric_prefix=STAGE_METRIC_PREFIX,
        selector=f'{selector},service="gateway"',
        group_keys=("service", "stage"),
        metric_family="gateway_v3",
        scope=selector,
    )
    runner_stage_overall_rows, runner_stage_overall_queries = build_stage_rows(
        args,
        end=end,
        window=window,
        metric_prefix=STAGE_METRIC_PREFIX,
        selector=runner_selector,
        group_keys=("service", "stage"),
        metric_family="runner_v3",
        scope=selector,
    )
    stage_overall_rows = gateway_stage_overall_rows + runner_stage_overall_rows
    stage_queries = {
        "gateway_v3": gateway_stage_queries,
        "runner_v3": runner_stage_queries,
        "gateway_v3_overall": gateway_stage_overall_queries,
        "runner_v3_overall": runner_stage_overall_queries,
    }
    return {
        "window": common,
        "queries": queries,
        "rows": rows,
        "stage_queries": stage_queries,
        "stage_rows": stage_rows,
        "stage_overall_rows": stage_overall_rows,
    }


_KV_RE = re.compile(r'(?P<key>[a-zA-Z][a-zA-Z0-9_]*)=(?P<value>"(?:\\.|[^"\\])*"|[^\s]+)')


def _decode_log_item(item: Any) -> dict[str, Any] | None:
    if isinstance(item, Mapping):
        data = item.get("data", item)
        if isinstance(data, str):
            try:
                decoded = json.loads(data)
                if isinstance(decoded, Mapping):
                    return {**decoded, "_truncated": bool(item.get("truncated")), "_row_id": decoded.get("@id", "")}
            except json.JSONDecodeError:
                return {"@message": data, "_truncated": bool(item.get("truncated")), "_row_id": item.get("@id", "")}
        if isinstance(data, Mapping):
            return {**data, "_truncated": bool(item.get("truncated")), "_row_id": data.get("@id", item.get("@id", ""))}
    return None


def parse_log_message(fields: Mapping[str, Any]) -> dict[str, str]:
    message = str(fields.get("@message", fields.get("message", "")))
    parsed: dict[str, str] = {}
    for match in _KV_RE.finditer(message):
        value = match.group("value")
        if value.startswith('"') and value.endswith('"'):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                value = value[1:-1]
        parsed[match.group("key")] = value
    for key in ("schema_version", "kind", "action", "observation_id", "execution_request_id", "task_id", "request_id", "run_id", "de_id", "team_id_l1", "team_id_l3", "scenario", "source", "task_type", "milestone", "stage", "result", "reason_code", "error_summary", "first_worker_event_type", "first_visible_event_type", "slow", "slow_level", "duration_ms", "emitted_at_unix_milli"):
        if key in fields and key not in parsed and fields[key] is not None:
            parsed[key] = str(fields[key])
    parsed["_row_id"] = str(fields.get("_row_id", fields.get("@id", "")))
    parsed["_timestamp"] = str(fields.get("@timestamp", ""))
    return parsed


def parse_logcli_output(raw: str) -> tuple[list[dict[str, str]], bool]:
    try:
        payload = json.loads(raw)
        items = payload if isinstance(payload, list) else [payload]
    except json.JSONDecodeError:
        items = [json.loads(line) for line in raw.splitlines() if line.strip()]
    records: dict[str, dict[str, str]] = {}
    conflicts: list[dict[str, Any]] = []
    conflicted_ids: set[str] = set()
    incomplete = False
    for item in items:
        decoded = _decode_log_item(item)
        if decoded is None:
            continue
        incomplete = incomplete or bool(decoded.get("_truncated"))
        record = parse_log_message(decoded)
        if "schema_version" not in record or record.get("schema_version") != "3":
            continue
        observation_id = record.get("observation_id") or record.get("_row_id")
        if not observation_id:
            continue
        previous = records.get(observation_id)
        comparable = {key: value for key, value in record.items() if key not in {"_row_id", "_timestamp"}}
        previous_comparable = (
            {key: value for key, value in previous.items() if key not in {"_row_id", "_timestamp"}}
            if previous is not None
            else None
        )
        if previous is not None and previous_comparable != comparable:
            conflicts.append({"observation_id": observation_id, "previous": previous, "current": record})
            conflicted_ids.add(observation_id)
            continue
        records[observation_id] = record
    if conflicts:
        incomplete = True
    for observation_id, record in records.items():
        if observation_id in conflicted_ids:
            record["_conflict"] = "true"
    return list(records.values()), incomplete


def _raw_logcli_item_count(raw: str) -> int:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return sum(1 for line in raw.splitlines() if line.strip())
    if isinstance(payload, list):
        return len(payload)
    return 1 if payload else 0


def run_logcli(app: str, start: datetime, end: datetime, *, runner=subprocess.run) -> tuple[list[dict[str, str]], bool]:
    command = [
        "smc", "logcli", "query", app,
        "--pql", f'"{LOG_MARKER}"',
        "--start", start.isoformat(), "--end", end.isoformat(),
        "--limit", str(LOG_LIMIT), "--json",
    ]
    completed = runner(command, check=True, capture_output=True, text=True)
    records, incomplete = parse_logcli_output(completed.stdout)
    return records, incomplete or _raw_logcli_item_count(completed.stdout) >= LOG_LIMIT


def collect_log_window(
    app: str,
    start: datetime,
    end: datetime,
    *,
    runner=subprocess.run,
    minimum_window: timedelta = timedelta(seconds=1),
) -> tuple[list[dict[str, str]], bool]:
    """Query a window, recursively splitting any capped/truncated response."""
    batch, incomplete = run_logcli(app, start, end, runner=runner)
    duration = end - start
    capped = len(batch) >= LOG_LIMIT
    if not incomplete and not capped:
        return batch, False
    if duration <= minimum_window:
        return batch, True
    midpoint = start + duration / 2
    if midpoint <= start or midpoint >= end:
        return batch, True
    left, left_incomplete = collect_log_window(
        app, start, midpoint, runner=runner, minimum_window=minimum_window
    )
    right, right_incomplete = collect_log_window(
        app, midpoint, end, runner=runner, minimum_window=minimum_window
    )
    return left + right, left_incomplete or right_incomplete


def collect_logs(args: argparse.Namespace, start: datetime, end: datetime) -> tuple[list[dict[str, str]], bool]:
    records: list[dict[str, str]] = []
    incomplete = False
    current = start
    apps = (args.gateway_log_app, args.runner_log_app)
    while current < end:
        next_day = min(end, (current + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0))
        if next_day <= current:
            next_day = end
        for app in apps:
            if not app:
                continue
            batch, batch_incomplete = collect_log_window(app, current, next_day)
            records.extend(batch)
            incomplete = incomplete or batch_incomplete
        current = next_day
    filtered = []
    for record in records:
        if any(record.get(key) != value for key, value in (("scenario", args.scenario), ("de_id", args.de_id), ("task_type", args.task_type), ("source", args.source)) if value):
            continue
        if record.get("team_id_l1") not in args.team_id_l1:
            continue
        filtered.append(record)
    return filtered, incomplete


def write_jsonl(path: Path, records: Iterable[Mapping[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as stream:
        for record in records:
            stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def format_summary_count(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.3f}"


def build_outputs(output_dir: Path, prom: Mapping[str, Any], logs: Sequence[Mapping[str, str]], *, start: datetime, end: datetime, incomplete: bool) -> dict[str, Any]:
    failures = [
        record
        for record in logs
        if record.get("action") == "settled"
        and record.get("kind") in {"milestone", "stage"}
        and record.get("result") in {"failed", "missing"}
    ]
    slow = [
        record
        for record in logs
        if record.get("action") == "settled"
        and record.get("kind") in {"milestone", "stage"}
        and record.get("slow") == "true"
    ]
    metric_rows = prom.get("rows", [])
    metric_counts: dict[str, float | None] = {}
    for output_key, row_key in (
        ("started", "started"),
        ("route_ready_success", "route_ready_success"),
        ("visible_success", "visible_success_count"),
    ):
        values = [row.get(row_key) for row in metric_rows]
        metric_counts[output_key] = (
            None
            if not values or any(value is None or not math.isfinite(float(value)) for value in values)
            else sum(float(value) for value in values)
        )
    log_counts = Counter(
        record.get("result")
        for record in logs
        if record.get("kind") == "milestone" and record.get("action") == "settled"
    )
    log_visible_success = sum(
        1
        for record in logs
        if record.get("kind") == "milestone"
        and record.get("action") == "settled"
        and record.get("milestone") == "first_worker_result_visible"
        and record.get("result") == "success"
    )
    visible_metric_count = metric_counts["visible_success"]
    reconciliation = {
        "status": "incomplete" if incomplete or visible_metric_count is None else "differs" if abs(visible_metric_count - log_visible_success) > 1e-9 else "exact_match",
        "metric_counts": dict(metric_counts),
        "log_counts": {**dict(log_counts), "visible_success": log_visible_success},
        "note": "Prometheus increase is a scrape-window estimate; log emitted records are execution evidence.",
    }
    summary = {
        "start": start.isoformat(), "end": end.isoformat(), "incomplete": incomplete,
        "rows": prom.get("rows", []),
        "stage_rows": prom.get("stage_rows", []),
        "stage_overall_rows": prom.get("stage_overall_rows", []),
        "failure_count": len(failures),
        "slow_count": len(slow),
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output_dir / "reconciliation.json").write_text(json.dumps(reconciliation, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_jsonl(output_dir / "failures.jsonl", failures)
    write_jsonl(output_dir / "slow_tasks.jsonl", slow)
    lines = [
        "# SRE Startup V3 周报",
        "",
        f"窗口：`{start.isoformat()}` ～ `{end.isoformat()}`（半开区间）",
        "",
        f"数据完整性：`{'incomplete' if incomplete else 'complete'}`",
        "",
        "## 总体",
        "",
        f"- Route Ready started：{format_summary_count(metric_counts['started'])}",
        f"- Route Ready success：{format_summary_count(metric_counts['route_ready_success'])}",
        f"- 首可见 Worker 结果 success：{format_summary_count(metric_counts['visible_success'])}",
        f"- 失败/缺失日志：{len(failures)}",
        f"- 慢任务（>300s）：{len(slow)}",
        "",
        "## 首可见耗时（按 scenario / DE / task_type）",
        "",
        "| scenario | de_id | task_type | count | P50(s) | P95(s) |",
        "|---|---|---|---:|---:|---:|",
    ]
    for row in prom.get("rows", []):
        def format_value(value: Any) -> str:
            return "N/A" if value is None else f"{value:.3f}"

        lines.append(
            "| {scenario} | {de_id} | {task_type} | {count} | {p50} | {p95} |".format(
                scenario=row.get("scenario", "unknown"),
                de_id=row.get("de_id", "unknown"),
                task_type=row.get("task_type", "unknown"),
                count=format_value(row.get("visible_success_count")),
                p50=format_value(row.get("visible_success_p50")),
                p95=format_value(row.get("visible_success_p95")),
            )
        )
    lines.extend(
        [
            "",
            "## Gateway / Runner 阶段汇总",
            "",
            "| metric family | scope | service | stage | samples | P50(s) | P95(s) |",
            "|---|---|---|---|---:|---:|---:|",
        ]
    )
    for row in prom.get("stage_overall_rows", []):
        lines.append(
            "| {metric_family} | {scope} | {service} | {stage} | {count} | {p50} | {p95} |".format(
                metric_family=row.get("metric_family", "unknown"),
                scope=row.get("scope", "unknown"),
                service=row.get("service", "unknown"),
                stage=row.get("stage", "unknown"),
                count=format_summary_count(row.get("success_count")),
                p50=format_summary_count(row.get("success_p50")),
                p95=format_summary_count(row.get("success_p95")),
            )
        )
    lines.extend(
        [
            "",
            "Gateway / Runner 均使用 V3 stage 指标及相同归因筛选，默认 SRE 21/22；各阶段样本数可能不同，分位数不可相加。阶段明细见 `summary.json` 的 `stage_rows`；失败和慢任务见 `failures.jsonl`、`slow_tasks.jsonl`；Prometheus 与日志对账见 `reconciliation.json`。",
        ]
    )
    (output_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return reconciliation


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", required=True, help="ISO timestamp with timezone")
    parser.add_argument("--end", required=True, help="ISO timestamp with timezone")
    parser.add_argument("--team-id-l1", default=os.environ.get("SRE_TEAM_IDS", ""))
    parser.add_argument("--scenario")
    parser.add_argument("--de-id")
    parser.add_argument("--task-type")
    parser.add_argument("--source")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--prometheus-url", default=DEFAULT_PROMETHEUS_URL)
    parser.add_argument("--gateway-log-app", default=DEFAULT_GATEWAY_LOG_APP)
    parser.add_argument("--runner-log-app", default=DEFAULT_RUNNER_LOG_APP)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        args.team_id_l1 = parse_team_filter(args.team_id_l1)
        start, end = parse_datetime(args.start), parse_datetime(args.end)
        if end <= start:
            raise ValueError("end must be after start")
        prom = build_prometheus_report(args, start, end)
        logs, logs_incomplete = collect_logs(args, start, end)
        reconciliation = build_outputs(args.output_dir, prom, logs, start=start, end=end, incomplete=logs_incomplete)
        manifest = {
            "schema_version": 1, "metric_version": 3, "start": start.isoformat(), "end": end.isoformat(),
            "team_id_l1": args.team_id_l1, "prometheus_url": args.prometheus_url,
            "gateway_log_app": args.gateway_log_app, "runner_log_app": args.runner_log_app,
            "log_marker": LOG_MARKER, "reconciliation_status": reconciliation["status"],
        }
        (args.output_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except (ValueError, IncompleteDataError, subprocess.CalledProcessError) as exc:
        print(f"startup weekly export failed: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
