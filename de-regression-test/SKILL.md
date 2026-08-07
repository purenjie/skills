---
name: de-regression-test
description: 数字员工(DE)服务上线后的自动化回归测试。在群里 @de bot 发两条回归问题(cachecloud 接入 / IP 查询)，追踪 gateway 和 worker_runner 的线上日志，验证执行链路是否正常，异常时通过 seatalk 私聊告警。用于 DE 服务部署上线后的回归验证。触发词：DE 回归测试、回归测试、de regression、上线后验证。
---

# DE 回归测试

服务上线后自动回归测试：发 @de bot 的回归问题 → 追踪线上日志 → 验证执行链路 → 异常告警。

## 适用场景

- 数字员工 gateway / worker_runner 部署上线后
- 需要验证 DE bot 的端到端处理链路是否正常
- 关心执行是否报错、是否正常结束、worker↔gateway 是否注册

## 前置条件

- `smc seatalk` 已配置 bot 凭证（`~/.seatalk/config.json`）
- `smc logcli` 已安装且 token 有效
- 两个日志应用可查：
  - Gateway: `shopee.engineering_infra.infra_products.digital_employee.gateway` (env liveish)
  - Runner: `shopee.engineering_infra.infra_products.digital_employee.worker_runner` (env live)

## 执行方式

### 一键脚本（推荐）

```bash
bash ~/.pi/agent/skills/de-regression-test/scripts/de_regression.sh
```

自动完成：发消息 → 等 3 分钟索引 → 查日志 → 判定 → seatalk 私聊告警/总结。约 4 分钟。

参数：
- `--no-wait`：跳过 3 分钟索引等待（调试用，日志可能查不全）
- `--notify-email <email>`：覆盖默认告警收件人（默认 `renjie.pu@shopee.com`）
- 环境变量 `NOTIFY_EMAIL` 同样可设默认收件人

### 交互式

对 pi 说「跑一下 DE 回归测试」，pi 按流程执行并实时反馈。

## 回归消息

固定两条，@de bot (DE-MPSRE-BETA, seatalk_id=9264960552) 发到数字员工联调群 (Njc3NDM4MjYwMDEz)：

1. 「如何接入 cachecloud」— QnA 直答路径
2. 「10.251.117.197 这个是啥 IP？」— OPR 任务路径（含 tool_call）

## 追踪策略

核心思路：**用消息内容关键词查 callback 入口 → 提取 request_id 前 8 位 → 补充查完整链路 → 在临时文件上 grep 判定**。

```
1. 发消息 → 拿 message_id + 时间戳 t
2. 等 3 分钟（Space Log 索引延迟 2-3 分钟）
3. 用消息内容关键词查 gateway callback 入口（原文在 callback body 里）
4. 从 callback 入口提取 request_id 前 8 位（纯 hex，PQL 友好）
5. 用前 8 位补充查完整链路，合并到临时文件
6. 在文件上 grep 判定 marker（避免 shell 特殊字符问题）
7. 用 task_id 查 runner 日志，确认 worker↔gateway 注册
```

> ⚠️ 追踪过程中踩过的坑很多（PQL 分词、shell 特殊字符、callback req ≠ 执行 req 等），
> 详见 [踩坑记录](references/pitfalls.md)。修改追踪逻辑前务必先读。

## 判定标准

| 状态 | 条件 |
|------|------|
| ✅ 正常完成 | terminal marker + group_chat 回复 + 无 error |
| ⚠️ 已结束未回复 | 有 terminal marker 但无 group_chat 回复 |
| ⚠️ callback已收未结束 | 有 seatalk_cb 但无 terminal（可能仍在执行） |
| ❌ 执行出错 | 日志含 error/panic/provisioning_error/dependency_error/non_actionable |
| ❌ 未发现 callback | 无 seatalk_cb 入口 |

**terminal marker**（任一即可）：
- `terminal_agent_event` — QnA 直答路径结束
- `plan_completed` — OPR 任务路径结束
- `result_scheduled` — direct_execution_rating 结束（QnA 直答）

**error 过滤**（这些是预期行为，不算异常）：
- `tcs_api | claim` 的 status=400 → 后续有 `claim_http_fail_open` 放行，正常
- `fail_open` / `claim_http_fail` → 预期容错
- `error_code:0` / `success:true` → 正常响应

## Gateway marker 链（参考）

```
[seatalk_cb] raw_request          ← SeaTalk callback 入口
[http_req] callback               ← HTTP 请求
[latency] callback_dispatch_started
[runner_api | classify_intent]    ← 意图分类
[runner_classify] accepted
[dems_task_api | create_task]
[tcs_api | create_ticket] / [create_process]
[runner_business_prepare] kafka_wait   ← Gateway→Runner handoff 边界
[seatalk_api | group_chat_typing] ← bot 输入中
[stream] agent_event (thinking/tool_call/plan_proposal)   ← OPR 路径
[stream] terminal_agent_event     ← QnA 结束
[direct_execution_rating] result_scheduled   ← QnA 直答结束
[seatalk_api | group_chat]        ← 回复发到群里
```

## Runner marker 链（OPR 路径才经过）

```
runner_kafka_message_payload      ← Kafka 投递
runner_kafka_ticket_started       ← Runner 启动
runner_gateway_execution_registered   ← worker↔gateway websocket 注册
```

QnA 直答路径不经 runner，runner 侧无记录属正常。

## 已知限制

- **task_id 提取可能不准**：消息1「cachecloud」关键词较泛，可能混入别人的 OPR-TYPE 日志。不影响主判定（QnA 路径不经 runner），但 OPR 路径的 runner 检查可能受影响。如需精确，可从 callback request_id 对应的 `result_scheduled` 行提取 task_id。
- **日志索引延迟**：Space Log 有 2-3 分钟延迟，脚本固定等 180s。若仍查不到，可增大 `INDEX_WAIT`。
- **PQL 分词**：含连字符/下划线的 ID 不能直接查，用前 8 位纯 hex。

## 排查指引

- **日志查不到**：确认等待 ≥3 分钟，或扩大时间窗。用 `--no-wait` + 手动指定时间调试。
- **判定异常但实际正常**：检查 error 过滤是否误判，看 `err_detail` 字段。
- **需要深度 RCA**：用 `digital-employee-live-rca` skill 的 `de_logs.py joint` 模式做跨服务完整追踪。

## 相关 skill

- `digital-employee-live-rca`：DE 生产事故深度 RCA，含完整 marker 链定义和 `de_logs.py` 跨服务追踪脚本。本 skill 的判定逻辑和 marker 链参考了它。
- `seatalk`：发消息、读历史。本 skill 用它发回归消息和告警。
- `logcli`：查 Space Log。本 skill 用它查 gateway/runner 日志。
