import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { Badge, Card, DataTable, type DataTableColumn } from "@/components/ui";
import { StatTiles, TrendChart } from "@/components/usage";
import { PROJECT } from "@/content";
import { requireIdentity } from "@/lib/auth-guards";
import { getProject, getProjectUsage } from "@/lib/vocky/app";
import { ApiError } from "@/lib/vocky/client";
import type {
  VockyCredential,
  VockyProject,
  VockyProjectUsage,
} from "@/lib/vocky/types";

import { MintCredentialForm } from "./mint-credential-form";
import { RevokeCredentialButton } from "./revoke-credential-button";

// P4.S4 — the per-project drill-down, reached from the dashboard's project list.
// A server component throughout; only the mint form and the per-row revoke button
// are client islands.
//
// TWO PARALLEL calls, and the credentials come from the USAGE payload — which
// looks like it contradicts S3's "ignore `usage.projects`" rule, but does not.
// There, the usage copy of a project used a NARROWER serializer (no `tenant_id`),
// so rendering it would have been lossy. Here, `_project_usage_response` bundles
// `credentials` through the IDENTICAL `serialize_credential` as the standalone
// list route, and bundles them BY DESIGN for exactly this page (the endpoint
// exists to surface each key's `last_used_at`). A third call to
// `GET /app/projects/{id}/credentials` would be dead weight: `revalidatePath`
// re-renders this page, which refetches usage — and the credentials with it.
//
// `/app/projects/{id}/usage` carries no `project` object, hence the separate
// `getProject` call for the header.
//
// The <title> is STATIC copy, not the project name: our vocky client is
// `cache: "no-store"`, so `generateMetadata` would cost a second uncached fetch
// for a cosmetic gain.
export const metadata: Metadata = { title: PROJECT.title };

const credentialColumns: DataTableColumn<VockyCredential>[] = [
  {
    key: "name",
    header: PROJECT.credentials.columns.name,
    cell: (credential) =>
      credential.name === null ? (
        <span className="text-steel italic">{PROJECT.credentials.unnamed}</span>
      ) : (
        <span className="font-medium text-ink">{credential.name}</span>
      ),
  },
  {
    key: "key",
    header: PROJECT.credentials.columns.key,
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
    header: PROJECT.credentials.columns.created,
    cell: (credential) => <Timestamp iso={credential.created_at} />,
  },
  {
    key: "lastUsed",
    header: PROJECT.credentials.columns.lastUsed,
    // `null` until the key is first used to ingest — the whole reason this page
    // reads the usage endpoint rather than the plain credentials list.
    cell: (credential) =>
      credential.last_used_at === null ? (
        <span className="text-body-sm text-steel">
          {PROJECT.credentials.never}
        </span>
      ) : (
        <Timestamp iso={credential.last_used_at} />
      ),
  },
  {
    key: "status",
    header: PROJECT.credentials.columns.status,
    // vocky has NO `status` field: Active ⇔ `revoked_at === null`. Revoked keys
    // stay listed (revoke is a stamp, not a delete), so the badge is derived.
    // Both variants come from the existing placeholder palette — P4 adds no new
    // badge token, so the P6 design gate swaps values only.
    cell: (credential) =>
      credential.revoked_at === null ? (
        <Badge variant="softGreen">{PROJECT.credentials.statusActive}</Badge>
      ) : (
        <Badge variant="archive">{PROJECT.credentials.statusRevoked}</Badge>
      ),
  },
  {
    key: "actions",
    header: <span className="sr-only">{PROJECT.credentials.columns.actions}</span>,
    actions: true,
    // An already-revoked key has nothing to revoke; the badge tells that story.
    // `project_id` comes off the row, which is what lets this stay a module-level
    // const rather than being rebuilt per render.
    cell: (credential) =>
      credential.revoked_at === null ? (
        <RevokeCredentialButton
          projectId={credential.project_id}
          credentialId={credential.id}
          credentialLabel={credential.name ?? credential.token_prefix}
        />
      ) : null,
  },
];

/** `"2026-07-16T09:31:02+00:00"` → `"Jul 16, 2026"`; unparseable → as-is. */
function formatTimestamp(iso: string): string {
  const at = new Date(iso);
  if (Number.isNaN(at.getTime())) return iso;
  return at.toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function Timestamp({ iso }: { iso: string }) {
  return (
    <time
      dateTime={iso}
      className="font-mono text-body-sm text-steel tabular-nums"
    >
      {formatTimestamp(iso)}
    </time>
  );
}

/**
 * Fetch the header + usage, mapping vocky's not-found statuses to the 404 page.
 *
 * 404 (missing OR another tenant's — vocky answers 404-never-403 so ids cannot be
 * probed) and 400 (not a UUID) both render the SAME not-found page: a malformed
 * id is effectively not-found, and distinguishing them would leak the shape of
 * what exists. A 401 never reaches here — `requireIdentity` already turned it into
 * a redirect. EVERYTHING ELSE rethrows: an outage should surface, not masquerade
 * as a missing project.
 *
 * The mapping lives in its own function so the `notFound()` call cannot ever sit
 * inside the `try` that wraps the fetches (it, like `redirect()`, signals by
 * throwing).
 */
async function loadProject(
  token: string,
  projectId: string,
): Promise<[VockyProject, VockyProjectUsage]> {
  try {
    return await Promise.all([
      getProject(token, projectId),
      getProjectUsage(token, projectId),
    ]);
  } catch (error) {
    if (error instanceof ApiError && (error.status === 404 || error.status === 400)) {
      notFound();
    }
    throw error;
  }
}

export default async function ProjectPage({
  params,
}: {
  // Next 16: dynamic route params arrive as a Promise.
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = await params;
  const { token } = await requireIdentity();
  const [project, usage] = await loadProject(token, projectId);

  return (
    <div className="mx-auto max-w-page">
      <h1 className="text-heading-3 text-ink">{project.name}</h1>

      <div className="mt-6 space-y-8">
        {/* Exactly ONE usage block on this page: StatTiles/TrendChart hardcode
            their `usage-totals` / `usage-trend` DOM ids, so a second block would
            collide. Both are reused AS-IS from S3 — the shapes are identical. */}
        <StatTiles
          heading={PROJECT.usage.heading}
          totals={usage.totals}
          tiles={PROJECT.usage.tiles}
          window={usage.window}
          windowPrefix={PROJECT.usage.windowPrefix}
          windowUnknown={PROJECT.usage.windowUnknown}
        />

        <TrendChart
          heading={PROJECT.trend.heading}
          days={usage.daily_counts}
          empty={PROJECT.trend.empty}
          partialDayNote={PROJECT.trend.partialDayNote}
          ariaLabel={PROJECT.trend.ariaLabel}
        />

        <section aria-labelledby="credentials">
          <h2 id="credentials" className="text-heading-4 text-ink">
            {PROJECT.credentials.heading}
          </h2>
          <p className="mt-1 text-body-sm text-steel">
            {PROJECT.credentials.lead}
          </p>

          <DataTable
            columns={credentialColumns}
            rows={usage.credentials}
            rowKey={(credential) => credential.id}
            // Overrides DataTable's built-in default, which would bypass
            // copy-as-data.
            empty={PROJECT.credentials.empty}
            className="mt-4"
          />

          <Card variant="base" className="mt-4">
            <h3 className="text-body-md font-semibold text-ink">
              {PROJECT.mint.heading}
            </h3>
            <div className="mt-3">
              <MintCredentialForm projectId={project.id} />
            </div>
          </Card>
        </section>
      </div>
    </div>
  );
}
