"""Tests for the self-contained weekly metric exporter."""

import json
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

from export_sre_startup_weekly import (
    build_outputs,
    IncompleteDataError,
    aggregate_vector,
    build_stage_rows,
    build_prometheus_report,
    query_prometheus,
    parse_datetime,
    parse_logcli_output,
    parse_team_filter,
)


class WeeklyExporterTest(unittest.TestCase):
    def test_parse_datetime_requires_timezone(self):
        self.assertEqual(parse_datetime("2026-09-07T00:00:00+08:00").utcoffset().seconds, 8 * 3600)
        with self.assertRaises(ValueError):
            parse_datetime("2026-09-07T00:00:00")

    def test_parse_team_filter(self):
        self.assertEqual(parse_team_filter("21, 22"), ["21", "22"])
        with self.assertRaises(ValueError):
            parse_team_filter(" , ")

    def test_parse_logcli_nested_json_and_deduplicates(self):
        message = (
            "[startup_observation] schema_version=3 kind=milestone action=settled "
            "observation_id=v3:exec-1 task_id=TASK-1 execution_request_id=exec-1 "
            "team_id_l1=21 milestone=first_worker_result_visible result=success slow=true"
        )
        raw = json.dumps([
            {"data": json.dumps({"@id": "row-1", "@message": message, "@timestamp": 1})},
            {"data": json.dumps({"@id": "row-2", "@message": message, "@timestamp": 1})},
        ])
        records, incomplete = parse_logcli_output(raw)
        self.assertFalse(incomplete)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["task_id"], "TASK-1")
        self.assertEqual(records[0]["slow"], "true")

    def test_parse_log_message_decodes_quoted_task_type(self):
        message = (
            '[startup_observation] schema_version=3 kind=stage action=settled '
            'observation_id=v3:exec-1 task_type="Rate Limit Operation" '
            'm0_at_unix_milli=1725811200000'
        )
        records, incomplete = parse_logcli_output(json.dumps([{"@message": message}]))
        self.assertFalse(incomplete)
        self.assertEqual(records[0]["task_type"], "Rate Limit Operation")
        self.assertEqual(records[0]["m0_at_unix_milli"], "1725811200000")

    def test_aggregate_vector_rejects_invalid_shape(self):
        with self.assertRaises(IncompleteDataError):
            aggregate_vector([{"metric": {"scenario": "QNA"}, "value": [1, "NaN"]}])

    def test_build_outputs_marks_metric_log_difference(self):
        output_dir = self._temporary_directory()
        prom = {"rows": [{"started": 1.0, "route_ready_success": 1.0, "visible_success_count": 2.0}]}
        logs = [{
            "kind": "milestone", "action": "settled", "milestone": "first_worker_result_visible", "result": "success",
        }]
        reconciliation = build_outputs(
            output_dir,
            prom,
            logs,
            start=datetime(2026, 9, 7, tzinfo=timezone.utc),
            end=datetime(2026, 9, 14, tzinfo=timezone.utc),
            incomplete=False,
        )
        self.assertEqual(reconciliation["status"], "differs")
        self.assertTrue((output_dir / "summary.md").exists())
        self.assertTrue((output_dir / "reconciliation.json").exists())

    def test_build_stage_rows_preserves_metric_family_and_scope(self):
        result = [{
            "metric": {"scenario": "RCA", "service": "runner", "stage": "runner_worker_start"},
            "value": [1, "3"],
        }]
        with patch("export_sre_startup_weekly.query_prometheus", return_value=result):
            rows, queries = build_stage_rows(
                SimpleNamespace(prometheus_url="https://example.invalid"),
                end=datetime(2026, 9, 9, tzinfo=timezone.utc),
                window="1d",
                metric_prefix="digital_employee_task_startup_stage_v3_latency_seconds",
                selector='service="runner",team_id_l1=~"21|22"',
                group_keys=("scenario", "service", "stage"),
                metric_family="runner_v3",
                scope='team_id_l1=~"21|22"',
            )

        self.assertEqual(rows[0]["metric_family"], "runner_v3")
        self.assertEqual(rows[0]["scope"], 'team_id_l1=~"21|22"')
        self.assertIn('team_id_l1=~"21|22"', queries["success_count"])

    def test_report_uses_v3_and_same_attribution_for_both_services(self):
        args = SimpleNamespace(
            prometheus_url="https://example.invalid", team_id_l1=["21", "22"],
            scenario="RCA", de_id="de-1", task_type="故障管理", source="seatalk",
        )
        def response(url, query, *, timestamp):
            self.assertIn("_v3_", query)
            for matcher in ('team_id_l1=~"21|22"', 'scenario="RCA"',
                            'de_id="de-1"', 'task_type="故障管理"', 'source="seatalk"'):
                self.assertIn(matcher, query)
            service = "runner" if 'service="runner"' in query else "gateway"
            return [{"metric": {"scenario": "RCA", "de_id": "de-1", "task_type": "故障管理",
                                "service": service, "stage": "runner_dems_startup_context"},
                     "value": [1, "3"]}]
        with patch("export_sre_startup_weekly.query_prometheus", side_effect=response):
            report = build_prometheus_report(
                args, datetime(2026, 9, 9, tzinfo=timezone.utc), datetime(2026, 9, 10, tzinfo=timezone.utc),
            )
        gateway, runner = report["stage_rows"]
        self.assertEqual(gateway["scope"], runner["scope"])
        self.assertEqual(runner["metric_family"], "runner_v3")
        self.assertEqual(runner["de_id"], "de-1")
        self.assertEqual(runner["task_type"], "故障管理")

    def test_prometheus_rejects_partial_or_empty_v3_response(self):
        from io import BytesIO

        for payload in (
            {"status": "success", "isPartial": True, "data": {"resultType": "vector", "result": [{}]}},
            {"status": "success", "data": {"resultType": "vector", "result": []}},
        ):
            with self.subTest(payload=payload), self.assertRaises(IncompleteDataError):
                query_prometheus(
                    "https://example.invalid", "digital_employee_task_startup_stage_v3_latency_seconds_count",
                    timestamp=datetime(2026, 9, 10, tzinfo=timezone.utc), retries=1,
                    opener=lambda *a, **kw: BytesIO(json.dumps(payload).encode()),
                )

    @staticmethod
    def _temporary_directory():
        import tempfile

        return __import__("pathlib").Path(tempfile.mkdtemp(prefix="startup-v3-test-"))


if __name__ == "__main__":
    unittest.main()
