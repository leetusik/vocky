import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import {
  Button,
  buttonVariants,
  Card,
  DataTable,
  type DataTableColumn,
  Input,
  inputVariants,
  Label,
} from "@/components/ui";
import { FEEDBACK } from "@/content";
import { requireIdentity } from "@/lib/auth-guards";
import { listFeedback, listProjects } from "@/lib/vocky/app";
import { ApiError } from "@/lib/vocky/client";
import type {
  VockyFeedback,
  VockyFeedbackPage,
  VockyFeedbackQuery,
  VockyProject,
} from "@/lib/vocky/types";

import { RatingBadge, Timestamp } from "./feedback-fields";

// P4.S5 — cross-project feedback list + Korean-safe search: the surface that
// finally exposes what P3 built. A server component throughout, with NO client
// island at all — the filter bar is a plain `<form method="GET">`, so it needs no
// JS, no `useSearchParams`, no `router.push`, and no debounce. Submitting
// navigates, which is exactly the semantic we want (each result set is its own
// URL, and browser back is "previous page").
//
// READ + SEARCH ONLY. Managing feedback (edit / delete / comment) lives on the
// `vk_`-keyed `/api/project/feedback` surface — a different credential entirely,
// and out of scope for this app — so there is nothing to mutate here and no
// server action on this page.
//
// TWO PARALLEL calls: `/app/projects` earns its round-trip twice over — records
// carry only `project_id`, so it supplies the id → name map (raw UUIDs in a
// table are unreadable) AND the project filter's options.
export const metadata: Metadata = { title: FEEDBACK.title };

/**
 * Every `GET /app/feedback` param, in vocky's own order.
 *
 * The UI surfaces only `q` / `project_id` / `feedback_value` — 16 inputs would be
 * a wall of niche debugging filters. The rest stay URL-REACHABLE: they are read
 * here, sent to vocky, and preserved across a filter submit (as hidden inputs)
 * and across pagination (as link params), so a hand-crafted URL survives both.
 *
 * `satisfies` ties this list to the client's query type — adding a param there
 * without adding it here is then a type error, not a silently ignored filter.
 */
const PARAM_KEYS = [
  "q",
  "project_id",
  "start_ingested_at",
  "end_ingested_at",
  "source_product",
  "source_integration",
  "conversation_id",
  "session_id",
  "user_id",
  "feedback_value",
  "channel",
  "target_type",
  "trigger_type",
  "tag",
  "limit",
  "cursor",
] as const satisfies readonly (keyof VockyFeedbackQuery)[];

type ParamKey = (typeof PARAM_KEYS)[number];

/** The active filters as raw URL strings, keyed by vocky's param names. */
type ActiveParams = Partial<Record<ParamKey, string>>;

/** The three params the filter form renders as real inputs. */
const FORM_FIELD_KEYS: readonly string[] = ["q", "project_id", "feedback_value"];

/**
 * Take the first value of a possibly-repeated param.
 *
 * This page is the app's first `searchParams` reader, and this is the wrinkle
 * `params` never had: a query string may legally repeat a key (`?q=a&q=b`), so
 * Next hands us a `string[]` for it, where a route `params` value is always a
 * plain string. vocky's own `request.query_params.get()` takes the FIRST
 * occurrence, so taking the first here keeps the URL, the form, and the filter
 * vocky actually applies in agreement.
 */
function takeFirst(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

/**
 * The active (non-blank) filters from the URL.
 *
 * BLANK IS ABSENT. This is not defensive tidying — it is load-bearing: a GET form
 * necessarily submits its empty fields, so choosing "All projects" and searching
 * puts `?q=&project_id=&feedback_value=` in the URL, and vocky answers **400** to
 * a blank `project_id` (`UUID("")`) or a blank `feedback_value` (`int("")`).
 * Dropping blanks here is what makes the unfiltered form submit mean "no filter".
 * Values are trimmed to match vocky's own normalization.
 */
function readActiveParams(
  raw: Record<string, string | string[] | undefined>,
): ActiveParams {
  const active: ActiveParams = {};
  for (const key of PARAM_KEYS) {
    const value = takeFirst(raw[key])?.trim();
    if (value) active[key] = value;
  }
  return active;
}

/**
 * URL strings → the typed client query.
 *
 * The four non-string params are NARROWED, not validated: vocky owns the rules
 * (`feedback_value` ∈ {1,2}, `limit` ∈ 1–100, the two enum filters) and answers
 * 400, which `loadFeedback` turns into the not-found page. Re-checking them here
 * would fork the UI from the backend's validation — the same reason the BFF's
 * credential routes let vocky own the password rules.
 */
function toQuery(active: ActiveParams): VockyFeedbackQuery {
  const { feedback_value, limit, target_type, trigger_type, ...text } = active;
  return {
    ...text,
    ...(feedback_value === undefined
      ? {}
      : { feedback_value: Number(feedback_value) as 1 | 2 }),
    ...(limit === undefined ? {} : { limit: Number(limit) }),
    ...(target_type === undefined
      ? {}
      : { target_type: target_type as VockyFeedbackQuery["target_type"] }),
    ...(trigger_type === undefined
      ? {}
      : { trigger_type: trigger_type as VockyFeedbackQuery["trigger_type"] }),
  };
}

/**
 * The next page's href: EVERY active filter, plus the new cursor.
 *
 * Resending the filters is mandatory, not tidy — vocky's cursor encodes only
 * `{ingested_at, id}`, so a bare `?cursor=…` would silently widen the scope to
 * every record from that point on. The old cursor is replaced, never appended.
 */
function nextPageHref(active: ActiveParams, cursor: string): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(active)) {
    if (key !== "cursor") search.set(key, value);
  }
  search.set("cursor", cursor);
  return `/feedback?${search.toString()}`;
}

/**
 * Fetch the page + the project list, mapping vocky's rejections to the 404 page.
 *
 * 404 (a `project_id` outside the tenant — vocky answers 404-never-403 so ids
 * cannot be probed) and 400 (a malformed id, a bad `feedback_value`, a garbled
 * `cursor`) render the SAME not-found page, the S4 policy applied to a query
 * string: every one of them means "the page you asked for does not exist", and
 * telling them apart would leak which ids do. A 401 never reaches here
 * (`requireIdentity` already redirected); EVERYTHING ELSE rethrows — an outage
 * must surface, not masquerade as an empty search.
 *
 * The mapping lives in its own function so `notFound()` can never sit inside the
 * `try` around the fetches: it signals by THROWING, exactly like `redirect()`, so
 * a `catch` would swallow it.
 */
async function loadFeedback(
  token: string,
  query: VockyFeedbackQuery,
): Promise<[VockyFeedbackPage, VockyProject[]]> {
  try {
    return await Promise.all([listFeedback(token, query), listProjects(token)]);
  } catch (error) {
    if (
      error instanceof ApiError &&
      (error.status === 404 || error.status === 400)
    ) {
      notFound();
    }
    throw error;
  }
}

function columns(
  projectNames: Map<string, string>,
): DataTableColumn<VockyFeedback>[] {
  return [
    {
      key: "when",
      header: FEEDBACK.list.columns.when,
      cell: (record) => <Timestamp iso={record.ingested_at} />,
    },
    {
      key: "project",
      header: FEEDBACK.list.columns.project,
      // Records carry only `project_id`; the name comes from the parallel
      // `/app/projects` call. The fallback covers a legacy NULL-project row (not
      // reachable through this endpoint's owned-id filter, but the type allows
      // it) and the race where a project is deleted between the two calls.
      cell: (record) => (
        <span className="text-body-sm text-slate">
          {(record.project_id && projectNames.get(record.project_id)) ||
            FEEDBACK.list.unknownProject}
        </span>
      ),
    },
    {
      key: "message",
      header: FEEDBACK.list.columns.message,
      // The way into the detail page. `message` is UNTRUSTED caller-supplied
      // text — rendered as a child, never as HTML and never into the href.
      cell: (record) => (
        <Link
          href={`/feedback/${record.id}`}
          className="line-clamp-2 max-w-prose font-medium text-ink hover:underline"
        >
          {record.message}
        </Link>
      ),
    },
    {
      key: "value",
      header: FEEDBACK.list.columns.value,
      cell: (record) => <RatingBadge value={record.feedback_value} />,
    },
    {
      key: "source",
      header: FEEDBACK.list.columns.source,
      cell: (record) => (
        <span className="font-mono text-body-sm text-steel">
          {record.source_product}
        </span>
      ),
    },
  ];
}

function FilterBar({
  active,
  projects,
}: {
  active: ActiveParams;
  projects: VockyProject[];
}) {
  // The URL-only filters, re-emitted as hidden inputs so a hand-crafted URL
  // survives a submit. `cursor` is deliberately NOT among them: submitting must
  // reset to page 1, and dropping it is exactly how a GET form does that.
  const passthrough = (Object.entries(active) as [ParamKey, string][]).filter(
    ([key]) => key !== "cursor" && !FORM_FIELD_KEYS.includes(key),
  );

  return (
    <Card variant="base">
      <h2 className="text-body-md font-semibold text-ink">
        {FEEDBACK.filters.heading}
      </h2>

      {/* A plain GET form: no JS, no client island. The browser builds
          `/feedback?q=…` itself and navigates, so every result set is a real,
          shareable URL and back/forward work for free. */}
      <form method="GET" action="/feedback" className="mt-3">
        {passthrough.map(([key, value]) => (
          <input key={key} type="hidden" name={key} value={value} />
        ))}

        <div className="flex flex-col gap-4 min-[900px]:flex-row min-[900px]:items-end">
          <div className="min-[900px]:flex-1">
            <Label htmlFor="q">{FEEDBACK.filters.searchLabel}</Label>
            <Input
              id="q"
              name="q"
              type="search"
              defaultValue={active.q ?? ""}
              placeholder={FEEDBACK.filters.searchPlaceholder}
              className="mt-1.5"
            />
          </div>

          <div className="min-[900px]:w-56">
            <Label htmlFor="project_id">{FEEDBACK.filters.projectLabel}</Label>
            <select
              id="project_id"
              name="project_id"
              defaultValue={active.project_id ?? ""}
              className={`${inputVariants()} mt-1.5`}
            >
              {/* Blank = every project the tenant owns. It submits as
                  `project_id=` and is dropped by `readActiveParams` — sending it
                  to vocky would be a 400. */}
              <option value="">{FEEDBACK.filters.projectAll}</option>
              {projects.map((project) => (
                <option key={project.id} value={project.id}>
                  {project.name}
                </option>
              ))}
            </select>
          </div>

          <div className="min-[900px]:w-40">
            <Label htmlFor="feedback_value">{FEEDBACK.filters.valueLabel}</Label>
            <select
              id="feedback_value"
              name="feedback_value"
              defaultValue={active.feedback_value ?? ""}
              className={`${inputVariants()} mt-1.5`}
            >
              {/* vocky accepts ONLY 1 or 2 — there is no filter for "unrated". */}
              <option value="">{FEEDBACK.filters.valueAny}</option>
              <option value="1">{FEEDBACK.filters.valueLiked}</option>
              <option value="2">{FEEDBACK.filters.valueDisliked}</option>
            </select>
          </div>

          <div className="flex items-center gap-2">
            <Button type="submit" size="sm">
              {FEEDBACK.filters.submitLabel}
            </Button>
            {/* A link, not a reset button: `type="reset"` would restore the
                submitted values, not clear the query. */}
            <Link
              href="/feedback"
              className={buttonVariants({ variant: "secondary", size: "sm" })}
            >
              {FEEDBACK.filters.resetLabel}
            </Link>
          </div>
        </div>

        <p className="mt-3 text-body-sm text-steel">
          {FEEDBACK.filters.searchHint}
        </p>
      </form>
    </Card>
  );
}

export default async function FeedbackPage({
  searchParams,
}: {
  // Next 16: search params arrive as a Promise, and a value is `string[]` for a
  // repeated key — see `takeFirst`.
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const active = readActiveParams(await searchParams);
  const { token } = await requireIdentity();
  const [page, projects] = await loadFeedback(token, toQuery(active));

  const projectNames = new Map(projects.map((p) => [p.id, p.name]));

  // Two DIFFERENT empty results. With no projects, nothing can have arrived yet
  // (vocky short-circuits to `{records: []}` without even querying) — telling the
  // reader to "clear filters" would be nonsense. With projects, an empty page
  // means the filters matched nothing.
  const empty =
    projects.length === 0
      ? FEEDBACK.list.emptyNoProjects
      : FEEDBACK.list.emptyNoMatches;

  return (
    <div className="mx-auto max-w-page">
      <h1 className="text-heading-3 text-ink">{FEEDBACK.lead}</h1>

      <div className="mt-6 space-y-8">
        <FilterBar active={active} projects={projects} />

        <section aria-labelledby="feedback-list">
          <h2 id="feedback-list" className="text-heading-4 text-ink">
            {FEEDBACK.list.heading}
          </h2>
          <p className="mt-1 text-body-sm text-steel">
            {FEEDBACK.list.timeNote}
          </p>

          <DataTable
            columns={columns(projectNames)}
            rows={page.records}
            rowKey={(record) => record.id}
            // Overrides DataTable's built-in default, which would bypass
            // copy-as-data.
            empty={empty}
            className="mt-4"
          />

          {/* Forward-only: keyset paging yields no previous cursor, and each page
              is its own URL, so browser back IS "previous". `next_cursor` is an
              OMITTED key when exhausted — hence `!== undefined`, never `!== null`
              (which would render this link forever). */}
          {page.next_cursor !== undefined && (
            <div className="mt-4 flex justify-end">
              <Link
                href={nextPageHref(active, page.next_cursor)}
                className={buttonVariants({ variant: "secondary", size: "sm" })}
              >
                {FEEDBACK.pagination.nextLabel}
              </Link>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
