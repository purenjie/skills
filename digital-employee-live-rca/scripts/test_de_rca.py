#!/usr/bin/env python3

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import de_logs
import de_rca


def record(raw: str) -> de_logs.LogRecord:
    return de_logs.LogRecord(
        raw=raw,
        timestamp=de_logs._parse_timestamp(raw),
        source_index=0,
        line_index=0,
    )


def startup_line(*, conversation_id: str = "CONV_EXTERNAL_API_51939") -> str:
    payload = {
        "id": "event-1",
        "data": {
            "current_process": {
                "ticket_id": "96529208-4e53-4dd9-9b16-f7369c051ecd",
                "handling_payload": {
                    "agent_identifier": f"DE-SRE-00414#{conversation_id}#RCA",
                    "conversation_id": conversation_id,
                    "digital_employee_id": "DE-SRE-00414",
                    "req_message": "Please help review the ticket. SWP-10955654",
                    "scenario_type": "RCA",
                    "task_id": "RCA-SRE-42617",
                    "task_type": "故障管理",
                    "ticket_id": "96529208-4e53-4dd9-9b16-f7369c051ecd",
                },
            }
        },
    }
    return (
        "2026-08-10 17:37:47,703 INFO runner.kafka.worker "
        "runner_kafka_message_payload ticket_id=96529208-4e53-4dd9-9b16-f7369c051ecd "
        f"payload={json.dumps(payload, ensure_ascii=False)}"
    )


def classification_line(
    *,
    conversation_id: str = "CONV_EXTERNAL_API_51939",
    scenario_type: str = "RCA",
    message: str = "Please help review the ticket.",
) -> str:
    request = {
        "request_id": "9e1182d3-6c9f-497d-af9f-ac5d9cf86880",
        "team_name": "AZ/Storage/Observability",
        "conversation_id": conversation_id,
        "digital_employee_id": "DE-SRE-00414",
        "message": message,
        "sender_email": "DE-ASO-EKS@shopee.com",
    }
    response = {
        "code": 0,
        "message": "success",
        "data": {
            "classification_id": "cls_9c875c23c9424386ad12145e74cc7e51",
            "request_id": request["request_id"],
            "task": {
                "scenario_type": scenario_type,
                "task_type_id": "OPR-TYPE-10966",
                "task_type": "故障管理",
                "language": "English",
            },
            "direct_response": "",
        },
    }
    return (
        "2026-08-10 17:37:32,034 INFO runner.admission.service "
        "runner_classification_with_context_created "
        "url=http://worker-runner.dems.shopee.io/v1/intents/classify_with_context "
        f"request={json.dumps(request, ensure_ascii=False, separators=(',', ':'))} "
        f"response={json.dumps(response, ensure_ascii=False, separators=(',', ':'))} "
        f"request_id={request['request_id']} scenario_type={scenario_type} "
        "llm_reason=User delegates ticket review to the agent without explicitly asking how-to; "
        "this is work-handling intent for downstream routing. "
        "final_rationale=[] llm_engine=claude llm_model=claude-haiku-4-5@20251001 "
        "total_latency_ms=3124"
    )


class FakeClient:
    def __init__(self, responses):
        self.responses = {key: list(value) for key, value in responses.items()}
        self.calls = []

    def query(self, *, service, term, start, end, label):
        self.calls.append({"service": service, "term": term, "start": start, "end": end, "label": label})
        queued = self.responses.get(term, [])
        records = queued.pop(0) if queued else []
        self.responses[term] = queued
        return de_rca.QueryResult(
            service=service,
            term=term,
            start=start,
            end=end,
            file=Path(f"/tmp/{label}.json"),
            duration_ms=5,
            records=records,
        )


class DeRcaTest(unittest.TestCase):
    def test_intent_classification_uses_ticket_then_conversation(self):
        ticket = "96529208-4e53-4dd9-9b16-f7369c051ecd"
        conversation = "CONV_EXTERNAL_API_51939"
        client = FakeClient(
            {
                ticket: [[record(startup_line())]],
                conversation: [[record(classification_line())]],
            }
        )

        bundle = de_rca.diagnose_intent(
            client=client,
            task_id="RCA-SRE-42617",
            ticket_id=ticket,
            conversation_id=None,
            created_at="2026-08-10T17:37:32+08:00",
            question="为什么被识别为 RCA？",
        )

        self.assertEqual(bundle["status"], "confirmed")
        self.assertEqual(bundle["query_count"], 2)
        self.assertEqual([call["term"] for call in client.calls], [ticket, conversation])
        self.assertEqual(bundle["classification"]["scenario_type"], "RCA")
        self.assertEqual(bundle["classification"]["task_type"], "故障管理")
        self.assertIn("User delegates ticket review", bundle["classification"]["llm_reason"])
        self.assertEqual(bundle["responsibility_boundary"], "Runner admission intent classification (/v1/intents/classify_with_context)")

    def test_other_classifications_in_same_minute_are_excluded(self):
        ticket = "96529208-4e53-4dd9-9b16-f7369c051ecd"
        conversation = "CONV_EXTERNAL_API_51939"
        client = FakeClient(
            {
                ticket: [[record(startup_line())]],
                conversation: [[
                    record(classification_line(conversation_id="CONV_OTHER", scenario_type="OPERATION")),
                    record(classification_line()),
                ]],
            }
        )
        bundle = de_rca.diagnose_intent(
            client=client,
            task_id="RCA-SRE-42617",
            ticket_id=ticket,
            conversation_id=None,
            created_at="2026-08-10T17:37:32+08:00",
            question="调用 Runner 意图识别日志",
        )
        self.assertEqual(bundle["status"], "confirmed")
        self.assertEqual(bundle["classification"]["conversation_id"], conversation)
        self.assertEqual(bundle["classification"]["scenario_type"], "RCA")

    def test_classification_does_not_need_task_id_on_marker(self):
        parsed = de_rca.classification_from_record(record(classification_line()))
        self.assertIsNotNone(parsed)
        self.assertNotIn("task_id", parsed)
        self.assertEqual(parsed["conversation_id"], "CONV_EXTERNAL_API_51939")

    def test_startup_context_preserves_non_payload_recovery_marker(self):
        task_id = "RCA-SRE-42617"
        context_line = (
            "2026-08-10 17:37:47 INFO runner.ticket_execution.service "
            "runner_ticket_execution_task_context_resolved "
            f"ticket_id=ticket-1 task_id={task_id} "
            "conversation_id=CONV_EXTERNAL_API_51939"
        )

        startup = de_rca.startup_context(
            [record(context_line)],
            "ticket-1",
        )

        self.assertEqual(
            startup["marker"],
            "runner_ticket_execution_task_context_resolved",
        )

    def test_ambiguous_conversations_stop_without_guessing(self):
        ticket = "96529208-4e53-4dd9-9b16-f7369c051ecd"
        client = FakeClient(
            {
                ticket: [[
                    record(startup_line(conversation_id="CONV_A")),
                    record(startup_line(conversation_id="CONV_B")),
                ]]
            }
        )
        bundle = de_rca.diagnose_intent(
            client=client,
            task_id="RCA-SRE-42617",
            ticket_id=ticket,
            conversation_id=None,
            created_at="2026-08-10T17:37:32+08:00",
            question="为什么是 RCA？",
        )
        self.assertEqual(bundle["status"], "ambiguous")
        self.assertEqual(bundle["reason"], "ambiguous_conversation_id")
        self.assertEqual(len(client.calls), 1)

    def test_missing_marker_expands_once_to_fifteen_minutes(self):
        ticket = "96529208-4e53-4dd9-9b16-f7369c051ecd"
        conversation = "CONV_EXTERNAL_API_51939"
        client = FakeClient(
            {
                ticket: [[record(startup_line())]],
                conversation: [[], [record(classification_line())]],
            }
        )
        bundle = de_rca.diagnose_intent(
            client=client,
            task_id="RCA-SRE-42617",
            ticket_id=ticket,
            conversation_id=None,
            created_at="2026-08-10T17:37:32+08:00",
            question="为什么是 RCA？",
            max_queries=3,
        )
        self.assertEqual(bundle["status"], "confirmed")
        self.assertEqual(bundle["query_count"], 3)
        self.assertEqual(client.calls[-1]["start"], "2026-08-10 17:32")
        self.assertEqual(client.calls[-1]["end"], "2026-08-10 17:47")

    def test_query_budget_returns_unconfirmed(self):
        ticket = "96529208-4e53-4dd9-9b16-f7369c051ecd"
        conversation = "CONV_EXTERNAL_API_51939"
        client = FakeClient(
            {
                ticket: [[record(startup_line())]],
                conversation: [[]],
            }
        )
        bundle = de_rca.diagnose_intent(
            client=client,
            task_id="RCA-SRE-42617",
            ticket_id=ticket,
            conversation_id=None,
            created_at="2026-08-10T17:37:32+08:00",
            question="为什么是 RCA？",
            max_queries=2,
        )
        self.assertEqual(bundle["status"], "unconfirmed")
        self.assertEqual(bundle["reason"], "classification_marker_not_found")
        self.assertEqual(len(client.calls), 2)

    def test_second_level_timestamp_is_normalized_to_minute_windows(self):
        center = de_rca.parse_incident_time("2026-08-10T17:37:32+08:00")
        self.assertEqual(de_rca.minute_window(center, 1, 4), ("2026-08-10 17:36", "2026-08-10 17:41"))

    def test_generic_query_terms_are_rejected_before_logcli(self):
        with tempfile.TemporaryDirectory() as directory:
            client = de_rca.RealLogClient(Path(directory))
            with self.assertRaises(de_rca.QueryFailure):
                client.query(
                    service="runner",
                    term="intent",
                    start="2026-08-10 17:37",
                    end="2026-08-10 17:38",
                    label="forbidden",
                )

    def test_test_environment_reads_complete_runner_container_log(self):
        with tempfile.TemporaryDirectory() as directory:
            client = de_rca.RealLogClient(Path(directory), environment="test")
            completed = mock.Mock(returncode=0, stderr="")
            with mock.patch.object(de_rca.subprocess, "run", return_value=completed) as run:
                client.query(
                    service="runner",
                    term="ticket-123",
                    start="2026-08-10 17:37",
                    end="2026-08-10 17:38",
                    label="test-source",
                )

        command = run.call_args.args[0]
        self.assertEqual(
            command,
            [
                "smc",
                "services",
                "run",
                "digitalemployee-workerrunner-test-sg",
                "--env",
                "test",
                "--raw",
                "--timeout",
                "45",
                "--",
                "cat",
                "/data/log/digitalemployee-workerrunner-test-sg/daemon.log",
            ],
        )

    def test_live_environment_pql_is_scoped_to_runner_live(self):
        with tempfile.TemporaryDirectory() as directory:
            client = de_rca.RealLogClient(Path(directory))
            completed = mock.Mock(returncode=0, stderr="")
            with mock.patch.object(de_rca.subprocess, "run", return_value=completed) as run:
                client.query(
                    service="runner",
                    term="ticket-123",
                    start="2026-08-10 17:37",
                    end="2026-08-10 17:38",
                    label="live-source",
                )

        command = run.call_args.args[0]
        self.assertEqual(command[command.index("--pql") + 1], '@env = live AND ("ticket-123")')

    def test_note_is_written_from_confirmed_bundle_without_query(self):
        ticket = "96529208-4e53-4dd9-9b16-f7369c051ecd"
        conversation = "CONV_EXTERNAL_API_51939"
        client = FakeClient(
            {
                ticket: [[record(startup_line())]],
                conversation: [[record(classification_line())]],
            }
        )
        bundle = de_rca.diagnose_intent(
            client=client,
            task_id="RCA-SRE-42617",
            ticket_id=ticket,
            conversation_id=None,
            created_at="2026-08-10T17:37:32+08:00",
            question="为什么是 RCA？",
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle_path = de_rca.write_bundle(bundle, root / "bundle")
            with mock.patch.object(de_logs, "NOTE_DIR", root / "notes"):
                note_path = de_rca.write_note_from_bundle(
                    bundle_path=bundle_path,
                    reason="Runner 意图分类返回 RCA",
                    conclusion="Runner 将该请求识别为 RCA。",
                    boundary="Runner admission intent classification",
                    next_step="检查分类规则。",
                )
            self.assertTrue(note_path.exists())
            note = note_path.read_text(encoding="utf-8")
            self.assertIn("runner_classification_with_context_created", note)
            self.assertIn("query_count：2", note)
        self.assertEqual(len(client.calls), 2, "writing the note must not issue another query")

    def test_tampered_bundle_is_rejected(self):
        bundle = {
            "status": "confirmed",
            "identifiers": {"task_id": "RCA-SRE-1"},
            "evidence": [{"marker": "x"}],
            "created_at": "2026-08-10T17:37:32+08:00",
            "integrity": "bad",
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bundle.json"
            path.write_text(json.dumps(bundle), encoding="utf-8")
            with self.assertRaises(ValueError):
                de_rca.write_note_from_bundle(
                    bundle_path=path,
                    reason="x",
                    conclusion="x",
                    boundary="x",
                    next_step="x",
                )


if __name__ == "__main__":
    unittest.main()
