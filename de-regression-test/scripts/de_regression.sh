#!/usr/bin/env bash
# DE 回归测试自动化脚本 (bash 3.2 兼容)
# 用法: ./de_regression.sh [--no-wait] [--notify-email <email>]
#
# 核心追踪策略 (规避 PQL 分词 + shell 特殊字符问题):
#   1. 发消息拿 message_id + 记录时间
#   2. 用消息内容关键词查 gateway callback 入口 (消息原文在 callback body 里)
#   3. 从 callback 入口日志提取 request_id 前 8 位 (纯 hex, PQL 友好)
#   4. 用 request_id 前 8 位补充查完整链路, 合并到临时文件
#   5. 判定 (在临时文件上 grep, 避免 echo "$var" 被 shell 解释特殊字符):
#      - terminal marker: terminal_agent_event / plan_completed / result_scheduled
#      - 回复: seatalk_api + group_chat
#      - 异常: error/panic/provisioning_error (排除预期 fail_open)
#   6. 用 task_id 查 runner 日志, 确认 worker↔gateway 注册
#   7. 异常 -> seatalk 私聊告警; 正常 -> 总结

set -uo pipefail

# ============ 配置 ============
GROUP_ID="Njc3NDM4MjYwMDEz"
DE_BOT_SEATALK_ID="9264960552"
NOTIFY_EMAIL="${NOTIFY_EMAIL:-renjie.pu@shopee.com}"
INDEX_WAIT=180

GATEWAY_APP="shopee.engineering_infra.infra_products.digital_employee.gateway"
RUNNER_APP="shopee.engineering_infra.infra_products.digital_employee.worker_runner"

MSG1_KW="如何接入 cachecloud"
MSG1_TEXT="如何接入 cachecloud"
MSG2_KW="10.251.117.197"
MSG2_TEXT="10.251.117.197 这个是啥 IP？"

# ============ 参数解析 ============
NO_WAIT=0
while [ $# -gt 0 ]; do
  case "$1" in
    --no-wait) NO_WAIT=1; shift ;;
    --notify-email) NOTIFY_EMAIL="$2"; shift 2 ;;
    *) shift ;;
  esac
done

# ============ 工具函数 ============
log() { echo "[$(date '+%H:%M:%S')] $*"; }

send_msg() {
  smc seatalk message send-group "$GROUP_ID" --format markdown \
    --text "<mention-tag target=\"seatalk://user?id=${DE_BOT_SEATALK_ID}\"/> $1" --json 2>&1 \
    | python3 -c "import sys,json; print(json.load(sys.stdin)['message_id'])"
}

ts_offset() {
  python3 -c "import datetime; print((datetime.datetime.fromtimestamp($1)+datetime.timedelta(seconds=$2)).strftime('%Y-%m-%d %H:%M'))"
}

# 查 gateway, 结果追加到指定文件 (避免 shell 变量特殊字符问题)
query_gateway_to() {
  local pql="$1" start="$2" end="$3" outfile="$4"
  smc logcli query "$GATEWAY_APP" --pql "$pql" --start "$start" --end "$end" \
    --limit 100 --timeout 60 --json 2>&1 | python3 -c "
import sys, json, re
try: data = json.load(sys.stdin)
except: sys.exit(0)
if isinstance(data, list): rows = data
elif isinstance(data, dict):
    if 'data' in data and isinstance(data['data'], list): rows = data['data']
    elif 'logs' in data: rows = data['logs']
    else: rows = [data]
else: rows = []
for r in rows:
    if not isinstance(r, dict): continue
    raw = r.get('data', '{}')
    try: obj = json.loads(raw) if isinstance(raw, str) else raw
    except: continue
    if not isinstance(obj, dict): continue
    msg = obj.get('@message', '')
    if msg: print(re.sub(r'\x1b\[[0-9;]*m', '', msg))
" >> "$outfile"
}

query_runner_to() {
  local pql="$1" start="$2" end="$3" outfile="$4"
  smc logcli query "$RUNNER_APP" --pql "$pql" --start "$start" --end "$end" \
    --limit 50 --timeout 60 --json 2>&1 | python3 -c "
import sys, json, re
try: data = json.load(sys.stdin)
except: sys.exit(0)
if isinstance(data, list): rows = data
elif isinstance(data, dict):
    if 'data' in data and isinstance(data['data'], list): rows = data['data']
    elif 'logs' in data: rows = data['logs']
    else: rows = [data]
else: rows = []
for r in rows:
    if not isinstance(r, dict): continue
    raw = r.get('data', '{}')
    try: obj = json.loads(raw) if isinstance(raw, str) else raw
    except: continue
    if not isinstance(obj, dict): continue
    msg = obj.get('@message', '')
    if msg: print(re.sub(r'\x1b\[[0-9;]*m', '', msg))
" >> "$outfile"
}

# 从文件提取 request_id 前 8 位
extract_req_short_from() {
  python3 -c "
import re
text = open('$1', encoding='utf-8', errors='replace').read()
m = re.search(r'request_id=([0-9a-f]{8})-', text)
print(m.group(1) if m else '')
"
}

# 从文件提取 task_id
extract_task_id_from() {
  python3 -c "
import re
text = open('$1', encoding='utf-8', errors='replace').read()
# 优先 QNA (QnA 直答路径), 其次 OPR (任务路径)
m = re.search(r'((?:QNA|OPR)-[A-Z]+-[0-9]+)', text)
print(m.group(1) if m else '')
"
}

notify() {
  log ">>> 告警发送到 $NOTIFY_EMAIL"
  smc seatalk message send-user "$NOTIFY_EMAIL" --text "$1" 2>&1 | head -2
}

# trace_one: 追踪单条消息. 参数: label keyword t_send out_file
# out_file: 3 行 result|task_id|err_detail
trace_one() {
  local label="$1" kw="$2" t_send="$3" out_file="$4"

  local ws we
  ws=$(ts_offset "$t_send" -60)
  we=$(ts_offset "$t_send" 480)

  local workdir
  workdir=$(mktemp -d)
  local gwfile="$workdir/gw.log"
  : > "$gwfile"

  # Step A: 用 keyword 查 callback 入口, 写入文件
  query_gateway_to "$kw" "$ws" "$we" "$gwfile"
  if [ ! -s "$gwfile" ]; then
    printf '%s\n%s\n%s\n' "❌ 用关键词 '$kw' 未查到日志 (可能索引未就绪或关键词不匹配)" "N/A" "" > "$out_file"
    rm -rf "$workdir"; return
  fi

  # Step B: 提取 request_id 前 8 位
  local req_short
  req_short=$(extract_req_short_from "$gwfile")

  # Step C: 用 req_short 补充查完整链路, 追加到同一文件
  if [ -n "$req_short" ]; then
    query_gateway_to "$req_short" "$ws" "$we" "$gwfile"
  fi

  # Step D: marker 判定 (在文件上 grep, 不经过 shell 变量)
  local has_cb=0 has_terminal=0 has_reply=0 has_err=0
  grep -q "seatalk_cb" "$gwfile" && has_cb=1 || true
  grep -qE "terminal_agent_event|plan_completed|result_scheduled" "$gwfile" && has_terminal=1 || true
  if grep -qi "seatalk_api" "$gwfile" && grep -qi "group_chat" "$gwfile"; then has_reply=1; fi
  # error: 排除预期 fail_open / claim 400 / 正常 success
  local err_detail
  err_detail=$(grep -iE "error|panic|provisioning_error|dependency_error|non_actionable|failed" "$gwfile" \
    | grep -viE "error_|no_error|error_code.?:0|fail_open|claim_http_fail|status.?:0|\"success\":true" \
    | grep -viE "tcs_api \| claim" \
    | head -3)

  local tid
  tid=$(extract_task_id_from "$gwfile")
  [ -z "$tid" ] && tid="N/A"

  # Step E: runner 侧 worker↔gateway 注册检查
  local runner_status=""
  if [ "$tid" != "N/A" ]; then
    local rfile="$workdir/runner.log"
    : > "$rfile"
    query_runner_to "$tid" "$ws" "$we" "$rfile"
    if grep -q "runner_gateway_execution_registered" "$rfile"; then
      runner_status="runner注册✅"
    elif grep -q "runner_kafka_ticket_started" "$rfile"; then
      runner_status="runner启动✅未注册"
    elif [ -s "$rfile" ]; then
      runner_status="runner有日志无注册marker"
    else
      runner_status="runner侧无记录(QnA直答可能不经runner)"
    fi
  else
    runner_status="runner无法查(task_id缺失)"
  fi

  local result
  if [ "$has_err" = "1" ]; then
    result="❌ 执行出错: $(echo "$err_detail" | head -1 | cut -c1-50) | ${runner_status}"
  elif [ "$has_terminal" = "1" ] && [ "$has_reply" = "1" ]; then
    result="✅ 正常完成 (terminal/plan+回复) | ${runner_status}"
  elif [ "$has_terminal" = "1" ]; then
    result="⚠️ 已结束未发回复 | ${runner_status}"
  elif [ "$has_cb" = "1" ]; then
    result="⚠️ callback已收未结束 (可能仍执行) | ${runner_status}"
  else
    result="❌ 未发现 callback 入口 | ${runner_status}"
  fi

  printf '%s\n%s\n%s\n' "$result" "$tid" "$err_detail" > "$out_file"
  rm -rf "$workdir"
}

# ============ 主流程 ============
log "===== DE 回归测试开始 ====="

log "Step 1: 发送回归消息"
T1=$(date +%s)
MSG1_ID=$(send_msg "$MSG1_TEXT")
log "消息1 已发送: '$MSG1_TEXT' | message_id=$MSG1_ID | t1=$(ts_offset "$T1" 0)"

sleep 10
T2=$(date +%s)
MSG2_ID=$(send_msg "$MSG2_TEXT")
log "消息2 已发送: '$MSG2_TEXT' | message_id=$MSG2_ID | t2=$(ts_offset "$T2" 0)"

if [ "$NO_WAIT" = "0" ]; then
  log "Step 2: 等待 ${INDEX_WAIT}s 让 Space Log 索引追上..."
  sleep "$INDEX_WAIT"
else
  log "Step 2: 跳过等待 (--no-wait)"
fi

log "Step 3: 追踪全链路并判定"

TMPDIR_RUN=$(mktemp -d)
trap 'rm -rf "$TMPDIR_RUN"' EXIT

log "  消息1: keyword='$MSG1_KW'"
trace_one "MSG1" "$MSG1_KW" "$T1" "$TMPDIR_RUN/msg1.txt"
RESULT1=$(sed -n '1p' "$TMPDIR_RUN/msg1.txt")
TASK1=$(sed -n '2p' "$TMPDIR_RUN/msg1.txt")
ERR1=$(sed -n '3p' "$TMPDIR_RUN/msg1.txt")
log "  消息1 结果: $RESULT1"

log "  消息2: keyword='$MSG2_KW'"
trace_one "MSG2" "$MSG2_KW" "$T2" "$TMPDIR_RUN/msg2.txt"
RESULT2=$(sed -n '1p' "$TMPDIR_RUN/msg2.txt")
TASK2=$(sed -n '2p' "$TMPDIR_RUN/msg2.txt")
ERR2=$(sed -n '3p' "$TMPDIR_RUN/msg2.txt")
log "  消息2 结果: $RESULT2"

log "Step 4: 汇总结论"
echo ""
echo "========================================"
echo "  DE 回归测试结果  $(date '+%Y-%m-%d %H:%M')"
echo "========================================"
echo "[消息1] '$MSG1_TEXT'"
echo "  message_id : $MSG1_ID"
echo "  task_id    : ${TASK1:-N/A}"
echo "  结论       : ${RESULT1}"
echo ""
echo "[消息2] '$MSG2_TEXT'"
echo "  message_id : $MSG2_ID"
echo "  task_id    : ${TASK2:-N/A}"
echo "  结论       : ${RESULT2}"
echo "========================================"

HAS_FAIL=0
case "$RESULT1" in ❌*) HAS_FAIL=1 ;; esac
case "$RESULT2" in ❌*) HAS_FAIL=1 ;; esac

SUMMARY="DE 回归测试 $(date '+%m-%d %H:%M')
消息1 '$MSG1_TEXT': ${RESULT1}
  task=${TASK1:-N/A}
消息2 '$MSG2_TEXT': ${RESULT2}
  task=${TASK2:-N/A}"

if [ "$HAS_FAIL" = "1" ]; then
  SUMMARY="⚠️ DE 回归测试发现异常

$SUMMARY

异常详情:
[MSG1] ${ERR1}
[MSG2] ${ERR2}

请检查 gateway/runner 日志。"
  log "检测到异常, 发送告警..."
  notify "$SUMMARY"
else
  log "全部正常, 发送总结..."
  notify "✅ DE 回归测试全部通过

$SUMMARY"
fi

log "===== 回归测试结束 ====="
