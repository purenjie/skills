# Worker Runner Marker Decision Guide

Use this reference only after the first Runner timeline exists. Runner production logs use `live`. For the current test deployment, use the skill script with `--environment test`; it reads Bromo service logs from `digitalemployee-workerrunner-test-sg` and filters the fetched output locally.

## Current source and identity contract

- Production PQL must be scoped with `@env = live`. The collector adds this automatically.
- `execution_request_id` is the stable logical execution identity across Gateway/Runner. `run_id` identifies a physical attempt and can change on Operation recovery or reprovision. Use `run_id` to distinguish attempts only after joining it to the stable execution/task.
- `runner_kafka_message_payload` is controlled by Runner payload-logging configuration and is also emitted selectively for important outcomes. Its absence is not proof that Kafka was not consumed. Prefer `runner_kafka_ticket_<status>`, task-context, startup, registration, or sandbox markers.
- Test Bromo rows normally have no LogDB `@env` field. That is expected for the test source and must not produce a live-environment warning.

## Outcome first

Runner emits its final Kafka handling marker dynamically as `runner_kafka_ticket_<status>`.

| Outcome marker | Meaning | Next step |
| --- | --- | --- |
| `runner_kafka_ticket_started` | startup completed and the execution became active | confirm `runner_gateway_execution_registered`, then return to Gateway |
| `runner_kafka_ticket_provisioning_error` | sandbox create, Gateway register, or worker start failed; offset is normally committed | read `reason`, then inspect the nearest stage markers |
| `runner_kafka_ticket_dependency_error` | a retryable dependency failed; offset is not committed | read `reason`; inspect Gateway upsert, DEMS, Redis/lifecycle, or Kafka dependency |
| `runner_kafka_ticket_non_actionable` | event was intentionally rejected/skipped | inspect environment, eligibility, source context, task type, route, and `reason` |
| `runner_kafka_ticket_inflight` | same execution is already provisioning | expected dedupe unless it remains stuck past the provisioning timeout |
| `runner_kafka_ticket_duplicate_active` | another active run already owns the task | expected dedupe; correlate the active `run_id` |
| `runner_kafka_ticket_ignored` | parsed Kafka event was intentionally ignored | inspect event type/source and `reason`; commit is normally recorded |
| `runner_kafka_ticket_parse_error` | Kafka event could not be parsed | inspect parse `reason` and topic/partition/offset; commit behavior is explicit on the line |

There is no current success marker named `runner_kafka_ticket_provisioning_succeeded`.

## Marker index

### Intent classification before task creation

| Marker | Proves | Key fields / next step |
| --- | --- | --- |
| `runner_classification_with_context_created` | Runner `/v1/intents/classify_with_context` classified a conversational request | `conversation_id`, DE ID, request message, response `scenario_type/task_type`, `llm_reason` |
| `runner_task_type_classify_finished` | Runner `/v1/intents/classify` classified an SWP/Jira template without conversation context | source type, team/template, matched task type |

Intent classification commonly happens before `task_id`, `ticket_id`, and `run_id` exist on the classifier marker. Do not infer that classification was absent because a task/run query did not return the marker.

Use this correlation chain:

```text
ticket_id or task_id
  → matching Kafka/DEMS payload
  → conversation_id on that same task payload
  → runner_classification_with_context_created for that conversation and minute
```

When multiple classification markers coexist in the same minute, filter by complete `conversation_id` and then confirm `digital_employee_id` and request message. Do not choose the first global classification marker.

`runner_ticket_catalog_validation_skipped reason=trusted_upstream_task_type` occurs after task creation. It proves Runner startup trusted the task type in the payload; it does not prove that `/v1/intents/classify_with_context` was never called earlier.

| Marker | Proves | Key fields / next step |
| --- | --- | --- |
| `runner_kafka_worker_started` | consumer worker started | mode, topic, group, payload logging |
| `runner_kafka_message_payload` | Kafka message reached Runner | topic, partition, offset, key/payload |
| `runner_kafka_worker_skipped_ticket_execution_disabled` | execution consumer was disabled | configuration boundary |
| `runner_ticket_execution_environment_mismatch` | payload/runtime environment guard rejected the event | compare payload and runtime environment |
| `runner_ticket_execution_provisioning_skipped` | provisioning path explicitly skipped the event | inspect eligibility/source/task-type `reason`; do not call it a Sandbox failure |
| `runner_ticket_execution_handler_lookup_failed` | DE/source handler resolution failed | source identity/directory |
| `runner_ticket_execution_inflight_blocked` | lifecycle saw the same creating run | inspect lifecycle age and run ownership |

### Task context and startup context

| Marker | Proves | Key fields / next step |
| --- | --- | --- |
| `runner_gateway_task_upsert_started` | Runner needed Gateway task/conversation resolution | request, ticket, task type |
| `runner_gateway_task_upsert_succeeded` | Gateway returned task context | correlate task/conversation/execution IDs |
| `runner_gateway_task_upsert_failed` | task-context dependency failed | `reason`, `retryable`; usually leads to dependency/non-actionable outcome |
| `runner_ticket_execution_task_context_resolved` | executable task context is known | `task_context_source=payload|gateway_upsert` |
| `runner_dems_startup_context_fetch_started` | DEMS startup-context fetch began | task, run, DE |
| `runner_dems_startup_context_fetch_succeeded` | startup context or SCC fallback resolved | template, team, `reason=dems_startup_context|scc_sandbox_fallback` |
| `runner_ticket_catalog_validation_skipped` | trusted upstream task type was accepted | expected behavior with reason |

The startup-context fetch can occur twice: preliminary route resolution and final credential/template resolution. Two successful pairs are not a duplicate-execution fault.

### Q&A warm pool

| Marker | Meaning |
| --- | --- |
| `qa_template_warm_pool_acquire_hit` | an existing idle sandbox was leased; cold create markers are not expected for this execution |
| `qa_template_warm_pool_acquire_miss` | continue through cold sandbox create |
| `qa_template_warm_pool_refill_created` | background refill created an idle sandbox; do not attribute it to the active ticket without matching IDs |
| `qa_template_warm_pool_release_live` | terminal cleanup released live warm-pool ownership |
| `qa_template_warm_pool_*_failed` | warm-pool store/refill/cleanup issue; correlate sandbox and DE before attribution |

Warm-pool refill logs use a synthetic `warm_pool_*` request ID and can coexist with a user task. They are not automatically part of that task.

### Cold sandbox and worker startup

| Marker | Proves | Key fields / next step |
| --- | --- | --- |
| `runner_sandbox_create_request` | cold `Sandbox.create` started | `request_id`, template, timeout; ticket/run may need correlation through execution request ID |
| `runner_sandbox_create_request_detail` | redacted DEBUG create detail | use only when INFO evidence is insufficient |
| `runner_sandbox_retry_scheduled` | a retryable sandbox call is waiting for another attempt | attempt, max attempts, reason |
| `runner_sandbox_api` / `runner_sandbox_api_error` | Sandbox HTTP boundary result | status, endpoint, duration, redacted response |
| `runner_sandbox_created` | cold sandbox exists | sandbox ID and cold-start duration |
| `runner_sandbox_worker_bootstrap_starting` | connect/exec worker bootstrap started | request ID, sandbox ID |
| `runner_sandbox_worker_bootstrap_finished` | connect/exec returned | exit code, stdout/stderr |
| `runner_sandbox_worker_bootstrap_failed` | bootstrap returned non-zero | sandbox ID, command, exit code |
| `runner_sandbox_first_chat_request` | first task message was prepared for injection | execution/task/run IDs; payload is redacted |

For warm-pool hit, start the active chain at acquire → Gateway register → first-chat/worker start. Do not require `runner_sandbox_created`.

### Runner → Gateway registration

| Marker | Proves | Key fields / next step |
| --- | --- | --- |
| `gateway_execution_register_binding_not_ready_retrying` | Gateway binding was not yet visible and Runner will retry | attempt/max/delay; expected transient race |
| `gateway_execution_register_binding_not_ready_exhausted` | binding remained unavailable after retries | Gateway binding/registration boundary |
| `runner_gateway_execution_registered` | Gateway accepted the execution registration | `ticket_id`, `task_id`, `run_id`, `instance_id`, `execution_request_id` |
| `runner_gateway_execution_status_notify_failed` | startup failure could not be projected to Gateway | Gateway availability/auth/contract |

`runner_gateway_execution_registered` is the return boundary. After it, inspect Gateway by the `execution_request_id` on the same line.

### Reprovision

| Marker | Meaning |
| --- | --- |
| `runner_task_reprovision_requested` | Gateway requested a new or reused execution |
| `runner_task_reprovision_liveness_check_failed` | old active sandbox liveness could not be confirmed |
| `runner_task_reprovision_stale_active_detected` | active DB lifecycle pointed to a non-running sandbox; Runner will terminate stale state |
| `runner_task_reprovision_completed` | reprovision produced an execution |
| `runner_task_reprovision_rejected` / `runner_task_reprovision_failed` | inspect reason and retryability |

### Terminal and cleanup

| Marker | Meaning |
| --- | --- |
| `runner_terminal_destroy_finished` | terminal cleanup attempted to destroy/release the instance |
| `runner_ticket_execution_start_cleanup_finished` | partial startup failure cleanup completed |
| `qa_template_warm_pool_release_live` | warm-pool live lease was released |

Verify the embedded `run_id/instance_id` before attributing cleanup failure to a task in the same time window.

### V3 startup observations

Runner emits `[startup_observation] schema_version=3` observations for current startup stages such as `runner_dems_startup_context`, `runner_pre_provision_prepare`, `runner_sandbox_cold_create`, `runner_sandbox_warm_pool_acquire`, `runner_gateway_register`, and `runner_worker_start`. Join them by `execution_request_id` plus task/DE fields. A warm-pool miss has no separate latency sample; only a successful acquire hit or acquire failure is observed. Long-tail `process_created_to_runner_consumed` observations can be V3-only, so absence of a legacy histogram sample is not a failed execution.

## Shortest scenario chains

### Was the Kafka task consumed?

`runner_kafka_message_payload` (when payload logging is enabled) → one `runner_kafka_ticket_<status>`

- No payload marker: Kafka/TCS delivery, consumer state, environment, logging configuration, or wrong window; do not treat it as a standalone non-consumption proof.
- Payload but no outcome: worker crash/iteration error, process interruption, or query truncation.

### Successful cold startup

`message_payload` → task context → startup context → `runner_sandbox_create_request` → `runner_sandbox_created` → `runner_gateway_execution_registered` → worker bootstrap/first-chat → `runner_kafka_ticket_started`

The exact register/bootstrap ordering reflects the current implementation: Gateway registration occurs before the final worker task injection is considered complete.

### Successful warm startup

`message_payload` → task context → startup context → `qa_template_warm_pool_acquire_hit` → `runner_gateway_execution_registered` → worker bootstrap/first-chat → `runner_kafka_ticket_started`

### Provisioning error

Start at `runner_kafka_ticket_provisioning_error reason=...`.

- Sandbox/create wording: inspect create/retry/API markers.
- Gateway register wording: inspect binding retry/exhaustion and Gateway registration endpoint.
- Worker start/bootstrap wording: inspect bootstrap and first-chat markers.
- Check `instance_id` on the outcome; a partially created sandbox may require cleanup.

### Dependency error

Start at `runner_kafka_ticket_dependency_error reason=...`.

Typical preceding boundaries:

- `runner_gateway_task_upsert_failed`;
- startup-context/DEMS call failure;
- lifecycle repository or provisioning lock failure;
- Kafka poll/commit dependency.

Because offset is normally not committed, repeated attempts are expected. Diagnose the dependency reason, not the repetition.

### Non-actionable

Start at `runner_kafka_ticket_non_actionable reason=...`.

Check, in order:

1. event type/source/environment eligibility;
2. DE/source identity;
3. task type extraction;
4. Gateway task context;
5. route/template decision.

`non_actionable` can be an intentional skip; call it a fault only if the rejected condition contradicts the expected contract for this ticket.

## Timing boundaries

- Gateway `kafka_wait` → `runner_kafka_message_payload`: TCS/Kafka delivery.
- `runner_kafka_message_payload` → task context resolved: Runner parse/context.
- cold create request → sandbox created: Sandbox platform.
- warm acquire hit → Gateway registration: warm activation path.
- Gateway registration retry/start → `runner_gateway_execution_registered`: Runner → Gateway.
- registration → `runner_kafka_ticket_started`: worker task injection/final startup.
