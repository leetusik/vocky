import { readFile } from "node:fs/promises";
import path from "node:path";

import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import {
  parseSkillFile,
  SkillPreview,
} from "@/components/landing/skill-preview";
import { LANDING } from "@/content";

// P11.S9 — the two floors of round 02's skill pane, asserted where they are
// actually decided: the SERVER HTML. Same `renderToStaticMarkup` technique as
// `snippet-ssr.test.ts` / `agent-quickstart-ssr.test.ts`; `SkillPreview` is an
// async server component, so it is awaited into an element first.
//
// 1. THE WHOLE FILE IS IN THE HTML (build-prompt §8, DECOMP2 correction 7).
//    §3.4's "collapsed shows the first 22 lines" reads like a truncation. It is
//    not one — truncating the server output would pass typecheck, lint, build
//    and every other check in this repo while silently breaking the no-JS floor
//    and making the no-JS footer a lie. The assertion below is on a string from
//    the file's LAST section, so a reintroduced truncation fails here.
// 2. THE COUNTS ARE COMPUTED, NEVER HARDCODED (§11.2). Both numbers are
//    re-derived from the file by this test, so a hardcode passes today and fails
//    the first time `SKILL.md` changes — which is the drift the rule exists for.

const SERVED = path.join(process.cwd(), "public", "SKILL.md");
const content = await readFile(SERVED, "utf8");
const { frontmatter, body, lines, bytes } = parseSkillFile(content);
const html = renderToStaticMarkup(await SkillPreview());

describe("SkillPreview server HTML", () => {
  it("splits the frontmatter losslessly", () => {
    expect(frontmatter + body).toBe(content);
    expect(frontmatter.endsWith("---")).toBe(true);
  });

  it("ships the WHOLE file, through its last section", () => {
    expect(html).toContain("# vocky-feedback");
    expect(html).toContain("## 8. Report back");
    expect(html).toContain(
      "Never claim a capture succeeded without a `202` response",
    );
  });

  it("renders no button at all pre-hydration, and the no-JS footer instead", () => {
    expect(html).not.toContain("<button");
    expect(html).toContain(
      LANDING.skill.preview.footerNoJs.replace("{lines}", String(lines)),
    );
    expect(html).toContain(LANDING.skill.preview.rawLabel);
  });

  it("keeps Download as a plain anchor to the served file", () => {
    expect(html).toContain('href="/SKILL.md"');
    expect(html).toContain("download=");
  });

  it("computes the line and byte counts from the file it just read", () => {
    expect(html).toContain(`${lines} lines · ${bytes} bytes`);
  });
});
