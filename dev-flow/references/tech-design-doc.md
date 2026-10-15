# 技术设计文档模板

改编自 Shopee DSFE 的 Server-Side Tech Design Template，用于本 skill 第 5 步「确定方向并连续实施」：方案讨论收敛后、进入实现前产出一份文档，与用户确认后再开工。

与原模板的差异：
- 新增 **第 8 节 Regression Verification Criteria**，原 Others、sign off 顺延为 9、10。回归标准在方案确认阶段就定好，而不是实现完再补。
- 删去原模板中 LowCode Platform 的六表建表示例，只保留结构和一个短示例，避免无关细节喧宾夺主。
- 章节标题保留英文，便于直接贴回 Confluence 走团队评审；填写指引用中文。

按需裁剪：标注 Optional 的章节没有内容就整节删掉，不要留空标题。标注 Mandatory 的章节如果判断不适用，写一行说明为什么不适用。

---

## 模板正文

```markdown
# {Project Name} - {Proposal Name} - {Status: wip / need review / approved}

| Version | Date | PIC | Description |
| --- | --- | --- | --- |
| v0.1 | YYYY.MM.DD | @owner | Initial draft for discussion |

## 1. Background (Mandatory)

- 业务背景
- 谁提出的需求
- 要解决什么问题

## 2. Goals

### 2.1 Business Goal (Optional)

### 2.2 Performance Goal (Optional)

eg. network latency must be less than xxx ms（没有实测依据时不要编造数字，写"沿用现有水位，不劣化"也可以）

## 3. Architecture Design (Mandatory)

### 3.1 System Architecture Design

画图基本规则：
- 用箭头表示数据流
- 图的最小单位是模块
- 区分当前实现、本次新增、未验证假设

## 4. Data Model Design

### 4.1 Database Model Design (Mandatory if you use MySQL)

#### 4.1.1 ERD

#### 4.1.2 SQL

CREATE TABLE IF NOT EXISTS `example_tab` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(255) NOT NULL,
  `status` TINYINT NOT NULL COMMENT '0: init, 1: active',
  `created_at` BIGINT NOT NULL,
  `updated_at` BIGINT NOT NULL,
  `is_deleted` TINYINT NOT NULL COMMENT '0: not deleted, 1: deleted',
  PRIMARY KEY (`id`),
  KEY `idx_example_name` (`name`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci;

### 4.2 Redis Data Model Design (Mandatory if you use Redis)

先说明：为什么需要 Redis、Redis 在这个业务模块里承担什么角色（缓存 / 分布式锁 / 状态标记 / 队列）。

| Key | Type | Usage | TTL | Estimated Capacity | Value | Comment |
| --- | --- | --- | --- | --- | --- | --- |
| instance:11111 | string | 标记实例是否已连接 | 30s | 20M | "1" | "1" = true |

Notes: key 用冒号(:)作分隔符。

## 5. Key Process Description

### 5.1 {流程名}

#### Sequence Diagram

#### Flow Chart

分支多、逻辑复杂时再补流程图；简单流程只画时序图即可。

## 6. API Design

### 6.1 Description

### 6.2 URL

### 6.3 Parameters

| Name | Payload Type | Description | Validation Rule | Is Required |
| --- | --- | --- | --- | --- |
| name | body | application 名称 | 仅字母数字，长度 < 256 | Yes |

### 6.4 Request Example

## 7. Monitoring and Alerting (Optional)

### 7.1 New Monitoring Metrics

| Key Metrics | Grafana Dashboard | Alert Rule |
| --- | --- | --- |
| QPS | [Link]() | [Link]() |
| Process Time | [Link]() | [Link]() |

### 7.2 Key Logs

| Event Name | Level | Trigger Point | Correlation ID | Sample |
| --- | --- | --- | --- | --- |
| app_created | INFO | 创建成功落库后 | trace_id | `event=app_created app_id=123 trace_id=xxx` |
| downstream_timeout | WARN | 下游调用超时 | trace_id | `event=downstream_timeout cost=2001ms trace_id=xxx` |

用于上线验收的关键日志，必须在生产默认日志级别下保留。

## 8. Regression Verification Criteria (Mandatory)

> 在方案确认阶段填写，与第 10 节 sign off 一并确认。实现完成后只更新「覆盖状态」列，不重写通过标准。

### 8.1 Regression Scenarios

| 场景 | 触发方式 / 前置条件 | 通过标准 | 验证方式 | 验证环境 | 覆盖状态 |
| --- | --- | --- | --- | --- | --- |
| 正常路径：创建 application | POST /applications，body 合法，name 未重复 | 返回 200；example_tab 新增一行且 status=1；日志出现 event=app_created 且本次 trace_id 可检索 | 自动化（集成测试） | test | 已覆盖 |
| 异常：参数超长 | name 长度 > 255 | 返回 400，错误码 INVALID_PARAM，不写库 | 自动化（单测） | - | 已覆盖 |
| 异常：下游超时 | 注入下游 3s 无响应 | 2s 超时返回 504；无半写状态；日志 event=downstream_timeout level=WARN | 人工（故障注入） | staging | 待实现 |
| 受影响旧功能：列表接口 | 新增字段后用旧版客户端调用 | 旧字段结构不变，旧客户端解析正常 | 自动化 | test | 已覆盖 |

### 8.2 场景来源（这几类不能缺）

- **正常路径**：第 6 节每个新增或变更的 API，至少一条。
- **关键异常**：参数校验失败、下游失败或超时、部分成功、重复请求（幂等性）。
- **受影响的旧功能**：改动触及的已有行为——这才是「回归」的本义，最容易漏。
- **数据兼容**：第 4.1 节有 schema 变更时，覆盖新旧数据共存、迁移与回滚。

场景不是越多越好，是上述几类不能缺。

### 8.3 通过标准的写法

必须可观察。一条合格的通过标准同时说明三件事：**接口返回什么、持久化状态变成什么、日志或指标能看到什么**。

- 反例：「创建成功」「功能正常」「符合预期」——无法判定，等于没写。
- 正例：「返回 200 且 example_tab 新增一行 status=1，日志出现 event=app_created 且含本次 trace_id」。

### 8.4 与可观测性的交叉检查

写不出「怎么判定通过」时，通常不是测试问题，而是设计缺少可观测性钩子：

| 写不出判定方式的症状 | 真正的设计缺口 | 回哪一节补 |
| --- | --- | --- |
| 状态变化无法从库或接口读出 | 缺状态字段或查询入口 | 第 4 节 Data Model |
| 失败路径无法与正常路径区分 | 缺关键日志或事件名不稳定 | 第 7.2 节 Key Logs |
| 整体是否劣化无法判断 | 缺指标或告警 | 第 7.1 节 Metrics |

**在这一节暴露的缺口要改设计，不要降低回归标准。** 这是把回归标准前置到方案阶段的主要收益——实现之后再发现「这个行为根本观测不到」，补救成本高得多。

### 8.5 覆盖状态取值

- `已覆盖`：对应自动化用例已存在或本次会写。
- `待实现`：确认要做，实现阶段补。
- `仅能上线验证`：测试环境无法构造。**必须在第 7 节有对应指标或告警**，否则上线后坏了没人知道。
- `不覆盖`：要写明原因和接受的风险。

## 9. Others

## 10. Sign Off: Stakeholders

签字范围包含第 8 节回归标准，不只是架构方案。

- [ ] @reviewer
```

---

## 配套约定

- **文档放哪**：优先沿用项目既有的设计文档位置；项目没有约定时，和用户确认后再落盘，不默认新建目录。
- **文档状态**：标题里的 status 实际维护。`wip` → `need review` → `approved`，approved 之后的实质修改要升版本号并在 changelog 里写清改了什么。
- **与实现的关系**：实现过程中回归重点或关键日志设计发生实质变化时，按本 skill 第 5 步的要求说明影响并与用户确认，同步更新第 7、8 节，不要让文档和实际行为脱节。
- **交付时**：第 8 节的表格直接作为验收清单，逐行标注已通过 / 失败 / 待验证，对应本 skill 第 6 步。
