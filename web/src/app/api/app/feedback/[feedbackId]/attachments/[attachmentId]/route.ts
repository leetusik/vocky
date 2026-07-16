import { getSession } from "@/lib/session";
import { ApiError, getRaw } from "@/lib/vocky/client";

// P4.S5 — the attachment download proxy: the app's only binary path, and the one
// place a `/app/*` payload reaches the browser without passing through a server
// component.
//
// WHY IT EXISTS: vocky serves attachments from
// `/app/feedback/{id}/attachments/{aid}`, which needs the session bearer — and
// the bearer lives sealed in an httpOnly cookie the browser cannot read, at an
// origin the browser never talks to (D-P4-2). So an `<a href>` straight to vocky
// would 401. This relays the bytes server-side instead, exactly like the auth
// routes relay credentials.
//
// It is NOT the S2 pipeline's kind of route: `lib/bff.ts` guards the PUBLIC,
// unauthenticated credential surface (rate limit, same-origin, zod). This is a
// GET behind the session cookie — no body to parse, no throttle to apply
// (vocky is the rate limiter of record), and a same-origin check would break the
// legitimate `download` navigation, which sends no Origin.
//
// SECURITY — the reason this is not a dumb pipe:
//   - `Content-Disposition: attachment` is FORCED. The bytes and their declared
//     content type are UPLOADER-supplied; vocky stores and echoes them as-is
//     with `nosniff` but no disposition. `nosniff` does not save you when the
//     declared type genuinely IS `text/html` — serving that inline from OUR
//     origin would be stored XSS against our own session cookie. Downloading it
//     is inert.
//   - The upstream `Content-Type` is passed through UNCHANGED (a download needs
//     it), which is safe only BECAUSE of the disposition above.
//   - `private, no-store`: one user's attachment must never be cached by a proxy
//     and handed to another.
export const runtime = "nodejs";
export const dynamic = "force-dynamic";

/** Both ids are UUIDs — a non-UUID can only be a hand-typed or tampered URL. */
const UUID_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/** Status-only replies: nothing about the upstream is ever echoed to the browser. */
function fail(status: number): Response {
  return new Response(null, {
    status,
    headers: { "Cache-Control": "private, no-store" },
  });
}

export async function GET(
  _req: Request,
  { params }: { params: Promise<{ feedbackId: string; attachmentId: string }> },
): Promise<Response> {
  // The cookie only — no `requireIdentity()`. That guard redirects to /login by
  // throwing, which is right for a page and wrong for a byte stream: a download
  // must answer a status, not an HTML login form. It also spends an `/auth/me`
  // round-trip this route does not need, since vocky re-authorizes the bearer
  // and re-checks tenant ownership on the call below anyway.
  const token = await getSession();
  if (!token) return fail(401);

  const { feedbackId, attachmentId } = await params;
  if (!UUID_PATTERN.test(feedbackId) || !UUID_PATTERN.test(attachmentId)) {
    return fail(400);
  }

  let upstream: Response;
  try {
    upstream = await getRaw(
      `/app/feedback/${encodeURIComponent(feedbackId)}/attachments/${encodeURIComponent(attachmentId)}`,
      { token },
    );
  } catch (error) {
    if (error instanceof ApiError) {
      // 404 — the record or attachment is missing, is another tenant's, or has
      // no stored object. vocky answers 404-never-403 for the cross-tenant case
      // on purpose, so passing it through verbatim is what preserves that: a 403
      // here would confirm the id exists.
      if (error.status === 404) return fail(404);
      // 401 — the session died between the cookie check and this call. Same
      // meaning as the missing-cookie branch above, so the same status.
      if (error.status === 401) return fail(401);
      // 503 — vocky's attachment storage is down. Ours is fine; theirs is not.
      if (error.status === 503) return fail(502);
      return fail(500);
    }
    // vocky unreachable, or SESSION/API env unset — never surfaced to the client.
    return fail(500);
  }

  // Stream the body through rather than buffering it. No `filename` in the
  // disposition: the detail page's `<a download={filename}>` names the file
  // browser-side, so the proxy never needs to know (and never has to escape a
  // caller-supplied filename into a header).
  return new Response(upstream.body, {
    status: 200,
    headers: {
      "Content-Type":
        upstream.headers.get("content-type") ?? "application/octet-stream",
      "Content-Disposition": "attachment",
      "X-Content-Type-Options": "nosniff",
      "Cache-Control": "private, no-store",
    },
  });
}
