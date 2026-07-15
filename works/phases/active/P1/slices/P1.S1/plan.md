# P1.S1 — Relicense to MIT

> Native plan for slice **P1.S1** (`implementation`, risk **low** → `slice-executor-low`, a
> literal plan-follower). Every edit below has exact target text — apply verbatim, no judgment
> calls. You never commit and never transition slice/phase status; write `result.md` and append
> a one-line note to `phase.md` when done, then return your verdict.

## Context

P1 relicenses vocky from AGPL-3.0 to MIT (full open source) as the base for the SaaS pivot. The
license is declared in exactly three files (confirmed by an Explore pass; see `phase.md` →
Findings → *License map*). Operator-confirmed copyright holder: **`Vocky`**. This slice changes
only those three files — no code, no durable docs (the license is absent from every durable doc).

## Edits (exact)

### 1. `LICENSE` — replace the entire file
Replace the full AGPL-3.0 text (currently starts `GNU AFFERO GENERAL PUBLIC LICENSE / Version 3,
19 November 2007`) with **exactly** this MIT text:

```
MIT License

Copyright (c) 2026 Vocky

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

The final file must contain the MIT text only (the entire ~660-line AGPL body is gone).

### 2. `pyproject.toml` — line 11
Change:
```
license = { text = "AGPL-3.0-only" }
```
to:
```
license = { text = "MIT" }
```
(Change only the `license` line. Do **not** touch line 8's `description` or the `mcp[cli]`
dependency on line 17 — those belong to slice P1.S2.)

### 3. `README.md` — line 380
Change:
```
Vocky is licensed under the GNU Affero General Public License v3.0. See [LICENSE](./LICENSE).
```
to:
```
Vocky is licensed under the MIT License. See [LICENSE](./LICENSE).
```
(Leave the `## License` heading on line 378 as-is.)

## Verification

- `grep -riE "AGPL|Affero|GNU|Public License" LICENSE pyproject.toml README.md` → the only
  permitted remaining match is the README heading `## License` (the word "License"); there must
  be **no** "AGPL", "Affero", "GNU", or "Public License" hits.
- `grep -n "MIT" LICENSE pyproject.toml README.md` → shows the new MIT declarations in all three.
- Optional sanity (no behavior change expected): `uv run python -c "import vocky.app"` still
  imports (the license edit is runtime-inert).

## phase.md note (append when done)
One line under Findings & Notes, e.g. "S1 done: relicensed to MIT (LICENSE + pyproject + README);
no durable-doc impact." No `doc-new-version` in this slice.
