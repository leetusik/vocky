import { readFile } from "node:fs/promises";
import path from "node:path";

import { LANDING } from "@/content";

import { SkillCopyButton } from "./skill-copy-button";
import { SkillPreviewBody } from "./skill-preview-body";
import { SKILL_CONTROL_CLASS } from "./skill-shared";

/**
 * SkillPreview — the served `/SKILL.md`, rendered (round 02, build-prompt §3.4).
 *
 * A SERVER component that reads `web/public/SKILL.md` — the SERVED copy, the one
 * `scripts/skill_parity.py` gates byte-for-byte against
 * `skills/vocky-feedback/SKILL.md` — at request time. Two rules from the design
 * record are load-bearing and neither is a style preference:
 *
 * 1. **Never a pasted excerpt.** A hand-copied excerpt forks silently from the
 *    parity gate: CI stays green while the landing shows a file the site does not
 *    serve. The bytes on screen are the bytes read.
 * 2. **The counts are COMPUTED** (`content.split("\n").length - 1` and
 *    `Buffer.byteLength`), never hardcoded (§11.2) — hardcoding drifts the moment
 *    the skill is edited. `web/tests/skill-preview-ssr.test.ts` re-derives both
 *    from the file itself, so a hardcode fails CI the first time the file changes.
 *
 * The whole file is always in the HTML — see `skill-preview-body.tsx` for why
 * "collapsed" is a visual window and not a truncation.
 *
 * `page.tsx` is already dynamic (it reads the session cookie), so a request-time
 * `fs` read changes nothing about the build output: `/` was and stays `ƒ`. The
 * path is resolved from `process.cwd()`, which is the app root in dev, in
 * `next start`, and in the standalone runtime (`Dockerfile` copies `public/` to
 * `/app/public` and runs `node server.js` from `/app`).
 *
 * No syntax highlighting, no markdown rendering, no library (§3.4, `result.md`
 * §6.5b): the frontmatter band is the ONLY structural distinction in the pane.
 */

const { skill } = LANDING;
const { preview } = skill;

/**
 * The served copy, relative to the Next app root. Never the canonical one.
 *
 * Kept as two LITERAL segments at the `path.join` call site below rather than a
 * spread constant: Turbopack's file tracer reads that call statically, and an
 * unanalyzable path makes it fall back to tracing the whole project into the
 * standalone output ("Encountered unexpected file in NFT list").
 */
const SERVED_SKILL_DIR = "public";
const SERVED_SKILL_FILE = "SKILL.md";

export interface SkillFile {
  /** The frontmatter INCLUDING both `---` fences, no trailing newline. */
  frontmatter: string;
  /**
   * Everything after the closing fence, starting with the newline that
   * terminates it — so `frontmatter + body === content`, exactly.
   */
  body: string;
  /** Newline count — whatever the file measures today, and tomorrow. */
  lines: number;
  bytes: number;
}

/**
 * Split the file ONCE on the closing frontmatter `---` (§3.4) and measure it.
 *
 * The split is lossless by construction — `frontmatter + body` reproduces the
 * input byte for byte, which is what lets the pane's rendered `textContent` be
 * the clipboard payload (see `skill-copy-button.tsx`). A file with no
 * frontmatter degrades to "all body", never to an exception.
 *
 * `body` therefore begins with the blank line that follows the closing fence:
 * the pane shows the file's own line structure, unedited. See `result.md` for
 * why the 22-line window is counted over the pane (frontmatter band included),
 * which is the only reading under which §3.4's parenthetical, §6.5's inventory
 * and the footer's "first 22 of <n>" all agree.
 */
export function parseSkillFile(content: string): SkillFile {
  const lines = content.split("\n").length - 1;
  const bytes = Buffer.byteLength(content);
  const fence = "\n---\n";
  const closing = content.startsWith("---\n") ? content.indexOf(fence) : -1;
  if (closing === -1) return { frontmatter: "", body: content, lines, bytes };
  const end = closing + fence.length - 1; // keep the closing `---`, drop its newline
  return {
    frontmatter: content.slice(0, end),
    body: content.slice(end),
    lines,
    bytes,
  };
}

/** Read + parse the served file. Exported so tests exercise the real path. */
export async function readServedSkill(): Promise<SkillFile> {
  const content = await readFile(
    path.join(process.cwd(), SERVED_SKILL_DIR, SERVED_SKILL_FILE),
    "utf8",
  );
  return parseSkillFile(content);
}

/**
 * Substitute `{lines}` / `{bytes}` / `{collapsed}` in the `LANDING.skill.preview`
 * templates. The strings stay copy-as-data (§11.4); only the substitution is
 * code, and the values are the ones just measured.
 */
function fill(template: string, values: Record<string, number>): string {
  return template.replace(/\{(\w+)\}/g, (match, key: string) =>
    key in values ? String(values[key]) : match,
  );
}

export async function SkillPreview() {
  const { frontmatter, body, lines, bytes } = await readServedSkill();

  return (
    <div className="overflow-hidden rounded-xl border border-hairline bg-canvas">
      {/* Header — filename, the computed meta, then Copy + the no-JS Download. */}
      <div className="flex items-center justify-between gap-3 border-b border-hairline bg-surface py-[9px] pr-2.5 pl-3.5">
        <div className="flex min-w-0 items-baseline gap-2.5">
          <span className="font-mono text-caption text-charcoal">
            {preview.filename}
          </span>
          <span className="truncate font-mono text-[11px] text-steel">
            {fill(preview.meta, { lines, bytes })}
          </span>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <SkillCopyButton
            variant="compact"
            label={LANDING.snippet.copyLabel}
            copiedLabel={LANDING.snippet.copiedLabel}
            failedLabel={LANDING.snippet.copyFailedLabel}
            announcement={skill.copyAnnouncement}
          />
          {/* Plain anchor, always in the HTML — §8's locked no-JS survivor. */}
          <a href={skill.downloadHref} download className={SKILL_CONTROL_CLASS}>
            {preview.downloadLabel}
          </a>
        </div>
      </div>

      <SkillPreviewBody
        frontmatter={
          frontmatter === "" ? null : (
            <div className="border-b border-hairline bg-surface-archive px-4 py-3 font-mono text-[12px] leading-[1.6] break-words whitespace-pre-wrap text-steel">
              {frontmatter}
            </div>
          )
        }
        body={
          <pre className="px-4 py-3.5 font-mono text-[12.5px] leading-[1.62] break-words whitespace-pre-wrap text-slate">
            {body}
          </pre>
        }
        footerCollapsed={fill(preview.footerCollapsed, {
          collapsed: preview.collapsedLines,
          lines,
        })}
        footerExpanded={fill(preview.footerExpanded, { lines })}
        footerNoJs={fill(preview.footerNoJs, { lines })}
        expandLabel={preview.expandLabel}
        collapseLabel={preview.collapseLabel}
        rawLabel={preview.rawLabel}
        rawHref={preview.rawHref}
      />
    </div>
  );
}
