import { redirect } from "next/navigation";

import {
  AgentQuickstart,
  ClosingCTA,
  Features,
  Hero,
  HowItWorks,
  LandingFooter,
  LandingNav,
  Pricing,
  Showcase,
  TrustStrip,
} from "@/components/landing";
import { getSession } from "@/lib/session";

// P9.S6 — the public landing (build-prompt §7). `/` was a pure redirect; it is now
// the signed-out marketing surface that reclaims the route. It sits OUTSIDE the
// `(app)` route group, so it renders its own nav + footer, not the app shell.
//
// The signed-in bounce is PRESERVED (the operator's "signed-in → dashboard"
// ruling): a live session at `/` still redirects to the dashboard, and only
// signed-out visitors see the landing. The check is the CHEAP one
// (`getSession` — cookie crypto + expiry only, no vocky round-trip); reading the
// cookie makes `/` dynamic, so it is never prerendered.
//
// Server component throughout; the only client island is the `<Reveal>` inside
// the `<Section reveal>` bands (progressive-enhancement, reduced-motion-safe).
//
// P11.S8 inserts `AgentQuickstart` at position 4, between `HowItWorks` and
// `Showcase` (round 02 build-prompt §2). `SkillSection` lands at position 5,
// P11.S9's job — not added here.
export default async function LandingPage() {
  const token = await getSession();
  if (token) redirect("/dashboard");

  return (
    <>
      <LandingNav />
      <main id="main-content">
        <Hero />
        <TrustStrip />
        <HowItWorks />
        <AgentQuickstart />
        <Showcase />
        <Features />
        <Pricing />
        <ClosingCTA />
      </main>
      <LandingFooter />
    </>
  );
}
