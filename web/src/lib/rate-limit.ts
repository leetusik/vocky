// In-memory, per-process sliding-window rate limiter for the BFF auth route
// handlers (P4.S2). Ported verbatim from hi2vi_web (`src/lib/rate-limit.ts`,
// including its P18.S2 cross-window fix). This is the DELIBERATELY WEAK first
// layer of abuse control:
//
//   - It is a module-level `Map`, so it RESETS on every process restart/redeploy
//     and is PER-PROCESS only (each worker / instance has its own window — it does
//     not coordinate across processes or machines).
//   - The real, robust limit is nginx `limit_req` at the edge (a P6 deploy
//     concern); the client-supplied IP (`x-forwarded-for`) is spoofable, so this
//     layer only blunts naive credential-stuffing / signup flooding.
//
// To avoid an unbounded-memory leak, every call prunes timestamps (and then empty
// keys) that have fallen outside the window before it decides. Each bucket stores
// ITS OWN `windowMs`, and the opportunistic global prune judges every OTHER bucket
// against THAT bucket's window — not the caller's — so a short-window caller can
// never prematurely evict a still-live long-window bucket.

interface Bucket {
  /** In-window hit timestamps (epoch ms), oldest first. */
  times: number[];
  /** The window length this bucket was last written under — its OWN prune horizon. */
  windowMs: number;
}

const buckets = new Map<string, Bucket>();

/** Sentinel used when the caller can't determine a key (e.g. no IP header). */
const MISSING_KEY = "__missing__";

export interface RateLimitResult {
  /** True if this request is within the limit and may proceed. */
  ok: boolean;
  /** Remaining requests in the current window after counting this one. */
  remaining: number;
  /** ms until the oldest in-window hit expires (when `ok` is false). */
  retryAfterMs: number;
}

/**
 * Record a hit for `key` and report whether it is within `limit` over the
 * trailing `windowMs`. Expired timestamps are pruned on every call (memory-leak
 * guard); a missing/empty key is funneled to a shared sentinel bucket rather than
 * bypassing the limit.
 *
 * Caveats (documented above): per-process only and reset on restart — treat as a
 * heuristic backed by nginx, not a guarantee.
 */
export function checkRateLimit(
  key: string | null | undefined,
  limit: number,
  windowMs: number,
): RateLimitResult {
  const bucketKey = key && key.trim() !== "" ? key : MISSING_KEY;
  const now = Date.now();
  const windowStart = now - windowMs;

  const recent = (buckets.get(bucketKey)?.times ?? []).filter(
    (t) => t > windowStart,
  );

  if (recent.length >= limit) {
    buckets.set(bucketKey, { times: recent, windowMs });
    const oldest = recent[0];
    return {
      ok: false,
      remaining: 0,
      retryAfterMs: Math.max(0, oldest + windowMs - now),
    };
  }

  recent.push(now);
  buckets.set(bucketKey, { times: recent, windowMs });

  // Opportunistically drop other buckets that have fully expired so the Map can't
  // grow without bound under churning keys. Each bucket is judged against ITS OWN
  // window (`now - bucket.windowMs`), never the caller's.
  for (const [k, bucket] of buckets) {
    if (k === bucketKey) continue;
    const bucketStart = now - bucket.windowMs;
    if (
      bucket.times.length === 0 ||
      bucket.times[bucket.times.length - 1] <= bucketStart
    ) {
      buckets.delete(k);
    }
  }

  return { ok: true, remaining: limit - recent.length, retryAfterMs: 0 };
}
