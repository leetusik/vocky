import {
  Badge,
  Button,
  Card,
  DataTable,
  Grid,
  type DataTableColumn,
} from "@/components/ui";
import { SECTION_IDS, SITE } from "@/content";

// P4.S1 design-system preview. This is the S1 smoke test: it renders the ported
// tokens + primitives (buttons, badges, cards, a responsive Grid, and the new
// DataTable) so `pnpm dev` proves the foundation before S2 wires auth/data. It
// is purely presentational — no vocky API calls. The authenticated `(app)` route
// group (dashboard/projects/feedback) is P4.S2's job.

interface PreviewRow {
  id: string;
  name: string;
  status: "active" | "revoked";
  lastUsed: string;
}

const PREVIEW_ROWS: PreviewRow[] = [
  { id: "p1", name: "acme-support", status: "active", lastUsed: "2026-07-15" },
  { id: "p2", name: "beta-widget", status: "active", lastUsed: "2026-07-11" },
  { id: "p3", name: "legacy-intake", status: "revoked", lastUsed: "2026-05-02" },
];

const PREVIEW_COLUMNS: DataTableColumn<PreviewRow>[] = [
  { key: "name", header: "Project", cell: (r) => <span className="font-medium">{r.name}</span> },
  {
    key: "status",
    header: "Status",
    cell: (r) => (
      <Badge variant={r.status === "active" ? "softGreen" : "archive"}>
        {r.status}
      </Badge>
    ),
  },
  {
    key: "lastUsed",
    header: "Last used",
    align: "right",
    cell: (r) => <span className="font-mono text-caption text-steel">{r.lastUsed}</span>,
  },
  {
    key: "actions",
    header: "",
    actions: true,
    cell: () => (
      <Button variant="link" className="text-body-sm">
        View
      </Button>
    ),
  },
];

export default function DesignSystemPreviewPage() {
  return (
    <main id="main-content" className="mx-auto max-w-page px-5 py-16 md:px-14">
      <header className="mb-12">
        <p className="text-micro uppercase text-green-dark">
          {SITE.name} · Design system
        </p>
        <h1 className="mt-2 text-heading-1 text-ink">Foundation preview</h1>
        <p className="mt-3 max-w-2xl text-body-lg text-slate">
          Placeholder palette (slate surfaces + one indigo accent) and the ported
          CVA primitives. Token names match hi2vi_web so the P6 design gate swaps
          values only — this page never calls the vocky API.
        </p>
      </header>

      <section id={SECTION_IDS.primitives} className="scroll-mt-24 space-y-12">
        <div>
          <h2 className="mb-4 text-heading-3 text-ink">Buttons</h2>
          <div className="flex flex-wrap items-center gap-3">
            <Button variant="primary">Primary</Button>
            <Button variant="secondary">Secondary</Button>
            <Button variant="primary" size="lg">
              Large
            </Button>
            <Button variant="primary" size="sm">
              Small
            </Button>
            <Button variant="link">Link action</Button>
            <Button variant="primary" disabled>
              Disabled
            </Button>
          </div>
        </div>

        <div>
          <h2 className="mb-4 text-heading-3 text-ink">Badges</h2>
          <div className="flex flex-wrap items-center gap-3">
            <Badge variant="signal">signal</Badge>
            <Badge variant="softGreen">soft accent</Badge>
            <Badge variant="security">security</Badge>
            <Badge variant="archive">archive</Badge>
            <Badge variant="dark">dark</Badge>
          </div>
        </div>

        <div>
          <h2 className="mb-4 text-heading-3 text-ink">Cards (Grid, 3-up)</h2>
          <Grid cols={3}>
            <Card variant="base">
              <h3 className="text-heading-4 text-ink">Base card</h3>
              <p className="mt-2 text-body-md text-slate">
                Hairline border on the canvas surface.
              </p>
            </Card>
            <Card variant="feature">
              <h3 className="text-heading-4 text-ink">Feature card</h3>
              <p className="mt-2 text-body-md text-slate">
                Soft elevation via the retoned shadow token.
              </p>
            </Card>
            <Card variant="dark">
              <h3 className="text-heading-4 text-on-dark">Dark card</h3>
              <p className="mt-2 text-body-md text-on-dark-muted">
                Explicit dark surface — no dark-mode toggle.
              </p>
            </Card>
          </Grid>
        </div>

        <div>
          <h2 className="mb-4 text-heading-3 text-ink">DataTable (new primitive)</h2>
          <DataTable
            columns={PREVIEW_COLUMNS}
            rows={PREVIEW_ROWS}
            rowKey={(r) => r.id}
          />
          <p className="mt-4 text-caption text-steel">
            Empty state (no rows):
          </p>
          <div className="mt-2">
            <DataTable
              columns={PREVIEW_COLUMNS}
              rows={[]}
              rowKey={(r) => r.id}
              empty="No projects yet."
            />
          </div>
        </div>
      </section>
    </main>
  );
}
