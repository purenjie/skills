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
| Same-day response | One person blocked with a workaround, or delay has a real same-day cost | Use a feasible response window; if none exists, surface the capacity conflict. |
| Routine maintenance | Limited impact, non-blocking defect, routine confirmation, or small repair | Agree timing against actual workload and response expectations. |
| Observe/defer | Low frequency or impact, clear workaround, or repair cost exceeds value | Capture; no current execution right. |

Discovery is not permission to execute. An acknowledgement can preserve responsiveness without surrendering attention:

```text
收到，我先确认影响和优先级，再结合已有安排确认处理时间，暂不承诺今天完成。
如果有持续影响、数据风险或多人阻塞，请补充范围和 workaround 情况，方便判断是否需要立即处理。
```

## Protected block and justified preemption

Protect a chosen work block when there is feasible capacity. Actual incidents and hard commitments may displace it; changed capacity or a need to stop can also require renegotiation. Do not use block protection to force work through exhaustion.

When switching is safe, leave only the restart information needed:

```markdown
- 被打断的工作与恢复第一步：
- 新时段／缩小范围／待协商：
```

Do not delay urgent incident response to complete this note. Afterward, agree a feasible recovery slot, reduce the scope, or mark rescheduling pending with the person or decision needed. Never automatically assign the next working day's first block or treat a pause as catch-up debt. A proposed change does not alter an external commitment until confirmed.

## Maintenance budget

Match response expectations and available time to the user's actual role. Batch requests only when their impact permits waiting. Do not impose universal counts such as two maintenance windows per day or three support tasks per week.

When incoming work exceeds capacity:

1. Name the real impact, required response, and competing commitment; include verification and coordination costs.
2. Propose one concrete change in scope, order, timing, ownership, or support. Identify who can authorize it rather than assuming the user can refuse.
3. Keep the change pending until agreed. Draft communication if helpful, but do not send it or change trackers without authorization.

If everything is genuinely urgent, surface the need for an owner decision or additional help. Repeated overload is an allocation problem to revisit with stakeholders, not evidence that the user needs a better planner. Do not solve it by adding a learning block, silently compressing rest, or promising that increased efficiency will cover the gap.

## Recurrence and prevention

When a failure recurs with material cost, assess whether a proportional preventive fix is worth selecting; recurrence does not automatically authorize a new project. Group symptoms only when they share a real mechanism, such as ownership ambiguity, state convergence, interface resilience, observability, regression coverage, or self-service gaps.

Estimate prevention value using:

```text
recurrence frequency × repair/context-switch cost × blast radius
```

When justified, leave one proportional prevention asset: a regression test, clearer error, key log, metric, alert, runbook, retry/timeout/idempotency rule, automated check, or self-service path.

During review, distinguish repair output from flow improvement. Do not turn a ten-minute low-frequency repair into a multi-day redesign.
