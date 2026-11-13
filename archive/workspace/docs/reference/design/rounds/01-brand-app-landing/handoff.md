# Design handoff — Round 01: brand, app UI & landing

**To:** Claude Design, with the operator (sugang)
**From:** Claude Code (vocky repo)
**Round:** 01 · **Phase:** P8 · **Slice:** P8.S2
**Repo:** `github.com/leetusik/vocky` (public) — connect via **Connect GitHub**, branch `main`

---

## 0. What this is, and who decides

This document says **what to design**. It decides **nothing**.

Every visual decision in this round — the palette, the type, the brand spirit, the landing's value prop
and its copy — is yours to make with the operator. Claude Code has deliberately proposed no palette, no
type direction, and no copy, and has answered none of the questions in §6. **They are posed, not
answered.** Where this document describes something, it is describing **what exists in the repo today**,
not recommending it.

**vocky is simultaneously a redesign and a first-time.**

- **Redesign:** six app surfaces are already built and shipped. You can read all of them in the repo.
- **First-time:** **no vocky brand exists.** The current palette is an explicit placeholder — the token
  *names* were ported 1:1 from another product (`hi2vi_web`) so that a later gate could swap *values*
  without touching call sites. `web/src/app/globals.css` says so in its own header:

  > PLACEHOLDER PALETTE. The token NAMES are ported 1:1 from hi2vi_web […] but the VALUES are a neutral
  > placeholder set — a slate/zinc surface ramp, one indigo accent, and standard red/amber signal states
  > — NOT a finished brand.

  That is why `--color-green` is currently **indigo** `#6366f1`. The name is inherited; the value is a
  placeholder. **This round is where vocky gets a real brand.**

---

## 1. Product context

**What vocky is** (`docs/current/product.md`):

> Vocky is a feedback layer for products and the surfaces around them. It captures human-triggered user
> feedback from websites and product experiences, structures it into usable signals, and helps teams
> understand what customers are asking for, praising, or struggling with. It is delivered as a free
> multi-tenant SaaS: a user signs up, gets a tenant (workspace) with projects, and mints per-project
> credentials that their product backend uses for server-to-server capture. **There are no paid plans or
> billing — the service is free.**

**The problem it solves:** "Product surfaces and customer interactions contain feedback that usually gets
buried in logs. Teams need structured feedback, not raw log or support noise."

**Who uses it:** teams building web/product experiences; developers integrating feedback capture into
product backends; product and ops teams reviewing customer voice.

**The domain chain:** user (email+password) → auto-provisioned **tenant** (workspace) → **projects** →
**project credentials** (`vk_`-prefixed keys, shown once, revocable) → **feedback** (project-scoped).

**Two facts that shape every app surface:**

1. **The web app is a signed-in tenant owner's surface, not an end-user one** (`experience.md`). The
   people leaving feedback never see it.
2. **The web app is read + search only.** From `experience.md`: *"There is no editing, commenting, or
   deleting here […] The web app is where a human finds feedback across projects."* Feedback
   *management* happens over the API, in the customer's own admin panel.

**Status:** pre-MVP, mid-pivot. Runs locally; not yet deployed. Contracts are early-stage.

**Product positioning notes** (facts, not direction): free is load-bearing and repeated — *"Paid plans,
billing, usage metering, or plan tiers"* is an explicit **Non-Goal**. Usage is *"operational visibility
only — no billing or metering."* The product is deliberately narrow: *"focus on explicit user actions,
such as like/dislike clicks and optional comments, rather than trying to infer feedback from every
interaction."*

**There is no tone, voice, or brand guidance anywhere in the repo.** We looked. That is a gap for this
session to fill with the operator, not for us to fill.

---

## 2. Scope checklist

Everything below is in scope for this one round.

### Foundations
- [ ] Color — the full palette (see §7 for what exists and the measured gap)
- [ ] Typography — faces and scale
- [ ] Spacing, radius, containers, breakpoints
- [ ] Motion (if any) — the repo has a reduced-motion-safe `Reveal` primitive, currently unused

### Components (`web/src/components/ui/`)
- [ ] `button` · `card` · `badge` · `field` (Label/Input/Textarea/Checkbox/FieldError) · `grid` ·
      `section` · `data-table` · `endpoint-card` · `reveal`

### App surfaces — all six are shipped and readable in the repo
- [ ] Login / signup
- [ ] App shell (topbar + left rail)
- [ ] Dashboard (usage tiles + trend chart + projects table + create-project form)
- [ ] Project detail (usage + API keys: mint / show-once / revoke)
- [ ] Feedback list (search + filters + table + pagination)
- [ ] Feedback detail (fields + tags + operator comments + attachments + raw data)

### Landing — **does not exist in code at all**
`web/src/app/page.tsx` is a pure redirect today. The landing must reclaim `/`.
- [ ] Hero
- [ ] Features
- [ ] Pricing — **see the open question in §6.1; do not assume this section's content**
- [ ] Footer

### States that **do not exist** — net-new design, asked for, not described
There are zero `loading.tsx` / `error.tsx` / `not-found.tsx` / `global-error.tsx` files and zero
`<Suspense>` boundaries in the app. Today: loading is a blank blocked render, errors fall through to
Next.js's default overlay, and `notFound()` (3 call sites) renders Next's default 404.
- [ ] Loading states
- [ ] Error states
- [ ] 404 / not-found

Empty and populated states **are** designed and shipped — read them. These three are the hole.

---

## 3. Where to look — real paths, real data

**Ground everything in this. Never lorem — every string below is real and shipped.**

### Routes → files (`web/src/app/`)

| Surface | Path |
|---|---|
| `/` (redirect only today) | `page.tsx` |
| `/login` | `(auth)/login/page.tsx`, `(auth)/login/login-form.tsx` |
| `/signup` | `(auth)/signup/page.tsx`, `(auth)/signup/signup-form.tsx` |
| auth chrome | `(auth)/layout.tsx`, `(auth)/auth-card.tsx`, `(auth)/credentials-form.tsx` |
| app shell | `(app)/layout.tsx` |
| `/dashboard` | `(app)/dashboard/page.tsx`, `create-project-form.tsx` |
| `/projects/[projectId]` | `(app)/projects/[projectId]/page.tsx`, `mint-credential-form.tsx`, `revoke-credential-button.tsx` |
| `/feedback` | `(app)/feedback/page.tsx`, `feedback-fields.tsx` |
| `/feedback/[feedbackId]` | `(app)/feedback/[feedbackId]/page.tsx` |

### Copy is data — `web/src/content/`

All shipped copy lives here, not inline in components. **This is your source for real strings.**

- `site.ts` — `name: "vocky"`, `titleTemplate: "%s · vocky"`,
  `description: "vocky — the tenant dashboard for your projects, credentials, and feedback."`
- `auth.ts` — `LOGIN_PAGE`, `SIGNUP_PAGE`, `AUTH_ERRORS`. Real: `"Access your workspace, projects, and
  feedback."`, `"An account with this email already exists. Sign in instead."`
- `app.ts` — shell chrome: rail = `Dashboard`, `Feedback`; `workspaceLabel: "Workspace"`,
  `logoutLabel: "Sign out"`, `soonTag: "Soon"`
- `dashboard.ts` — tiles Total/Liked/Disliked/Unrated, `windowPrefix: "Last 30 days ·"`, trend note
  `"First and last days are partial."`, `namePlaceholder: "e.g. Support widget"`
- `project.ts` — `"API keys"`, `lead: "Use a key's value as the API credential your service sends to
  vocky."`, and the show-once warning: `"This is the only time this key will ever be shown. It cannot be
  recovered — if you lose it, revoke it and create a new one."`
- `feedback.ts` — the largest. `searchPlaceholder: "e.g. 결제 or checkout"`, `searchHint: "Matches any
  part of the feedback text, comment, or context — Korean and English alike."`, columns
  When/Project/Feedback/Rating/Source, `timeNote: "Times are shown in UTC, newest first."`,
  `downloadNote: "Attachments download rather than open in the browser."`
- `nav.ts` / `section-ids.ts` — **vestigial**: leftovers from a deleted P4.S1 preview page (`Overview`,
  `Primitives`). Not live surfaces.

### Data shapes — `web/src/lib/vocky/types.ts`

Mirrors the Python serializers. Key types: `VockyProject`, `VockyCredential` (note: **no `status`
field** — Active ⇔ `revoked_at === null`; `token_prefix` is a 12-char display stub), `VockyFeedback` /
`VockyFeedbackDetail` (message, feedback_value `1|2|null`, comment, channel, tags[], messages[],
attachments, …), `VockyUsage` / `VockyProjectUsage` (window, totals, daily_counts).

**All feedback strings are untrusted caller-supplied text** — design for hostile length and content.

### Tokens and fonts
- `web/src/app/globals.css` — the `@theme` block (the placeholder palette), a shadcn `:root` alias layer,
  and the base layer
- `web/src/lib/fonts.ts` — `next/font/google`: Noto Sans KR + JetBrains Mono, build-time self-hosted

### Components
`web/src/components/ui/` (the design system) · `web/src/components/usage/` (`stat-tiles`, `trend-chart`)
· `web/src/components/app-shell/` (`app-shell`, `rail-nav`, `logout-button`). The latter two are **app
components, not the design system**.

---

## 4. Locked vs. in play

This is how the session is shaped without anything being decided for you.

### In play — move these freely
- **Brand spirit** — vocky has none. This round invents it.
- **Palette, type, fonts, spacing, radius, motion, layout, density, expression**
- **Component vocabulary** — this is a bootstrapping pass; adding, splitting, or retiring primitives is
  on the table (see §6.3–6.5)
- **Landing copy — in play this pass only.** The exception, not the rule: the landing has no copy at all
  and none may be invented by Claude Code, so its value prop and messaging are concluded here with the
  operator.

### Locked
- **App copy** in `web/src/content/` — the shipped app's strings stay. (The landing's do not exist yet;
  see above.)
- **System structure** — routes, the BFF boundary, the tenancy model.
- **Data contracts** — locked *by default*, but **reopenable if the design requires it. Name the cost;
  do not assume it.** The operator has explicitly put backend in scope if the design needs it, and has
  said: *"not just re-skinning. there maybe feature change while re-design process."*

### Locked floors — non-negotiable, and several are security

These are behaviours a design pass could plausibly "improve" into a bug or a vulnerability. Do not.

- **Login must give the identical error for a wrong password and an unknown email.** A more "helpful"
  message is an account-enumeration vulnerability.
- **404-never-403** on anything outside your tenant — revealing existence is the leak.
- **The show-once key crossing** — the plaintext `vk_…` key is shown exactly once, with the explicit
  warning that it can never be recovered. Revoked keys stay listed as Revoked, for auditability.
- **Attachments download; they never render inline.** Deliberate, security-driven.
- **Times are shown in UTC and labeled as such.**
- **`h1–h6 { word-break: keep-all }`** — Korean line-breaking. Must survive any type change.
- **`--font-sans` must stay Korean-capable** — feedback content is Korean (`"결제를 못 했습니다"`).
- **The a11y floor**, including `FieldError` rendering an empty `<p class="min-h-[1.25rem]">` when there
  is no error: deliberate, so it reserves space and stays in the tree for `aria-live`.
- **Distinct empty states** — "no projects yet" and "no feedback matches these filters" are different
  messages and must stay different.

---

## 5. Operator attachments — asked, not answered

**vocky has no logo and no wordmark.** The app-shell brand is literally text styled with
`text-[18px] tracking-[-0.3px]`. There is no mark, no icon, no brand asset of any kind in the repo.

**Question for the operator:** is there a logo/wordmark to upload, or should this round design the brand
mark? If assets exist, upload them now. If not, that is itself a design decision for this session.

---

## 6. Open questions — posed, never answered

Claude Code has not answered any of these and will not. **Ask the operator.**

### 6.1 The landing — and a contradiction we will not resolve for you
- What is vocky's **value prop**? What does the hero say? There is no copy and no positioning doc.
- **The pricing section vs. "vocky is free."** The scope list asks for a pricing section, but the product
  docs say *"There are no paid plans or billing"* and name paid plans an explicit **Non-Goal**. That
  scope item most likely rode in from hi2vi's landing structure (vocky inherited unused
  `pricing`/`pricingFeatured` `Card` variants from it). **So: does the landing have a pricing section at
  all? If yes, what does it say for a product with no prices — a "free forever" statement, something
  else?** We are not deciding this.
- Does a **signed-in visitor at `/`** see the landing, or get bounced to the dashboard? (Today `/` is a
  pure redirect; its own comment anticipates *"this bounce moves behind the landing's CTA"* — but that is
  a P4-era assumption, not a decision.)

### 6.2 Brand and foundations
- **Palette** — and **how far to carry the hi2vi vibe** (see §7). The operator's instruction was *"make a
  design system only for vocky but inherit hi2vi vibe."* How literally?
- **Type direction** — faces and scale.
- **The `on-primary` flip** — a dependency, not an independent choice: a bright accent flips text on the
  primary dark; a saturated mid-tone keeps it white. hi2vi's bright green `#2ff28f` takes
  `--color-on-primary: #061512` (dark text); vocky's indigo placeholder takes `#ffffff`.
- **Dark mode** — `experience.md` currently states *"There is no dark-mode toggle"*, and `globals.css`
  has no `.dark` block, on purpose. Keep it that way, or not?
- **Token renames vs. value swaps.** Names were kept hi2vi-identical *precisely so the gate swaps values
  only*. `--color-green` holding an indigo is the visible cost of that choice. Renaming is possible but
  not free — it is call-site churn. A decision, not a default.

### 6.3 The hand-rolled primitives — the real component questions
The shipped UI works around gaps in its own design system:
- **No `Select`** — the feedback filter bar uses a native `<select>` borrowing `inputVariants()` through
  a template literal, bypassing `cn()`. Add a real `Select`?
- **No destructive `Button` variant** — revoke uses `secondary`. P4 refused to invent a token with no
  hi2vi source. Add one?
- **No `Chip`/`Tag`** — feedback-detail tags are a bespoke `rounded-full` span, not `Badge`. Add one?
- **`LogoutButton` is a bespoke chip**, not the `Button` primitive. Fold it in?

### 6.4 Inherited-but-unused — adopt or drop?
Not equal billing: **several are exactly what a landing needs.** Dead in shipped code: `Section`,
`Reveal`, `EndpointCard`, `Checkbox`, `Textarea`. Unused: `Card` variants `dark`/`archive`/`security`/
`pricing`/`pricingFeatured`; `Badge` variants `signal` (the *default*)/`security`/`dark`; `Button`
`secondaryOnDark` + size `lg`; `Grid cols={2|3}`; the `--spacing-section*`/`--spacing-hero` group;
`--container-wide`; `--breakpoint-xs`; and 6 of 14 type steps (`hero-display`, `display-lg`, `heading-1`,
`heading-2`, `body-lg`, `code-md`).

### 6.5 Semantics and specifics
- **`Badge variant="archive"` currently means two opposite things** — *Revoked* (a dead key) and
  *Disliked* (negative feedback). Split it?
- **`TrendChart` is ~140 lines of dependency-free inline SVG.** Keep it, or adopt a chart library? (A
  prior decision explicitly deferred this to "the design gate" — this one.)
- **`--font-en` has no vendored face.** It has exactly one call site — `button.tsx:18`, the
  `buttonVariants` base — so **every button renders in the visitor's system font** while its
  surroundings are Noto Sans KR. Vendor a face, or drop the token?
- **`--breakpoint-xs` has zero consumers.** Declared at `globals.css:176`; no `xs:` variant appears
  anywhere in `web/src/`. Meanwhile there are **11 hardcoded `min-[900px]:`** utilities. vocky's one
  declared breakpoint is unused and its one real breakpoint is untokenized. Adopt `xs`, drop it, or
  tokenize 900px?
- **`/projects/[id]` marks no rail item current** (projects aren't a rail item). Flagged in review as
  worth a deliberate call once the rail grows.
- **8 palette collision groups** — distinct token names holding identical values, so they render as
  duplicates wherever the palette is shown: `ink`==`canvas-dark` · `forest`==`charcoal` ·
  `forest-mid`==`slate`==`hairline-dark` · `surface-soft`==`hairline-soft`==`archive-cream`==
  `surface-band` · `trust-sage`==`hairline-strong`==`on-dark-muted` · `archive-olive`==`muted` ·
  `surface-green`==`surface-security`. An artifact of the placeholder set — worth knowing when you
  assign real values.

---

## 7. REFERENCE — hi2vi vibe

> **This section is DATA, NOT A PROPOSAL.** The operator asked to *"inherit hi2vi vibe"*. hi2vi_web is a
> different product with its own brand. It is reproduced here **only** so you can ask the operator how far
> to carry it. **Nothing here is a recommendation for vocky.** Reference lives at
> `/Users/sugang/projects/personal/hi2vi_web` (not in this repo).

### The measured gap — this is smaller than it looks

Extracted mechanically from both `tokens.css` files, with an assertion that all 41 tokens are covered:

- **`--color-*`: 41/41 names shared, 2/41 values identical** — and those two agree only by triviality
  (`canvas` and `on-dark` are both `#ffffff`).
- **`--text-*` (48 incl. bundled), `--radius*` (8), `--spacing-*` (4), `--container-*` (2),
  `--breakpoint-xs` (1): names 100% shared, zero differing values — byte-identical.**
- **So there is no structural gap. The gap is chromatic and typographic: 39 color values + 2 typefaces.**
- `--font-mono` is **already the same face** (JetBrains Mono) — only the internal root var name differs.
  The real type gap is 2 tokens: `--font-sans` (Noto Sans KR vs Pretendard — both Korean-capable) and
  `--font-en` (bare system stack vs Inter).

### hi2vi's palette (reference only)

```css
/* Dark green surfaces */
--color-ink: #061512;          --color-forest: #0b2a22;
--color-forest-mid: #123b31;   --color-forest-soft: #1b4a3d;
/* Signal greens */
--color-green: #2ff28f;        /* primary CTA / signature signal */
--color-green-deep: #00b66a;   --color-green-dark: #007a4d;
--color-green-soft: #ddfbea;
/* Security accents */
--color-security-mint: #9af7c7; --color-security-teal: #1fcb91;
--color-trust-sage: #c8e6d2;
/* Warm history accents */
--color-victory-lime: #b7e65b;  --color-archive-olive: #a8c85a;
--color-archive-cream: #f3f0d8;
/* Signal states */
--color-danger: #d4503c;        --color-danger-deep: #a83c29;
--color-surface-danger: #fdeeea; --color-hairline-danger: #f1d3cc;
--color-caution: #bd7b1c;       --color-caution-deep: #8a5810;
--color-surface-caution: #fbf2df; --color-hairline-caution: #ebddbf;
/* Surfaces */
--color-canvas: #ffffff;        --color-canvas-dark: #061512;
--color-surface: #f7faf7;       --color-surface-soft: #f1f6f2;
--color-surface-green: #effbf4; --color-surface-archive: #fbfaf0;
--color-surface-security: #f0faf5; --color-surface-band: #eef6f1;
/* Hairlines */
--color-hairline: #dce6df;      --color-hairline-soft: #ebf1ed;
--color-hairline-strong: #b8c8bf; --color-hairline-dark: #24463b;
/* Text */
--color-charcoal: #18231f;      --color-slate: #41524a;
--color-steel: #687a72;         --color-muted: #93a39b;
--color-on-dark: #ffffff;       --color-on-dark-muted: #afc5ba;
--color-on-primary: #061512;    /* dark text on the bright green CTA */
```

hi2vi type: `--font-sans: Pretendard`, `--font-en: Inter`, `--font-mono: JetBrains Mono` (vendored woff2).

### vocky's current values (the placeholder — what you are replacing)

```css
/* Dark neutral surfaces */
--color-ink: #0f172a;          --color-forest: #1e293b;
--color-forest-mid: #334155;   --color-forest-soft: #475569;
/* Accent — one indigo */
--color-green: #6366f1;        --color-green-deep: #4f46e5;
--color-green-dark: #4338ca;   --color-green-soft: #e0e7ff;
/* Secondary accent tints */
--color-security-mint: #c7d2fe; --color-security-teal: #818cf8;
--color-trust-sage: #cbd5e1;
/* Muted decorative accents */
--color-victory-lime: #a5b4fc;  --color-archive-olive: #94a3b8;
--color-archive-cream: #f1f5f9;
/* Signal states */
--color-danger: #dc2626;        --color-danger-deep: #b91c1c;
--color-surface-danger: #fef2f2; --color-hairline-danger: #fecaca;
--color-caution: #d97706;       --color-caution-deep: #b45309;
--color-surface-caution: #fffbeb; --color-hairline-caution: #fde68a;
/* Surfaces */
--color-canvas: #ffffff;        --color-canvas-dark: #0f172a;
--color-surface: #f8fafc;       --color-surface-soft: #f1f5f9;
--color-surface-green: #eef2ff; --color-surface-archive: #f9fafb;
--color-surface-security: #eef2ff; --color-surface-band: #f1f5f9;
/* Hairlines */
--color-hairline: #e2e8f0;      --color-hairline-soft: #f1f5f9;
--color-hairline-strong: #cbd5e1; --color-hairline-dark: #334155;
/* Text */
--color-charcoal: #1e293b;      --color-slate: #334155;
--color-steel: #64748b;         --color-muted: #94a3b8;
--color-on-dark: #ffffff;       --color-on-dark-muted: #cbd5e1;
--color-on-primary: #ffffff;    /* white text on the indigo placeholder */
```

vocky type: `--font-sans: Noto Sans KR`, `--font-en: <bare system stack>`, `--font-mono: JetBrains Mono`,
via `next/font/google` (build-time self-hosted, CSP-safe, no vendored binaries).

### One mechanical property worth knowing

Verified in the compiled bundle, not inferred: **Tailwind utilities compile to `var(--color-*)`
references, not baked hex** — `.bg-green { background-color: var(--color-green); }`. **So changing a token
value rethemes every component at once.** That is the property this whole gate rests on: the instant the
palette is swapped, every surface re-themes.

---

## 8. Required outputs — strict

**A round is incomplete without both files.** Write them into this design-system project at these exact
paths:

### `output/result.md`
What was designed, decision by decision. Foundations (every token value), type, components, each app
surface, each landing section, and the loading/error/404 states. **Every departure from this handoff must
be logged** — if you changed scope, dropped something, or resolved a locked item, say so explicitly and
say why.

Answer every question in §6, or record explicitly that a question was deliberately left open.

### `output/build-prompt.md`
**The implementation contract.** This is what the implementation phase (P9) decomposes and sizes its work
from — without it, P9 is guessing.

It must be concrete enough that an engineer can build from it **without inventing a single design
decision**: exact token values, exact type steps, component APIs and variants, per-surface layout and
behaviour, states, and what changes in which file. Where the design implies backend or data work that
does not exist, **say so** — do not quietly drop it.

---

## 9. Definition of done

- [ ] Every §2 checklist item is designed, or explicitly deferred with a reason.
- [ ] Every §6 question is answered by the operator, or explicitly left open on the record.
- [ ] `output/result.md` written, every departure logged.
- [ ] `output/build-prompt.md` written, concrete enough to build from with **no design decisions left to
      invent**. This is the bar the read-back checks against.
- [ ] Locked floors in §4 respected — especially the security ones.
- [ ] Everything grounded in the repo's real content and real data shapes. No lorem.

---

## 10. Notes on process

- **The repo is the truth.** Claude Design reads it directly via Connect GitHub. There is no canvas
  mirror, no cards, and no token mirror to keep in sync — a previous mirror was deleted precisely because
  it could only drift.
- **Claude Code will not edit what you return.** The record is landed as-is and read-only. Nits become
  implementation-time to-dos.
- **Implementation is a separate phase (P9)**, and per the operator it is *"not just re-skinning. there
  maybe feature change while re-design process."* Design for what is right, not for what is cheap to
  build — but name the cost when it is large.
