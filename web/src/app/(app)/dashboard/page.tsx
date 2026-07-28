import type { Metadata } from "next";
import Link from "next/link";

import { Badge, Card, DataTable, type DataTableColumn } from "@/components/ui";
import { StatTiles, TrendChart } from "@/components/usage";
import { DASHBOARD } from "@/content";
import { requireIdentity } from "@/lib/auth-guards";
import { getUsage, listOrgCredentials, listProjects } from "@/lib/vocky/app";
import type { VockyCredential, VockyProject } from "@/lib/vocky/types";

import { CreateProjectForm } from "./create-project-form";
import { MintOrgCredentialForm } from "./mint-org-credential-form";
import { RevokeOrgCredentialButton } from "./revoke-org-credential-button";

// P4.S3 — the tenant dashboard: the post-login home and the app's first real data
// page. A server component throughout (only the create-project form and the
// org-key mint/revoke islands are client islands), rendering inside the S2
// `(app)` shell with the S1 primitives.
//
// THREE PARALLEL calls (P10.S4 added the third). `/app/usage` also embeds a
// project list, but it uses a narrower serializer (no `tenant_id`) — so the
// project list renders from `/app/projects`, the canonical shape, and
// `usage.projects` is ignored rather than double-rendered. Neither of those two
// carries org-level credentials, so `listOrgCredentials` is a third leg of the
// same `Promise.all` rather than a second, sequential round-trip.
//
// No tenant round-trip: the shell topbar already renders the tenant from the
// `cache()`d `/auth/me` the layout fetched, so `GET /app/tenant` would buy a
// round-trip and nothing else. (The decomposition sketched it; dropped here.)
export const metadata: Metadata = { title: DASHBOARD.title };

const columns: DataTableColumn<VockyProject>[] = [
  {
    key: "name",
    header: DASHBOARD.projects.columns.name,
    // The route exists as of S4, so the name is the way into the drill-down (the
    // rail deliberately has no Projects entry — a project is reached from here).
    cell: (project) => (
      <Link
        href={`/projects/${project.id}`}
        className="font-medium text-ink hover:text-green-dark hover:underline"
      >
        {project.name}
      </Link>
    ),
  },
  {
    key: "created",
    header: DASHBOARD.projects.columns.created,
    align: "right",
    cell: (project) => (
      <time
        dateTime={project.created_at}
        className="font-mono text-body-sm text-steel tabular-nums"
      >
        {formatCreated(project.created_at)}
      </time>
    ),
  },
];

/** `"2026-07-16T09:31:02+00:00"` → `"Jul 16, 2026"`; unparseable → as-is. */
function formatCreated(iso: string): string {
  const at = new Date(iso);
  if (Number.isNaN(at.getTime())) return iso;
  return at.toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

/**
 * P10.S4 — a SLIMMER column set local to this page, not the per-project
 * `credentialColumns` in `../projects/[projectId]/page.tsx`: the org table has
 * no project binding, its actions cell renders the org-scoped revoke island,
 * and extracting a shared parameterized factory would edit the shipped
 * project page for marginal gain. Every row here is org-level by construction
 * (`listOrgCredentials` only ever returns `project_id: null` rows), so there
 * is no project column.
 */
const orgCredentialColumns: DataTableColumn<VockyCredential>[] = [
  {
    key: "name",
    header: DASHBOARD.orgKeys.columns.name,
    cell: (credential) =>
      credential.name === null ? (
        <span className="text-steel italic">{DASHBOARD.orgKeys.unnamed}</span>
      ) : (
        <span className="font-medium text-ink">{credential.name}</span>
      ),
  },
  {
    key: "key",
    header: DASHBOARD.orgKeys.columns.key,
    // `token_prefix` is `key[:12]` — a display stub, never a usable credential.
    // The plaintext key exists only in the mint response; it is not here to show.
    cell: (credential) => (
      <span className="font-mono text-body-sm text-steel">
        {credential.token_prefix}…
      </span>
    ),
  },
  {
    key: "created",
    header: DASHBOARD.orgKeys.columns.created,
    cell: (credential) => (
      <time
        dateTime={credential.created_at}
        className="font-mono text-body-sm text-steel tabular-nums"
      >
        {formatCreated(credential.created_at)}
      </time>
    ),
  },
  {
    key: "lastUsed",
    header: DASHBOARD.orgKeys.columns.lastUsed,
    cell: (credential) =>
      credential.last_used_at === null ? (
        <span className="text-body-sm text-steel">
          {DASHBOARD.orgKeys.never}
        </span>
      ) : (
        <time
          dateTime={credential.last_used_at}
          className="font-mono text-body-sm text-steel tabular-nums"
        >
          {formatCreated(credential.last_used_at)}
        </time>
      ),
  },
  {
    key: "status",
    header: DASHBOARD.orgKeys.columns.status,
    // vocky has NO `status` field: Active ⇔ `revoked_at === null`. Revoked keys
    // stay listed (revoke is a stamp, not a delete), so the badge is derived.
    cell: (credential) =>
      credential.revoked_at === null ? (
        <Badge variant="active">{DASHBOARD.orgKeys.statusActive}</Badge>
      ) : (
        <Badge variant="revoked">{DASHBOARD.orgKeys.statusRevoked}</Badge>
      ),
  },
  {
    key: "actions",
    header: (
      <span className="sr-only">{DASHBOARD.orgKeys.columns.actions}</span>
    ),
    actions: true,
    // An already-revoked key has nothing to revoke; the badge tells that story.
    cell: (credential) =>
      credential.revoked_at === null ? (
        <RevokeOrgCredentialButton
          credentialId={credential.id}
          credentialLabel={credential.name ?? credential.token_prefix}
        />
      ) : null,
  },
];

export default async function DashboardPage() {
  // Both are needed: `token` for the server-to-server `/app/*` calls, `identity`
  // for nothing here (the shell renders it) — so only `token` is destructured.
  // The `cache()` on `requireIdentity` means this shares the layout's ONE
  // /auth/me round-trip.
  const { token } = await requireIdentity();

  // Error policy mirrors `auth-guards.ts` exactly: a 401 (a mid-request
  // revocation race) is turned into a redirect by `requireIdentity` above; any
  // other failure from these calls propagates to the error boundary rather than
  // being swallowed. An outage should surface, not masquerade as an empty
  // dashboard.
  const [projects, usage, orgCredentials] = await Promise.all([
    listProjects(token),
    getUsage(token),
    listOrgCredentials(token),
  ]);

  return (
    <div className="mx-auto max-w-page">
      <h1 className="text-heading-3 text-ink">{DASHBOARD.lead}</h1>

      <div className="mt-6 space-y-6">
        <StatTiles
          heading={DASHBOARD.usage.heading}
          totals={usage.totals}
          tiles={DASHBOARD.usage.tiles}
          window={usage.window}
          windowPrefix={DASHBOARD.usage.windowPrefix}
          windowUnknown={DASHBOARD.usage.windowUnknown}
        />

        <TrendChart
          heading={DASHBOARD.trend.heading}
          days={usage.daily_counts}
          empty={DASHBOARD.trend.empty}
          partialDayNote={DASHBOARD.trend.partialDayNote}
          ariaLabel={DASHBOARD.trend.ariaLabel}
        />

        <section aria-labelledby="projects">
          <h2 id="projects" className="text-heading-4 text-ink">
            {DASHBOARD.projects.heading}
          </h2>

          <DataTable
            columns={columns}
            rows={projects}
            // Keyed by `id`: names are unique per org as of P10.S1
            // (`UNIQUE(tenant_id, name)`), but keying on `id` predates that
            // constraint and stays correct regardless — `id` is the row's
            // true identity.
            rowKey={(project) => project.id}
            // Overrides DataTable's built-in default, which would bypass
            // copy-as-data.
            empty={DASHBOARD.projects.empty}
            className="mt-4"
          />

          <Card variant="base" className="mt-4">
            <h3 className="text-body-md font-semibold text-ink">
              {DASHBOARD.createProject.heading}
            </h3>
            <div className="mt-3">
              <CreateProjectForm />
            </div>
          </Card>
        </section>

        {/* P10.S4 — the org-keys panel. An org-level key deliberately does not
            appear in any project's drill-down (S3), which is why it needs its
            own section here rather than living inside the projects table. Does
            not collide with StatTiles'/TrendChart's `usage-totals` /
            `usage-trend` DOM ids. */}
        <section aria-labelledby="org-keys">
          <h2 id="org-keys" className="text-heading-4 text-ink">
            {DASHBOARD.orgKeys.heading}
          </h2>
          <p className="mt-1 text-body-sm text-steel">
            {DASHBOARD.orgKeys.lead}
          </p>

          <DataTable
            columns={orgCredentialColumns}
            rows={orgCredentials}
            rowKey={(credential) => credential.id}
            // Overrides DataTable's built-in default, which would bypass
            // copy-as-data.
            empty={DASHBOARD.orgKeys.empty}
            className="mt-4"
          />

          <Card variant="base" className="mt-4">
            <h3 className="text-body-md font-semibold text-ink">
              {DASHBOARD.orgKeys.mint.heading}
            </h3>
            <div className="mt-3">
              <MintOrgCredentialForm />
            </div>
          </Card>
        </section>
      </div>
    </div>
  );
}
