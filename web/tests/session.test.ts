import { beforeEach, describe, expect, it } from "vitest";

import {
  assertSameOrigin,
  clearedSessionCookieOptions,
  openSession,
  readSessionCookie,
  SESSION_COOKIE,
  sealSession,
  sessionCookieOptions,
} from "@/lib/session";

// P4.S2 — the sealed-cookie crypto core. These are the tests that matter most in
// the whole slice: if `openSession` can ever be made to return a token it was not
// given, the BFF's entire session model is void.

const SECRET = "p4s2-test-secret-not-a-real-one";
/** Shaped like vocky's real token: `secrets.token_urlsafe(32)`, ~43 chars, no prefix. */
const TOKEN = "0GkQ3vJ8bYd1wZs5RfN7tXcA2eLmPqU9hVjK4oIyB6M";
const THIRTY_DAYS_MS = 30 * 24 * 60 * 60 * 1000;

beforeEach(() => {
  process.env.SESSION_SECRET = SECRET;
});

/** Flip the first character of segment `index` of `v1.<iv>.<ct>.<tag>`. */
function tamper(sealed: string, index: number): string {
  const parts = sealed.split(".");
  const seg = parts[index];
  parts[index] = (seg[0] === "A" ? "B" : "A") + seg.slice(1);
  return parts.join(".");
}

describe("sealSession / openSession", () => {
  it("round-trips the vocky token", () => {
    expect(openSession(sealSession(TOKEN))).toBe(TOKEN);
  });

  it("emits the versioned 4-part envelope and never the bare token", () => {
    const sealed = sealSession(TOKEN);
    expect(sealed.split(".")).toHaveLength(4);
    expect(sealed.startsWith("v1.")).toBe(true);
    expect(sealed).not.toContain(TOKEN);
  });

  it("uses a fresh IV per seal (same token → different ciphertext)", () => {
    expect(sealSession(TOKEN)).not.toBe(sealSession(TOKEN));
  });

  it("returns null for a tampered IV, ciphertext, or auth tag", () => {
    const sealed = sealSession(TOKEN);
    expect(openSession(tamper(sealed, 1))).toBeNull();
    expect(openSession(tamper(sealed, 2))).toBeNull();
    expect(openSession(tamper(sealed, 3))).toBeNull();
  });

  it("returns null for a malformed, empty, or wrong-version value", () => {
    expect(openSession(undefined)).toBeNull();
    expect(openSession("")).toBeNull();
    expect(openSession("garbage")).toBeNull();
    expect(openSession(sealSession(TOKEN).replace(/^v1\./, "v2."))).toBeNull();
  });

  it("returns null once the embedded exp has passed", () => {
    const now = Date.now();
    const sealed = sealSession(TOKEN, now);
    expect(openSession(sealed, now + THIRTY_DAYS_MS - 1_000)).toBe(TOKEN);
    expect(openSession(sealed, now + THIRTY_DAYS_MS + 1)).toBeNull();
  });

  it("returns null when the key changed (secret rotation invalidates sessions)", () => {
    const sealed = sealSession(TOKEN);
    process.env.SESSION_SECRET = `${SECRET}-rotated`;
    expect(openSession(sealed)).toBeNull();
  });

  it("returns null instead of throwing when SESSION_SECRET is unset", () => {
    const sealed = sealSession(TOKEN);
    delete process.env.SESSION_SECRET;
    expect(openSession(sealed)).toBeNull();
  });
});

describe("cookie options", () => {
  it("issues httpOnly / SameSite=Strict / path=/ with vocky's 30-day TTL", () => {
    expect(sessionCookieOptions()).toEqual({
      httpOnly: true,
      sameSite: "strict",
      secure: false, // NODE_ENV is not "production" under test
      path: "/",
      maxAge: THIRTY_DAYS_MS / 1000,
    });
  });

  it("clears with maxAge 0, keeping the other attributes", () => {
    expect(clearedSessionCookieOptions().maxAge).toBe(0);
    expect(clearedSessionCookieOptions().httpOnly).toBe(true);
  });
});

describe("readSessionCookie", () => {
  const withCookie = (cookie: string) =>
    new Request("http://localhost/x", { headers: { cookie } });

  it("finds the session cookie among others", () => {
    const req = withCookie(`a=1; ${SESSION_COOKIE}=sealed-value; b=2`);
    expect(readSessionCookie(req)).toBe("sealed-value");
  });

  it("returns undefined when absent or when there is no cookie header", () => {
    expect(readSessionCookie(withCookie("a=1"))).toBeUndefined();
    expect(readSessionCookie(new Request("http://localhost/x"))).toBeUndefined();
  });
});

describe("assertSameOrigin", () => {
  const withHeaders = (headers: Record<string, string>) =>
    new Request("http://localhost/x", { headers });

  it("accepts same-origin / none Sec-Fetch-Site, or a matching Origin host", () => {
    expect(assertSameOrigin(withHeaders({ "sec-fetch-site": "same-origin" }))).toBe(true);
    expect(assertSameOrigin(withHeaders({ "sec-fetch-site": "none" }))).toBe(true);
    expect(
      assertSameOrigin(
        withHeaders({ origin: "http://localhost:3030", host: "localhost:3030" }),
      ),
    ).toBe(true);
  });

  it("rejects cross-site, a mismatched Origin, and no origin signal at all", () => {
    expect(assertSameOrigin(withHeaders({ "sec-fetch-site": "cross-site" }))).toBe(false);
    expect(
      assertSameOrigin(
        withHeaders({ origin: "http://evil.example", host: "localhost:3030" }),
      ),
    ).toBe(false);
    expect(assertSameOrigin(withHeaders({}))).toBe(false);
  });
});
