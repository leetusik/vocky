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
