import type { Metadata } from "next";
import Link from "next/link";

import { Card, DataTable, type DataTableColumn } from "@/components/ui";
import { StatTiles, TrendChart } from "@/components/usage";
import { DASHBOARD } from "@/content";
import { requireIdentity } from "@/lib/auth-guards";
import { getUsage, listProjects } from "@/lib/vocky/app";
import type { VockyProject } from "@/lib/vocky/types";

import { CreateProjectForm } from "./create-project-form";

// P4.S3 — the tenant dashboard: the post-login home and the app's first real data
// page. A server component throughout (only the create-project form is a client
// island), rendering inside the S2 `(app)` shell with the S1 primitives.
//
// Two PARALLEL calls, not one. `/app/usage` also embeds a project list, but it
// uses a narrower serializer (no `tenant_id`) — so the list renders from
// `/app/projects`, the canonical shape, and `usage.projects` is ignored rather
// than double-rendered. `Promise.all` makes the second call free in wall-clock
// terms, and keeps each endpoint's meaning intact.
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
  const [projects, usage] = await Promise.all([
    listProjects(token),
    getUsage(token),
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
            // Keyed by `id`, never `name`: vocky enforces no uniqueness, so two
            // projects in one tenant may legitimately share a name.
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
      </div>
    </div>
  );
}
