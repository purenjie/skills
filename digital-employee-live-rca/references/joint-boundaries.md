# Gateway–Runner Joint Boundaries

Use this reference when a confirmed marker crosses services.

## Environment and current identity

- Production Gateway/Runner use `liveish/live` respectively, and the collector scopes each LogDB PQL to that environment.
- Test queries use Bromo service logs: `digitalemployee-gateway-test-sg` and `digitalemployee-workerrunner-test-sg`. Bromo has no remote time predicate, so the collector fetches once and locally filters application timestamps and the full requested ID.
- `execution_request_id` is the stable logical join key. `run_id` is the physical attempt and may change during recovery/reprovision; never join by time proximity alone.

## Identity bridge

| Direction | Boundary marker | Required correlation |
| --- | --- | --- |
| Gateway → Runner | `[runner_business_prepare] kafka_wait` | take `ticket_id` from this exact line |
| Runner → Gateway | `runner_gateway_execution_registered` | match the same `ticket_id/run_id`, then take `execution_request_id` from this exact line |
| Gateway → Sandbox | `[runner_execution_register] registered` / `[stream] send2agent` | stable `execution_request_id` and current route identity |
| Sandbox → Gateway | `[stream] first_agent_event` / `[stream] agent_event` | same `execution_request_id` |

Never use the first global `ticket_id` or `execution_request_id` from a multi-task log batch.

## Expected startup chain

1. Gateway ingress/classification.
2. Gateway DEMS/TCS preparation.
3. Gateway `[runner_business_prepare] kafka_wait ticket_id=...`.
4. Runner `runner_kafka_message_payload`.
5. Runner task/startup context.
6. Runner cold create or Q&A warm-pool acquire.
7. Runner `runner_gateway_execution_registered execution_request_id=...`.
8. Runner `runner_kafka_ticket_started`.
9. Gateway `[runner_execution_register] registered`.
10. Gateway first `[stream] agent_event`.
11. Gateway rendering and, for SeaTalk channels, `[seatalk_api]` result.

For current startup timing, `[startup_observation] schema_version=3` adds the V3 milestones `gateway_route_ready`, `first_worker_event`, and `first_worker_result_visible` plus service/stage observations. Treat `first_worker_result_visible` as a Gateway Worker-content boundary; continue to SeaTalk markers for user-visible delivery.

Registration and `started` can appear close together; use timestamps and IDs, not assumed file order.

## Failure routing

| Last confirmed fact | First missing/rejected successor | Responsibility focus |
| --- | --- | --- |
| Gateway before `kafka_wait` | task/TCS preparation failed | Gateway, DEMS, or TCS business write |
| Gateway `kafka_wait` | no correlated Runner payload marker | TCS/Kafka delivery, Runner consumer, payload-logging configuration, or query window |
| Runner payload | dependency/non-actionable outcome | Runner context/dependency/eligibility |
| Runner context | provisioning error | Sandbox, Gateway register, or worker bootstrap according to `reason` |
| Runner registered | no Gateway register marker | Runner → Gateway HTTP acceptance/binding |
| Gateway registered | no first Agent event | sandbox WebSocket, route identity, AgentHub/event stream |
| First Agent event | no rendering marker | Gateway Worker/card orchestration |
| Rendering marker | SeaTalk rejection | SeaTalk API/payload/token contract |

## Concurrency

Run Gateway and Runner first-pass queries concurrently only when both sides already have usable IDs. Otherwise:

1. query Gateway;
2. extract the `ticket_id` from `kafka_wait`;
3. query Runner;
4. extract `execution_request_id` from the matching registration;
5. query Gateway follow-up.

This dependency chain is intentionally sequential to preserve attribution.

## Round versus execution terminal

For runner-backed Q&A/RCA:

- `chat_response` or `knowledge_qa_completed` can end one user round;
- the same Runner execution may remain alive for follow-up;
- absence of Runner cleanup after these events is not a fault by itself.

Use `plan_completed`, `error`, explicit stop/cancel, and Gateway terminal-cleanup markers when diagnosing execution teardown.

## Minimum evidence

A joint RCA needs:

- the last successful marker before the boundary;
- the first rejected/missing successor or terminal outcome;
- IDs proving both markers belong to the same task/run;
- the reason/status field that explains the boundary when available.

If the chain stops because a dependent service has no evidence, state the exact missing marker and the next query required to close it.
