# P4.S5 — Result: Cross-project feedback list + Korean-safe search + detail

**Status: done.** The phase's flagship read surface is live: `/feedback` (list +
Korean-safe search + keyset pagination), `/feedback/[feedbackId]` (detail), and
the attachment download proxy. `/feedback` is now a real rail route, not a "Soon"
stub. No server actions were added — the action manifest still holds exactly the
3 from S3/S4.

## What landed (all under `web/`)

| File | What |
| --- | --- |
| `src/lib/vocky/types.ts` | `VockyFeedback` / `…Comment` / `…Attachment` / `…Detail` / `…Page` / `…Query` (+`// ── /app/feedback shapes (P4.S5) ──` banner) |
| `src/lib/vocky/app.ts` | `listFeedback` / `getFeedbackDetail` + the `feedbackQueryString` builder |
| `src/lib/vocky/client.ts` | **added** `getRaw` (raw/binary GET). `getJson`/`sendJson` untouched |
| `src/app/(app)/feedback/page.tsx` | **new** — list, filter form, pagination |
| `src/app/(app)/feedback/feedback-fields.tsx` | **new** — `formatUtc` / `Timestamp` / `RatingBadge` shared by list + detail |
| `src/app/(app)/feedback/[feedbackId]/page.tsx` | **new** — detail |
| `src/app/api/app/feedback/[feedbackId]/attachments/[attachmentId]/route.ts` | **new** — attachment proxy |
| `src/content/feedback.ts` | **new** — `FEEDBACK` copy |
| `src/content/index.ts` | re-export under `// Feedback (P4.S5)` |
| `src/content/app.ts` | dropped `soon: true` from `/feedback`; reworded the two stale doc comments |
| `tests/vocky-app.test.ts` | `── (P4.S5) ──` block, +6 tests |

Untouched, per the guardrails: `auth-guards.ts`, `session.ts`, `env.ts`,
`bff.ts`, `app-shell/*`, `data-table.tsx`, `components/usage/*`, `badge.tsx`,
`button.tsx`, `vitest.config.ts`, `.env.example`. No new deps, no new env, no new
tokens/variants, no `src/vocky/**` edits.

## Verification

### 1. In-sandbox gate — all green

| Command | Result |
| --- | --- |
| `pnpm install --frozen-lockfile` | pass (no lockfile change) |
| `pnpm typecheck` | pass |
| `pnpm lint` | pass |
| `pnpm test` | **56/56** (50 + 6 new) |
| `pnpm build` | pass — `/feedback`, `/feedback/[feedbackId]`, and the proxy all `ƒ (Dynamic)` |
| action manifest | **3** registered (1 dashboard + 2 project) — **unchanged**, S5 adds none |
| `python3 scripts/workflow.py validate` | pass |

### 2. Live E2E — driven end-to-end, `pnpm dev` on :3030 against live vocky on :8000

Heeding S4's gotcha: **`pnpm dev`, never `pnpm start`** (the prod build marks the
cookie `Secure`; a plain-http client never replays it). vocky healthy, worker
current — 8 fresh captures all persisted **with `project_id`** within ~1s.

Setup: 2 users × their own tenants; user A with 2 projects (`Checkout widget`,
`Docs site`) + minted `vk_` keys; 8 captures (Korean, English, mixed
`feedback_value` 1/2/null, one rich record with an uploaded PNG + 2 operator
comments, one XSS probe).

**The flagship check — `?q=결제` through the BFF:**

| Row | Matches `q=결제`? | Why it matters |
| --- | --- | --- |
| `결제 오류가 있어요` | ✅ | plain stem |
| `결제를 못 했습니다` | ✅ | **조사-attached** — proves substring, not tokenized |
| `Sudden logout` (comment: `결제 화면에서 튕겼어요`) | ✅ | **proves `q` matches on `comment`**, not just `message` |
| `Checkout was smooth and fast` | ❌ | correctly excluded |
| `Docs are unclear`, `검색이 잘 안 돼요` | ❌ | correctly excluded |

Also: `?q=결제를` → 1 row; `?q=checkout` → 1 row (case-insensitive against
`Checkout was…`).

**Everything else driven:**

- **List** — 6 rows newest-first, project **names** not UUIDs (a scan confirmed
  **zero bare UUIDs** rendered as cell text), ratings derived Liked/Disliked/Unrated.
- **The blank-param submit** — `?q=&project_id=&feedback_value=` (exactly what an
  empty GET form produces) → **200 with all 6 rows**. Without blank-omission this
  is a vocky **400**; it is the single sharpest edge in the slice.
- **Filters** — `?project_id=` → 4 rows; `?feedback_value=1` → 1 row;
  `?tag=urgent&source_product=checkout` → 1 row.
- **Both empty states, distinctly** — fresh tenant → "No projects yet…" (and *not*
  the no-matches copy); `?q=결제&project_id=<Docs site>` → "No feedback matches
  these filters" (and *not* the no-projects copy).
- **Pagination** — `?limit=2` → 3 pages × 2 rows, **no repeats**, Next link
  **absent** on the last page (proves the omitted-`next_cursor` handling).
- **Filters across the cursor boundary** — `?q=결제&limit=2` → page 1 (2 rows) →
  Next carries `q=%EA%B2%B0%EC%A0%9C` → page 2 (the 3rd match only). The English
  and docs rows are **absent from page 2**, proving the scope did not widen.
- **Hidden passthrough** — `?tag=urgent&source_product=checkout` renders both as
  hidden inputs and **`cursor` is not among them** (a submit resets to page 1).
- **Cross-tenant, 404-never-403** — A filtering by B's `project_id` → **404**; B's
  matching `결제` row **absent** from A's search; the **same record id → 200 for B,
  404 for A**.
- **Legacy NULL-`project_id` rows** — the DB holds **56**; A's `?limit=100` list
  shows **7** (their own only), the legacy id appears **nowhere** in the page, and
  a direct read of it → **404**.
- **Detail page** — message, comment, project name, integration, trigger,
  conversation/session/user ids, target text, trigger message, both tags, both
  operator comments (incl. the `null`-author → "Unknown author" fallback), the
  attachment (`shot.png` / `image/png` / `70 B` + proxy link with
  `download="shot.png"`), and all 5 raw JSON blobs. **0 `<form>` elements** — the
  read-only contract is structural, not just intended.
- **Attachment proxy** — A's download: **200**, `content-disposition: attachment`,
  `content-type: image/png`, `x-content-type-options: nosniff`,
  `cache-control: private, no-store`, and the bytes **`cmp`-identical** to the
  uploaded PNG. Hardening: no cookie → **401**; user B → **404**; malformed
  feedback id → **400**; malformed attachment id → **400**; unknown-but-valid uuid
  → **404**.
- **Error mapping** — detail: random uuid → 404, malformed id → 404. List:
  `?project_id=not-a-uuid` → 404, `?feedback_value=9` → 404, `?cursor=garbage` → 404.
- **XSS** — a captured `<script>alert(1)</script><img src=x onerror=alert(2)>`
  renders **escaped as text** on both list and detail; no live script/onerror in
  either document.
- **Leak checks** — across 5 rendered pages: **0** occurrences of the session
  token, **0** `vk_` strings, **0** `vocky_session`.
- **Rail nav** — `/feedback` is a real `<a href="/feedback">` with
  `aria-current="page"`; the "Soon" tag is **gone**.
- **Dev log** — **0** 500s / unhandled errors across the whole run (26×200, 2×400,
  1×401, 10×404 — every non-200 intentional).

## Deviations from `plan.md`

1. **`feedback-fields.tsx` (new, colocated).** The plan named 4 new files; this is
   a 5th. `formatUtc` + `RatingBadge` are needed identically by the list *and* the
   detail page, and duplicating them across sibling routes was the worse option.
   Colocated in the route folder — the S4 idiom for a non-route file (only
   page/route/layout files become routes). It is not a `@/components/ui` primitive
   on purpose: both helpers encode vocky's shapes (`1|2|null`, UTC ISO), and the
   ui/ kit is domain-free and P6-swappable.
2. **The list page maps 400/404 → `notFound()`.** The plan specified this mapping
   only for the detail page — but its own E2E requires "a second user's
   `project_id` → 404", which is a *list*-page fetch. I extended the S4 policy
   verbatim (404 = missing-or-foreign, 400 = malformed ⇒ same page, since
   distinguishing leaks what exists). Verified live in both directions.
3. **The proxy maps vocky 401 → 401** (the plan says 404→404, 503→502, others→500).
   The route already answers 401 for a missing cookie, and a vocky 401 means the
   identical thing (the token died mid-request) — routing it to 500 would blame us
   for a dead session. Everything unexpected still → 500.
4. **Timestamps are pinned to UTC** with a "Times are shown in UTC, newest first."
   note. Not specified. These render *server-side*, so an unpinned zone silently
   prints the deploy box's clock and passes it off as local time; and unlike
   S3/S4's date-only formatters this keeps the time, without which a newest-first
   page of same-day rows looks unsorted.
5. **`web/.env.local` created** (gitignored, untracked) — required to run the live
   E2E; `.env.example` untouched as instructed. Left in place for the review slice.

Nothing else diverged. The plan's design calls (GET form / no client island,
forward-only pagination, the 3-filter UI over the full param set, the parallel
`/app/projects` fetch, forced `Content-Disposition: attachment`, keeping the
`soon` mechanism) were all implemented as written.

## Notes for the review slice

- **vocky is left healthy on `:8000`**; the local `worker` image is current
  (fresh captures persist with `project_id`). The Next dev server is stopped.
- The **Doc impact** line is appended to `phase.md`; it feeds `frontend.md`,
  `experience.md`, and `architecture.md`.
- One knock-on the guardrails forbade me from fixing: `app-shell/rail-nav.tsx`'s
  doc comment still reads "*routes a later slice ships — /feedback is S5*", now
  stale (the mechanism it describes is still correct, and no item sets `soon`
  today). It is a comment only, in a file S5 was told not to touch. Worth a
  one-line reword whenever that file is next opened.
