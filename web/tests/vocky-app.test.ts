import {
  afterEach,
  beforeAll,
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";

import {
  createCredential,
  createOrgCredential,
  createProject,
  getFeedbackDetail,
  getProject,
  getProjectUsage,
  getUsage,
  listFeedback,
  listOrgCredentials,
  listProjects,
  revokeCredential,
  revokeOrgCredential,
} from "@/lib/vocky/app";
import type {
  VockyCredential,
  VockyFeedback,
  VockyProject,
  VockyUsage,
} from "@/lib/vocky/types";

// P4.S3/S4 — the `/app/*` client seam, driven against a STUBBED vocky (global
// fetch is replaced; the live round-trip is verified separately against a real
// vocky). What these lock down: the envelope unwrapping, that the bearer + path
// go out correctly, and the shapes that bite — the zero-project
// `daily_counts: []`, and the mint response, whose plaintext `key` must survive
// the call (it is the only copy that will ever exist). P10.S4 adds the
// org-level credential surface (`project_id: null`), additive beside the
// per-project one.

const TOKEN = "0GkQ3vJ8bYd1wZs5RfN7tXcA2eLmPqU9hVjK4oIyB6M";

const PROJECT: VockyProject = {
  id: "3f2a1b0c-0000-4d5e-8f9a-1b2c3d4e5f6a",
  name: "Support widget",
  tenant_id: "9a8b7c6d-1111-4e5f-9a0b-2c3d4e5f6a7b",
  created_at: "2026-07-16T00:00:00+00:00",
};

const CREDENTIAL: VockyCredential = {
  id: "5c4d3e2f-2222-4a1b-8c9d-0e1f2a3b4c5d",
  project_id: PROJECT.id,
  name: null,
  /** `key[:12]` — `"vk_"` + 9 chars. A display stub, never a usable key. */
  token_prefix: "vk_A1b2C3d4e",
  created_at: "2026-07-16T00:00:00+00:00",
  last_used_at: null,
  revoked_at: null,
};

/**
 * An ORG-LEVEL sibling of `CREDENTIAL` (P10.S4): identical shape, but
 * `project_id: null` — the org-key signal, and the only difference between a
 * project-bound and an org-level credential on the wire.
 */
const ORG_CREDENTIAL: VockyCredential = {
  ...CREDENTIAL,
  id: "6d5e4f3a-4444-4b2c-9d0e-1f2a3b4c5d6e",
  project_id: null,
};

beforeAll(() => {
  process.env.VOCKY_API_BASE_URL = "http://vocky.test:8000";
});

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn());
});
afterEach(() => {
  vi.unstubAllGlobals();
});

/**
 * Stub vocky's response. Must build a FRESH `Response` per call
 * (`mockImplementation`, not `mockResolvedValue`): a body can only be consumed
 * once, so a shared instance would make every call after the first throw.
 */
function stubVocky(status: number, body: unknown) {
  vi.mocked(fetch).mockImplementation(() =>
    Promise.resolve(
      new Response(body === undefined ? null : JSON.stringify(body), {
        status,
        headers: { "content-type": "application/json" },
      }),
    ),
  );
}

/** The `[url, init]` of the single fetch the call under test made. */
function lastCall() {
  const [url, init] = vi.mocked(fetch).mock.calls[0] as [string, RequestInit];
  return { url, init, headers: init.headers as Record<string, string> };
}

describe("listProjects", () => {
  it("unwraps {projects} and sends the bearer to /app/projects", async () => {
    stubVocky(200, { projects: [PROJECT] });

    await expect(listProjects(TOKEN)).resolves.toEqual([PROJECT]);

    const { url, init, headers } = lastCall();
    expect(url).toBe("http://vocky.test:8000/app/projects");
    expect(init.method).toBe("GET");
    expect(headers.Authorization).toBe(`Bearer ${TOKEN}`);
  });

  it("yields [] for a tenant with no projects, and for a missing key", async () => {
    stubVocky(200, { projects: [] });
    await expect(listProjects(TOKEN)).resolves.toEqual([]);

    stubVocky(200, {});
    await expect(listProjects(TOKEN)).resolves.toEqual([]);
  });

  it("passes distinct projects through keyed on id, not name", async () => {
    // P10.S1 added `UNIQUE(tenant_id, name)`, so vocky itself never returns two
    // same-named projects for one tenant — this test no longer asserts a
    // duplicate-name scenario. What it still locks down: the client trusts
    // `id`, not `name`, as each row's identity (unaffected either way).
    const other: VockyProject = {
      ...PROJECT,
      id: "twin-id",
      name: "Another project",
    };
    stubVocky(200, { projects: [PROJECT, other] });

    const projects = await listProjects(TOKEN);
    expect(projects).toHaveLength(2);
    expect(new Set(projects.map((p) => p.id)).size).toBe(2);
  });
});

describe("createProject", () => {
  it("POSTs {name} and unwraps {project}", async () => {
    stubVocky(201, { project: PROJECT });

    await expect(createProject(TOKEN, "Support widget")).resolves.toEqual(
      PROJECT,
    );

    const { url, init, headers } = lastCall();
    expect(url).toBe("http://vocky.test:8000/app/projects");
    expect(init.method).toBe("POST");
    expect(init.body).toBe(JSON.stringify({ name: "Support widget" }));
    expect(headers.Authorization).toBe(`Bearer ${TOKEN}`);
    expect(headers["Content-Type"]).toBe("application/json");
  });

  it("throws an ApiError carrying the status on a 400", async () => {
    stubVocky(400, { detail: "name: must not be blank" });

    await expect(createProject(TOKEN, "   ")).rejects.toMatchObject({
      name: "ApiError",
      status: 400,
    });
  });
});

describe("getUsage", () => {
  it("calls /app/usage BARE (vocky defaults the window to 30 days)", async () => {
    stubVocky(200, {
      window: { start_ingested_at: "a", end_ingested_at: "b" },
      totals: { total: 0, liked: 0, disliked: 0, unrated: 0 },
      daily_counts: [],
      projects: [],
    });

    await getUsage(TOKEN);

    const { url } = lastCall();
    expect(url).toBe("http://vocky.test:8000/app/usage");
  });

  it("passes the payload through, including the zero-project daily_counts: []", async () => {
    // The empty-tenant shape: vocky short-circuits to zeroed metrics and does NOT
    // zero-fill, so the series is absent entirely rather than 31 zero buckets.
    const zeroTenant: VockyUsage = {
      window: {
        start_ingested_at: "2026-06-16T09:31:02+00:00",
        end_ingested_at: "2026-07-16T09:31:02+00:00",
      },
      totals: { total: 0, liked: 0, disliked: 0, unrated: 0 },
      daily_counts: [],
      projects: [],
    };
    stubVocky(200, zeroTenant);

    await expect(getUsage(TOKEN)).resolves.toEqual(zeroTenant);
  });

  it("passes through a populated series with its date-only `day` buckets", async () => {
    stubVocky(200, {
      window: {
        start_ingested_at: "2026-06-16T09:31:02+00:00",
        end_ingested_at: "2026-07-16T09:31:02+00:00",
      },
      totals: { total: 3, liked: 2, disliked: 1, unrated: 0 },
      daily_counts: [
        { day: "2026-06-16", total: 1, liked: 1, disliked: 0, unrated: 0 },
        { day: "2026-06-17", total: 2, liked: 1, disliked: 1, unrated: 0 },
      ],
      projects: [
        { id: PROJECT.id, name: PROJECT.name, created_at: PROJECT.created_at },
      ],
    });

    const usage = await getUsage(TOKEN);
    expect(usage.totals.total).toBe(3);
    expect(usage.daily_counts.map((d) => d.day)).toEqual([
      "2026-06-16",
      "2026-06-17",
    ]);
    // The narrower usage serializer: no `tenant_id`, hence its own type.
    expect(usage.projects[0]).not.toHaveProperty("tenant_id");
  });
});

// ── /app/projects/{id} — the per-project drill-down (P4.S4) ─────────────────

describe("getProject", () => {
  it("unwraps {project} from /app/projects/{id}", async () => {
    stubVocky(200, { project: PROJECT });

    await expect(getProject(TOKEN, PROJECT.id)).resolves.toEqual(PROJECT);

    const { url, init, headers } = lastCall();
    expect(url).toBe(`http://vocky.test:8000/app/projects/${PROJECT.id}`);
    expect(init.method).toBe("GET");
    expect(headers.Authorization).toBe(`Bearer ${TOKEN}`);
  });

  it("throws ApiError(404) for a missing OR cross-tenant id (vocky never 403s)", async () => {
    stubVocky(404, { detail: "project not found" });

    await expect(getProject(TOKEN, PROJECT.id)).rejects.toMatchObject({
      name: "ApiError",
      status: 404,
    });
  });
});

describe("createCredential", () => {
  it("returns BOTH the credential and the show-once plaintext key", async () => {
    const key = "vk_A1b2C3d4e5F6g7H8i9J0k1L2m3N4o5P6";
    stubVocky(201, { credential: CREDENTIAL, key });

    // The whole point of the envelope: unwrapping to `credential` would discard
    // the only copy of the key that will ever exist.
    await expect(createCredential(TOKEN, PROJECT.id)).resolves.toEqual({
      credential: CREDENTIAL,
      key,
    });

    const { url, init, headers } = lastCall();
    expect(url).toBe(
      `http://vocky.test:8000/app/projects/${PROJECT.id}/credentials`,
    );
    expect(init.method).toBe("POST");
    // An omitted name sends `{}` — vocky defaults it to null — not `{name: null}`.
    expect(init.body).toBe("{}");
    expect(headers.Authorization).toBe(`Bearer ${TOKEN}`);
  });

  it("sends {name} when one is given", async () => {
    stubVocky(201, {
      credential: { ...CREDENTIAL, name: "Production" },
      key: "vk_zzz",
    });

    const minted = await createCredential(TOKEN, PROJECT.id, "Production");
    expect(minted.credential.name).toBe("Production");
    expect(lastCall().init.body).toBe(JSON.stringify({ name: "Production" }));
  });
});

describe("revokeCredential", () => {
  it("DELETEs the credential and resolves undefined on vocky's 204", async () => {
    stubVocky(204, undefined);

    await expect(
      revokeCredential(TOKEN, PROJECT.id, CREDENTIAL.id),
    ).resolves.toBeUndefined();

    const { url, init, headers } = lastCall();
    expect(url).toBe(
      `http://vocky.test:8000/app/projects/${PROJECT.id}/credentials/${CREDENTIAL.id}`,
    );
    expect(init.method).toBe("DELETE");
    expect(init.body).toBeUndefined();
    expect(headers.Authorization).toBe(`Bearer ${TOKEN}`);
  });
});

// ── /app/credentials — the org-level key surface (P10.S4) ───────────────────

describe("listOrgCredentials", () => {
  it("unwraps {credentials} and sends the bearer to /app/credentials", async () => {
    stubVocky(200, { credentials: [ORG_CREDENTIAL] });

    await expect(listOrgCredentials(TOKEN)).resolves.toEqual([ORG_CREDENTIAL]);

    const { url, init, headers } = lastCall();
    expect(url).toBe("http://vocky.test:8000/app/credentials");
    expect(init.method).toBe("GET");
    expect(headers.Authorization).toBe(`Bearer ${TOKEN}`);
  });

  it("tolerates a missing envelope key, yielding []", async () => {
    stubVocky(200, {});
    await expect(listOrgCredentials(TOKEN)).resolves.toEqual([]);
  });
});

describe("createOrgCredential", () => {
  it("returns BOTH the credential and the show-once plaintext key, whole", async () => {
    const key = "vk_Z9y8X7w6V5u4T3s2R1q0P9o8N7m6L5k4";
    stubVocky(201, { credential: ORG_CREDENTIAL, key });

    // Same envelope discipline as `createCredential`: unwrapping to
    // `credential` would discard the only copy of the key that will ever exist.
    await expect(createOrgCredential(TOKEN)).resolves.toEqual({
      credential: ORG_CREDENTIAL,
      key,
    });

    const { url, init, headers } = lastCall();
    expect(url).toBe("http://vocky.test:8000/app/credentials");
    expect(init.method).toBe("POST");
    // An omitted name sends `{}` — vocky defaults it to null — not `{name: null}`.
    expect(init.body).toBe("{}");
    expect(headers.Authorization).toBe(`Bearer ${TOKEN}`);
  });

  it("sends {name} when one is given", async () => {
    stubVocky(201, {
      credential: { ...ORG_CREDENTIAL, name: "Mobile app" },
      key: "vk_zzz",
    });

    const minted = await createOrgCredential(TOKEN, "Mobile app");
    expect(minted.credential.name).toBe("Mobile app");
    expect(minted.credential.project_id).toBeNull();
    expect(lastCall().init.body).toBe(JSON.stringify({ name: "Mobile app" }));
  });
});

describe("revokeOrgCredential", () => {
  it("DELETEs the encoded credential id and resolves undefined on vocky's 204", async () => {
    stubVocky(204, undefined);

    await expect(
      revokeOrgCredential(TOKEN, ORG_CREDENTIAL.id),
    ).resolves.toBeUndefined();

    const { url, init, headers } = lastCall();
    expect(url).toBe(
      `http://vocky.test:8000/app/credentials/${ORG_CREDENTIAL.id}`,
    );
    expect(init.method).toBe("DELETE");
    expect(init.body).toBeUndefined();
    expect(headers.Authorization).toBe(`Bearer ${TOKEN}`);
  });
});

describe("getProjectUsage", () => {
  it("calls /app/projects/{id}/usage BARE and passes credentials through", async () => {
    // A capture-less project: vocky zero-FILLS (no zero-project short-circuit
    // here, unlike /app/usage), so `daily_counts` is never `[]` on this route.
    stubVocky(200, {
      window: {
        start_ingested_at: "2026-06-16T09:31:02+00:00",
        end_ingested_at: "2026-07-16T09:31:02+00:00",
      },
      totals: { total: 0, liked: 0, disliked: 0, unrated: 0 },
      daily_counts: [
        { day: "2026-06-16", total: 0, liked: 0, disliked: 0, unrated: 0 },
        { day: "2026-06-17", total: 0, liked: 0, disliked: 0, unrated: 0 },
      ],
      credentials: [CREDENTIAL],
    });

    const usage = await getProjectUsage(TOKEN, PROJECT.id);

    expect(lastCall().url).toBe(
      `http://vocky.test:8000/app/projects/${PROJECT.id}/usage`,
    );
    expect(usage.daily_counts.every((d) => d.total === 0)).toBe(true);
    // No `projects` list here — this payload carries `credentials` instead, via
    // the SAME serializer as the standalone list route, which is why the page
    // needs no separate credentials call.
    expect(usage).not.toHaveProperty("projects");
    expect(usage.credentials).toEqual([CREDENTIAL]);
    // Active ⇔ revoked_at === null; there is no `status` field to read.
    expect(usage.credentials[0]).not.toHaveProperty("status");
  });
});

// ── /app/feedback — cross-project read + search (P4.S5) ─────────────────────
// The app's first query-string caller, so these lock down the URL BUILDING as
// much as the unwrapping: the two shapes that bite are `next_cursor`'s absence
// and the blank params vocky 400s on.

const FEEDBACK: VockyFeedback = {
  id: "7e6d5c4b-3333-4f2a-9b8c-7d6e5f4a3b2c",
  message: "결제 오류가 있어요",
  source_product: "checkout",
  feedback_value: 2,
  comment: null,
  channel: null,
  source_integration: null,
  conversation_id: null,
  session_id: null,
  user_id: null,
  // WHO recorded it, orthogonal to `trigger_type` (WHY). `null` = unspecified.
  recorded_by: "agent",
  trigger_type: "dislike",
  trigger_message: null,
  trigger_metadata: {},
  target_type: null,
  target_id: null,
  target_role: null,
  target_text: null,
  event_at: null,
  ingested_at: "2026-07-16T09:31:02Z",
  tags: [],
  messages: [],
  used_context: [],
  source_metadata: {},
  attributes: {},
  project_id: PROJECT.id,
};

describe("listFeedback", () => {
  it("calls /app/feedback BARE when no params are given", async () => {
    stubVocky(200, { records: [FEEDBACK] });

    await expect(listFeedback(TOKEN)).resolves.toEqual({
      records: [FEEDBACK],
    });

    const { url, headers } = lastCall();
    // No trailing `?` — the bare path, exactly as the other GETs send it.
    expect(url).toBe("http://vocky.test:8000/app/feedback");
    expect(headers.Authorization).toBe(`Bearer ${TOKEN}`);
  });

  it("encodes params (spaces as +) and omits every blank one", async () => {
    stubVocky(200, { records: [] });

    await listFeedback(TOKEN, {
      q: "결제 오류",
      project_id: PROJECT.id,
      feedback_value: 2,
      // URL-driven only: no rendered control, but it must reach vocky.
      recorded_by: "agent",
      // Blank/undefined must be OMITTED, not sent: vocky 400s on a blank `tag`
      // or `cursor`, and a GET filter form submits its empty fields.
      tag: "",
      cursor: "   ",
      channel: undefined,
    });

    // URLSearchParams does all the escaping — `+` for the space (Starlette
    // decodes it back) and one layer of percent-encoding for the Korean.
    expect(lastCall().url).toBe(
      "http://vocky.test:8000/app/feedback" +
        `?q=%EA%B2%B0%EC%A0%9C+%EC%98%A4%EB%A5%98&project_id=${PROJECT.id}&feedback_value=2` +
        "&recorded_by=agent",
    );
  });

  it("surfaces next_cursor when vocky sends one", async () => {
    stubVocky(200, { records: [FEEDBACK], next_cursor: "eyJpZCI6ImEifQ" });

    const page = await listFeedback(TOKEN, { limit: 1 });
    expect(page.next_cursor).toBe("eyJpZCI6ImEifQ");
    expect(lastCall().url).toBe("http://vocky.test:8000/app/feedback?limit=1");
  });

  it("yields next_cursor === undefined when the key is OMITTED (never null)", async () => {
    // The shape that bites: vocky DROPS the key on the last page rather than
    // sending null, so a `!== null` test would page forever.
    stubVocky(200, { records: [FEEDBACK] });

    const page = await listFeedback(TOKEN);
    expect(page.next_cursor).toBeUndefined();
    expect("next_cursor" in page).toBe(false);
  });
});

describe("getFeedbackDetail", () => {
  it("unwraps the {record} envelope with its comments + attachments", async () => {
    // Wrapped, unlike the list's bare `records` — the asymmetry this unwraps.
    stubVocky(200, {
      record: {
        ...FEEDBACK,
        comments: [
          {
            id: "c1",
            author: null,
            body: "refunded",
            created_at: "2026-07-16T10:00:00Z",
          },
        ],
        attachments: [
          {
            id: "a1",
            content_type: "image/png",
            byte_size: 1024,
            filename: "shot.png",
            created_at: "2026-07-16T10:00:00Z",
            url: `/app/feedback/${FEEDBACK.id}/attachments/a1`,
          },
        ],
      },
    });

    const record = await getFeedbackDetail(TOKEN, FEEDBACK.id);
    expect(record.message).toBe(FEEDBACK.message);
    expect(record.comments[0].author).toBeNull();
    // vocky-relative and bearer-gated — the page proxies it, never links it.
    expect(record.attachments[0].url).toBe(
      `/app/feedback/${FEEDBACK.id}/attachments/a1`,
    );
    expect(lastCall().url).toBe(
      `http://vocky.test:8000/app/feedback/${FEEDBACK.id}`,
    );
  });

  it("throws ApiError(404) for a missing OR cross-tenant id (vocky never 403s)", async () => {
    stubVocky(404, { detail: "feedback not found" });

    await expect(getFeedbackDetail(TOKEN, FEEDBACK.id)).rejects.toMatchObject({
      name: "ApiError",
      status: 404,
    });
  });
});
