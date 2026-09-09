---
name: digital-employee-live-rca
description: Investigate Digital Employee Gateway and Worker Runner online incidents from ID-correlated logs and produce a concise, evidence-backed root cause. Use for SeaTalk callback/reply/card/approval failures, Gateway task startup and rendering issues, Runner Kafka/task-context/provisioning/warm-pool/bootstrap failures, execution registration or reprovision problems, intent classification, and Gateway–Runner handoff incidents.
---

# Digital Employee Live RCA

Find the first unexpected break, rejection, or missing successor in the target-environment marker chain. Prefer a short, ID-correlated evidence chain over collecting the full lifecycle.

This skill is agent-independent. It requires only a shell, Python 3, `smc logcli` for production, `smc services logs` for the verified test source, and `smc seatalk` when the RCA notification contract applies; it does not depend on an agent-specific extension or tool protocol.

## Environment selection, truth, and safety

- Default to the online production environments when the user does not name an environment: Gateway `shopee.engineering_infra.infra_products.digital_employee.gateway` / `liveish`, Runner `shopee.engineering_infra.infra_products.digital_employee.worker_runner` / `live`.
- If the user explicitly says `test` / `测试环境`, query the test deployment. Do not fall back to `liveish` or `live`, and do not treat a production-app PQL miss as evidence about test.
  - Use `scripts/de_logs.py ... --environment test`. It reads the active Bromo test services: Gateway `digitalemployee-gateway-test-sg` and Runner `digitalemployee-workerrunner-test-sg` with `smc services logs -e test`.
  - Bromo has no remote time predicate. The collector fetches each service once, then retains only rows with a parseable application timestamp inside the requested window and the full requested ID. Unparseable container metadata and stale rows are excluded from RCA evidence.
  - Test Space can currently list the Gateway/Runner applications but may fail to resolve them to LogDB. `smc -c shopeetest logcli --base-url https://space.test.shopee.io` is optional only when that mapping becomes queryable; a mapping/auth failure is a query boundary, not an incident fact.
- Online service logs are the runtime evidence. Local logs and source code can explain expected behavior but cannot prove what happened in the target environment.
- The current Gateway contracts are documented in `docs/tech_docs/content/docs/reference/log-troubleshooting.md`, `de-core-execution-chain.md`, and `task-startup-metrics.md`; the current Runner markers are defined by `runner/kafka/worker.py`, `runner/ticket_execution/service.py`, `runner/agent_instance/client.py`, and `docs/log-troubleshooting.md`. When an older reference and a current marker disagree, use the target-environment line and current code as the source of truth, and call out rollout/version uncertainty.
- Treat diagnostic API fields and script `signals` as routing hints. Confirm conclusions from marker lines and their complete fields.
- Redact tokens, secrets, credentials, and Authorization headers.
- Never convert `unconfirmed`, `ambiguous`, or `query_failed` into a confirmed root cause.

## Start contract

Before querying, capture:

- the symptom in the user's words;
- the narrowest reliable incident time or bounded window;
- the strongest available ID;
- the fact or missing boundary that would close the investigation.

Use a targeted fact contract for a requested field, response, card decision, count, or marker:

> Find `<field/marker>` in `<service>` for `<ID/window>`; it proves `<user-facing fact>`.

Otherwise use a boundary contract:

> Find the first expected successor after `<known ID/marker>` that is absent, rejected, or reports a terminal reason.

## Choose the shortest route

| Question shape | Primary join key | First command |
| --- | --- | --- |
| Why RCA/QNA/OPERATION, task type, or `llm_reason` | `conversation_id` | `scripts/de_rca.py diagnose --target intent_classification` |
| Gateway-only callback, card, approval, rendering, or SeaTalk failure | `thread_id`, then `request_id/task_id` | `scripts/de_logs.py gateway` |
| Runner-only Kafka, context, provisioning, warm-pool, bootstrap, or registration failure | `run_id`, then `ticket_id/task_id` | `scripts/de_logs.py runner` |
| Gateway–Runner handoff or unknown owner | `thread_id` when available | `scripts/de_logs.py joint` |

ID relationships:

- Gateway: `thread_id` → `conversation_id` → `request_id` → `task_id` → `execution_request_id` → `message_id`.
- Runner: `ticket_id` → `conversation_id` → `task_id` → `run_id` → `execution_request_id`.
- Intent classification uses `conversation_id` because classification can precede `task_id/ticket_id/run_id` on the marker.
- Cross-service attribution must take `ticket_id` or `execution_request_id` from the exact boundary line, never the first global ID in a multi-task window.

If multiple candidate conversations, tickets, runs, or executions remain after exact filtering, return `ambiguous`; do not choose the first.

## Fast workflow

1. State the contract and use the strongest ID with a 3–5 minute window around the incident.
2. Select the target-environment log source first. For the default production environments, run exactly one route from the table. For test, use the script's Bromo collector; do not use production LogDB as a fallback. Resolve `<skill-dir>` from this `SKILL.md` location; do not copy scripts elsewhere.
3. Read the structured evidence bundle from `de_rca.py`, or the terminal summary plus raw JSON files from `de_logs.py`.
4. Stop immediately when the requested fact is proved or the first responsibility boundary has a confirmed terminal reason.
5. If an expected marker is missing, widen once to 15 minutes. Widen further only to a user-provided bounded incident window.
6. Load only the reference for the first observed boundary, then cross at most one additional responsible boundary.
7. Classify the outcome as `confirmed`, `unconfirmed`, `ambiguous`, or `query_failed`.
8. Once the RCA conclusion is formed, call the notification script immediately. Report its delivery result with the RCA response.

Intent classification:

```bash
python3 <skill-dir>/scripts/de_rca.py diagnose \
  --target intent_classification \
  --created-at "<ISO-8601 timestamp>" \
  --question "<user's exact question>" \
  --ticket-id "<ticket_id>" \
  --task-id "<task_id>"
```

The deterministic classifier path uses `ticket_id/task_id` only to recover `conversation_id` from the strongest matching Runner task/payload/context marker, then matches `runner_classification_with_context_created`. Because Kafka payload logging is conditional, the evidence bundle preserves the actual recovery marker instead of assuming `runner_kafka_message_payload`. It allows at most 3 queries by default, expands the initial 5-minute window once, and returns a bounded evidence bundle.

General log collection:

```bash
python3 <skill-dir>/scripts/de_logs.py gateway --thread-id <thread_id> \
  --start "YYYY-MM-DD HH:MM" --end "YYYY-MM-DD HH:MM"

python3 <skill-dir>/scripts/de_logs.py runner --run-id <run_id> \
  --start "YYYY-MM-DD HH:MM" --end "YYYY-MM-DD HH:MM"

python3 <skill-dir>/scripts/de_logs.py joint --thread-id <thread_id> \
  --start "YYYY-MM-DD HH:MM" --end "YYYY-MM-DD HH:MM"

# Test environment: Gateway/Runner Bromo daemon.log, locally bounded by timestamp.
python3 <skill-dir>/scripts/de_logs.py joint --environment test --thread-id <thread_id> \
  --start "YYYY-MM-DD HH:MM" --end "YYYY-MM-DD HH:MM"
```

Time contract:

- Without `--start/--end`, the collector queries the most recent `1h` (`--hours 1`).
- For a bounded range, pass both values in local Asia/Shanghai time: `--start "2026-09-01 00:00" --end "2026-09-01 01:00"`. The parser also accepts `T` between date and time.
- Production ranges are split into small independent `smc logcli` segments. Test Bromo logs are fetched once and filtered locally by application timestamp, so a test query over a historical window depends on the active service retaining that window.

Useful options:

- `--segment-minutes 1`: retry only a saturated interval at finer granularity.
- `--parallel 8`: run independent time segments concurrently.
- `--limit 100`: RCA safety cap per production segment; a segment reaching 100 is saturated, so split that interval before concluding absence. The script clamps larger values to 100.
- `--keyword <rare-term>`: use only a distinctive ID or rare marker. Generic terms are rejected.
- `--dry-run`: inspect exact `smc logcli` commands without querying.
- `--out-dir <dir>`: isolate raw JSON and summary artifacts for this incident.
- `--environment test`: uses the verified Bromo test services instead of Space LogDB. `de_rca.py diagnose` accepts the same option for intent classification.

Use the default recent-hours window only when no reliable timestamp exists. Never combine a broad window with generic keywords.

## Accuracy and stopping rules

- A PQL miss is not proof of absence. Inspect exact-filtered JSON; UUID-like terms may require the script's short-tail retrieval followed by full-ID filtering.
- Production PQL is automatically scoped to the service's current environment: Gateway `@env = liveish`, Runner `@env = live`. Test Bromo output normally has no LogDB `@env`; do not flag that as environment mixing.
- The collector strips terminal ANSI sequences before marker extraction. A Gateway line such as `[INFO] ... [startup_observation]` must be reported as `[startup_observation]`, not `[INFO]`.
- If a segment reaches the query limit, retry only that interval with smaller segments.
- Use complete JSON fields, not truncated terminal tables.
- Once a complete marker answers the question and contains the correlated ID, do not query it again under another ID.
- Prefer explicit terminal `reason/status`, rejection, or a missing expected successor over generic words such as `failed` in payload text.
- Confirm that any failing `run_id/task_id/instance_id` belongs to the incident. Stale cleanup in the same window is a separate incident.
- Context scrub, warm-pool acquire, replay, `inflight`, and `duplicate_active` are states, not root causes by themselves.
- Keep dependency-following sequential: Gateway `kafka_wait` → Runner payload; Runner registration → Gateway follow-up.
- Query Gateway and Runner concurrently only when both sides already have usable correlated IDs.

## Boundary shortcuts

Gateway:

- No ingress marker: callback/HTTP delivery, signature, route, environment, or window.
- `[de_execution_blocked]`: read the JSON `record_kind=summary`, `diagnostic_id`, `stage`, `reason_code`, `impact`, and `exchanges`; large diagnostics also emit evidence chunks, which must be reassembled by `diagnostic_id` and verified before interpreting.
- `[startup_observation] schema_version=3`: use the structured `kind/action/milestone/stage/result` fields and the stable execution IDs for current startup timing. `first_worker_result_visible` means Gateway received displayable Worker content; it does not mean the SeaTalk write succeeded.
- `[stream] send2agent` without `[stream] agent_event`: route identity, AgentHub, sandbox connectivity, or runner execution.
- `[stream] agent_event` without user-visible success: Worker/card/direct-stream orchestration, then `[seatalk_api]`.
- `[runner_business_prepare] kafka_wait`: Gateway completed the handoff; switch using the `ticket_id` on that line.
- Runner-backed first turns are injected by Runner. After Agent registration, missing `send2agent` can be expected; missing `agent_event` after registration points to the sandbox process/event boundary.

Runner:

- `runner_kafka_message_payload` is conditional on payload logging configuration and selected outcomes. Its absence is not proof that Kafka was not consumed; prefer a `runner_kafka_ticket_<status>` outcome, task-context marker, or downstream startup marker.
- `runner_kafka_ticket_ignored` / `parse_error`: Kafka event was rejected or could not be parsed; inspect the status/reason and commit fields.
- `runner_ticket_execution_environment_mismatch` / `runner_ticket_execution_provisioning_skipped`: Runner rejected or skipped the event at an explicit eligibility/environment boundary.
- `runner_kafka_ticket_dependency_error`: retryable dependency boundary unless a later terminal outcome supersedes it.
- `runner_kafka_ticket_non_actionable`: inspect the exact eligibility/context rejection.
- `runner_kafka_ticket_provisioning_error`: use `reason` and stage to choose sandbox, Gateway registration, or bootstrap.
- `runner_kafka_ticket_started`: startup succeeded; confirm matching Gateway registration.
- `qa_template_warm_pool_acquire_hit`: missing cold create is expected.
- `runner_gateway_execution_registered`: return to Gateway using its correlated `execution_request_id`.
- `execution_request_id` is the stable logical execution identity; `run_id` identifies a physical attempt and can change on Operation recovery/reprovision. Never attribute a cleanup or event to the active task from time proximity alone.

For runner-backed Q&A/RCA, `chat_response` or `knowledge_qa_completed` can end a round while the execution remains alive. Do not infer cleanup failure from these events alone.

## References

Load only after the first timeline identifies the relevant boundary:

- Gateway rendering, cards, admission, task flow, or SeaTalk: `references/gateway-log-troubleshooting.md`.
- Runner Kafka, context, provisioning, warm pool, bootstrap, registration, or reprovision: `references/runner-log-troubleshooting.md`.
- Cross-service handoff: `references/joint-boundaries.md`.
- Known attribution traps and expected states: `references/root-cause-patterns.md`.

## SeaTalk notification

Default recipient: `renjie.pu@shopee.com`.

The user has explicitly pre-authorized one automatic notification to this fixed recipient after each completed RCA. This authorization applies only to this skill, this recipient, and the completed RCA summary. Do not ask for confirmation, change the recipient, send unrelated messages, or retry a failed delivery unless the user explicitly requests it.

Send one notification for every terminal outcome. The Markdown includes status, question, key IDs, conclusion, root cause or unconfirmed reason, responsibility boundary, at most 3 evidence lines, elapsed time, and next step. The script writes the exact sent message to the incident run directory for audit.

```bash
python3 <skill-dir>/scripts/notify_rca.py \
  --output <incident-run-dir>/seatalk-notification.md \
  --status confirmed \
  --question "<question>" \
  --identifier "task_id=<task_id>" \
  --conclusion "<conclusion>" \
  --reason "<root cause or unconfirmed reason>" \
  --boundary "<responsibility boundary>" \
  --evidence "<time / service / marker / key fields / judgement>" \
  --duration "<elapsed time>" \
  --next-step "<next step>"
```

Call the script exactly once after the RCA reaches a terminal outcome. A SeaTalk failure does not alter the RCA status; report it separately as notification failure and do not retry automatically.

## Output

Reply in Chinese unless asked otherwise:

```text
结论：
根因：
证据链：
- 时间 / 服务 / marker / 关键字段 / 判断
责任边界：
影响范围：
下一步：
知识库：
- <created note path, only when created>
通知：
- <sent | send failed>
```

For runner-backed execution, include available durations for Gateway handoff → Runner payload, provision/acquire → registration, registration → first Agent event, and first Agent event → SeaTalk result.
