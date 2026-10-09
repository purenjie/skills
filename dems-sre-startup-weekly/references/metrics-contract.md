# 周报指标契约

本文件是 weekly skill 的自包含查询契约。线上指标族、labels 或 stage 发生变化时，应与
`scripts/export_sre_startup_weekly.py` 和对应测试一起更新。

## Gateway V3

- milestone counter：`digital_employee_task_startup_milestone_v3_total`
- milestone histogram：`digital_employee_task_startup_milestone_v3_duration_seconds`
- stage histogram：`digital_employee_task_startup_stage_v3_latency_seconds`
- 固定归因 labels：`de_id/team_id_l1/team_id_l3/scenario/source/task_type`
- 周报默认筛选：由 `--team-id-l1` / `SRE_TEAM_IDS` 提供
- SeaTalk TTFT：`milestone="first_worker_result_visible",source="seatalk"`
- Sandbox 可投递就绪：`milestone="gateway_route_ready"`

`first_worker_result_visible` 在 Gateway 收到可展示 Worker 内容时结算，不包含 SeaTalk API
耗时；`thinking` 不计入，`tool_call` 和其他进入展示路径的有效 Worker 事件计入。

## Runner V3

- stage histogram：`digital_employee_task_startup_stage_v3_latency_seconds`
- labels：`de_id/team_id_l1/team_id_l3/scenario/source/task_type/service/stage/result`
- 查询 Scope：`service="runner"`、团队筛选由 `--team-id-l1` / `SRE_TEAM_IDS` 提供；其他筛选与 Gateway 一致
- 明细分组：`scenario/de_id/task_type/service/stage`

固定 stage：

- `process_created_to_runner_consumed`
- `runner_dems_startup_context`
- `runner_pre_provision_prepare`
- `runner_sandbox_warm_pool_acquire`
- `runner_sandbox_cold_create`
- `runner_gateway_register`
- `runner_worker_start`

仅查询 V3；旧 release 指标不作为 fallback。Runner V3 空结果保留为 incomplete。
分别确认 Gateway 和 Runner 的实际 V3 覆盖时间；发布前后的窗口不能伪装成完全同口径。

## 聚合约束

- success rate 使用 milestone `success / started`。
- milestone 成功数使用 counter；分位数样本数使用 histogram `_count`。
- Histogram P50/P95 是桶内插值，不是原始任务精确值。
- Gateway / Runner 使用相同归因筛选并列展示，但各 stage 样本集合可能不同，不能相加分位数；share 分别在各服务内部归一化。
- `started - success` 表示尚未观察到 terminal，不直接等于失败。
- Prometheus labels 不放 `task_id/execution_request_id/run_id/request_id`；下钻使用结构化日志。
