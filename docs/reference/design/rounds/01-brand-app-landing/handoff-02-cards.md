# Design handoff — Round 01, addendum 02: render the design as a card set

**To:** Claude Design, with the operator (sugang)
**From:** Claude Code (vocky repo)
**Round:** 01 (addendum) · **Phase:** P8 · **Slice:** P8.S2
**Project:** `1eaa0803-46e3-426a-ab04-17a802170234` — `vocky design system`
**Supersedes:** the required-output manifest of `handoff.md` (§8) and its §10 "no cards" statement.
Everything else in `handoff.md` stands.

---

## 0. This is a visibility pass. It decides nothing new.

**Round 01's design is done and it is not in question.** `output/result.md` and `output/build-prompt.md`
are complete, **authoritative, and stay exactly as they are.** This addendum does not reopen them, does
not ask for a redesign, and does not change a single design decision.

**The problem is that the operator cannot see it.**

The round came back as two monolithic files — `Vocky Round 01 - Design System.html` and
`Vocky Round 01 - Landing.html` — with **no line-1 `@dsCard` marker on either**. The Design System pane
builds its index from that marker, compiling it into `_ds_manifest.json` on the app's self-check. No
marker → no card → **the pane is empty.** The operator has a complete `build-prompt.md` they can neither
see, review, nor fix.

**That is our fault, not yours.** The original `handoff.md` explicitly told you there were "no cards"
(§10) and its required-output manifest (§8) asked only for `result.md` and `build-prompt.md`. You
delivered exactly what was asked. The rule was wrong and has since been corrected: **the card set is a
required output of the round, and markdown alone is not a round.**

**So: render what you have already designed as a reviewable card set.** Same design, visible.

**Any real design change from here is the operator's to make, on the cards.** That is the whole point —
cards are the surface they co-work on, one at a time. This pass just gets the design onto that surface.

---

## 1. What to deliver

### 1.1 One card per reviewable unit

**Never one monolithic page.** The operator fixes one card at a time, and a monolith can be neither
reviewed nor superseded piecemeal — that is exactly what went wrong. Each card is its own file.

These are the `group`s, which become the pane's headings, and the units in each:

| `group` | Cards |
|---|---|
| **Foundations** | color · type · spacing/radius |
| **Components** | button · card · badge · field · select · chip · data-table · endpoint-card · section/grid |
| **App** | login/signup · shell · dashboard · project detail · feedback list · feedback detail |
| **Landing** | nav+hero · how-it-works · showcase · features · pricing · closing+footer |
| **States** | loading · error · 404 |

**27 cards.** This list is the **floor, not the ceiling**: if round 01 designed a reviewable unit that is
not on this list, **it gets a card too.** The list was assembled from the outside — do not drop something
you designed just because it is missing here.

Grouping is organization, not design. Naming the groups is how we keep the round reviewable without
deciding anything inside it.

### 1.2 Line 1 of every card file — exactly this shape

```html
<!-- @dsCard group="Components" name="Button" subtitle="Primary / secondary / ghost · 3 sizes" viewport="960x600" -->
```

It must be **line 1**, exactly — the app's self-check compiles the marker into `_ds_manifest.json`, and
anything else on line 1 means no card.

- `group` — one of the five above; plus the file path, this is what the pane needs
- `name` — the card's label
- `subtitle` — **what the card is for.** This is where a card explains itself
- `viewport` — sized to the unit; a full app surface needs more room than a badge

### 1.3 `tokens.css` — carrying round 01's real values

Author a `tokens.css` holding the round's **actual token values** (they are in `build-prompt.md` §2–§4),
and **link it from the cards**, so the pane compiles the Foundations group from real values rather than
a description.

**You author this, not us.** The palette *is* the design. A copy maintained on our side would be a mirror,
and a mirror only drifts — that is exactly why the previous one was deleted.

### 1.4 Supersede the two monoliths

`Vocky Round 01 - Design System.html` and `Vocky Round 01 - Landing.html` must **not survive as a second
source of truth.** Delete or replace them as part of this pass. One design, one place to review it.

---

## 2. Ground every card in real content — no lorem

The repo is connected; use it. Real strings, real data shapes, real edge cases. A card showing invented
copy is a card that lies about how the design holds up.

Concretely — these are shipped and real:

- **Feedback search** (`web/src/content/feedback.ts`): placeholder `"e.g. 결제 or checkout"`; hint
  `"Matches any part of the feedback text, comment, or context — Korean and English alike."`
- **Feedback list columns**: `When` · `Project` · `Feedback` · `Rating` · `Source`, with
  `"Times are shown in UTC, newest first."`
- **The `vk_` show-once warning** (`web/src/content/project.ts`), verbatim:
  `"This is the only time this key will ever be shown. It cannot be recovered — if you lose it, revoke it and create a new one."`
- **Korean feedback content** — real records read like `"결제를 못 했습니다"`. **The feedback cards must
  show Korean text**, because that is what the product actually renders and it is what the type choice
  has to survive.
- **Data shapes** (`web/src/lib/vocky/types.ts`): a credential has **no `status` field** — Active ⇔
  `revoked_at === null`; `token_prefix` is a 12-char stub. Feedback strings are **untrusted
  caller-supplied text**: show a hostile-length example somewhere.
- **Copy lives in `web/src/content/*.ts`**, not inline in components.

The locked floors from `handoff.md` §4 still hold — including the security ones (login's deliberately
identical wrong-password / unknown-email error, 404-never-403, attachments never rendering inline, UTC
timestamps) and `word-break: keep-all` with a Korean-capable `--font-sans`.

---

## 3. Definition of done

**The cards appear in the operator's Design System pane.** Not "the files exist" — the pane renders them,
grouped under the five headings, with Foundations compiled from `tokens.css`.

- [ ] One card file per reviewable unit; **no monolith**
- [ ] Line 1 of every card is a valid `@dsCard` marker, exactly as specified
- [ ] `_ds_manifest.json` compiles and the cards are visible in the pane
- [ ] `tokens.css` carries round 01's real values and the cards link it
- [ ] Every card grounded in real repo content — Korean strings included, no lorem
- [ ] The two monoliths are gone
- [ ] `result.md` and `build-prompt.md` are **unchanged** — this pass edits neither

If rendering the cards surfaces a genuine gap in the design, **do not silently invent a fix**: note it and
raise it with the operator. They decide, on the card.
