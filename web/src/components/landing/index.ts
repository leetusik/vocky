// Barrel for the public landing sections (P9.S6, build-prompt §7.4). Composed
// from the adopted vocky primitives (Section / Card / Button / Badge / Chip /
// EndpointCard / Grid / Reveal) + the brand Mark / Wordmark — no primitive is
// rebuilt here. Consumed only by `app/page.tsx`, which reclaims `/` as the
// signed-out landing.
export { LandingNav } from "./landing-nav";
export { Hero } from "./hero";
export { TrustStrip } from "./trust-strip";
export { HowItWorks } from "./how-it-works";
// P11.S8 — round 02's agent quickstart, page position 4, anchored `#quickstart`.
export { AgentQuickstart } from "./agent-quickstart";
export { Showcase } from "./showcase";
export { Features } from "./features";
export { Pricing } from "./pricing";
export { ClosingCTA } from "./closing-cta";
export { LandingFooter } from "./landing-footer";
