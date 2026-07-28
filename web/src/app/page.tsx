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
  SkillSection,
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
// P11.S8/S9 insert round 02's two new sections between `HowItWorks` and
// `Showcase` (build-prompt §2): `AgentQuickstart` at position 4 and
// `SkillSection` at position 5. `SkillSection` renders `SkillPreview`, which
// reads `public/SKILL.md` at REQUEST time — safe precisely because this route is
// already dynamic (the cookie read above), so `/` stays `ƒ`, never prerendered.
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
        <SkillSection />
        <Showcase />
        <Features />
        <Pricing />
        <ClosingCTA />
      </main>
      <LandingFooter />
    </>
  );
}
