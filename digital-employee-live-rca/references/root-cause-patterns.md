# Root-cause Patterns

Use these only after a marker timeline exists. They are hypotheses that still require ID-correlated log evidence.

## Gateway

- `[de_execution_blocked]` with `record_kind=summary`: route from its explicit `stage`/`reason_code` and verify any split evidence by `diagnostic_id`; do not infer the cause from the marker name alone.
- `[startup_observation] schema_version=3`: use the reported `result` and stage/milestone timing. `first_worker_result_visible` proves displayable Worker content reached Gateway, not successful SeaTalk rendering.
- `send2agent` without `agent_event`: Gateway reached the Agent boundary; focus on route identity, AgentHub, sandbox connection, or runner execution.
- `agent_event` without rendering success/rejection: focus on Worker/card/direct-stream orchestration.
- SeaTalk rejection after a valid Agent event: user-visible failure is at the SeaTalk API/payload/token boundary.
- `knowledge_qa_completed`: expect card/stream update, not `send_text`; it ends a round but can leave runner-backed execution alive.
- `task_orch transition_conflict/require_status_conflict`: usually stale/duplicate click, actor mismatch, or state already changed; verify whether that is expected.
- `runner_event_stream restored_on_agent_connect`: expected recovery after Gateway restart/reconnect, not a fault by itself.

### Empty/orphan stream card

Evidence shape:

1. a Q&A/RCA path initializes a new interactive stream card;
2. context fallback re-routes the request to Operation;
3. Operation updates the old anchor through `[task_card] update_decision`;
4. the newly initialized stream receives no write.

`inherited_task_context_scrubbed` is an expected fallback, not the root cause. The fault boundary is card orchestration only when the new card is proved to have no matching update/finish while another anchor is updated.

Do not infer an orphan from `stream_id` occurrence count alone.

## Runner

- `runner_kafka_message_payload` may be absent because payload logging is conditional. An outcome, task-context, startup, registration, or sandbox marker is stronger evidence than payload-marker absence.
- `runner_ticket_execution_environment_mismatch` and `runner_ticket_execution_provisioning_skipped` are explicit guard/eligibility boundaries, not generic Sandbox failures.
- V3 `[startup_observation]` stages provide current startup evidence; a warm-pool miss and a V3-only long-tail observation are expected sampling behavior, not root causes.
- `runner_kafka_ticket_started`: successful startup outcome; confirm matching Gateway registration.
- `runner_kafka_ticket_dependency_error`: retryable dependency boundary; read `reason` and do not mislabel repeated consumption as the cause.
- `runner_kafka_ticket_non_actionable`: intentional or contractual rejection; verify the rejected condition was expected to be actionable.
- `runner_kafka_ticket_provisioning_error`: read `reason` first and route to cold create, Gateway register, or worker bootstrap.
- warm-pool acquire hit with no cold create: expected warm path.
- cold create succeeded but no registration: Runner → Gateway registration.
- registration succeeded but no `started`: final worker start/task injection.
- `inflight` or `duplicate_active`: expected dedupe unless lifecycle age/owner proves it is stale.

## Stale-resource attribution trap

A cleanup failure in task X's time window does not prove X failed.

Before attribution:

1. extract the failing `run_id/task_id/instance_id` from the error payload or request path;
2. compare it with X's active run;
3. look for that resource's own create/register chain;
4. attribute the failure to the owning task.

If the IDs differ, state: the active task's result and the stale resource's cleanup failure are separate events.

`Paused sandbox ... not found` for an old run commonly means idle auto-pause raced with explicit terminal destroy. Treat missing/paused sandbox cleanup as idempotency behavior only after proving the resource is old.

## Expected states that are not root causes alone

- context scrub or scenario flip;
- warm-pool hit/miss/refill;
- replay/restoration;
- `inflight`/`duplicate_active`;
- card heartbeat stop/reset;
- queued keepalive retry;
- terminal cleanup of a different run.

Always continue to the user-visible or contract-breaking consequence.
