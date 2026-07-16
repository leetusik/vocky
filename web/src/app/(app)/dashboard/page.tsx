import type { Metadata } from "next";

import { Card } from "@/components/ui";
import { APP_SHELL, DASHBOARD_PLACEHOLDER } from "@/content";
import { requireIdentity } from "@/lib/auth-guards";

// P4.S2 — /dashboard PLACEHOLDER. Its only job is to prove the auth round-trip
// end-to-end: sealed httpOnly cookie → server guard → token unsealed → vocky
// `GET /auth/me` called server-to-server with the bearer → the real identity
// rendered. It makes its own guarded call rather than trusting the layout, so the
// page itself demonstrates the seam S3–S5 build on (the `cache()` on
// `requireIdentity` means this still costs ONE /auth/me per request).
//
// S3 replaces this with the real tenant dashboard (projects + create + usage).
export const metadata: Metadata = { title: DASHBOARD_PLACEHOLDER.title };

export default async function DashboardPage() {
  const { identity } = await requireIdentity();
  const tenantName = identity.tenant?.name ?? APP_SHELL.noTenant;

  return (
    <div className="mx-auto max-w-page">
      <h1 className="text-heading-3 text-ink">{DASHBOARD_PLACEHOLDER.lead}</h1>

      <Card variant="base" className="mt-6">
        <p className="text-body-md text-ink">
          {DASHBOARD_PLACEHOLDER.signedInPrefix}{" "}
          <b className="font-semibold">{identity.user.email}</b>
          {" · "}
          <b className="font-semibold">{tenantName}</b>
        </p>
        <p className="mt-4 text-body-sm text-steel">
          {DASHBOARD_PLACEHOLDER.note}
        </p>
        <p className="mt-2 text-body-sm text-steel">
          {DASHBOARD_PLACEHOLDER.nextUp}
        </p>
      </Card>
    </div>
  );
}
