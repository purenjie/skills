---
name: dems-sre-startup-weekly
description: 生成 Digital Employee SRE 启动链路 V3 周报，并在明确要求发布时追加或更新 Confluence 每周指标追踪页面。用于 SRE team 21/22 的 DEMS 创建任务到 Sandbox 建立连接、DEMS 创建任务到 SeaTalk TTFT、Scenario、DE、task_type 和 stage 周维度统计；不用于线上事故 RCA 或修改指标上报代码。
---

# DEMS SRE 启动指标周报

从只读 Prometheus 聚合生成老板可扫描的周报，同时保留数据完整性和 Histogram 精度边界。

## 固定范围

- 目标页面：`${CONFLUENCE_BASE_URL}/pages/viewpage.action?pageId=${CONFLUENCE_PAGE_ID}`
- 页面 ID：`${CONFLUENCE_PAGE_ID}`
- 导出脚本：`<skill-dir>/scripts/export_sre_startup_weekly.py`
- 默认团队：通过 `--team-id-l1` 或 `SRE_TEAM_IDS` 配置。
- 时区：`Asia/Shanghai`（`+08:00`）
- 正式周窗口使用半开区间：周一 `00:00` 到下周一 `00:00`。

本 skill 自包含统计实现和指标契约，不读取或调用 Gateway/Runner 项目中的脚本、文档或源码。`<skill-dir>` 从当前 `SKILL.md` 的实际路径解析，不依赖调用时的工作目录。

如果用户给出“截至今天某时刻”，生成当前周的 preview，并在标题、结论和数据说明中明确标注截止时间；不要伪装成完整自然周。

## 执行流程

1. 读取 [指标契约](references/metrics-contract.md)，并使用本 skill 自带导出脚本。线上指标族发生变化时，先更新 skill 内的契约、脚本和测试。
2. 用 `smc confluence page get "$CONFLUENCE_PAGE_ID" --section overview,content --format markdown --output json` 读取页面版本和正文。保留所有历史周，不覆盖旧章节。
3. 确认 V3 数据实际开始时间。若查询窗口早于首次 V3 上报，报告必须同时写“查询窗口”和“实际 V3 覆盖时间”。
4. 在临时目录执行导出脚本。默认统计团队 21、22；SeaTalk TTFT 只使用 `source=seatalk`。
5. 检查 `summary.json`、`reconciliation.json` 和 `manifest.json`：
   - 空结果、partial 响应、日志截断、缺失服务必须保留为 `incomplete`，不能写成 0。
   - Runner 未上报 V3 时，导出按 `incomplete` 失败；报告预览只能展示已核实的 Gateway stage，并明确写“Runner V3 stage 尚未覆盖”。不得回退旧指标补齐。
   - `started - success` 是截止时尚未观察到 terminal 的数量，不直接等于失败。
   - 成功数使用 milestone counter；P50/P95 的样本数使用 Histogram `_count`。
   - Gateway / Runner stage 均查询 `digital_employee_task_startup_stage_v3_latency_seconds`，分别用 `service="gateway"` / `service="runner"` 区分，并使用相同的团队、source、scenario、DE 和 task_type 筛选后汇总。
6. 按 [Confluence 周报格式](references/confluence-report.md)生成一个新周章节。先生成本地预览；只有用户明确要求“更新/发布到 Confluence”时才执行写入。
7. 写入时把新周放在旧周之前，保留页面 H1。用 `smc confluence page update "$CONFLUENCE_PAGE_ID" --file <page.md> --format markdown --submit --output json`，随后重新读取页面并确认标题、版本、截止时间和关键数字。

## 数据模式

### Prometheus 查询入口（强制使用 HTTP API）

- 本 skill 的所有指标查询必须直接调用 Prometheus HTTP API；禁止使用 `smc grafana`，包括 datasource discovery、metric get 和 PromQL query，也不得将其作为 fallback。
- 默认 base URL：通过 `--prometheus-url` 或 `PROMETHEUS_URL` 配置。即时查询使用 `GET <base-url>/api/v1/query`，参数为 `query`（PromQL）和 `time`（Unix 时间戳）；参数必须 URL 编码。
- 周报使用本 skill 自带的 `scripts/export_sre_startup_weekly.py`，其 `query_prometheus` 已实现上述 API 调用和响应检查。临时核验指标是否上报、标签或样本新鲜度，也通过同一 API 查询。需要更换地址时使用脚本的 `--prometheus-url` 参数。
- 不以 Grafana token 或 datasource discovery 为前置条件。缺少 Grafana 凭据不能判定 Prometheus 不可访问；必须实际请求上述 API 后判断。
- 查询失败时报告该 API 的实际 HTTP、网络或响应错误；`status` 非 `success`、partial 或空结果保留为 `incomplete`，不得当作零流量或上报成功。HTTP 200 也必须继续检查响应内容。
- 上报核验应确认目标指标族的 `service`、环境和归因标签，并检查最新样本时间；已有其他服务或旧指标族的数据不能代替目标新指标的验证。日志抽样与 Prometheus 聚合对账分别说明证据范围。

普通周报只查询 Prometheus，避免为了展示汇总全量扫描数万条日志：

```bash
python3 <skill-dir>/scripts/export_sre_startup_weekly.py \
  --start '<mondayT00:00:00+08:00>' \
  --end '<next-mondayT00:00:00+08:00>' \
  --team-id-l1 "$SRE_TEAM_IDS" \
  --prometheus-url "$PROMETHEUS_URL" \
  --gateway-log-app "${GATEWAY_LOG_APP:-}" \
  --runner-log-app "${RUNNER_LOG_APP:-}" \
  --top-de-min-success 100 \
  --output-dir '<temporary-output-dir>'
```

日志未查询时，不得把 `failure_count=0` 或 `slow_count=0` 写入报告。失败定位、慢任务排查或分位数精确抽样时，再查询 `[startup_observation] schema_version=3` 日志，并在相同窗口内与 Histogram `_count` 对账。

### Sandbox 建连失败排查

“DEMS 创建任务 → Sandbox 建立连接”的失败不能只依赖 milestone 的 `failed` / `missing`：Sandbox 未启动、复用已有 Sandbox、观测未结算或 projection gap 都可能没有对应 terminal counter。

1. 以 `gateway_route_ready started` 为候选全集，按 `execution_request_id` 关联 `action=bound` 和 route-ready terminal。
2. 对没有 route-ready terminal 的候选，继续查询 Gateway 的 `[startup_trace]`、`[runner_business_prepare]`、`[runner_execution_status_http]`、`[runner_execution_status]`、`[runner_execution_register]` 和 `[stream] agent_event`。
3. 再用相同 `execution_request_id` / `task_id` 查询 Runner 应用日志，确认 Kafka 消费、预处理、Sandbox provision/reuse、Gateway register 和 Worker start 的最后检查点。
4. 若已经收到合法 Worker event 或 SeaTalk TTFT success，应判为“观测缺口，排除 Sandbox 启动失败”；`sandbox_provisioning_skipped` 只表示 Gateway 指示 Runner 跳过本次 provisioning，必须结合后续 route/Worker event 判断，不得直接写成失败或复用成功。
5. 只有日志明确显示 startup failure、Sandbox 未建立且任务已终止，才进入失败表。Prometheus 与日志数量不能对齐时，剩余差值写“无法映射，排查不完整”，不得结论为 0 失败。

### Runner V3 stage 查询

Runner 查询 `digital_employee_task_startup_stage_v3_latency_seconds{service="runner"}`，默认筛选由 `--team-id-l1` / `SRE_TEAM_IDS` 提供，并沿用 Gateway 的其他归因筛选。汇总线上实际存在的 stage 的 success samples、P50、P95 和分位数归一化占比：

- `process_created_to_runner_consumed`
- `runner_dems_startup_context`
- `runner_pre_provision_prepare`
- `runner_sandbox_warm_pool_acquire`（暖池命中）
- `runner_sandbox_cold_create`（冷启动）
- `runner_gateway_register`
- `runner_worker_start`

Runner V3 与 Gateway V3 均包含 `de_id/team_id_l1/team_id_l3/scenario/source/task_type/service/stage/result` 标签。Confluence 两者均标成“目标团队集合，V3”（有额外筛选时注明）。相同筛选不代表所有阶段经过相同任务，必须分别显示样本数；归因为 `unknown` 的数据不能当作目标团队数据。旧 release 指标不参与本周报统计，历史 release 周与 V3 不做同口径环比。

暖池与冷启动是互斥分支：同时展示两个原始 stage；需要 Runner 阶段占比时，额外将两者的 V3 histogram buckets 聚合成诊断项 `runner_sandbox_acquire`，只用该合并项参与 Runner 内部的占比归一化，避免重复计算。任一 stage 没有观测时写“未覆盖”，不要补 0。Gateway 与 Runner 的 share 分别在各服务内部归一化。

Preview 数据量较小时，可以降低 `--top-de-min-success`，但必须在表格前显示门槛和“低样本，仅供预览”。正式周默认门槛为 100。

## 统计口径

- DEMS 创建任务 → Sandbox 建立连接：`gateway_route_ready success / started`。表示 Gateway 已确认 Sandbox WebSocket route 可投递，不表示任务完成。
- DEMS 创建任务 → SeaTalk TTFT：`first_worker_result_visible`，从 M0 到 Gateway 收到 Worker 的 `seatalk_visible_event`；不包含 SeaTalk API 更新耗时，排除 `thinking`。
- Overall、Scenario、Top DE、`Scenario/task_type` 使用同一组指标：started、success、success rate、P50、P95、`>5m`、`>10m`、`>30m`。
- Stage 展示 success samples、P50、P95、P50 share、P95 share。分位数不可相加；share 只是同一范围内各 stage 分位数的诊断性归一化。
- Prometheus P50/P95 是 Histogram 桶内插值。样本少于 100 时标记低样本；需要精确值时使用日志抽样，不用日志值悄悄替换 Prometheus 周趋势。
- V2 与 V3 不做环比。只有两个完整、同口径 V3 周窗口才能计算周环比。

## 输出边界

- Confluence 默认只放可扫描的结论和聚合表。用户明确要求失败下钻时，可以增加一张简表，仅展示 `task_id`、业务指标、结果和经日志确认的简短原因；不得展示 `execution_request_id`、`run_id`、`request_id`、原始日志或用户输入。
- 失败表只收录明确的 `failed` / `missing`，或有直接终止证据的未完成任务。`started - success` 只能汇总为“截止时未结算”，不得逐条写成失败。完整下钻仍保留在 `failures.jsonl`、`slow_tasks.jsonl` 或临时调查产物中。
- 不修改 Grafana dashboard、Prometheus 指标、Gateway/Runner 代码或历史 Confluence 周数据。
- 写入失败或回读不一致时停止，不重复提交未知状态的页面更新。
