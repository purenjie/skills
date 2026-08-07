# 踩坑记录

本文档记录 DE 回归测试脚本开发过程中踩过的所有坑，以及最终解法。
修改 `de_regression.sh` 追踪逻辑前务必先读，避免重蹈覆辙。

## 坑 1：macOS bash 3.2 不支持关联数组 `declare -A`

### 现象

```
de_regression.sh: line 178: declare: -A: invalid option
```

脚本用到 `declare -A RESULT` 存每条消息的判定结果，在 macOS 自带 `/bin/bash`（3.2.57）下直接报错退出。

### 根因

macOS 出于 GPL 协议原因自带 bash 停在 3.2，而关联数组 `declare -A` 是 bash 4+ 特性。

### 解法

完全不使用关联数组。改用**临时文件**传递每条消息的判定结果：
- `trace_one` 把结果写到 `$TMPDIR_RUN/msg1.txt`（3 行：result / task_id / err_detail）
- 主流程用 `sed -n '1p'` 读取

同时所有 bash 语法都保证 3.2 兼容：
- `[ $# -gt 0 ]` 代替 `[[ ]]` 部分场景
- `case` 代替 `[[ == * ]]` 模式匹配
- 不用 `$'...'`、`{var,,}` 等 4+ 特性

---

## 坑 2：message_id 含 `_` `-` 导致 PQL 语法报错

### 现象

用 `smc seatalk message send-group` 返回的 message_id 直接做 PQL 查询：

```
Error: search error: syntax parse: line 1:55 mismatched input 'mK' expecting {INT, FLOAT}
```

### 根因

message_id 格式如 `u7oirumAclDtMkjP41LPhlLpfvXNAhNSqhQ00QdcepvomgBdoBVALr-mK`，
其中 `-` 被 PQL 解析为减号运算符，`_` 也被当分词符。加双引号 `"..."` 虽不报错，
但变成短语匹配，message_id 是唯一串，整串匹配不到分词后的日志。

### 验证

- 不加引号 → 语法报错
- 加双引号 → 不报错但 0 结果
- 用前 32 字符纯字母数字 → 0 结果（PQL 整词 token 匹配，前缀不是完整 token）

### 解法

**不用 message_id 做 PQL**。改用**消息内容关键词**（如「如何接入 cachecloud」「10.251.117.197」）
查 callback 入口——消息原文存在 callback body 里，PQL 能匹配。

---

## 坑 3：request_id UUID 连字符被 PQL 分词

### 现象

用完整 request_id `6cd67bc2-dcb0-46a9-8088-08ef08fafa9c` 做 PQL 查询，返回空。

### 根因

UUID 含多个连字符，PQL 在连字符处分词，完整 UUID 不是一个可匹配的 token。
`digital-employee-live-rca` skill 里也明确提到："A UUID with many dashes tokenizes inside PQL even when quoted"。

### 验证

- 完整 UUID → 0 结果
- 前 8 位纯 hex `6cd67bc2` → 命中 18+ 条

### 解法

用 request_id 的**前 8 位纯 hex**（如 `6cd67bc2`）做 PQL。前 8 位无连字符，PQL 友好，
且足够独特（4 亿分之一冲突率，单时间窗内不会撞）。

```bash
extract_req_short() {
  python3 -c "
import sys, re
m = re.search(r'request_id=([0-9a-f]{8})-', sys.stdin.read())
print(m.group(1) if m else '')
"
}
```

---

## 坑 4：`echo "$var" | grep` 被 shell 特殊字符坑

### 现象

这是最隐蔽的坑。日志变量 `gw_logs` 里明明含 1 条 `seatalk_cb`（`grep -c` 返回 1），
但 `echo "$gw_logs" | grep -q "seatalk_cb"` 却判定为不存在（has_cb=0）。

### 根因

日志内容含反引号 `` ` ``、`$`、双引号、转义字符等。当用 `echo "$gw_logs"` 输出时，
shell 会重新解释这些特殊字符，导致 `seatalk_cb` 那行内容被破坏，grep 匹配失败。

### 验证

```bash
# grep -c 直接读变量 → 1
echo "$gw_logs" | grep -c 'seatalk_cb'   # 但这个其实也走 echo，不可靠

# 写文件后 grep → 可靠
printf '%s\n' "$gw_logs" > /tmp/x.log
grep -c 'seatalk_cb' /tmp/x.log          # 1
```

### 解法

**所有日志内容都落临时文件，用 `grep file` 而非 `echo "$var" | grep`**。

```bash
local gwfile="$workdir/gw.log"
: > "$gwfile"
query_gateway_to "$kw" "$ws" "$we" "$gwfile"   # 直接追加到文件
# 判定时
grep -q "seatalk_cb" "$gwfile" && has_cb=1 || true
```

`query_gateway_to` 函数把 logcli 输出经 python 提取 `@message` 后**直接重定向追加到文件**，
全程不经过 shell 变量。

---

## 坑 5：callback request_id ≠ 执行阶段 request_id

### 现象

用 callback 入口的 request_id `6cd67bc2` 查 gateway 日志，能拿到 callback/classify/create_process，
但**查不到 `terminal_agent_event` / `plan_completed`**（执行结束 marker）。
因为执行阶段的日志用的是另一个 request_id `0ff40c12`。

### 根因

Gateway 收到 SeaTalk callback 时用一个 request_id 处理入口逻辑（classify/create_process/kafka_wait），
然后把请求转给 Runner，Runner 执行阶段用**新的 request_id**。两个 request_id 不相同。

### 关联纽带

callback request_id 的日志里包含一条 `[direct_execution_rating] result_scheduled request_id=<执行req> task_id=<tid>`，
这条日志**同时含 callback request_id、执行 request_id、task_id**，是关联的纽带。

### 解法

用 callback request_id 前 8 位查，能拿到：
- `result_scheduled`（QnA 路径的结束 marker，本身就是 terminal）
- `task_id`（用于查 runner）

把 `result_scheduled` 纳入 terminal marker 判定，就不需要再追执行阶段 request_id。

---

## 坑 6：`tcs_api | claim` status=400 是预期 fail_open，非异常

### 现象

MSG1 判定为 ❌ 执行出错，err_detail 是：
```
[WARN] [tcs_api | claim] exchange ... status=400 response={"code":400,"message":"Infrabot service failed..."}
```

### 根因

Gateway 在 callback 处理时会调 `[tcs_api | claim]` 抢占 ticket，有时返回 400。
但这是**预期容错路径**：紧接着有 `[tcs_admission] claim_http_fail_open`，claim 失败会放行，不影响主流程。

### 解法

error 过滤排除这类预期 WARN：

```bash
err_detail=$(grep -iE "error|panic|provisioning_error|..." "$gwfile" \
  | grep -viE "error_|no_error|error_code.?:0|fail_open|claim_http_fail|status.?:0|\"success\":true" \
  | grep -viE "tcs_api \| claim" \
  | head -3)
```

---

## 坑 7：QnA 直答路径不经 Runner

### 现象

两条回归消息的 runner 侧都查不到 `runner_gateway_execution_registered` 等标记，
最初以为 runner 出问题了。

### 根因

回归用的两条消息走的是 **QnA 直答路径**（`direct_execution_rating` → `result_scheduled`），
不经过 Runner 的 Kafka/ticket/registration 链路。只有 OPR 任务路径才走 Runner。

### 解法

- terminal marker 增加 `result_scheduled`（QnA 结束标志）
- runner 侧无记录时显示 `runner侧无记录(QnA直答可能不经runner)`，不算异常

---

## 坑 8：日志索引延迟 2-3 分钟

### 现象

发完消息立即查日志，报 `query time range is outside max retention range`，
或返回 0 条。

### 根因

Space Log 平台有约 2-3 分钟的索引延迟。当前时间的日志还没建好索引。
"max retention end" 比当前时间落后约 2 分钟。

### 解法

发完消息后 `sleep 180` 等 3 分钟再查。参数化 `INDEX_WAIT`，必要时可调大。

---

## 坑 9：关键词「cachecloud」太泛，混入别人日志

### 现象

MSG1 用 `cachecloud` 查 gateway，返回 65 条，含 8 个不同 request_id，
task_id 提取到 `OPR-TYPE-10978`（别人的），而非自己的 `QNA-SRE-xxxxx`。

### 根因

cachecloud 是常见词，群里其他人也在问。单关键词 + 时间窗仍可能混入。

### 缓解

- 用完整短语「如何接入 cachecloud」查 callback 入口（更独特）
- task_id 提取虽不准，但不影响主判定（QnA 路径不经 runner，runner 检查跳过）
- 如需精确 task_id，应从 callback request_id 对应的 `result_scheduled` 行提取，
  而非从全局 grep

### 待优化

如以后 OPR 路径需要精确 runner 检查，改进 task_id 关联逻辑：
先定位 callback req → 查其 `result_scheduled` 行 → 提取该行的 task_id。

---

## 总结：可复用的经验

1. **macOS 脚本一律 bash 3.2 兼容**，不依赖 4+ 特性（关联数组、`[[ ]]` 高级模式等）。
2. **PQL 查询 ID 时**：含 `-` `_` 的 ID 用不了，取纯字母数字子串（前 8 位 hex 最稳）。
3. **日志内容含特殊字符时**：一律落临时文件用 `grep file`，绝不用 `echo "$var" | grep`。
4. **跨阶段关联**：callback req 和执行 req 不同时，找同时含两个 ID 的关联行（如 `result_scheduled`）。
5. **error 判定要先识别预期容错**：fail_open / claim 400 / non_actionable 可能是正常的，看后续 marker。
6. **路径区分**：QnA 直答 vs OPR 任务，marker 链不同，terminal 判定要覆盖两条路径。
7. **日志索引延迟**：查询类操作固定等待 2-3 分钟。
