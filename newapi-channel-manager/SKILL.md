---
name: newapi-channel-manager
description: Manage Jay's New-API deployment on racknerd_root. Use this skill whenever the user asks to create, update, delete, inspect, or test New-API channels, add OpenAI-compatible providers/models, validate all channel connectivity, diagnose New-API admin/channel-list errors, or operate on /opt/1panel/apps/new-api/new-api. This skill is especially important when the user provides a channel connection JSON like newapi_channel_conn, a key/base_url/models, or says “加到 newapi”, “验证所有渠道”, “渠道连通性”, “管理台获取渠道列表失败”.
---

# New-API Channel Manager

This skill manages Jay's New-API instance deployed through 1Panel on `racknerd_root`.

## Deployment facts

- SSH target: `racknerd_root`
- Project dir: `/opt/1panel/apps/new-api/new-api`
- Container: `new-api`
- Compose file: `/opt/1panel/apps/new-api/new-api/docker-compose.yml`
- Env file: `/opt/1panel/apps/new-api/new-api/.env`
- SQLite DB: `/opt/1panel/apps/new-api/new-api/data/one-api.db`
- Logs: `/opt/1panel/apps/new-api/new-api/logs`

Most admin-console channel config is stored in SQLite table `channels`, not in YAML.

## Safety rules

1. Always acknowledge briefly, then operate with tools.
2. Never print raw API keys, tokens, passwords, or bearer secrets. Redact as `sk-***REDACTED***`.
3. Before changing the DB, always create a timestamped backup under the same `data/` directory.
4. Prefer precise patch/update over rewriting the DB or compose file.
5. After channel mutation, restart New-API via compose and check container health.
6. Validate JSON-bearing fields after changes; invalid/empty JSON in these fields can break the admin channel list.
7. If an upstream is blocked by Cloudflare/WAF from RackNerd, do not keep retrying endlessly. Report that the server IP is blocked and offer delete/disable/proxy/allowlist options.

## Important table fields

`channels` relevant fields:

- `id`
- `type`
- `key`
- `open_ai_organization`
- `test_model`
- `status`
- `name`
- `weight`
- `created_time`
- `test_time`
- `response_time`
- `base_url`
- `other`
- `models`
- `group`
- `model_mapping`
- `status_code_mapping`
- `priority`
- `auto_ban`
- `other_info`
- `tag`
- `setting`
- `param_override`
- `header_override`
- `remark`
- `channel_info`
- `settings`

For current New-API versions, `setting`, `channel_info`, and `settings` must be valid JSON. Do not insert empty strings into them. Safest approach: copy these fields from an existing healthy channel of the same `type` unless the user explicitly supplies special settings.

## Supported channel creation flow

Use this when the user provides channel info, e.g.:

```json
{"_type":"newapi_channel_conn","key":"sk-...","url":"https://example.com","models":["gpt-x","claude-y"]}
```

or casually says: “把这个渠道加到 newapi，OpenAI 格式，模型 A/B”.

### Steps

1. Parse:
   - `name`: if not supplied, derive from hostname, e.g. `muyuan` from `https://muyuan.do`.
   - `type`: OpenAI-compatible defaults to `1`.
   - `base_url`: from `url`.
   - `models`: comma-separated string.
   - `test_model`: first model unless user specifies otherwise.
   - `group`: default `default`.
2. Preflight test from the same execution environment if possible:
   - First test local only if the user asks quick validation.
   - For real New-API usability, test from `racknerd_root`, because New-API runs there.
3. Backup DB.
4. Insert or update channel by matching `name` or `base_url`.
5. For JSON-bearing fields, copy a valid template from existing same-type channel:
   - `setting`
   - `channel_info`
   - `settings`
   - `header_override`
   - `remark`
6. Restart container.
7. Run JSON validity check and channel connectivity check.
8. Report concise result, including backup path, channel id, and whether the channel is usable from RackNerd.

## Create/update channel command template

Run this from local shell. Replace placeholders inside the remote Python only. Do not echo raw key.

```bash
ssh racknerd_root 'bash -s' <<'REMOTE'
set -euo pipefail
cd /opt/1panel/apps/new-api/new-api
TS=$(date +%Y%m%d-%H%M%S)
cp data/one-api.db "data/one-api.db.before-channel-change.$TS.bak"
echo "backup=data/one-api.db.before-channel-change.$TS.bak"
python3 <<'PY'
import sqlite3, time
DB='data/one-api.db'
NAME='REPLACE_NAME'
BASE='REPLACE_BASE_URL'
KEY='REPLACE_SECRET_KEY'
MODELS='REPLACE_COMMA_MODELS'
TYPE=1
TEST_MODEL=MODELS.split(',')[0].strip()
now=int(time.time())
conn=sqlite3.connect(DB)
conn.row_factory=sqlite3.Row
cur=conn.cursor()

tpl=cur.execute('''
select setting, channel_info, settings, header_override, remark
from channels
where type=?
  and setting is not null and setting<>'' and json_valid(setting)
  and channel_info is not null and length(channel_info)>2 and json_valid(channel_info)
  and settings is not null and settings<>'' and json_valid(settings)
order by id
limit 1
''', (TYPE,)).fetchone()
if not tpl:
    raise SystemExit('No valid template channel found for this type; inspect existing channels first.')

row=cur.execute('select id from channels where name=? or base_url=?', (NAME, BASE)).fetchone()
if row:
    cid=row['id']
    cur.execute('''
    update channels
    set type=?, key=?, base_url=?, models=?, status=1, "group"='default',
        priority=0, weight=0, auto_ban=1, test_model=?,
        setting=?, channel_info=?, settings=?, header_override=?, remark=?
    where id=?
    ''', (TYPE, KEY, BASE, MODELS, TEST_MODEL, tpl['setting'], tpl['channel_info'], tpl['settings'], tpl['header_override'], tpl['remark'], cid))
    action='updated'
else:
    cur.execute('''
    insert into channels
    (type, key, open_ai_organization, test_model, status, name, weight, created_time, test_time,
     response_time, base_url, other, balance, balance_updated_time, models, "group", used_quota,
     model_mapping, status_code_mapping, priority, auto_ban, other_info, tag, setting,
     param_override, header_override, remark, channel_info, settings)
    values
    (?, ?, '', ?, 1, ?, 0, ?, 0,
     0, ?, '', 0, 0, ?, 'default', 0,
     '', '', 0, 1, '', '', ?,
     '', ?, ?, ?, ?)
    ''', (TYPE, KEY, TEST_MODEL, NAME, now, BASE, MODELS, tpl['setting'], tpl['header_override'], tpl['remark'], tpl['channel_info'], tpl['settings']))
    cid=cur.lastrowid
    action='inserted'
conn.commit()
print(f'{action} channel_id={cid}')
conn.close()
PY
if command -v docker-compose >/dev/null 2>&1; then
  docker-compose up -d >/tmp/newapi-restart.log 2>&1
else
  docker compose up -d >/tmp/newapi-restart.log 2>&1
fi
sleep 2
docker ps --filter name=new-api --format '{{.Names}} {{.Status}}'
sqlite3 -header -column data/one-api.db "select id,name,json_valid(setting) as setting_ok,json_valid(channel_info) as channel_info_ok,json_valid(settings) as settings_ok from channels order by id;"
REMOTE
```

## Test all channels flow

Use this when the user asks to “验证所有渠道”, “测试所有渠道连通性”, “newapi 下所有渠道是否能请求”.

### What to test

- For OpenAI-compatible type `1`: direct upstream smoke test via `POST {base_url}/v1/chat/completions`.
- For DeepSeek-compatible type `43`: use default base `https://api.deepseek.com` if `base_url` is empty, then same OpenAI-compatible chat endpoint.
- For Gemini or other adapter-specific types, do not fake success. Mark as “not directly tested” unless you implement the specific adapter test or call New-API’s own admin test endpoint with proper auth.

### Test command template

```bash
ssh racknerd_root 'bash -s' <<'REMOTE'
set -euo pipefail
cd /opt/1panel/apps/new-api/new-api
python3 <<'PY'
import sqlite3,json,urllib.request,urllib.error,time,re
DB='data/one-api.db'
conn=sqlite3.connect(DB); conn.row_factory=sqlite3.Row
rows=conn.execute('select id,name,type,status,key,base_url,models,test_model from channels order by id').fetchall()
conn.close()
DEFAULT_BASE={43:'https://api.deepseek.com'}

def pick_model(models,test):
    return (test or '').strip() or ((models or '').split(',')[0].strip() if models else '')

def red(s):
    return re.sub(r'(sk-|sess-|eyJ)[A-Za-z0-9._-]+', r'\1***REDACTED***', str(s))[:300]

def test_openai(base,key,model):
    payload={'model':model,'messages':[{'role':'user','content':'Reply exactly: ok'}],'max_tokens':20,'temperature':0}
    req=urllib.request.Request(base.rstrip('/')+'/v1/chat/completions', data=json.dumps(payload).encode(), method='POST')
    headers={
      'Authorization':'Bearer '+key,
      'Content-Type':'application/json',
      'Accept':'application/json',
      'User-Agent':'Mozilla/5.0 AlmaNewApiChannelCheck/1.0'
    }
    for k,v in headers.items(): req.add_header(k,v)
    t=time.time()
    try:
        with urllib.request.urlopen(req,timeout=30) as r:
            body=r.read(65536).decode('utf-8','replace')
            try: obj=json.loads(body)
            except Exception: obj={}
            content=((obj.get('choices') or [{}])[0].get('message') or {}).get('content') if isinstance(obj,dict) else ''
            return True,r.status,int((time.time()-t)*1000),(content or '')[:60]
    except urllib.error.HTTPError as e:
        body=e.read(2048).decode('utf-8','replace')
        if 'Cloudflare' in body or 'Attention Required' in body:
            note='Cloudflare/WAF 403; likely server IP blocked'
        else:
            note=red(body).replace('\n',' ')
        return False,e.code,int((time.time()-t)*1000),note
    except Exception as e:
        return False,'-',int((time.time()-t)*1000),red(type(e).__name__+': '+str(e))

print('ID\tNAME\tTYPE\tMODEL\tRESULT\tSTATUS\tMS\tNOTE')
for r in rows:
    b=(r['base_url'] or '').strip() or DEFAULT_BASE.get(r['type'],'')
    m=pick_model(r['models'], r['test_model'])
    if r['status']!=1:
        print(f"{r['id']}\t{r['name']}\t{r['type']}\t{m}\tSKIP\t-\t-\tdisabled")
    elif r['type'] in (1,43) and b and m and r['key']:
        ok,st,ms,note=test_openai(b,r['key'],m)
        print(f"{r['id']}\t{r['name']}\t{r['type']}\t{m}\t{'OK' if ok else 'FAIL'}\t{st}\t{ms}\t{note}")
    else:
        print(f"{r['id']}\t{r['name']}\t{r['type']}\t{m}\tSKIP\t-\t-\tdirect tester unavailable for this channel type")
PY
REMOTE
```

## Diagnose admin “获取渠道列表失败”

This usually means malformed channel data, often invalid JSON fields.

Run:

```bash
ssh racknerd_root 'bash -s' <<'REMOTE'
set -euo pipefail
cd /opt/1panel/apps/new-api/new-api
echo '--- JSON validity'
sqlite3 -header -column data/one-api.db "select id,name,json_valid(setting) as setting_ok,json_valid(channel_info) as channel_info_ok,json_valid(settings) as settings_ok,length(setting),length(channel_info),length(settings) from channels order by id;"
echo '--- recent logs'
docker logs --tail 200 new-api 2>&1 | sed -E 's/(sk-|sess-|eyJ)[A-Za-z0-9._-]+/\1***REDACTED***/g' | grep -iE 'error|panic|json|channel|failed|失败|invalid' | tail -80 || true
REMOTE
```

If one channel has invalid JSON fields, backup DB and copy valid `setting/channel_info/settings/header_override/remark` from a healthy same-type channel.

## Delete or disable a bad channel

Prefer disable if unsure; delete if user explicitly asks.

Delete template:

```bash
ssh racknerd_root 'bash -s' <<'REMOTE'
set -euo pipefail
cd /opt/1panel/apps/new-api/new-api
TS=$(date +%Y%m%d-%H%M%S)
cp data/one-api.db "data/one-api.db.before-delete-channel.$TS.bak"
echo "backup=data/one-api.db.before-delete-channel.$TS.bak"
python3 <<'PY'
import sqlite3
TARGET_ID=REPLACE_ID
conn=sqlite3.connect('data/one-api.db')
cur=conn.cursor()
print('matched=', cur.execute('select id,name,base_url from channels where id=?',(TARGET_ID,)).fetchall())
cur.execute('delete from channels where id=?',(TARGET_ID,))
print('deleted=', cur.rowcount)
conn.commit(); conn.close()
PY
if command -v docker-compose >/dev/null 2>&1; then docker-compose up -d >/tmp/newapi-restart-delete.log 2>&1; else docker compose up -d >/tmp/newapi-restart-delete.log 2>&1; fi
sleep 2
docker ps --filter name=new-api --format '{{.Names}} {{.Status}}'
REMOTE
```

Disable template:

```bash
sqlite3 data/one-api.db "update channels set status=2 where id=REPLACE_ID;"
```

## Reporting format

Keep reports compact:

- What changed: channel name/id/type/models.
- Backup path.
- Container health.
- Connectivity table: ID, name, model, result, status, latency, note.
- Any unresolved risk, especially Cloudflare/WAF or unsupported adapter type.

Do not include raw keys.
