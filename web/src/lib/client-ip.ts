/**
 * Best-effort client IP from proxy headers, shared by the rate-limited BFF auth
 * route handlers (login / signup). Ported verbatim from hi2vi_web
 * (`src/lib/client-ip.ts`): the first comma-segment of `x-forwarded-for`, else
 * `x-real-ip`, else an `"unknown"` sentinel.
 *
 * The value is client-supplied and therefore spoofable — like the in-memory rate
 * limiter it feeds, this is a weak first layer, backed by nginx at the edge (P6).
 */
export function clientIp(h: Headers): string {
  const xff = h.get("x-forwarded-for");
  if (xff) {
    const first = xff.split(",")[0]?.trim();
    if (first) return first;
  }
  const real = h.get("x-real-ip")?.trim();
  if (real) return real;
  return "unknown";
}
