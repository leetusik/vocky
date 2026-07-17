import { redirect } from "next/navigation";

import {
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
        <Showcase />
        <Features />
        <Pricing />
        <ClosingCTA />
      </main>
      <LandingFooter />
    </>
  );
}
