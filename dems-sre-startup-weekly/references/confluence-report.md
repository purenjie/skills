# Confluence 周报格式

更新目标：`${CONFLUENCE_BASE_URL}/pages/viewpage.action?pageId=${CONFLUENCE_PAGE_ID}`。仅在用户明确要求发布时更新该页面，保留历史周章节。

目标是让 leader 一屏看懂结论，再按需查看维度和阶段。数字统一保留一位小数；数量显示整数；比例保留一位百分比。

## 周章节顺序

```markdown
## Wxx｜YYYY-MM-DD ～ YYYY-MM-DD（截至 MM-DD HH:mm）

> **Warning:** V3 覆盖范围、是否完整、Runner stage 是否缺失、低样本提示。

### 一句话结论

- 结论 1：DEMS 创建任务 → Sandbox 建立连接的成功率和 P95。
- 结论 2：DEMS 创建任务 → SeaTalk TTFT 的成功率和 P95。
- 结论 3：主要耗时 stage；如果数据不足则改写成数据边界。

### 总体 Scorecard

### 异常任务明细（仅在用户明确要求时）

### 按 Scenario

### 需要关注的 DE

### 按 task_type

### Stage 耗时构成

### 指标说明与数据边界
```

## 总体 Scorecard

| 指标 | 本期 | 环比 |
| --- | --- | --- |
| 任务启动观测数 | count | `-` 或同口径 V3 环比 |
| DEMS 创建任务 → Sandbox 建立连接成功观测 | success / started（rate） | ... |
| DEMS 创建任务 → Sandbox 建立连接 P50 / P95 | seconds | ... |
| DEMS 创建任务 → Sandbox 建立连接 >5m / >10m / >30m | percentages | ... |
| DEMS 创建任务 → SeaTalk TTFT 成功观测 | success / started（rate） | ... |
| DEMS 创建任务 → SeaTalk TTFT P50 / P95 | seconds | ... |
| DEMS 创建任务 → SeaTalk TTFT >5m / >10m / >30m | percentages | ... |

没有两个完整 V3 周时，环比写 `-`，并解释 V2/V3 不可直接比较。

## Scenario、DE 和 task_type

三类表保持相同核心列：

| 维度 | started | Sandbox 建连成功观测 | 建连 P50 / P95 | SeaTalk TTFT 成功观测 | TTFT P50 / P95 |
| --- | ---: | --- | --- | --- | --- |

- Scenario：展示全部当前值。
- DE：正式周只展示 Ready success samples 达到门槛后、Ready P95 最高的 10 个；preview 可降低门槛并明确标注。
- task_type：使用 `Scenario / task_type`，避免同名类型跨 Scenario 混淆。低于 20 个 success samples 的行标注 `低样本`。

## 异常任务明细

只有用户明确要求失败下钻时才展示，且必须先用同一窗口内的日志确认：

| 指标 | task_id | 结果 | 原因 |
| --- | --- | --- | --- |
| DEMS 创建任务 → Sandbox 建立连接 / DEMS 创建任务 → SeaTalk TTFT | task_id | failed / missing / 已终止未完成 | 经日志确认的简短直接原因 |

- 只列明确的 `failed` / `missing`，或有 `task_stop` 等直接终止证据的未完成任务。
- `started - success` 只汇总为“截止时未结算”，不生成失败 task_id。
- Sandbox 建连必须补查 Gateway/Runner 日志；已收到 Worker event 的候选标为“观测缺口，排除启动失败”，不要放进失败表。
- Prometheus 与日志无法完全映射时，明确写未映射数量和“排查不完整”，不能写“无失败”。
- 原因只写日志可以直接证明的事实；不能确认根因时写“直接原因已确认，根因待查”。
- 不放 `execution_request_id`、`run_id`、`request_id`、原始日志、用户输入或其他敏感上下文。

## Stage 耗时构成

| service | stage | samples | P50 | P50 share | P95 | P95 share |
| --- | --- | ---: | ---: | ---: | ---: | ---: |

表后固定说明：Stage P50/P95 来自不同任务排序位置，不能相加还原端到端 P50/P95；share 仅用于识别主要耗时位置。

Gateway / Runner 均使用 `digital_employee_task_startup_stage_v3_latency_seconds`，以 service 区分；筛选相同的 SRE 21/22 和其他归因标签。两者独立查询后合并展示，并增加 Scope 列，标成“SRE 21/22，V3”及实际额外筛选。各 stage 样本集合可能不同，需保留样本数。Runner V3 缺失时标注 incomplete，不回退旧 release 指标。

Runner 的 warm/cold stage 原始值均展示；占比计算使用两者 V3 bucket 合并得到的 `runner_sandbox_acquire`，避免把互斥分支重复加入分母。Gateway 与 Runner 的 share 分别在各服务内部归一化，不计算跨服务合计。Runner 阶段包含 `runner_dems_startup_context`；缺失观测标注“未覆盖”。

## 结论写法

- 先说当前事实，再说边界，不推测根因。
- `started - success` 写成“截止时未观察到 terminal”，不要写成“失败”。
- `failed`/`missing` counter 没有序列时写“无可用序列”或 `N/A`，不要写 0。
- P95 落在宽桶且样本少时，写“Histogram 估算”，不要描述为精确耗时。
- Runner V3 缺失时，不把 Gateway stage 称为“完整启动链路”。

## 发布检查

- 新章节位于旧周之前，历史内容逐字保留。
- 页面标题不变。
- 查询窗口、实际 V3 覆盖时间、截止时间、时区均已写明。
- Overall 等于各 Scenario 聚合；Visible 只统计 `source=seatalk`。
- Confluence 回读后的 started、success、P50、P95 与本地 `summary.json` 一致。
