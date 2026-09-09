#!/usr/bin/env python3

import argparse
import json
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

import de_logs


class DeLogsTest(unittest.TestCase):
    def test_live_pql_is_scoped_to_service_environment(self):
        gateway_pql = de_logs.build_pql(["TASK-1"], service="gateway")
        runner_pql = de_logs.build_pql(["TASK-1"], service="runner")

        self.assertEqual(gateway_pql, '@env = liveish AND ("TASK-1")')
        self.assertEqual(runner_pql, '@env = live AND ("TASK-1")')

    def test_default_logcli_window_is_one_hour(self):
        self.assertEqual(de_logs.DEFAULT_HOURS, 1)

    def test_test_environment_uses_bromo_service_logs_once(self):
        args = argparse.Namespace(
            environment="test",
            limit=100,
            timeout=30,
            start="2026-09-09 10:00",
            end="2026-09-09 10:05",
            hours=None,
            segment_minutes=1,
        )

        command = de_logs.build_command(
            de_logs.GATEWAY_APP, '"TASK-1"', args, args.start, args.end
        )

        self.assertEqual(
            command,
            [
                "smc",
                "services",
                "logs",
                "digitalemployee-gateway-test-sg",
                "--env",
                "test",
                "--wide",
                "--show-table=false",
            ],
        )
        self.assertEqual(de_logs.windows(args), [(None, None)])

    def test_test_window_excludes_unparseable_and_out_of_range_records(self):
        window = (
            de_logs.parse_minute("2026-09-09 10:00"),
            de_logs.parse_minute("2026-09-09 10:05"),
        )
        records = [
            de_logs.LogRecord("2026-09-09 10:02:00 task_id=TASK-1", de_logs.parse_minute("2026-09-09 10:02"), 0, 0),
            de_logs.LogRecord("2026-09-09 10:08:00 task_id=TASK-1", de_logs.parse_minute("2026-09-09 10:08"), 0, 1),
            de_logs.LogRecord("task_id=TASK-1", None, 0, 2),
        ]

        filtered = de_logs.filter_records_by_window(records, window)

        self.assertEqual([record.raw for record in filtered], [records[0].raw])

    def test_segment_queries_run_concurrently(self):
        active = 0
        max_active = 0
        lock = threading.Lock()

        def fake_run(*_args, **_kwargs):
            nonlocal active, max_active
            with lock:
                active += 1
                max_active = max(max_active, active)
            time.sleep(0.02)
            with lock:
                active -= 1
            return argparse.Namespace(returncode=0, stderr="")

        with tempfile.TemporaryDirectory() as directory:
            args = argparse.Namespace(
                out_dir=directory,
                dry_run=False,
                parallel=4,
                start="2026-07-27 10:00",
                end="2026-07-27 10:04",
                segment_minutes=1,
                limit=100,
                timeout=120,
                hours=None,
            )
            with mock.patch.object(de_logs.subprocess, "run", side_effect=fake_run):
                files = de_logs.run_query(
                    de_logs.GATEWAY_APP,
                    "gateway",
                    ["thread-1"],
                    args,
                    "test",
                )

        self.assertEqual(len(files), 4)
        self.assertGreaterEqual(max_active, 2)

    def test_joint_first_pass_queries_services_concurrently(self):
        active = 0
        max_active = 0
        lock = threading.Lock()

        def fake_query(_app, service, _terms, _args, _label):
            nonlocal active, max_active
            with lock:
                active += 1
                max_active = max(max_active, active)
            time.sleep(0.02)
            with lock:
                active -= 1
            return [Path(f"{service}.json")]

        empty_summary = {
            "files": [],
            "ids": {},
            "timeline": [],
            "signals": {},
            "_text": "",
        }
        args = argparse.Namespace(
            mode="joint",
            out_dir="/tmp/de-logs-test",
            dry_run=False,
            parallel=4,
            start="2026-07-27 10:00",
            end="2026-07-27 10:04",
            segment_minutes=1,
            limit=100,
            timeout=120,
            hours=None,
            task_id="task-1",
            thread_id="thread-1",
            request_id=None,
            message_id=None,
            execution_request_id=None,
            ticket_id="ticket-1",
            run_id=None,
            keyword=[],
            write_note=False,
        )
        with (
            mock.patch.object(de_logs, "parse_args", return_value=args),
            mock.patch.object(de_logs, "prepare_run_dir", return_value=Path("/tmp/de-logs-test/run")),
            mock.patch.object(de_logs, "run_query", side_effect=fake_query),
            mock.patch.object(de_logs, "summarize", return_value=empty_summary),
            mock.patch.object(de_logs, "write_run_summary"),
        ):
            de_logs.main()

        self.assertEqual(max_active, 2)

    def test_empty_text_has_no_boundary_hint(self):
        self.assertEqual(de_logs.analyze_signals("", "runner"), {})

    def test_environment_mismatch_is_reported(self):
        text = (
            '2026-07-27 10:00:00 runner_kafka_ticket_started '
            'ticket_id=t-1 {"@env":"liveish"}'
        )

        signals = de_logs.analyze_signals(text, "runner")

        self.assertIn("expected live", signals["environment_warning"])

    def test_test_logs_do_not_require_logdb_environment_field(self):
        text = (
            "2026-09-09 10:00:00 [runner_business_prepare] kafka_wait "
            "ticket_id=t-1"
        )

        signals = de_logs.analyze_signals(text, "gateway", environment="test")

        self.assertNotIn("environment_warning", signals)

    def test_ansi_level_prefix_is_not_treated_as_gateway_marker(self):
        line = (
            "\x1b[36m[INFO]\x1b[0m 2026-09-09 10:00:00 "
            "\x1b[36m[startup_observation]\x1b[0m schema_version=3 "
            "kind=stage action=settled stage=gateway_route_ready result=success"
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "logs.log"
            path.write_text(line + "\n", encoding="utf-8")

            text = de_logs.read_text([path])

        timeline = de_logs.extract_timeline(text, "gateway")

        self.assertIn("[INFO]", text)
        self.assertEqual(len(timeline), 1)
        self.assertIn("[startup_observation]", timeline[0])
        self.assertNotIn("[INFO]", timeline[0])
        signals = de_logs.analyze_signals(text, "gateway")
        self.assertIn("stage=gateway_route_ready", signals["startup_observation"])

    def test_blocked_diagnostic_summary_is_reduced_to_correlation_fields(self):
        text = (
            '2026-09-09 10:00:00 [de_execution_blocked] '
            '{"record_kind":"summary","diagnostic_id":"diag-1",'
            '"stage":"state_commit","reason_code":"redis_timeout","impact":"blocked"}'
        )

        signals = de_logs.analyze_signals(text, "gateway")

        self.assertEqual(
            signals["execution_blocked"],
            "[de_execution_blocked] record_kind=summary diagnostic_id=diag-1 "
            "stage=state_commit reason_code=redis_timeout",
        )

    def test_empty_structured_fields_do_not_capture_next_field_as_value(self):
        text = (
            "[startup_observation] schema_version=3 kind=stage action=settled "
            "request_id= run_id= de_id=DE-SRE-1 result=success error_summary=\"\""
        )

        self.assertNotIn("run_id", de_logs.extract_ids(text))
        self.assertIsNone(de_logs.extract_field(text, "request_id"))
        self.assertIsNone(de_logs.extract_field(text, "run_id"))
        self.assertNotIn("failure_like_hint", de_logs.analyze_signals(text, "gateway"))

    def test_current_runner_started_is_success(self):
        text = "\n".join(
            [
                "2026-07-27 10:00:00 runner_kafka_message_payload ticket_id=t-1",
                "2026-07-27 10:00:01 runner_gateway_execution_registered ticket_id=t-1 execution_request_id=req-1",
                "2026-07-27 10:00:02 runner_kafka_ticket_started ticket_id=t-1 task_id=QNA-1 run_id=r-1",
            ]
        )

        signals = de_logs.analyze_signals(text, "runner")

        self.assertEqual(signals["runner_result"], "started")
        self.assertIn("switch back to Gateway", signals["boundary_hint"])

    def test_latest_runner_outcome_wins_after_retry(self):
        text = "\n".join(
            [
                "2026-07-27 10:00:00 runner_kafka_ticket_dependency_error ticket_id=t-1 reason=temporary timeout",
                "2026-07-27 10:01:00 runner_kafka_ticket_started ticket_id=t-1",
            ]
        )

        signals = de_logs.analyze_signals(text, "runner")

        self.assertEqual(signals["runner_result"], "started")

    def test_conditional_payload_marker_absence_is_not_consumption_proof(self):
        text = (
            "2026-09-09 10:00:00 runner_kafka_worker_started "
            "topic=tss.process.created"
        )

        signals = de_logs.analyze_signals(text, "runner")

        self.assertIn("payload_logging_note", signals)
        self.assertNotEqual(
            signals.get("boundary_hint"),
            "Runner/Kafka before message consumption",
        )

    def test_json_records_are_sorted_and_structured_ids_are_extracted(self):
        payload = [
            {
                "timestamp": "2026-07-27T10:00:02+08:00",
                "message": "runner_kafka_ticket_started",
                "ticket_id": "ticket-1",
            },
            {
                "timestamp": "2026-07-27T10:00:01+08:00",
                "message": "runner_kafka_message_payload",
                "ticket_id": "ticket-1",
            },
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "logs.json"
            path.write_text(json.dumps(payload), encoding="utf-8")

            text = de_logs.read_text([path], exact_terms=["ticket-1"])

        self.assertLess(
            text.index("runner_kafka_message_payload"),
            text.index("runner_kafka_ticket_started"),
        )
        self.assertEqual(de_logs.extract_ids(text)["ticket_id"], ["ticket-1"])

    def test_logcli_data_wrapper_is_decoded(self):
        nested = {
            "@timestamp": 1785127201000,
            "@message": (
                "runner_kafka_ticket_started "
                "ticket_id=ticket-1 execution_request_id=req-1"
            ),
            "@env": "live",
        }
        payload = [
            {
                "data": json.dumps(nested),
                "truncated": False,
                "base64Encoded": False,
            }
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "logs.json"
            path.write_text(json.dumps(payload), encoding="utf-8")

            text = de_logs.read_text([path], exact_terms=["ticket-1"])

        self.assertIn("runner_kafka_ticket_started", text)
        self.assertEqual(de_logs.extract_ids(text)["execution_request_id"], ["req-1"])

    def test_short_tail_matches_are_excluded_without_full_id(self):
        records = [
            de_logs.LogRecord(
                raw="runner_kafka_ticket_started ticket_id=other-abc123",
                timestamp=None,
                source_index=0,
                line_index=0,
            )
        ]

        filtered = de_logs.filter_records(
            records,
            ["4893d190-2dea-42a5-897c-20703beabc123"],
        )

        self.assertEqual(filtered, [])

    def test_warm_pool_marker_is_in_runner_timeline(self):
        text = (
            "2026-07-27 10:00:00 qa_template_warm_pool_acquire_hit "
            "request_id=req-1 sandbox_id=s-1"
        )

        timeline = de_logs.extract_timeline(text, "runner")

        self.assertEqual(len(timeline), 1)
        self.assertIn("qa_template_warm_pool_acquire_hit", timeline[0])

    def test_joint_boundary_uses_id_on_matching_line(self):
        summary = {
            "_text": "\n".join(
                [
                    "ticket_id=stale-ticket unrelated cleanup",
                    "[runner_business_prepare] kafka_wait task_id=TASK-1 ticket_id=right-ticket",
                ]
            )
        }

        values = de_logs.correlated_ids(
            summary,
            marker_pattern=r"\[runner_business_prepare\]\s+kafka_wait",
            id_key="ticket_id",
        )

        self.assertEqual(values, ["right-ticket"])

    def test_multiple_boundary_ids_are_preserved_for_ambiguity_guard(self):
        summary = {
            "_text": "\n".join(
                [
                    "[runner_business_prepare] kafka_wait task_id=TASK-1 ticket_id=ticket-1",
                    "[runner_business_prepare] kafka_wait task_id=TASK-2 ticket_id=ticket-2",
                ]
            )
        }

        values = de_logs.correlated_ids(
            summary,
            marker_pattern=r"\[runner_business_prepare\]\s+kafka_wait",
            id_key="ticket_id",
        )

        self.assertEqual(values, ["ticket-1", "ticket-2"])
    def test_conversation_id_is_extracted_and_can_drive_runner_query(self):
        conversation_id = "CONV_EXTERNAL_API_51939"
        text = (
            "runner_classification_with_context_created "
            f"conversation_id={conversation_id} scenario_type=RCA"
        )
        ids = de_logs.extract_ids(text)
        self.assertEqual(ids["conversation_id"], [conversation_id])

        args = argparse.Namespace(
            keyword=[],
            ticket_id=None,
            conversation_id=conversation_id,
            task_id=None,
            run_id=None,
            execution_request_id=None,
        )
        self.assertEqual(de_logs.service_terms(args, "runner"), [conversation_id])

    def test_conversation_exact_filter_excludes_other_classifications(self):
        records = [
            de_logs.LogRecord(
                raw="runner_classification_with_context_created conversation_id=CONV_OTHER scenario_type=QNA",
                timestamp=None,
                source_index=0,
                line_index=0,
            ),
            de_logs.LogRecord(
                raw="runner_classification_with_context_created conversation_id=CONV_TARGET scenario_type=RCA",
                timestamp=None,
                source_index=0,
                line_index=1,
            ),
        ]
        filtered = de_logs.filter_records(records, ["CONV_TARGET"])
        self.assertEqual(len(filtered), 1)
        self.assertIn("scenario_type=RCA", filtered[0].raw)

    def test_redaction_covers_credentials(self):
        value = (
            "Authorization=Bearer secret-token "
            "api_key=abc connect_token=def "
            '"personal_token":"ghi"'
        )

        redacted = de_logs.redact_text(value)

        self.assertNotIn("secret-token", redacted)
        self.assertNotIn("api_key=abc", redacted)
        self.assertNotIn("connect_token=def", redacted)
        self.assertNotIn('"personal_token":"ghi"', redacted)

    def test_write_note_requires_confirmed_fields(self):
        args = argparse.Namespace(
            write_note=True,
            dry_run=False,
            note_reason=None,
            note_conclusion=None,
            note_boundary=None,
        )

        with self.assertRaises(SystemExit):
            de_logs.write_note(args, [])

    def test_dash_heavy_pql_keeps_full_term_and_tail(self):
        term = "4893d190-2dea-42a5-897c-20703be17181"

        pql = de_logs.build_pql([term])

        self.assertIn(f'"{term}"', pql)
        self.assertIn('"20703be17181"', pql)

    def test_generic_pql_term_is_rejected(self):
        with self.assertRaises(SystemExit):
            de_logs.build_pql(["error"])

    def test_run_summary_is_structured_and_redacted(self):
        summaries = [
            {
                "ids": {"task_id": ["TASK-1"]},
                "timeline": ["marker Authorization=Bearer secret-token"],
                "signals": {"reason": "api_key=abc"},
                "files": ["/tmp/raw.json"],
                "_text": "raw logs are intentionally omitted",
            }
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = de_logs.write_run_summary(Path(directory), summaries)
            payload = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(payload["identifiers"]["task_id"], ["TASK-1"])
        self.assertNotIn("_text", payload["summaries"][0])
        self.assertNotIn("secret-token", json.dumps(payload))
        self.assertNotIn("api_key=abc", json.dumps(payload))


if __name__ == "__main__":
    unittest.main()
