import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

import { LANDING } from "@/content";

// P11.S6 — the three commands the landing invites a visitor to PASTE. Every other
// string on the page is prose a reader forgives; these are bytes a shell executes.
// A prettier reflow, a smart-quote substitution or a lost line continuation would
// still render, still typecheck, and still ship a command that silently does the
// wrong thing — so they are re-spelled here as literals. The install line is also
// checked against the installer it invokes, because the landing and
// `web/public/install.sh` are the two places it is written down and they must not
// drift apart.

const INSTALL_COMMAND = "curl -fsSL https://vocky.hi2vi.com/install.sh | bash";

describe("landing copy payloads", () => {
  it("spells the install command exactly as web/public/install.sh documents it", () => {
    expect(LANDING.heroInstall.command).toBe(INSTALL_COMMAND);
    expect(LANDING.quickstart.steps.install.command).toBe(INSTALL_COMMAND);

    const installer = readFileSync(
      new URL("../public/install.sh", import.meta.url),
      "utf8",
    );
    expect(installer).toContain(INSTALL_COMMAND);
  });

  it("keeps the ~/.zshenv block on three lines, quotes intact", () => {
    expect(LANDING.quickstart.steps.env.command).toBe(
      '# ~/.zshenv\nexport VOCKY_BASE_URL="https://vocky.hi2vi.com"\nexport VOCKY_API_TOKEN="vk_..."',
    );
  });

  it("keeps the verify command's literal \\n and its line continuations", () => {
    expect(LANDING.quickstart.steps.verify.command).toBe(
      "curl -sS -o /dev/null -w '%{http_code}\\n' \\\n" +
        '  -H "Authorization: Bearer $VOCKY_API_TOKEN" \\\n' +
        '  "$VOCKY_BASE_URL/api/feedback"',
    );
  });
});
