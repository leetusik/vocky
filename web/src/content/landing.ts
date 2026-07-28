// Copy for the public landing at `/` (P9.S6, build-prompt §7.3). The landing is
// the largest net-new surface of the vocky brand apply: it reclaims `/` from the
// old redirect and speaks to signed-out visitors. Copy-as-data, the S1
// convention — every string lives here so the `components/landing/*` sections
// stay pure presentation.
//
// GROUNDED, NOT LOREM: every claim is a real vocky product fact — the
// server-to-server `POST /api/feedback` capture call, `vk_` ingest keys (shown
// once, hashed, revocable), the 1/2/null rating, cross-project substring search
// over message/comment/target text, MIT-licensed + self-hostable. The hero
// request body mirrors the real capture CONTRACT in `src/vocky/capture.py`
// (`message` incl. Korean, the REQUIRED nested `source.product`,
// `feedback_value: 2` = dislike, `target_type`, `tags`). `lib/vocky/types.ts`
// describes the stored/READ record, where `source_product` is flat — the
// capture REQUEST nests it, and only the request is depicted here.
//
// DOC LINKS RESOLVE TO A REAL TARGET — the GitHub repo, its README, its MIT
// LICENSE — never a fake `/docs` route that would 404 (a locked floor).
//
// P11.S6 adds round 02's three onboarding blocks (`snippet`, `heroInstall`,
// `quickstart`, `skill`). Both floors still hold: every command in them is real
// and shipped (the `curl | bash` installer at `web/public/install.sh`, the
// `vocky capture` CLI, the `vk_` bearer contract), and the only new link targets
// are the in-page anchors `#quickstart` / `#skill` and `/SKILL.md`, which is the
// byte-identical served copy of `skills/vocky-feedback/SKILL.md` in
// `web/public/`. The hosted host name resolves once P12 deploys — the landing
// page and the files it points at ship together, so no live page ever serves a
// dead command.

import { SECTION_IDS } from "./section-ids";

// The real public targets for every "docs" / "GitHub" / "license" reference.
// `github.com/leetusik/vocky` is the actual origin (branch `main`, with a
// root-level MIT `LICENSE` and `README.md`), so each link resolves.
const REPO_URL = "https://github.com/leetusik/vocky";
const DOCS_URL = `${REPO_URL}#readme`;
const LICENSE_URL = `${REPO_URL}/blob/main/LICENSE`;

export const LANDING = {
  // ── Nav ──────────────────────────────────────────────────────────────────
  // In-page anchors derive from SECTION_IDS so they never drift from the
  // `<Section id>` targets. "Docs" is an EXTERNAL link (the repo README), not an
  // in-page anchor — vocky has no `/docs` route to fake.
  nav: {
    links: [
      { label: "Features", href: `#${SECTION_IDS.features}` },
      { label: "How it works", href: `#${SECTION_IDS.how}` },
      { label: "Pricing", href: `#${SECTION_IDS.pricing}` },
      { label: "Docs", href: DOCS_URL, external: true },
    ],
    signIn: { label: "Sign in", href: "/login" },
    startFree: { label: "Start free", href: "/signup" },
  },

  // ── Hero ─────────────────────────────────────────────────────────────────
  hero: {
    eyebrow: "Voice of customer, for builders",
    headline: "Capture the feedback your product is already getting.",
    sub: "vocky is a feedback layer for your product. Your backend sends explicit user reactions — likes, dislikes, comments — over a single REST call, and vocky turns them into structured signal you can search across every project.",
    ctaPrimary: { label: "Start free", href: "/signup" },
    ctaSecondary: { label: "Read the docs", href: DOCS_URL, external: true },
    // The request panel: a real `POST /api/feedback` body, the capture shape a
    // backend actually sends. `feedback_value: 2` = dislike (mirrors the
    // captured card below); `target_type` is a real enum value; the two `tags`
    // are what the trust strip's "search 결제 or checkout" finds.
    request: {
      method: "POST",
      path: "/api/feedback",
      auth: "Authorization: Bearer vk_9f3c…",
      body: `{
  "source": { "product": "checkout-web" },
  "message": "결제 단계에서 카드가 자꾸 거절돼요.",
  "feedback_value": 2,
  "target_type": "message",
  "tags": ["결제", "checkout"]
}`,
    },
    // The captured record, as vocky stores + shows it: the same Korean message,
    // a `disliked` rating badge, and the two tags rendered as chips.
    captured: {
      label: "Captured",
      meta: "checkout-web · just now",
      message: "결제 단계에서 카드가 자꾸 거절돼요.",
      rating: "Disliked",
      tags: ["결제", "checkout"],
    },
  },

  // ── Snippet copy (shared) ────────────────────────────────────────────────
  // The four universal labels of the `Snippet` primitive (P11.S6, round 02
  // build-prompt §7). Every snippet on the page shows the same button copy, so
  // it lives once here; each consumer spreads it and adds its own
  // `announcement` (a polite live region that says "Copied." four times tells a
  // screen-reader user nothing). `copiedLabel` carries the ✓ as a character —
  // round 02 uses no icon component anywhere.
  snippet: {
    copyLabel: "Copy",
    copiedLabel: "✓ Copied",
    copyFailedLabel: "Copy failed",
    selectionHint: "The command is selected for you — press ⌘C (Ctrl+C).",
  },

  // ── Hero install row ─────────────────────────────────────────────────────
  // Appended BELOW the hero's two-column grid (build-prompt §4); nothing inside
  // the grid changes. `command` is byte-locked: it must match
  // `web/public/install.sh`'s header, `docs/cli.md` and `README.md` character
  // for character (a `tests/landing-copy.test.ts` re-spelling guards it). The
  // narrow caption is the < 900px (`app:`) variant, which drops the third
  // clause — both strings are copy, so neither is sliced at render time.
  heroInstall: {
    label: "Install the CLI",
    sub: "Or skip it — the same capture is one REST call.",
    command: "curl -fsSL https://vocky.hi2vi.com/install.sh | bash",
    caption:
      "no sudo · installs uv if it's missing · re-run any time to upgrade",
    captionNarrow: "no sudo · installs uv if it's missing",
    copyAnnouncement: "Copied the install command.",
  },

  // ── Trust strip ──────────────────────────────────────────────────────────
  // Real facts, not fake logos. Verbatim from build-prompt §7.3.
  trust: {
    items: [
      "POST /api/feedback",
      "structured signal, not log noise",
      "search 결제 or checkout",
      "MIT-licensed",
    ],
  },

  // ── How it works (3 steps) ───────────────────────────────────────────────
  how: {
    eyebrow: "How it works",
    heading: "Three steps from a reaction to a searchable signal.",
    steps: [
      {
        n: "1",
        title: "Create a project, mint a key",
        body: "Spin up a project and mint a vk_ ingest key. It's shown once, stored only as a hash, and revocable the moment it leaks.",
      },
      {
        n: "2",
        title: "Your backend sends feedback",
        body: "On every like, dislike, or comment, your server POSTs to /api/feedback. Server-to-server — no browser SDK to ship.",
      },
      {
        n: "3",
        title: "Search & review it",
        body: "Every reaction is searchable across all your projects, in Korean and English, from one dashboard.",
      },
    ],
  },

  // ── Agent quickstart ─────────────────────────────────────────────────────
  // Round 02's surface 2 (build-prompt §5), page position 4, anchored
  // `#quickstart`. GROUNDED: every command here is real and shipped — the
  // installer is `web/public/install.sh` (P11.S3), `vocky capture` is
  // `src/vocky/cli/capture.py` (P11.S2), and the verify call is the
  // zero-side-effect credential probe (a bare `GET /api/feedback` passes the
  // `vk_` auth middleware and only then 400s on the missing filter) — which is
  // why 400 is the SUCCESS reading here and 401 says stop, never retry.
  //
  // `steps` is an OBJECT, not an array: the four steps carry four different
  // content shapes (block vs row snippet, note+trap vs reading list), so they
  // are rendered explicitly rather than mapped. The `<ol>` ordering lives in the
  // component; `n` is the numeral the design paints in the step marker.
  //
  // Rich strings use `{ text, code }`: `text` is the verbatim sentence and every
  // occurrence of each `code` token renders as an inline `<code>` (§5.1 names
  // exactly which tokens those are). Splitting the copy into segments here would
  // hide a transcription slip at a segment boundary; keeping one whole sentence
  // keeps it byte-checkable.
  quickstart: {
    eyebrow: "Get started · for agents",
    heading: "Two variables, and your coding agent can capture.",
    lede: "The whole agent contract is two environment variables — no plugin, no SDK, no config file. Export them once and every coding agent on the machine gets the same access.",
    steps: {
      install: {
        n: "1",
        title: "Install the CLI",
        sub: "One line. It bootstraps uv if you don't have it and needs no sudo.",
        command: "curl -fsSL https://vocky.hi2vi.com/install.sh | bash",
        copyAnnouncement: "Copied the install command.",
      },
      env: {
        n: "2",
        title: "Export the two variables",
        snippetLabel: "~/.zshenv",
        command: `# ~/.zshenv
export VOCKY_BASE_URL="https://vocky.hi2vi.com"
export VOCKY_API_TOKEN="vk_..."`,
        copyAnnouncement: "Copied the environment block.",
        note: {
          text: "Put them in ~/.zshenv, never a repo .env. A repo .env is never auto-loaded by Claude Code or Codex, so a resolver never sees it — and a key in a repo file is one commit away from leaking. ~/.zshenv is sourced by every zsh invocation, so every Bash call, every Codex exec, and every repo you work in inherits it.",
          code: ["~/.zshenv", ".env", "exec"],
        },
        trap: {
          label: "Known trap · Codex only",
          body: {
            text: "The workspace-write sandbox denies outbound network by default, so the capture POST fails silently. Add network_access = true under [sandbox_workspace_write] in ~/.codex/config.toml. Claude Code needs no equivalent change.",
            code: [
              "workspace-write",
              "network_access = true",
              "[sandbox_workspace_write]",
              "~/.codex/config.toml",
            ],
          },
        },
      },
      verify: {
        n: "3",
        title: "Verify before you capture anything",
        sub: "This writes nothing. It only proves the two variables are right.",
        snippetLabel: "verify",
        command: `curl -sS -o /dev/null -w '%{http_code}\\n' \\
  -H "Authorization: Bearer $VOCKY_API_TOKEN" \\
  "$VOCKY_BASE_URL/api/feedback"`,
        copyAnnouncement: "Copied the verify command.",
        // The chip always repeats the literal code — colour is never the sole
        // signal (§3.3). `400` reads green, `401` danger, anything else caution.
        readings: [
          {
            code: "400",
            verdict: "Ready.",
            body: "The token authenticated; the endpoint only rejected a bare GET for a missing filter.",
          },
          {
            code: "401",
            verdict: "Stop.",
            body: "The key is wrong, revoked, or VOCKY_API_TOKEN is unset. Fix the key — don't retry, don't fall back to another path.",
          },
          {
            code: "else",
            verdict: "",
            body: "Connection refused, timeout, DNS failure — VOCKY_BASE_URL is wrong or the service is unreachable.",
          },
        ],
      },
      capture: {
        n: "4",
        title: "Capture",
        command: `vocky capture "결제를 못 했습니다" --product acme-web --value 2`,
        copyAnnouncement: "Copied the capture command.",
        resultBadge: "Captured",
        resultText: "request_id 8f3c1d2e-4a77-4b19-9f0c-2b7d5e6a1c34",
      },
    },
    // The fifth row of the step list: no numeral, a `·` marker. "the skill"
    // links to the section S9 adds — the anchor id exists from P11.S6, so the
    // link compiles and resolves once #skill lands.
    peer: {
      before:
        "No install, or not zsh? The same capture is one POST /api/feedback with the same bearer key — ",
      linkLabel: "the skill",
      after: " spells out the REST path.",
      href: `#${SECTION_IDS.skill}`,
    },
    aside: {
      contractLabel: "The contract",
      contractRows: [
        { name: "VOCKY_BASE_URL", value: "host" },
        { name: "VOCKY_API_TOKEN", value: "vk_…" },
      ],
      contractBody:
        "Both are read by the CLI, the REST path and /mcp alike. A vk_ key has no test tier — mint one with vocky keys mint or take one from the dashboard.",
      worksWithLabel: "Works with",
      worksWith: ["Claude Code", "Codex", "any zsh shell"],
    },
  },

  // ── Agent skill ──────────────────────────────────────────────────────────
  // Round 02's surface 3 (build-prompt §6 + §3.4), page position 5, anchored
  // `#skill` — no nav link by design. The pane reads the SERVED
  // `web/public/SKILL.md` at request time, so `preview.meta` / the footers are
  // TEMPLATES: `{lines}` and `{bytes}` are computed from the file just read and
  // hardcoding either is forbidden (§11.2) — they would drift the moment the
  // skill is edited, and a pasted excerpt would fork silently from the
  // `scripts/skill_parity.py` byte gate even while CI stayed green.
  // `{collapsed}` is `preview.collapsedLines`, the design's 22-line window.
  // Button labels for the two copy affordances here reuse `LANDING.snippet`.
  skill: {
    eyebrow: "Agent skill",
    heading: "Hand your agent the whole procedure.",
    lede: {
      text: "vocky-feedback is a published skill file: the two-variable setup, the verify step, three capture paths and an error table branch by branch — written to be followed verbatim, not interpreted.",
      code: ["vocky-feedback"],
    },
    copyAction: "Copy the skill",
    copyAnnouncement: "Copied the skill file.",
    downloadAction: "Download SKILL.md",
    downloadHref: "/SKILL.md",
    served: "served verbatim at vocky.hi2vi.com/SKILL.md · MIT",
    insideLabel: "What's inside",
    inside: [
      "Set up the two-variable contract",
      "Verify before you capture anything",
      "Path A — capture with the CLI",
      "Path B — raw REST",
      "Path C — /mcp",
      "Error handling — branch by branch",
      "Report back",
    ],
    preview: {
      filename: "SKILL.md",
      meta: "{lines} lines · {bytes} bytes",
      downloadLabel: "Download",
      collapsedLines: 22,
      footerCollapsed: "Showing the first {collapsed} of {lines} lines",
      footerExpanded:
        "Showing all {lines} lines · served verbatim at /SKILL.md",
      // No-JS: the toggle island never renders, so the footer says how to read
      // it instead and offers the raw file as a plain anchor (§8).
      footerNoJs:
        "{lines} lines · scroll to read · served verbatim at /SKILL.md",
      expandLabel: "Show the whole file",
      collapseLabel: "Collapse",
      rawLabel: "Open the raw file",
      rawHref: "/SKILL.md",
    },
  },

  // ── Showcase ("One place to look") ───────────────────────────────────────
  // A browser-framed mock of the real feedback list. Columns match the app's
  // own (When / Project / Feedback / Rating), rows carry rating badges. `frame`
  // is a decorative window label — NOT a link (no fake domain to 404).
  showcase: {
    eyebrow: "One place to look",
    heading: "Every reaction, across every project.",
    frame: "vocky · Feedback",
    columns: {
      when: "When",
      project: "Project",
      message: "Feedback",
      rating: "Rating",
    },
    rows: [
      {
        when: "2m ago",
        project: "checkout-web",
        message: "결제 단계에서 카드가 자꾸 거절돼요.",
        rating: "disliked",
        ratingLabel: "Disliked",
      },
      {
        when: "14m ago",
        project: "docs-site",
        message: "Search finally finds my Korean tags.",
        rating: "liked",
        ratingLabel: "Liked",
      },
      {
        when: "1h ago",
        project: "mobile-api",
        message: "Checkout feels much faster now.",
        rating: "liked",
        ratingLabel: "Liked",
      },
      {
        when: "3h ago",
        project: "checkout-web",
        message: "배송 조회가 안 돼요.",
        rating: "disliked",
        ratingLabel: "Disliked",
      },
      {
        when: "5h ago",
        project: "dashboard",
        message: "An export to CSV would help a lot.",
        rating: "unrated",
        ratingLabel: "Unrated",
      },
    ],
  },

  // ── Features (6) ─────────────────────────────────────────────────────────
  features: {
    eyebrow: "Why vocky",
    heading: "A feedback layer, not another analytics tool.",
    items: [
      {
        title: "Server-to-server capture",
        body: "Your backend POSTs to /api/feedback on every like, dislike, or comment. One authenticated REST call — no browser SDK, no client bundle.",
      },
      {
        title: "Structured, not log noise",
        body: "Every reaction lands as a typed record — message, rating, tags, source — ready to search and review, never buried in a log stream.",
      },
      {
        title: "Search in any language",
        body: "Case-insensitive substring search across message, comment, and target text. The same query finds 결제 or checkout.",
      },
      {
        title: "Per-project API keys",
        body: "Mint a vk_ ingest key per project. It's shown once, stored only as a hash, and revocable the instant it leaks.",
      },
      {
        title: "Like, dislike, listen",
        body: "Capture the reactions users deliberately give — likes, dislikes, comments. Explicit signal only; no implicit tracking or behavioral guesswork.",
      },
      {
        title: "Free & self-hostable",
        body: "MIT-licensed and free while we build. Run vocky on your own infrastructure, or use the hosted version — your data, your call.",
      },
    ],
  },

  // ── Pricing (Free now + paid later) ──────────────────────────────────────
  // The "coming later" card is COPY ONLY — its control is disabled, there is no
  // waitlist endpoint this round (build-prompt §9).
  pricing: {
    heading: "Free while we're building. Paid plans later.",
    sub: "Everything vocky does today is free. Paid tiers arrive when the extras below do.",
    free: {
      name: "Free",
      badge: "Available now",
      price: "$0",
      priceNote: "/ forever, for now",
      inclusions: [
        "Unlimited projects & keys",
        "Unlimited capture",
        "Cross-project search",
        "Comments & attachments",
        "Self-host or hosted",
      ],
      cta: { label: "Start free", href: "/signup" },
    },
    pro: {
      name: "Pro & Teams — coming later",
      price: "—",
      items: [
        "Team seats & roles",
        "Longer retention",
        "Saved views & exports",
        "Priority support",
      ],
      disabledLabel: "Not yet — vocky is free today",
    },
  },

  // ── Closing CTA ──────────────────────────────────────────────────────────
  closing: {
    heading: "Start hearing what your users actually think.",
    sub: "Create a project, mint a key, and capture your first reaction in minutes. Free while we build.",
    ctaPrimary: { label: "Start free", href: "/signup" },
    ctaSecondary: { label: "Read the docs", href: DOCS_URL, external: true },
  },

  // ── Footer ───────────────────────────────────────────────────────────────
  footer: {
    tagline: "The feedback layer for your product.",
    columns: [
      {
        heading: "Product",
        links: [
          { label: "Features", href: `#${SECTION_IDS.features}` },
          { label: "How it works", href: `#${SECTION_IDS.how}` },
          { label: "Pricing", href: `#${SECTION_IDS.pricing}` },
        ],
      },
      {
        heading: "Project",
        links: [
          { label: "Documentation", href: DOCS_URL, external: true },
          { label: "GitHub", href: REPO_URL, external: true },
          { label: "MIT license", href: LICENSE_URL, external: true },
        ],
      },
      {
        heading: "Account",
        links: [
          { label: "Sign in", href: "/login" },
          { label: "Start free", href: "/signup" },
        ],
      },
    ],
    legal: "© 2026 vocky · pre-MVP",
  },
} as const;
