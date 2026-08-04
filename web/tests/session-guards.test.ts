import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { cookies } from "next/headers";

import {
  getSession,
  requireSession,
  SESSION_COOKIE,
  sealSession,
} from "@/lib/session";

// P4.S2 — the server guards. `next/headers` and `next/navigation` are mocked
// because both need a real request scope; the logic under test is "what does the
// guard do with a given cookie", which is exactly what matters at the auth
// boundary. Kept in its own file so the `next/*` mocks don't leak into the route
// tests, which need the real modules.

vi.mock("next/headers", () => ({ cookies: vi.fn() }));
vi.mock("next/navigation", () => ({
  redirect: (url: string) => {
    throw new Error(`REDIRECT:${url}`);
  },
}));

const TOKEN = "0GkQ3vJ8bYd1wZs5RfN7tXcA2eLmPqU9hVjK4oIyB6M";

beforeAll(() => {
  process.env.SESSION_SECRET = "p4s2-test-secret-not-a-real-one";
});

/** Point the mocked cookie store at `value` (or nothing at all). */
function withCookie(value: string | undefined) {
  const store = {
    get: (name: string) =>
      name === SESSION_COOKIE && value !== undefined ? { value } : undefined,
  };
  vi.mocked(cookies).mockResolvedValue(
    store as unknown as Awaited<ReturnType<typeof cookies>>,
  );
}

beforeEach(() => {
  vi.mocked(cookies).mockReset();
});

describe("getSession", () => {
  it("returns the unsealed vocky token for a valid cookie", async () => {
    withCookie(sealSession(TOKEN));
    await expect(getSession()).resolves.toBe(TOKEN);
  });

  it("returns null when the cookie is absent or tampered", async () => {
    withCookie(undefined);
    await expect(getSession()).resolves.toBeNull();

    withCookie(`${sealSession(TOKEN)}tampered`);
    await expect(getSession()).resolves.toBeNull();
  });
});

describe("requireSession", () => {
  it("returns the token — the bearer the (app) tree injects into vocky calls", async () => {
    withCookie(sealSession(TOKEN));
    await expect(requireSession()).resolves.toBe(TOKEN);
  });

  it("redirects to /login when there is no valid session", async () => {
    withCookie(undefined);
    await expect(requireSession()).rejects.toThrow("REDIRECT:/login");
  });
});
