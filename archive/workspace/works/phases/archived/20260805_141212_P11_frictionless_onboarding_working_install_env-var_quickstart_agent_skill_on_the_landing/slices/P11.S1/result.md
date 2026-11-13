# P11.S1 result — Landing hero honesty

## Summary

Applied the three verbatim edits from `plan.md` to `web/src/content/landing.ts`. No other file was
touched. `git diff --stat` confirms exactly one file changed (7 insertions, 5 deletions).

## The three edits, as landed

### Edit 1 — file-header comment (was lines 11-13, now lines 11-15)

```
// request body mirrors the real capture CONTRACT in `src/vocky/capture.py`
// (`message` incl. Korean, the REQUIRED nested `source.product`,
// `feedback_value: 2` = dislike, `target_type`, `tags`). `lib/vocky/types.ts`
// describes the stored/READ record, where `source_product` is flat — the
// capture REQUEST nests it, and only the request is depicted here.
```

### Edit 2 — auth line (line 59)

```
      auth: "Authorization: Bearer vk_9f3c…",
```

### Edit 3 — payload first field (line 61)

```
  "source": { "product": "checkout-web" },
```

Full request body now reads exactly as the plan specified:

```
{
  "source": { "product": "checkout-web" },
  "message": "결제 단계에서 카드가 자꾸 거절돼요.",
  "feedback_value": 2,
  "target_type": "message",
  "tags": ["결제", "checkout"]
}
```

No other field in the body was touched, and no component (`hero.tsx`) was edited.

## Validation — verbatim output

1. `pnpm typecheck` (from `web/`):
```
> vocky-web@0.1.0 typecheck /Users/sugang/projects/personal/vocky/web
> tsc --noEmit
```
Exit 0. PASS.

2. `pnpm test` (from `web/`):
```
> vocky-web@0.1.0 test /Users/sugang/projects/personal/vocky/web
> vitest run

 RUN  v4.1.10 /Users/sugang/projects/personal/vocky/web

 Test Files  5 passed (5)
      Tests  61 passed (61)
```
61 passed across 5 files — matches the pre-slice baseline exactly. PASS.

3. `pnpm lint` (from `web/`):
```
> vocky-web@0.1.0 lint /Users/sugang/projects/personal/vocky/web
> eslint .
```
Exit 0, no warnings/errors. PASS.

4. `pnpm format:check` (from `web/`):
```
> vocky-web@0.1.0 format:check /Users/sugang/projects/personal/vocky/web
> prettier --check .

Checking formatting...
[warn] README.md
[warn] src/app/(app)/projects/[projectId]/actions.ts
[warn] src/app/apple-icon.tsx
[warn] src/app/opengraph-image.tsx
[warn] src/lib/bff.ts
[warn] src/lib/env.ts
[warn] src/lib/session.ts
[warn] src/lib/vocky/auth.ts
[warn] tests/auth-routes.test.ts
[warn] tests/session-guards.test.ts
[warn] tests/session.test.ts
[warn] tests/vocky-auth.test.ts
[warn] Code style issues found in 12 files. Run Prettier with --write to fix.
```
Exit 1, but **none of the 12 named files is `src/content/landing.ts`** — per the plan, these are
pre-existing formatting drift unrelated to this slice. Left untouched, as instructed.

5. `grep -rn "vk_live" web/ src/ docs/ --exclude-dir=node_modules` (from repo root):
No output, exit 1 (grep convention for "no matches"). **No `vk_live` occurrences anywhere in the repo.**
PASS.

6. `grep -n "source_product" web/src/content/landing.ts` (from repo root):
```
14:// describes the stored/READ record, where `source_product` is flat — the
```
Exactly one match, on the "describes the stored/READ record" comment line — exactly the expected,
intended occurrence. PASS.

## Deviations from plan

None. All three edits were applied exactly as specified (verbatim strings, indentation, Korean text, and
the `…` character all reproduced). Only `web/src/content/landing.ts` was edited.

## For later slices

- The hero now depicts a truthful `vk_` key shape and a truthful nested `source.product` capture request.
  `P11.S5` (design round 02) can safely read the real repo without designing around a lie.
- The five "DO NOT TOUCH" read-path occurrences of `source_product`
  (`web/src/app/(app)/feedback/page.tsx`, `web/src/app/(app)/feedback/[feedbackId]/page.tsx`,
  `web/src/lib/vocky/types.ts`, `web/tests/vocky-app.test.ts`, `src/vocky/smoke.py:141`) were left
  untouched, confirmed correct, and confirmed unaffected by this slice's grep checks.
- Pre-existing prettier drift in 12 unrelated files (see step 4 above) is **not** introduced by this
  slice and was left alone per the plan's instruction.
