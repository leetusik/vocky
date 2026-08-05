import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import type { ReactNode } from "react";

import { buttonVariants, Card, Chip } from "@/components/ui";
import { FEEDBACK } from "@/content";
import { requireIdentity } from "@/lib/auth-guards";
import { getFeedbackDetail, listProjects } from "@/lib/vocky/app";
import { ApiError } from "@/lib/vocky/client";
import type { VockyFeedbackDetail, VockyProject } from "@/lib/vocky/types";

import { RatingBadge, Timestamp } from "../feedback-fields";

// P4.S5 — one feedback record in full, reached from the list's message link.
// A server component throughout; no client island, and no server action — this
// surface is READ-ONLY by design. Editing, deleting, and commenting live on the
// `vk_`-keyed `/api/project/feedback` surface (a PATCH here would 405), so there
// is nothing on this page to submit.
//
// EVERY string rendered below is CALLER-SUPPLIED, UNTRUSTED text — it arrives
// from whatever service holds a `vk_` ingest key. All of it goes through JSX as
// text children, which React escapes; nothing here uses `dangerouslySetInnerHTML`
// or feeds a value into an `href`. The one uploader-controlled byte stream
// (attachments) is forced to download by our proxy rather than rendered inline.
export const metadata: Metadata = { title: FEEDBACK.detail.title };

/**
 * Fetch the record + the project list, mapping vocky's rejections to the 404 page.
 *
 * 404 (missing, another tenant's, or a legacy NULL-project row — vocky answers
 * 404-never-403 so ids cannot be probed) and 400 (not a UUID) both render the
 * SAME not-found page: a malformed id is effectively not-found, and
 * distinguishing them would leak the shape of what exists. A 401 never reaches
 * here (`requireIdentity` already redirected); EVERYTHING ELSE rethrows.
 *
 * The mapping lives in its own function so `notFound()` can never sit inside the
 * `try` around the fetches — it signals by THROWING, exactly like `redirect()`.
 *
 * `listProjects` rides along only to name the record's project (it carries just
 * an id, and a raw UUID is unreadable); it can produce neither a 400 nor a 404,
 * so it cannot trip the mapping above.
 */
async function loadFeedback(
  token: string,
  feedbackId: string,
): Promise<[VockyFeedbackDetail, VockyProject[]]> {
  try {
    return await Promise.all([
      getFeedbackDetail(token, feedbackId),
      listProjects(token),
    ]);
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

/** The `—` stand-in for any field vocky returned as `null`. */
function Empty() {
  return <span className="text-steel">{FEEDBACK.detail.fieldEmpty}</span>;
}

/** One label/value pair. `children` of `null`/`undefined` renders as `—`. */
function Field({ label, children }: { label: string; children?: ReactNode }) {
  return (
    <div>
      <dt className="text-caption text-steel">{label}</dt>
      <dd className="mt-0.5 text-body-sm break-words text-ink">
        {children ?? <Empty />}
      </dd>
    </div>
  );
}

/** An opaque caller-supplied id — monospaced so it can be read and compared. */
function Mono({ children }: { children: ReactNode }) {
  return <span className="font-mono text-body-sm">{children}</span>;
}

/** `1536` → `"1.5 KB"`. Binary units, matching how vocky counts the stored bytes. */
function formatBytes(bytes: number): string {
  const units = FEEDBACK.attachments.byteUnits;
  let value = bytes;
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  return `${unit === 0 ? value : value.toFixed(1)} ${units[unit]}`;
}

/** True when a free-form blob has anything worth showing. */
function hasContent(value: Record<string, unknown> | unknown[]): boolean {
  return Array.isArray(value)
    ? value.length > 0
    : Object.keys(value).length > 0;
}

/**
 * One free-form JSON blob, collapsed.
 *
 * vocky enforces NO schema on `trigger_metadata` / `source_metadata` /
 * `attributes` / `messages` / `used_context` — they are whatever the caller sent
 * — so there is nothing to render them as but themselves. `JSON.stringify` into
 * a text child: the values are untrusted, and this is the one place their raw
 * shape is visible.
 */
function RawBlock({
  label,
  value,
}: {
  label: string;
  value: Record<string, unknown> | unknown[];
}) {
  return (
    <details className="rounded-md border border-hairline bg-surface px-4 py-3">
      <summary className="cursor-pointer text-body-sm font-medium text-slate">
        {label}
      </summary>
      <pre className="mt-3 overflow-x-auto font-mono text-body-sm text-ink">
        {JSON.stringify(value, null, 2)}
      </pre>
    </details>
  );
}

export default async function FeedbackDetailPage({
  params,
}: {
  // Next 16: dynamic route params arrive as a Promise.
  params: Promise<{ feedbackId: string }>;
}) {
  const { feedbackId } = await params;
  const { token } = await requireIdentity();
  const [record, projects] = await loadFeedback(token, feedbackId);

  const projectName =
    (record.project_id &&
      projects.find((p) => p.id === record.project_id)?.name) ||
    null;

  const rawBlocks: [string, Record<string, unknown> | unknown[]][] = (
    [
      [FEEDBACK.detail.raw.triggerMetadata, record.trigger_metadata],
      [FEEDBACK.detail.raw.sourceMetadata, record.source_metadata],
      [FEEDBACK.detail.raw.attributes, record.attributes],
      [FEEDBACK.detail.raw.messages, record.messages],
      [FEEDBACK.detail.raw.usedContext, record.used_context],
    ] as [string, Record<string, unknown> | unknown[]][]
  ).filter(([, value]) => hasContent(value));

  return (
    <div className="mx-auto max-w-page">
      <Link
        href="/feedback"
        className="text-body-sm text-slate hover:text-ink hover:underline"
      >
        ← {FEEDBACK.detail.backLabel}
      </Link>

      <div className="mt-4 space-y-6">
        <section aria-labelledby="feedback-message">
          <div className="flex items-center justify-between gap-4">
            <h1 id="feedback-message" className="text-heading-3 text-ink">
              {FEEDBACK.detail.messageHeading}
            </h1>
            <RatingBadge value={record.feedback_value} />
          </div>

          <Card variant="base" className="mt-3">
            {/* The end user's own words — untrusted text, whitespace preserved
                so multi-line feedback reads as it was written. */}
            <p className="text-body-md break-words whitespace-pre-wrap text-ink">
              {record.message}
            </p>
          </Card>

          <h2 className="mt-6 text-body-md font-semibold text-ink">
            {FEEDBACK.detail.commentHeading}
          </h2>
          <Card variant="featureMuted" className="mt-2">
            {record.comment === null ? (
              <p className="text-body-sm text-steel">
                {FEEDBACK.detail.commentNone}
              </p>
            ) : (
              <p className="text-body-sm break-words whitespace-pre-wrap text-ink">
                {record.comment}
              </p>
            )}
          </Card>
        </section>

        <section aria-labelledby="feedback-details">
          <h2 id="feedback-details" className="text-heading-4 text-ink">
            {FEEDBACK.detail.detailsHeading}
          </h2>
          <p className="mt-1 text-body-sm text-steel">
            {FEEDBACK.list.timeNote}
          </p>

          <Card variant="base" className="mt-3">
            <dl className="grid grid-cols-1 gap-x-6 gap-y-4 sm:grid-cols-2 app:grid-cols-3">
              <Field label={FEEDBACK.detail.fields.project}>
                {projectName}
              </Field>
              <Field label={FEEDBACK.detail.fields.value}>
                <RatingBadge value={record.feedback_value} />
              </Field>
              <Field label={FEEDBACK.detail.fields.sourceProduct}>
                <Mono>{record.source_product}</Mono>
              </Field>
              <Field label={FEEDBACK.detail.fields.sourceIntegration}>
                {record.source_integration && (
                  <Mono>{record.source_integration}</Mono>
                )}
              </Field>
              <Field label={FEEDBACK.detail.fields.channel}>
                {record.channel}
              </Field>
              {/* WHO recorded it (agent | human), vs the trigger below, which is
                  WHY. `null` = unspecified, rendered as the empty dash. */}
              <Field label={FEEDBACK.detail.fields.recordedBy}>
                {record.recorded_by}
              </Field>
              <Field label={FEEDBACK.detail.fields.triggerType}>
                {record.trigger_type}
              </Field>
              <Field label={FEEDBACK.detail.fields.targetType}>
                {record.target_type}
              </Field>
              <Field label={FEEDBACK.detail.fields.targetRole}>
                {record.target_role}
              </Field>
              <Field label={FEEDBACK.detail.fields.conversationId}>
                {record.conversation_id && (
                  <Mono>{record.conversation_id}</Mono>
                )}
              </Field>
              <Field label={FEEDBACK.detail.fields.sessionId}>
                {record.session_id && <Mono>{record.session_id}</Mono>}
              </Field>
              <Field label={FEEDBACK.detail.fields.userId}>
                {record.user_id && <Mono>{record.user_id}</Mono>}
              </Field>
              {/* Caller-reported: when the feedback HAPPENED, vs `ingested_at`,
                  when vocky stored it. They can differ by a lot on a batched
                  or replayed capture. */}
              <Field label={FEEDBACK.detail.fields.eventAt}>
                {record.event_at && <Timestamp iso={record.event_at} />}
              </Field>
              <Field label={FEEDBACK.detail.fields.ingestedAt}>
                <Timestamp iso={record.ingested_at} />
              </Field>
              <Field label={FEEDBACK.detail.fields.id}>
                <Mono>{record.id}</Mono>
              </Field>
            </dl>

            {/* The two long-form context fields, given their own full-width
                block rather than a grid cell they would overflow. */}
            {(record.trigger_message !== null ||
              record.target_text !== null) && (
              <dl className="mt-6 space-y-4 border-t border-hairline-soft pt-6">
                {record.trigger_message !== null && (
                  <Field label={FEEDBACK.detail.fields.triggerMessage}>
                    <span className="whitespace-pre-wrap">
                      {record.trigger_message}
                    </span>
                  </Field>
                )}
                {record.target_text !== null && (
                  <Field label={FEEDBACK.detail.fields.targetText}>
                    <span className="whitespace-pre-wrap">
                      {record.target_text}
                    </span>
                  </Field>
                )}
              </dl>
            )}
          </Card>

          <h3 className="mt-6 text-body-md font-semibold text-ink">
            {FEEDBACK.detail.tagsHeading}
          </h3>
          {record.tags.length === 0 ? (
            <p className="mt-2 text-body-sm text-steel">
              {FEEDBACK.detail.tagsNone}
            </p>
          ) : (
            <ul className="mt-2 flex flex-wrap gap-2">
              {record.tags.map((tag) => (
                // Keyed by the tag itself: vocky stores tags as a list and does
                // not de-duplicate, so the index guards a repeated tag.
                <li key={tag}>
                  <Chip>{tag}</Chip>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section aria-labelledby="feedback-comments">
          <h2 id="feedback-comments" className="text-heading-4 text-ink">
            {FEEDBACK.detail.commentsHeading}
          </h2>
          {record.comments.length === 0 ? (
            <p className="mt-2 text-body-sm text-steel">
              {FEEDBACK.detail.commentsNone}
            </p>
          ) : (
            <ul className="mt-3 space-y-3">
              {record.comments.map((comment) => (
                <li key={comment.id}>
                  <Card variant="featureMuted">
                    <div className="flex items-baseline justify-between gap-3">
                      <span className="text-body-sm font-medium text-ink">
                        {comment.author ?? FEEDBACK.detail.commentAuthorUnknown}
                      </span>
                      <Timestamp iso={comment.created_at} />
                    </div>
                    <p className="mt-2 text-body-sm break-words whitespace-pre-wrap text-slate">
                      {comment.body}
                    </p>
                  </Card>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section aria-labelledby="feedback-attachments">
          <h2 id="feedback-attachments" className="text-heading-4 text-ink">
            {FEEDBACK.attachments.heading}
          </h2>
          {record.attachments.length === 0 ? (
            <p className="mt-2 text-body-sm text-steel">
              {FEEDBACK.attachments.none}
            </p>
          ) : (
            <>
              <p className="mt-1 text-body-sm text-steel">
                {FEEDBACK.attachments.downloadNote}
              </p>
              <ul className="mt-3 space-y-2">
                {record.attachments.map((attachment) => (
                  <li
                    key={attachment.id}
                    className="flex items-center justify-between gap-4 rounded-md border border-hairline bg-surface px-4 py-3"
                  >
                    <div className="min-w-0">
                      <p className="truncate text-body-sm text-ink">
                        {attachment.filename ?? FEEDBACK.attachments.unnamed}
                      </p>
                      <p className="mt-0.5 font-mono text-caption text-steel">
                        {attachment.content_type} ·{" "}
                        {formatBytes(attachment.byte_size)}
                      </p>
                    </div>
                    {/* OUR proxy, not `attachment.url`: vocky's url is a
                        vocky-relative path that needs the session bearer, which
                        exists only on our server. The proxy forces
                        `Content-Disposition: attachment`; the filename is applied
                        here, browser-side, which is why it need not know it. */}
                    <a
                      href={`/api/app/feedback/${record.id}/attachments/${attachment.id}`}
                      download={attachment.filename ?? undefined}
                      className={buttonVariants({
                        variant: "secondary",
                        size: "sm",
                      })}
                    >
                      {FEEDBACK.attachments.downloadLabel}
                    </a>
                  </li>
                ))}
              </ul>
            </>
          )}
        </section>

        <section aria-labelledby="feedback-raw">
          <h2 id="feedback-raw" className="text-heading-4 text-ink">
            {FEEDBACK.detail.rawHeading}
          </h2>
          {rawBlocks.length === 0 ? (
            <p className="mt-2 text-body-sm text-steel">
              {FEEDBACK.detail.rawNone}
            </p>
          ) : (
            <div className="mt-3 space-y-2">
              {rawBlocks.map(([label, value]) => (
                <RawBlock key={label} label={label} value={value} />
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
