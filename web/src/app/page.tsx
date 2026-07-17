import { redirect } from "next/navigation";

import { getSession } from "@/lib/session";

// P4.S2 — root redirect. `/` is a pure router for now: a signed-in visitor goes to
// the dashboard, everyone else to login. (P9 replaces this with the public landing
// page, at which point this bounce moves behind the landing's CTA.)
//
// This replaces S1's design-system preview, which was that slice's smoke test and
// has served its purpose — the primitives are now exercised by the real auth and
// shell surfaces.
//
// The check is the CHEAP one (`getSession` — cookie crypto + expiry only, no vocky
// call): a crypto-valid-but-revoked cookie lands on /dashboard, whose guard 401s
// and returns the visitor to /login, which then renders the form rather than
// bouncing back (see `redirectIfAuthenticated`). Reading the cookie makes `/`
// dynamic, so it is never prerendered.
export default async function RootPage(): Promise<never> {
  const token = await getSession();
  redirect(token ? "/dashboard" : "/login");
}
