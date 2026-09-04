# Interruption and Maintenance Control

Read this reference when bugs, help requests, approvals, confirmations, or small fixes repeatedly fragment protected work.

The goal is not zero interruption. It is to stop every new event from automatically receiving execution rights and to reduce future problem inflow.

## Execution-right gate

Before switching tasks, establish:

- who is blocked;
- what is affected and whether impact is continuing or spreading;
- whether data, security, or multi-user risk exists;
- whether a usable workaround exists.

| Lane | Evidence | Execution right |
| --- | --- | --- |
| Immediate incident | Continuing impact, data/security risk, spread, or multiple people materially blocked | Preempt now. |
| Same-day response | One person blocked with a workaround, or delay has a real same-day cost | Next maintenance window. |
| Weekly maintenance | Limited impact, non-blocking defect, routine confirmation, or small repair | Weekly maintenance budget. |
| Observe/defer | Low frequency or impact, clear workaround, or repair cost exceeds value | Capture; no current execution right. |

Discovery is not permission to execute. An acknowledgement can preserve responsiveness without surrendering attention:

```text
收到，我先记录。如果当前没有持续影响、数据风险或多人阻塞，
我会放到今天的维护窗口处理；如果影响正在扩大，请补充范围和 workaround 情况。
```

## Protected block and justified preemption

Default to the first available focus block for the daily 主动推进 item. Only an immediate incident or existing hard commitment may preempt it.

Before switching for a justified interruption, record:

```markdown
- 被打断的工作：
- 当前做到：
- 恢复时第一步：
- 新的具体时段：
```

The interruption is not fully handled until displaced work has a new concrete slot. If the incident consumes the day, use the next working day's first block as the final fallback.

## Maintenance budget

Use one or two bounded windows, usually 30–45 minutes, for triage, reviews, confirmations, and small repairs. Batch related issues when they share context.

Defaults:

- no more than one or two maintenance windows per day;
- no more than two or three independent maintenance commitments per week;
- work above the budget must displace a named commitment.

Do not use a maintenance window as permission for an unlimited queue.

## Recurrence and prevention

On the third occurrence of the same failure class, assess a mechanism-level fix. Group symptoms only when they share a real mechanism, such as ownership ambiguity, state convergence, interface resilience, observability, regression coverage, or self-service gaps.

Estimate prevention value using:

```text
recurrence frequency × repair/context-switch cost × blast radius
```

When justified, leave one proportional prevention asset: a regression test, clearer error, key log, metric, alert, runbook, retry/timeout/idempotency rule, automated check, or self-service path.

During review, distinguish repair output from flow improvement. Do not turn a ten-minute low-frequency repair into a multi-day redesign.
