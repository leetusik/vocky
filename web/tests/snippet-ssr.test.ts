import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { Snippet, type SnippetCopy } from "@/components/ui/snippet";
import { LANDING } from "@/content";

// P11.S6 — the no-JS floor (round 02 build-prompt §8) asserted where it is
// actually decided: the SERVER HTML. A visitor without JavaScript must see the
// snippet's selectable text and NO copy button at all — never a present-but-inert
// one — so the button is gated behind hydration. `renderToStaticMarkup` reaches
// that exact frame without a DOM, which is why this is testable in the Node-env
// suite at all; everything after hydration (the 2s revert, the Range/Selection
// fallback, the live region) still needs a browser and is S10's fidelity pass.

const COPY: SnippetCopy = {
  ...LANDING.snippet,
  announcement: LANDING.heroInstall.copyAnnouncement,
};

const render = (props: Partial<Parameters<typeof Snippet>[0]> = {}) =>
  renderToStaticMarkup(
    createElement(Snippet, {
      command: LANDING.heroInstall.command,
      copy: COPY,
      ...props,
    }),
  );

describe("Snippet server HTML", () => {
  it("ships the command as selectable text with no copy button", () => {
    const html = render();
    expect(html).not.toContain("<button");
    expect(html).toContain(LANDING.heroInstall.command);
  });

  it("keeps the command on one line at any width", () => {
    expect(render()).toContain("min-w-0 flex-1 overflow-x-auto");
    expect(render()).toContain("whitespace-pre");
  });

  it("colours block comment lines without removing them from the copy", () => {
    const html = render({
      variant: "block",
      command: LANDING.quickstart.steps.env.command,
      label: LANDING.quickstart.steps.env.snippetLabel,
    });
    expect(html).toContain('<span class="text-trust-sage"># ~/.zshenv</span>');
    expect(html).toContain("export VOCKY_API_TOKEN=&quot;vk_...&quot;");
  });
});
