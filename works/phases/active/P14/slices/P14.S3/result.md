# Result — P14.S3: End-to-end verification of agent-recorded capture

**Verdict: done.** Every item in `plan.md` was proven against the running local stack. One product
change was made: a three-line deploy-time guard in `src/vocky/smoke.py` (the plan's sanctioned
optional extension). All ad-hoc drivers stayed in the session scratchpad and were not committed.

Stack: `make compose-up` **rebuilt** `app` + `worker` (the running containers were 7 days old and
predated S1/S2 — without the rebuild none of the live evidence below would have been about P14's
code), then `make migrate` + `make wait-ready`.

---

## 1. Full suite + static gates

```
$ make test
238 passed in 9.82s                       # matches the S2 baseline exactly

$ make check-skill-parity
PASS — web/public/SKILL.md matches the canonical skill byte-for-byte.

$ uv run alembic check
INFO  [alembic.autogenerate.compare.constraints] Detected removed index
      'ix_feedback_events_search_trgm' on 'feedback_events'
FAILED: New upgrade operations detected:
      [('remove_index', Index('ix_feedback_events_search_trgm', ...))]
```

`alembic check` reports **only** the known pre-existing trigram-index drift — no `add_column`, no
`add_index`, i.e. `recorded_by` and `ix_feedback_events_recorded_by` match the ORM model exactly.

`make test` was run again after the `smoke.py` edit: **238 passed**. `python3 scripts/workflow.py
validate` → `Workflow validation passed.`

## 2. Migration reversibility (targets pinned by revision id, never `-1`)

```
$ uv run alembic downgrade 20260728_1200
INFO  Running downgrade 20260805_1200 -> 20260728_1200, add feedback recorded_by marker
$ uv run alembic current
20260728_1200
$ psql -tAc "select count(*) from information_schema.columns
             where table_name='feedback_events' and column_name='recorded_by'"   -> 0
$ psql -tAc "select count(*) from pg_indexes
             where indexname='ix_feedback_events_recorded_by'"                   -> 0

$ uv run alembic upgrade head
INFO  Running upgrade 20260728_1200 -> 20260805_1200, add feedback recorded_by marker
$ uv run alembic current
20260805_1200 (head)
$ psql -tAc "select column_name, data_type, is_nullable from information_schema.columns
             where table_name='feedback_events' and column_name='recorded_by'"
recorded_by|text|YES
$ psql -tAc "select indexdef from pg_indexes where indexname='ix_feedback_events_recorded_by'"
CREATE INDEX ix_feedback_events_recorded_by ON public.feedback_events USING btree (recorded_by)
```

Down and back up against a real Postgres holding real rows; column nullable, index restored
verbatim, no data loss, no backfill.

## 3. REST round-trip

`make smoke` (the untouched `vocky-smoke` REST loop) passed before any edit:

```
healthz ok at http://127.0.0.1:8000
POST /api/feedback accepted: a0f39a56-8416-4062-abeb-b04fb50a1624
GET /api/feedback ok: 1 record(s)
```

Then the live matrix (driver: scratchpad `p14_s3_live.py`; run id `4293ed207713`, its own signed-up
user + project + `vk_` key). Explicit `recorded_by: "human"` on REST, and one capture omitting it:

```
REST accepted: human=9abac4fd-… omitted=3bbae97b-…
REST bad marker -> 400 {"detail":"recorded_by must be one of: agent, human"}
```

## 4. MCP round-trip — the headline

One **real authenticated MCP session** over HTTP against the container's `/mcp` (`vk_` bearer,
`mcp.client.streamable_http` + `ClientSession`, JSON-RPC `initialize` → `tools/list` →
two `tools/call capture_feedback`):

```
MCP {"serverInfo": "Vocky 1.28.1", "tools": ["capture_feedback"],
     "recorded_by_in_schema": true,
     "recorded_by_schema": {"anyOf": [{"type":"string"},{"type":"null"}],
                            "default": null, "title": "Recorded By"}}
MCP {"call": "mcp-default",  "isError": false,
     "structured": {"request_id": "13235202-…", "status": "accepted"}}
MCP {"call": "mcp-explicit", "isError": false,
     "structured": {"request_id": "34675f8f-…", "status": "accepted"}}
```

`mcp-default` omitted `recorded_by` entirely and carried D3's field mapping — Korean free-text
sentiment in `message` (`감사합니다 정말 도움이 되었어요 (…)`) and the agent's note in `comment`
(`사용자가 수출 흐름을 마친 뒤 남긴 소감입니다 감사 표현 …`), `source.integration = "langchain-mcp"`.
`mcp-explicit` passed `recorded_by: "human"`.

**Read back through `GET /api/feedback` after the worker persisted (all four in one page):**

```
  rest-human    recorded_by='human'   integration='curl'          message='REST explicit human …'
  rest-omitted  recorded_by=None      integration='curl'          message='REST omitted marker …'
  mcp-default   recorded_by='agent'   integration='langchain-mcp' message='감사합니다 정말 도움이 …'
  mcp-explicit  recorded_by='human'   integration='langchain-mcp' message='MCP explicit human …'
```

**Confirmed at the storage layer, not just the serializer:**

```
$ psql -c "select session_id, recorded_by, source_integration, left(message,30), left(comment,28)
           from feedback_events where source_product='p14s3-4293ed207713' order by session_id;"
 mcp-default  | agent  | langchain-mcp | 감사합니다 정말 도움이 되었어요 … | 사용자가 수출 흐름을 마친 뒤 남긴 소감입니다 감사
 mcp-explicit | human  | langchain-mcp | MCP explicit human …             | agent relaying a human-recor
 rest-human   | human  | curl          | REST explicit human …            |
 rest-omitted |        | curl          | REST omitted marker …            |      <- NULL, unspecified
```

D2 proven live end to end: MCP default `agent`, explicit value wins, REST stays `NULL`, and the
marker survives the hand-written Redis serialize → deserialize round-trip into Postgres.

## 5. Filtered reads (three surfaces, not the two the plan asked for)

```
  GET /api/feedback?recorded_by=agent        n=1 sessions=['mcp-default']  markers=['agent']
  GET /api/feedback?recorded_by=human        n=2 sessions=['mcp-explicit','rest-human']
  GET /admin/api/feedback?recorded_by=agent  n=1 sessions=['mcp-default']  markers=['agent']
  GET /app/feedback?recorded_by=agent        n=1 sessions=['mcp-default']  markers=['agent']
  GET /app/feedback (no marker filter)       n=4 markers=['None','agent','human']   <- additivity
  bad filter value -> 400 {"detail":"recorded_by must be one of: agent, human"}
```

The unfiltered read still returns all four including the `NULL` row — absent-means-no-filter holds,
and the 400 string is byte-identical to the capture-side one.

**`pg_trgm` search over the Korean text** (`/app/feedback?q=`, the only surface with `q`):

```
  q='감사'            n=1 sessions=['mcp-default']   # sentiment substring (message)
  q='도움이 되었어요'  n=1 sessions=['mcp-default']   # sentiment phrase (message)
  q='수출 흐름'        n=1 sessions=['mcp-default']   # agent note substring (comment)
  q='존재하지않는문구'  n=0 sessions=[]                # negative control
  q=감사 & recorded_by=agent -> n=1                   # search + marker compose
```

D3's core claim verified: because sentiment lands in `message` and the note in `comment`, both are
already inside the trigram search expression — Korean substrings match with zero index work.

## 6. MCP Host allowlist (D4 item 1 — verify only, no config edited)

Negative, against the compose app (whose allowlist is the localhost default):

```
[compose-default] POST /mcp/  Host: 127.0.0.1:8000    -> 200  {"jsonrpc":"2.0","id":1,"result":{…}}
[compose-default] POST /mcp/  Host: vocky.hi2vi.com   -> 421  Invalid Host header
```

Positive: a second server process started from the same tree/DB on port 8011 with
`VOCKY_MCP_ALLOWED_HOSTS=vocky.hi2vi.com` — the **exact value `compose.prod.yml:143` sets** — and a
full authenticated MCP session driven with that `Host`:

```
[allowlisted-public-host] POST /mcp/ Host: 127.0.0.1:8011  -> 200
[allowlisted-public-host] POST /mcp/ Host: vocky.hi2vi.com -> 200
[allowlisted-public-host] authenticated MCP session Host: vocky.hi2vi.com ->
    initialize OK serverInfo=Vocky 1.28.1, tools=['capture_feedback'],
    capture isError=False status=accepted
$ psql … where source_product like 'p14s3-host-%'
 p14s3-host-9fa6b2f40da2 | agent | host-allowlist probe …
```

No `Origin` header was sent by any of these non-browser clients and none was required — D4's reading
that leaving `VOCKY_MCP_ALLOWED_ORIGINS` unset is correct is confirmed empirically. Nothing under
`compose.prod.yml`, `docker-compose.yml`, or `.env` was modified; the ad-hoc server was stopped
afterwards (`8011:000`, `8000:200`, all four vocky containers healthy).

## 7. The one product change: a terse smoke guard

`src/vocky/smoke.py` — the reference capture payload now sends `"recorded_by": "human"` and the
existing round-trip assertion gained one clause (`matched_record.get("recorded_by") != "human"`).
Three lines plus a comment, inside the loop that already exists.

Why it earns its keep: the suite covers the marker in-process, but the queue's hand-written
`_serialize_payload`/`_deserialize_payload` pair is the one place a capture field is dropped
**silently**, and `vocky-smoke` is the only check that exercises the real app → Redis → worker →
Postgres → read path against a **deployed** environment (`make smoke`, `make external-smoke`,
`make external-verify`, and the deploy script's post-deploy gate). No new harness, no new file.

```
$ make smoke                       # after the edit
POST /api/feedback accepted: e586e059-…
GET /api/feedback ok: 1 record(s)
$ psql -tAc "select recorded_by, source_integration from feedback_events
             where source_product='vocky-smoke' order by ingested_at desc limit 2;"
human|make-smoke                   <- this run
|make-smoke                        <- the pre-edit run, still NULL
```

## Prod rollout ordering (recorded, not executed — P12 owns deploy)

Migrate **before** deploying code that reads `recorded_by`. The column is nullable with no backfill
and the index is a plain btree over a fresh all-NULL column, so the migration is instant and
non-blocking — there is no lock window to schedule around. Old-code + new-schema is safe (old code
never selects the column); new-code + old-schema 500s.

`deploy/deploy.sh` already enforces exactly this: step 6 `alembic upgrade head` in a one-off
container, step 7 `up -d` to recreate api/worker on the new images against the already-migrated
schema. **No operational change is required for P14.** `deploy/rollback.sh` deliberately does not
re-migrate ("assumes additive migrations") — P14's migration is additive, so a rollback to pre-P14
images over the P14 schema is safe and the column simply goes unread.

## Deviations from `plan.md`

- **Filtered reads on three surfaces, not two** (`/api/feedback`, `/admin/api/feedback`,
  `/app/feedback`) — cheap once the driver existed. The fourth (`/api/project/feedback`) shares
  `normalize_list_query` with the two `/app`+`/admin` surfaces already covered.
- **The `q` trigram search ran on `/app/feedback` only** — that is the *only* surface that accepts
  `q` (`app_feedback_api.py:133` is the sole assignment to `filters.search` in the codebase).
- **The Host-allowlist positive case needed a second server process**, because local
  `docker-compose.yml` does not forward `VOCKY_MCP_ALLOWED_HOSTS` to the `app` service (see the
  phase.md note). No config file was edited; the process was started with the env pair and stopped.
- **`make compose-up` rebuilt the app/worker images.** Not called out in the plan, but the running
  containers predated S1/S2 and would have made every "live" result meaningless.
- One product edit (the smoke guard) rather than none — the plan's explicitly sanctioned option.

## Files changed

- `src/vocky/smoke.py` (3 lines + comment)
- `works/phases/active/P14/slices/P14.S3/result.md` (this file)
- `works/phases/active/P14/phase.md` (cross-slice notes + Doc impact lines)

Scratchpad only, **not committed**: `p14_s3_live.py`, `p14_s3_host.py`, `server8011.log` under
`…/51e74da6-f51d-4ef8-b562-d111e6105058/scratchpad/`.
