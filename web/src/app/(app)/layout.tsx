import { AppShell } from "@/components/app-shell";
import { requireIdentity } from "@/lib/auth-guards";

// P4.S2 — the authenticated route group. EVERYTHING under `(app)` is server-gated
// here: `requireIdentity()` unseals the session cookie (redirecting to /login when
// it is absent/invalid/expired) and confirms the token is still live at vocky via
// a bearer-injected `GET /auth/me`, so the body only renders for a real session.
//
// The `(app)` group is invisible in the URL, so this wraps /dashboard (S2
// placeholder → S3), /projects/[projectId] (S4), and /feedback (S5). Reading the
// cookie makes the whole subtree dynamic — never prerendered, never cached across
// users. `requireIdentity` is `cache()`d, so a page that also calls it shares this
// layout's single /auth/me round-trip.
export default async function AppLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const { identity } = await requireIdentity();

  return <AppShell identity={identity}>{children}</AppShell>;
}
