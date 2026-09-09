# Gateway Marker Decision Guide

Use this reference only after the first Gateway timeline exists. Gateway production logs use `liveish`. For the current test deployment, use the skill script with `--environment test`; it reads Bromo service logs from `digitalemployee-gateway-test-sg` and applies the time/ID filter locally.

## Current observability contracts

- Production PQL must be scoped with `@env = liveish`. The collector adds this automatically; a LogDB miss in another environment is not evidence about Gateway liveish.
- Current startup drill-down uses `[startup_observation] schema_version=3`. Read `kind`/`action` plus `milestone` or `stage`, `result`, `reason_code`, `task_id`, `execution_request_id`, `request_id`, `run_id`, and the timestamp fields. The V3 milestones are `gateway_route_ready`, `first_worker_event`, and `first_worker_result_visible`.
- `first_worker_result_visible` means Gateway received displayable Worker content. It does not wait for SeaTalk card/message write success; continue to `[seatalk_api]` for the user-visible result.
- Current V3 stage names include `gateway_dems_create_task`, `gateway_tcs_ticket`, `gateway_tcs_process`, `worker_started_to_sandbox_websocket_routable`, `gateway_route_ready_to_first_worker_event`, and `gateway_first_worker_event_to_first_worker_result_visible`. Runner stages are documented in the Runner reference and should be joined by the same execution identity.
- `[de_execution_blocked]` is a structured diagnostic, not a generic Worker failure. Prefer `record_kind=summary`; use its `diagnostic_id`, `stage`, `reason_code`, `impact`, and `exchanges`. If a large record emits evidence chunks, collect all parts by `diagnostic_id`, order by `part_index`, and verify `part_count`, encoded length, and SHA-256 before decoding. Count the summary once.
- `[runner_event_handoff] event_channel_closed_after_settled_round` is a normal close after the round has already settled; do not treat it like `event_channel_closed_without_terminal`, which requires checking whether a terminal event was missing during the grace window.
- ANSI color sequences can surround the log level and marker. Remove the control bytes before matching; `[INFO]` is a level, while `[startup_observation]` and `[de_execution_blocked]` are the business markers.

## Marker index

### Ingress

| Marker | Proves | Key fields / next step |
| --- | --- | --- |
| `[http_req]` | HTTP request reached Gateway and completed | `request_id`, `method`, `path`, request/response body; `/metrics` is excluded |
| `[binding]` | Handler binding or validation result | `json_error`, `validation_error`, `handler_error` |
| `[seatalk_cb]` | SeaTalk callback parsing | `recv`, `invalid_signature`, `decode_*_failed`, `unhandled_event` |
| `[external_trigger_http]` / `[monitoring_alert_http]` | Internal trigger reached its authenticated handler | authorization, request fields, accepted marker |

### Routing and Agent boundary

| Marker | Proves | Key fields / next step |
| --- | --- | --- |
| `[route] local/cross_instance/k1_not_found` | Gateway route decision | `agent`, `thread`, `target_gw`; `k1_not_found` is a route failure |
| `[pubsub]` | Cross-instance transfer | require forwarded → received → worker/frame push |
| `[stream] send2agent` | A frame was written to the Agent WebSocket boundary | `request_id`, `event`, `agent_id`, `source_request_id` |
| `[stream] first_agent_event` | First sandbox event for this request/execution arrived | start of sandbox output latency |
| `[stream] agent_event` | Agent event entered BotService | classify by `event` before checking rendering |
| `[stream] terminal_agent_event` | One request/render round ended | not necessarily task or Runner execution terminal |
| `[agent_hub]` | Connection, request map, identity, buffering, or drain result | `v2_event_unknown_request`, `v2_event_agent_mismatch`, `event_channel_full` |
| `[runner_event_stream] restored_on_agent_connect` | Gateway restored a runner event stream after reconnect/restart | correlate `task_id`, `execution_request_id`, `run_id`, `instance_id` |

### Admission and task startup

| Marker | Proves | Key fields / next step |
| --- | --- | --- |
| `[tcs_admission]` | Existing-ticket claim/binding decision | distinguish no binding, DM skip/context, claim failure, thread mismatch |
| `[runner_classify]` | Runner active classification result | `scenario_type`, `task_type`, confirmation/approval decision |
| `[compass_key_balance]` | Credential/key availability admission | `decision`, `key_unavailable`, `code`, `type`; never expose tokens |
| `[runner_business_prepare]` | Gateway-owned DEMS/TCS preparation | follow TCS/DEMS API markers; `kafka_wait` is the Runner handoff |
| `[tcs_api | create_ticket]` / `[tcs_api | process_webhook]` | TCS business write result | status, response, duration |
| `[dems_task_api | create_task]` / `[dems_task_api | review_task]` | DEMS business write result | response code, task ID, lifecycle write |
| `[startup_trace]` | Cross-service startup milestone | `trace_id`, `task_id`, `execution_request_id`, `stage`, `result`, `reason_code` |
| `[startup_observation] schema_version=3` | Current V3 startup observation | `kind`, `action`, `milestone`/`stage`, `result`, stable execution IDs, timing fields; use for current startup drill-down |
| `[de_execution_blocked]` | Execution was blocked at an explicit Gateway diagnostic boundary | summary/evidence record kind, `diagnostic_id`, `stage`, `reason_code`, `impact`, exchanges |
| `[task_startup_diagnosis]` / `[task_diagnosis]` | Diagnostic snapshot persistence/read issue | diagnostic aid only; confirm with runtime markers |

### Runner callbacks

| Marker | Proves | Key fields / next step |
| --- | --- | --- |
| `[runner_execution_started_http] accepted` | Runner reported Kafka execution start to Gateway | correlate `ticket_id`, `run_id` |
| `[runner_execution_started]` | Gateway projected DOING to TCS | inspect replay or TCS failure |
| `[runner_execution_http] registered` | Runner registration HTTP was accepted | not yet proof that sandbox events arrived |
| `[runner_execution_register] registered` | AgentHub request/event stream was installed | canonical `execution_request_id` |
| `[runner_execution_register] replay_stream_restored` | repeated register restored a lost in-memory stream | expected replay recovery |
| `[runner_execution_status_http] accepted` | Runner reported startup failure | continue to `[runner_execution_status] settled` |
| `[runner_execution_status] settled` | Gateway projected startup failure to DEMS/card | verify user-visible projection |
| `[runner_event_handoff] event_channel_closed_without_terminal` | runner event stream closed after grace/shutdown | inspect route reconnect and terminal-blocked state |
| `[runner_terminal_cleanup]` | Gateway notified Runner terminal cleanup | distinguish notified, duplicate, retry, blocked |

### Card and SeaTalk rendering

| Marker | Proves | Key fields / next step |
| --- | --- | --- |
| `[worker]` | Event payload validation and rendering orchestration | missing fields, unmarshal, send/update failure |
| `[task_card] update_decision` | update existing card vs send a new card | `decision`, `reason`, `message_id`, user/card sequence |
| `[task_orch]` | task guard or transition result | conflicts, stale click, rating, collect-info binding |
| `[task_card_heartbeat]` | card title liveness only | not a task-state transition |
| `[direct_execution_stream]` | Q&A/RCA stream lifecycle | `update_failed`, `finish_retry`, queued keepalive, `stop` |
| `[direct_execution_rating]` | delayed Q&A/RCA rating lifecycle | schedule, claim, send, feedback, unknown result |
| `[seatalk_api]` | SeaTalk OpenAPI result | endpoint, status, `seatalk_code`, rejection body |

### Newer execution surfaces

| Marker | Scope |
| --- | --- |
| `[external_task_execution]` / `[headless_task]` | unattended external task startup, terminal event, DEMS/TCS/Runner cleanup |
| `[sop_execution]` / `[sop_execution_status_http]` | durable SOP execution binding, status projection, completion acknowledgement, stop races |
| `[external_trigger]` / `[external_trigger_bootstrap]` | SeaTalk group/thread bootstrap and fixed-task startup |

## Shortest scenario chains

### Callback or reply missing

`[http_req]` → `[seatalk_cb] recv` → `[route]` → `[stream] send2agent` → `[stream] agent_event` → `[worker]` → `[seatalk_api]`

- Missing ingress: delivery/signature/window.
- `send2agent` with no event: AgentHub/sandbox/Runner execution.
- Event with no visible result: Worker/card/SeaTalk.

### Card did not update

`[stream] agent_event` → `[worker]` → `[task_card] update_decision` or `[direct_execution_stream]` → `[seatalk_api]`

- Use `task_id`, `message_id`, `stream_id`, and `execution_request_id`.
- For Q&A/RCA `knowledge_qa_completed`, expect stream/card update, not `send_text`.
- `finish_retry` means terminal stream projection is retrying transport/decode failures.
- SeaTalk business rejection is terminal for that projection and is not retried as a transport error.

### Q&A/RCA rating missing

`knowledge_qa_completed` → `[direct_execution_rating] result_scheduled` → `claimed` → `sent|send_unknown|claim_released`

- `result_reference_missing`: no schedulable result reference.
- `question_accepted`: a new question resets the pending candidate for that scenario.
- `send_unknown`: do not resend automatically; SeaTalk receipt is uncertain.

### Gateway → Runner startup

`[runner_classify] accepted` → DEMS/TCS preparation → `[runner_business_prepare] kafka_wait`

`kafka_wait` must carry the `ticket_id` used for Runner lookup. Do not keep searching Gateway for sandbox provisioning after this line.

### Runner returned but user still sees nothing

Runner registration → `[runner_execution_http]` → `[runner_execution_register]` → `[stream] first_agent_event` → rendering marker → `[seatalk_api]`

- Registration without first event: sandbox WebSocket/AgentHub/event-stream restoration.
- First event without rendering success/rejection: Worker/card path.
- Rendering request with SeaTalk rejection: SeaTalk contract/payload/token boundary.

### Runner-backed follow-up or approval stalled

`[direct_runtime_control] dispatched|pending_reprovision_enqueued` → `[runner_pending_outbound]` → Runner reprovision → `[runner_execution_register]` → flush

Check that control frames use the current task's stable `execution_request_id`, not a click request ID or previous run ID.

### Headless or SOP execution

- Headless: external ingress/startup → Runner registration → `[headless_task]` terminal projection → Runner cleanup.
- SOP: `external_execution_required` → `[sop_execution]` binding/waiting projection → `[sop_execution_status_http]` → Worker completion acknowledgement.

Do not expect SeaTalk markers for a headless channel.

## Terminal distinctions

- `chat_response`, `plan_info_required`, `plan_proposal`, and `knowledge_qa_completed` can end one runner-backed round while the sandbox execution remains reusable.
- `plan_completed` and `error` normally drive task/Runner terminal behavior, subject to business-side effects succeeding.
- `knowledge_qa_completed` does not by itself require Runner terminal cleanup.

## High-risk attribution checks

- Match `execution_request_id` between registration, Agent event, control frame, and rendering.
- Match failure `run_id/instance_id` to the task before blaming the active task.
- Treat replay restoration, queued keepalive, heartbeat stop, and card send-new decisions as state transitions, not faults by themselves.
