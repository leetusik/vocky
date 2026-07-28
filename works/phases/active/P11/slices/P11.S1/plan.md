# P11.S1 — Landing hero honesty: nested `source.product` + real `vk_` key shape

## Why

The landing hero publishes two statements that are false against the running product. A visitor who
copy-pastes the depicted request gets a `400`. This slice makes the hero true **before** the design gate
(`P11.S5`), because Claude Design reads the real repo — designing a round around a lie would bake the lie
into the design.

1. `web/src/content/landing.ts:57` shows `Bearer vk_live_9f3c…`. **There is no `live` tier.** Keys are
   `"vk_" + secrets.token_urlsafe(32)` at both project and org scope (`src/vocky/app_api.py:241,320`).
2. `landing.ts:59` shows a **top-level** `"source_product"`. Capture **requires a nested**
   `source: {product, integration?}` (`src/vocky/capture.py:27-31`, field declared at `:38`, non-blank
   guard at `:275`). A working in-tree reference is `src/vocky/smoke.py:112`.
3. The file-header comment at `landing.ts:11-13` asserts the wrong contract — it points at
   `lib/vocky/types.ts` (the **read/stored** record) as the source of truth for the capture **request**,
   and names `source_product` as a hero field. Leaving it would invite a future reader to "fix" the body
   back to the broken shape.

## Scope — exactly one file

**Edit `web/src/content/landing.ts` and nothing else.** No component changes: `hero.tsx:27-30` only
interpolates `hero.request.auth` and `hero.request.body`, so it needs no edit. This is copy inside an
already-designed component, which is **not** a design round.

### DO NOT TOUCH — `source_product` is correct on the read path

These occurrences describe the **stored record**, where the field genuinely is flat. Leave every one of
them exactly as it is:

- `web/src/app/(app)/feedback/page.tsx`
- `web/src/app/(app)/feedback/[feedbackId]/page.tsx`
- `web/src/lib/vocky/types.ts`
- `web/tests/vocky-app.test.ts`
- `src/vocky/smoke.py:141` (a `GET /api/feedback` query parameter)

Only the **capture request** nests it.

## The three edits, verbatim

### Edit 1 — the file-header comment (currently lines 10-13)

Find this exact block:

```
// over message/comment/target text, MIT-licensed + self-hostable. The hero
// request body mirrors the real capture shape in `lib/vocky/types.ts`
// (`message` incl. Korean, `feedback_value: 2` = dislike, `source_product`,
// `target_type`, `tags`).
```

Replace it with:

```
// over message/comment/target text, MIT-licensed + self-hostable. The hero
// request body mirrors the real capture CONTRACT in `src/vocky/capture.py`
// (`message` incl. Korean, the REQUIRED nested `source.product`,
// `feedback_value: 2` = dislike, `target_type`, `tags`). `lib/vocky/types.ts`
// describes the stored/READ record, where `source_product` is flat — the
// capture REQUEST nests it, and only the request is depicted here.
```

### Edit 2 — the auth line (currently line 57)

Find this exact line:

```
      auth: "Authorization: Bearer vk_live_9f3c…",
```

Replace it with:

```
      auth: "Authorization: Bearer vk_9f3c…",
```

Keep the trailing `…` — it marks the value as truncated, which is honest. Only `live_` is removed.

### Edit 3 — the payload's first field (currently line 59)

Find this exact line (it is inside a template literal, so its indentation is content, not code style —
reproduce the two leading spaces exactly):

```
  "source_product": "checkout-web",
```

Replace it with:

```
  "source": { "product": "checkout-web" },
```

Leave the rest of the body untouched. **The other four fields are all valid top-level capture fields**
(`src/vocky/capture.py:34-57`): `message`, `feedback_value`, `target_type`, `tags`. Only the first field
was wrong.

The body must end up reading exactly:

```
{
  "source": { "product": "checkout-web" },
  "message": "결제 단계에서 카드가 자꾸 거절돼요.",
  "feedback_value": 2,
  "target_type": "message",
  "tags": ["결제", "checkout"]
}
```

## Validation — run these in order, from `web/`

1. `pnpm typecheck` → must exit 0.
2. `pnpm test` → must be **61 passed** across 5 files, the same as before this slice (no test asserts
   these constants today).
3. `pnpm lint` → must exit 0.
4. `pnpm format:check` → if it names `src/content/landing.ts`, run
   `pnpm exec prettier --write src/content/landing.ts` and re-run. If it names **other** files, those are
   pre-existing — leave them alone and say so in `result.md`.

Then from the repo root:

5. `grep -rn "vk_live" web/ src/ docs/ --exclude-dir=node_modules` → must return **no matches anywhere in
   the repo**.
6. `grep -n "source_product" web/src/content/landing.ts` → must return **no matches** (the comment no
   longer names it as a hero field, and the payload no longer uses it — note the replacement comment does
   mention `source_product` when describing the read record, so expect exactly the one occurrence on the
   `describes the stored/READ record` line; that one is correct and intended).

If any check fails in a way the steps above do not cover, **escalate** — do not improvise a fix.

## Out of scope

- No component, style, or layout change. `hero.tsx` is not edited.
- No install line, no new section — those are `P11.S3` and the `P11.S5` design round.
- No doc version. If this changes durable truth, append **one line** to the `## Doc impact` section of
  `works/phases/active/P11/phase.md`; never run `doc-new-version`.

## When done

Write `works/phases/active/P11/slices/P11.S1/result.md` (free-form): the three edits as they landed, the
verbatim output of each validation command, and anything the later slices should know. Append any durable
cross-slice note to `works/phases/active/P11/phase.md`. Do not commit and do not change any slice or phase
status.
