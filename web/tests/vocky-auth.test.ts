import { describe, expect, it } from "vitest";

import { activeTenant, normalizeAuthResponse } from "@/lib/vocky/auth";
import type { VockyTenant, VockyUser } from "@/lib/vocky/types";

// P4.S2 — vocky's signup/login TENANT ASYMMETRY is the one shape mismatch the BFF
// has to absorb: signup answers `tenant` (singular), login answers `tenants[]`.
// Both must collapse to one `{token, user, tenant}` so nothing downstream branches
// on which call produced the session.

const USER: VockyUser = {
  id: "6f1d2c3b-0000-4a5b-8c9d-1e2f3a4b5c6d",
  email: "owner@example.com",
  created_at: "2026-07-16T00:00:00+00:00",
};
const TENANT: VockyTenant = {
  id: "9a8b7c6d-1111-4e5f-9a0b-2c3d4e5f6a7b",
  name: "owner's workspace",
  created_at: "2026-07-16T00:00:00+00:00",
};
const TOKEN = "0GkQ3vJ8bYd1wZs5RfN7tXcA2eLmPqU9hVjK4oIyB6M";

describe("normalizeAuthResponse", () => {
  it("maps signup's `tenant` and login's `tenants[]` to an identical session", () => {
    const fromSignup = normalizeAuthResponse({
      token: TOKEN,
      user: USER,
      tenant: TENANT,
    });
    const fromLogin = normalizeAuthResponse({
      token: TOKEN,
      user: USER,
      tenants: [TENANT],
    });

    expect(fromSignup).toEqual({ token: TOKEN, user: USER, tenant: TENANT });
    expect(fromLogin).toEqual(fromSignup);
  });

  it("treats tenants[0] as the active tenant (matching vocky's require_user)", () => {
    const second: VockyTenant = { ...TENANT, id: "second", name: "second" };
    expect(
      normalizeAuthResponse({
        token: TOKEN,
        user: USER,
        tenants: [TENANT, second],
      }).tenant,
    ).toEqual(TENANT);
  });
});

describe("activeTenant", () => {
  it("yields null rather than throwing when the user has no tenant", () => {
    expect(activeTenant({})).toBeNull();
    expect(activeTenant({ tenants: [] })).toBeNull();
  });
});
