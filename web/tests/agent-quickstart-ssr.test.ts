import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { AgentQuickstart } from "@/components/landing/agent-quickstart";
import { LANDING } from "@/content";

// P11.S8 — the no-JS floor (build-prompt §8) held for the WHOLE section, not
// just one Snippet in isolation: four copy-button islands compose here
// (install, env, verify, capture), so this is the cheapest CI proof that none
// of them renders a button pre-hydration while every command still ships as
// selectable server-rendered text. Same `renderToStaticMarkup` technique as
// `snippet-ssr.test.ts`.
describe("AgentQuickstart server HTML", () => {
  const html = renderToStaticMarkup(createElement(AgentQuickstart));

  it("ships no copy button across all four snippets, pre-hydration", () => {
    expect(html).not.toContain("<button");
  });

  it("still ships every step's command as selectable text", () => {
    expect(html).toContain(LANDING.quickstart.steps.install.command);
    expect(html).toContain("VOCKY_API_TOKEN");
    expect(html).toContain("%{http_code}");
    expect(html).toContain("acme-web");
  });

  it("renders the #quickstart anchor and the peer link to #skill", () => {
    expect(html).toContain('id="quickstart"');
    expect(html).toContain('href="#skill"');
  });
});
