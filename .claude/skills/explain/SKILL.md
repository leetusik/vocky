---
name: explain
description: Research a topic, a code change, or a general (non-code) question and save a single self-contained interactive HTML explainer — for code, Background, Intuition, Code, a cited "Best practices & next steps" section and a 5-question quiz; for general research, a free-form outline fitted to the question with every claim cited, a Sources list and the quiz — into your personal knowledge base, setting one up on first use if none is configured. Use ONLY when the operator wants an explanation persisted as a document (explain and document, write this up, document what we just changed) — NOT for ordinary questions that deserve a normal chat answer.
argument-hint: <topic, change-ref or question> [general] [here] [research|no-research]
allowed-tools: Read, Grep, Glob, Write, Bash(curl -sS --max-time 5:*), Bash(curl -sS --max-time 30:*), Bash(python3 -c:*), Bash(command -v:*), Bash(knowledge:*), Bash(uv tool install:*), Bash(mkdir -p:*), Bash(rm -f:*), WebSearch, WebFetch, Bash(git diff:*), Bash(git log:*), Bash(git show:*)
disable-model-invocation: true
---

# explain

<!-- Vendored from leetusik/knowledge @ d0c2c38 — plugin/skills/explain/SKILL.md.
     De-plugin-ified for this workspace: step 2a's self-service onboarding replaces the
     plugin-only setup command, and the offline local-file fallback is removed. Since
     workspace v31 this workspace ships Claude Code only, so upstream's two Codex notes
     (the `workspace-write` network caveat in step 2a and the `<noreply@openai.com>`
     attribution parenthetical) are dropped too.
     Workspace-local addition (workspace v52, not upstream): research mode — a third mode for
     general, non-code research with a free-form outline (steps 1, 3, 4.2a, 7).
     Nothing syncs the two copies — re-vendor by hand, and keep research mode when you do. -->

Produce an educational explainer — a single **self-contained interactive HTML page**
(spec in step 4) — about a topic **or a code change** in the current repo or
conversation, **or a general research question** that is not about this repo's code, and file it in **your** personal knowledge base (configured on this
machine; step 2a sets one up on first use if none exists). This skill produces a
**saved document**: if the operator only asked a question and did not ask for anything
to be saved, answer normally in chat and write no files.

There is one output format everywhere: all three modes — explaining a topic, explaining a
code change/diff/phase, and general research — emit the same kind of interactive HTML
explainer. Only research mode trades the fixed code-shaped outline for a free-form one.

## 1. Resolve the topic and the mode

**Arguments** = the skill arguments: $ARGUMENTS. First, strip any of these **trailing
standalone words** (they compose — any combination, any order) and remember each flag:

- `general` → MODE=research (force research mode, skipping the detection below).
- `here` → PROJECT_COPY=yes (also write a copy into the current project, step 6).
- `research` → force the "Best practices & next steps" web-research section **ON** (skip
  the judgment gate in step 3; still degrade gracefully offline).
- `no-research` → force that section **OFF** (run no web research this time).

Strip every trailing flag word before using the rest as the topic. `research` and
`no-research` are mutually exclusive; if both appear, the last one wins. If neither
appears, the section is **default-on through the judgment gate** (step 3).

**What remains after stripping is the TOPIC / change-ref.** Decide the MODE from it:

- **Change mode** — the arguments name or point at a code change: a diff, a branch, a
  PR, a commit or commit range, a phase, or a phrase like "what we just changed" / "this
  PR" / "the last commit". Also change mode when the arguments are **empty and** the
  conversation just completed a concrete code change (a review, a merge, a fix you just
  made) — i.e. "document what we just changed".
- **Topic mode** — anything else: the arguments name a concept, tool, subsystem, or file
  to explain. Also topic mode when the arguments are empty and the recent conversation is
  an analysis/discussion rather than a change you just made.
- **Research mode** — the subject is a question about the world rather than this repo's
  code: a market, a technology landscape, a product or vendor comparison, a domain
  concept, a decision with options, the findings of a research phase or slice. Detect it
  when the subject has **no meaningful grounding in this repo's code** — a "Code" section
  would be empty or forced. `general` forces it. A workspace phase or slice whose work is
  research (a `research` slice, a phase whose intent is a question rather than a change)
  is research mode, not change mode; a phase that changed code stays change mode.
- **Empty and none fits** → ask the user what to explain (a topic, a change or a
  question), then continue.

Topic and change mode produce the **same document**, with the same fixed content sections
(§4.2); only the lens differs, and step 3 says how. Research mode keeps the same page
contract (§4.1) but writes a **free-form outline** fitted to the question (§4.2a).

## 2. Resolve the knowledge base configuration

The knowledge base is no longer hardcoded to one machine — resolve it from config.
**Run this one command** and read its `KEY=VALUE` output; do not reason about the
resolution rules by hand:

    python3 -c '
    import json, os
    home = os.path.expanduser("~")
    def env(k):
        v = os.environ.get(k)
        return v if v else None
    env_root = env("KB_ROOT")
    env_api = env("KB_API_BASE_URL")
    env_token = env("KB_API_TOKEN")
    xdg = os.environ.get("XDG_CONFIG_HOME") or os.path.join(home, ".config")
    cfg_path = os.path.join(xdg, "knowledge-kb", "config.json")
    cfg = None
    if os.path.isfile(cfg_path):
        try:
            cfg = json.load(open(cfg_path))
        except Exception as e:
            print("KB_STATUS=error")
            print("KB_ERROR=cannot parse " + cfg_path + ": " + str(e))
            raise SystemExit(0)
    legacy_root = os.path.join(home, "projects", "personal", "knowledge")
    legacy = os.path.isfile(os.path.join(legacy_root, "mkdocs.yml"))
    if cfg is None and not legacy and not (env_root or env_api or env_token):
        print("KB_STATUS=unconfigured")
        raise SystemExit(0)
    if cfg is not None:
        b_root = cfg.get("kb_root")
        api = cfg.get("api") or {}
        b_api = api.get("base_url")
        b_token = api.get("token")
        site = cfg.get("site") or {}
        b_site = site.get("base_url")
    elif legacy:
        b_root, b_api, b_token, b_site = legacy_root, "http://localhost:8766", None, "http://localhost:8765"
    else:
        b_root = b_api = b_token = b_site = None
    kb_root = env_root or b_root or ""
    api_base = env_api or b_api or "http://localhost:8766"
    token = env_token or b_token or ""
    site_base = b_site or "http://localhost:8765"
    kb_root = os.path.expanduser(kb_root) if kb_root else ""
    local_fallback = bool(kb_root) and os.path.isfile(os.path.join(kb_root, "mkdocs.yml"))
    print("KB_STATUS=configured")
    print("KB_ROOT=" + kb_root)
    print("KB_API_BASE_URL=" + api_base)
    print("KB_API_TOKEN=" + token)
    print("KB_SITE_BASE_URL=" + site_base)
    print("KB_LOCAL_FALLBACK=" + ("yes" if local_fallback else "no"))
    '

Read the output:

- `KB_STATUS=unconfigured` → go to **step 2a** and set one up. Write no files anywhere
  until it succeeds.
- `KB_STATUS=error` → **STOP** and report the `KB_ERROR` line (the config file exists
  but is unreadable); do not fall back to another source, and do not run step 2a — a
  broken config is a thing to fix, not to overwrite.
- `KB_STATUS=configured` → remember these values for the steps below:
  - `KB_API_BASE_URL` — the document API base (used in step 5).
  - `KB_API_TOKEN` — a bearer token, or empty (empty = no token; used in step 5).
  - `KB_SITE_BASE_URL` — the viewer base (used in step 7).
  - `KB_ROOT` and `KB_LOCAL_FALLBACK` are **unused** by this skill. A hosted account has
    no `kb_root`, and there is no local-file fallback: if the API is unreachable the save
    fails and is reported as failed. Ignore both values.

What the command resolves, for reference (per-key, highest priority first):

1. **Env overrides** — `KB_ROOT`, `KB_API_BASE_URL`, `KB_API_TOKEN`, each overriding
   just its own key.
2. **Config file** — `$XDG_CONFIG_HOME/knowledge-kb/config.json` (default
   `~/.config/knowledge-kb/config.json`), written by `knowledge init` (step 2a), with
   keys `kb_root`, `api.base_url`, `api.token`, `site.base_url`. Omitted keys default to
   `api.base_url` → `http://localhost:8766`, `site.base_url` → `http://localhost:8765`,
   token → none; `kb_root` is absent for a hosted account, which is the normal shape.
3. **Legacy convention** — if `~/projects/personal/knowledge/mkdocs.yml` exists, use
   `kb_root=~/projects/personal/knowledge`, `api.base_url=http://localhost:8766`,
   `site.base_url=http://localhost:8765`, no token. (Keeps self-hosted machines that
   predate the CLI working.)
4. **Nothing** → unconfigured (step 2a).

## 2a. Set up a knowledge base (only when KB_STATUS=unconfigured)

Reached only when nothing is configured. Write no files anywhere until substep 6 below succeeds.

**Ask first — this creates an account on an external service.** State plainly what you
are about to do: create (or log into) an account on the hosted knowledge service at
`https://knowledge.hi2vi.com`, install the `knowledge` CLI on this machine, and write an
org API key to `~/.config/knowledge-kb/config.json` (mode 0600). Then ask for **one**
thing: the email address to use.

The hosted service is the recommended path — offer it as the default, not as one of two
options. If the operator declines, STOP with a single sentence: this skill points at any
other knowledge base, self-hosted or otherwise, via the `KB_API_BASE_URL` and
`KB_API_TOKEN` env vars. Do not walk them through self-hosting.

1. `command -v knowledge` — if it resolves, skip to 3.
2. **Install the CLI.** Requires Python 3.12+. Check `command -v uv`:
   - uv present → `uv tool install git+https://github.com/leetusik/knowledge#subdirectory=cli`
   - uv absent → say so and get an explicit yes before running
     `curl -fsSL https://knowledge.hi2vi.com/install.sh | bash` (it installs uv first).
     Piping a remote script into a shell is a bigger ask than a tool install — never run
     it unasked.

   `uv tool install` puts the binary in `~/.local/bin`, which may not be on this shell's
   PATH. If `command -v knowledge` still fails afterwards, use `~/.local/bin/knowledge`
   for the rest of this step and tell the operator to run `uv tool update-shell`. If
   neither install works, STOP and report — do not fall back.
3. **Generate a password off argv.** A password must never be a shell argument: argv is
   world-readable via `ps` and is kept in shell history.

       mkdir -p /tmp/kb-onboard
       python3 -c 'import secrets,string,pathlib; a=string.ascii_letters+string.digits+"-_"; pathlib.Path("/tmp/kb-onboard/pw.txt").write_text("".join(secrets.choice(a) for _ in range(24)))'

   Read that file — you must show the password to the operator in substep 6.
4. **Onboard.** `knowledge init` is idempotent: it signs up, or on a 409 (email already
   registered) logs in instead, reuses the project, and mints or reuses an **org-level**
   key that authorizes every project — one key, all repos.

       knowledge init --email <EMAIL> --password-stdin < /tmp/kb-onboard/pw.txt

   - exit 0 → continue.
   - login failure (the email is registered with a different password) → do **not** retry
     signup. Tell the operator the email already has an account and ask for its password;
     write it to the same temp file with the Write tool (never as an argument) and re-run
     the identical command. **At most one retry.**
   - any other non-zero exit → STOP and report stderr verbatim.
5. `rm -f /tmp/kb-onboard/pw.txt` — always, on every path, including failures.
6. **Verify, then resume.** `knowledge config` exits 0 only when a usable knowledge base
   is configured. It prints the same `KB_*` keys but **redacts the token**, so it is a
   probe, never a value source: re-run the step 2 resolver to load the real values and
   continue at step 3 with them.

   Report to the operator: the account email, the config path, and — once, prominently —
   the generated password to save now. `knowledge init` deliberately writes no `kb_root`,
   so this config is remote-only, which is the intended shape for a hosted account.

## 3. Research (read-only)

Ground **every** claim in reality — never invent paths, commands, config snippets, or
behavior; quote them from real files. Reuse conclusions already established in this
conversation rather than re-deriving them. Audience: novice programmer (research mode: a
smart reader new to the domain), unless the user says otherwise.

**Repo research — by mode:**

- **Change mode:** read the actual change, not your memory of it. Use `git diff`,
  `git log`, and `git show` (e.g. `git show <ref>`, `git diff <base>..<head>`,
  `git log --stat`) to get the real diff and the surrounding history, then read the
  changed files and the code around them. Every statement about what changed is grounded
  in the real diff and real files.
- **Topic mode:** read the real code, configs, compose files, and scripts that make the
  topic work here, exactly as before — walk the actual implementation.
- **Research mode:** start from what is already known before searching. In a workspace
  (`scripts/workflow.py` exists) and the subject is a phase or slice, read that phase's
  `intent.md` (the question as the operator asked it), its `phase.md`, and the `result.md`
  of each slice that researched it — those findings and their cited pages are your first
  sources. Reuse what this conversation already established too. Then run the web
  research described below as the **body** of the document, not an add-on.

**Knowledge-base research — is this an update to an existing document?**

The KB versions documents **in place**: re-explaining a topic publishes **v2 of the same
document**, not a second post. A document's path encodes its ORIGINAL date, so writing
about the same topic on a later day would otherwise silently create a second, unrelated
document — check first. Derive `project` and `slug` exactly as step 5 defines them, then
run one list call (every `curl` in this skill takes
`-H "Authorization: Bearer <KB_API_TOKEN>"` when `KB_API_TOKEN` from step 2 is non-empty
and no header when it is empty — both forms are spelled out in step 5):

    curl -sS --max-time 5 '<KB_API_BASE_URL>/api/documents?project=<project>&limit=200'

Look in `items` for an entry whose `slug` matches, or whose `title` is plainly this same
topic under a different slug. Match on **subject**, not recency: a genuinely different
subject is a new document even in the same project.

- **No match** → remember `PRIOR=none`; this is a new document.
- **A match** → remember its `rel_path` and `version` as `PRIOR_REL_PATH` /
  `PRIOR_VERSION` (step 5 uses both), and read what the current version says, so the new
  explainer builds on it instead of silently contradicting it:

      curl -sS --max-time 5 '<KB_API_BASE_URL>/api/documents/by-path/<PRIOR_REL_PATH>'

  The `markdown` field is the current body — for an HTML explainer, its extracted plain
  text, which is what you need to know what was already said (you re-author the page
  itself from scratch anyway). Only if an **older** body matters, list and fetch the
  archived ones:

      curl -sS --max-time 5 '<KB_API_BASE_URL>/api/documents/by-path/<PRIOR_REL_PATH>/versions'
      curl -sS --max-time 5 '<KB_API_BASE_URL>/api/documents/by-path/<PRIOR_REL_PATH>/versions/<n>'

  The list answers `{rel_path, current_version, total, versions}` and holds only the
  **superseded** bodies, newest first; `total: 0` means there is no older history yet,
  not an error. The current version is never listed there — the fetch above is it.
- Any error or unreachable API here is **never fatal**: treat it as `PRIOR=none` and
  carry on — step 5 still catches a collision with a 409.

Either way, write a **complete, standalone document** (a version is a full replacement,
not a diff): keep what still holds, correct what changed, add what is new.

**Web research — the "Best practices & next steps" section (default-on):**

In topic and change mode this is the one part that reaches *beyond* the codebase: how the
implementation compares to prevailing external practice. (**Research mode** works
differently: see the end of this subsection.) Decide whether to run it:

1. **Forced?** If `no-research` was given (step 1), skip it — go to step 4 with no
   best-practices section. If `research` was given, run it (skip the judgment gate below)
   but still honor the offline degradation in point 4.
2. **Judgment gate (the default path).** Run web research **unless** the subject has no
   meaningful external comparison surface: skip it for purely-internal material
   (repo-private glue, personal naming conventions, one-off wiring nobody else has an
   opinion on) and for trivial fixes (a typo, a version bump, a one-line guard). When in
   doubt on a substantive engineering subject, run it.
3. **Run it (WebSearch / WebFetch).** Search for how this class of problem is solved in
   general — the relevant patterns, standards, well-known libraries, documented
   trade-offs — and **open the pages you cite** (WebFetch) so every claim rests on a page
   you actually read. Gather enough to say: where the implementation **aligns** with
   prevailing practice, where it **deliberately diverges** (and why that can be
   legitimate here), and **2–4 concrete next steps**.
4. **Degrade gracefully — never hang, never loop, never fail the save.** If WebSearch /
   WebFetch are unavailable, or the first couple of attempts error or time out, **stop
   trying**: skip the section, remember the outcome as `skipped-offline`, and move on to
   step 4. Missing research must never cost the operator the document — the offline path
   always falls through to a successful save. Do not retry in a loop.

Remember the outcome for the report (step 7): **included**, **skipped-by-judgment**
(purely-internal / trivial), or **skipped-offline** (tools unavailable or errored). A
failed research step **never** blocks the save.

**Research mode — web research is the body.** There is no judgment gate: the research is
the document. Search broadly enough to map the question (the main options or positions,
the evidence for each, where sources disagree), and **open every page you cite**
(WebFetch) — the same rule as above, now applied to every claim in the document. Prefer
primary sources (official docs, papers, filings, the vendor's own pricing page) over
summaries of them, and note each source's date when the subject moves fast.

- `no-research` in research mode → run **no new** web searches; build the document only
  from the material already gathered (this conversation, the phase/slice results and the
  pages they cite). `research` is a no-op here.
- **Offline / tools erroring** → same rule as point 4 above: stop trying, and fall back to
  the material already gathered. If that material is too thin to ground the document,
  **STOP** and report that research mode needs either web access or prior findings —
  never write an ungrounded research document.

Remember the outcome for step 7 as **included** (web research ran), **prior-only**
(`no-research`, or offline with enough prior material), or **stopped-offline**.

## 4. Write the document — one interactive HTML explainer

The output is **always** a single self-contained interactive HTML page (both modes).
There is no markdown output any more. Author the whole page, then save it in step 5.

### 4.1 Hard constraints (the render breaks if violated)

The knowledge base renders this file inside an opaque-origin
`sandbox="allow-scripts"` iframe: inline JavaScript runs, but **every external request is
blocked and there is no `allow-forms` / `allow-popups`**. So:

- **Self-contained, zero external requests.** Inline `<style>` and inline `<script>`
  only. No CDN, no web fonts (use a system font stack), no network-fetched images, no
  `<link rel="stylesheet">`, no `@import`, no `url(http…)`. **No `fetch` /
  `XMLHttpRequest` anywhere.** Diagrams are HTML/CSS or inline `<svg>` — never a fetched
  image.
- **No `<form>`** and **no `target="_blank"`** (the sandbox allows neither). Plain
  `<a href="…">` links are fine; the quiz uses plain buttons/divs with JS handlers.
- The file **starts exactly at `<!DOCTYPE html>`** — no leading blank line, no
  frontmatter (the API writes the metadata itself, step 5).

### 4.2 Page shape

- `<!DOCTYPE html>`, `<html lang="en">`, `<head>` with `<meta charset>`,
  `<meta name="viewport" content="width=device-width, initial-scale=1">`, and a
  `<title>` matching the document's H1.
- One long page (**no tab navigation**) with a **table of contents** at the top linking
  each section by `id`. In topic and change mode, sections in this fixed order (research
  mode: §4.2a instead):

  1. **Background** — change mode: the system as it was before this change, plus context;
     topic mode: what this is and why it exists here. Offer a deeper beginner background
     (note it can be skipped if the reader already knows it), then the narrower part
     directly relevant.
  2. **Intuition** — the core idea in essence (not the full detail), with **concrete toy
     data** and diagrams; change mode: why the change and what it buys; topic mode: the
     mental model.
  3. **Code** — a high-level walkthrough of the real code: change mode walks the diff,
     grouped/ordered logically; topic mode walks the actual implementation here.
  4. **Best practices & next steps** — *present only when step 3 ran web research.* When
     research was skipped, this section **and its ToC entry are simply absent** — the
     document carries no "skipped" note; the chat report (step 7) says why instead. See
     §4.3.
  5. **Quiz** — 5 interactive questions (§4.4).

- Readable column width, comfortable typography, responsive/mobile styling. Use
  **callout boxes** for key concepts, definitions, and important edge cases. Render code
  in `<pre>` blocks whose CSS sets `white-space: pre-wrap` (or `pre` with horizontal
  scroll in a container) — before saving, scan every code block and confirm this, or the
  browser collapses the newlines onto one line.
- **Diagrams are HTML/CSS or inline SVG, never ASCII art.** Pick a small family of
  diagram styles and reuse them across the explanation; put real example data in the
  figures (a simplified UI view for UI changes, a data-flow/component diagram with
  example data for system changes).
- Tone: the clarity and flow of Martin Kleppmann — an essay with smooth transitions
  between sections, not a bullet dump; define each piece of jargon on first use; classic,
  engaging, novice-friendly by default. **No length cap** — as long as the teaching needs
  (typical explainers run a few hundred lines of HTML).

### 4.2a Research mode — a free-form outline

Research mode keeps every rule in §4.1 and §4.2 **except the fixed section list**: there is
no Background / Intuition / Code / Best-practices sequence. Instead:

- **Design the outline from the question.** Pick 3–8 sections whose headings name what the
  reader learns, in the order the reasoning needs. Examples of shapes, not templates: a
  landscape (*The question → How the field is organised → The main players → What
  separates them → Where it is heading*); a decision memo (*What we need → Options →
  Compared on the criteria that matter → Recommendation → Risks and open questions*); a
  concept explainer (*Why it matters → The core idea → How it works in practice → Common
  misconceptions*). Merge, split or invent sections as the material demands.
- **Fixed bookends only:** the H1 and the table of contents at the top; at the bottom a
  **Sources** section (`id="sources"`) and then the **Quiz** (`id="quiz"`, §4.4). Every
  section, bookends included, gets a ToC entry and a kebab-case `id`.
- **Open with the answer.** The first section states the question as asked (for a phase,
  in the operator's words from `intent.md`) and the short answer or main findings, so a
  reader who stops there still leaves with the conclusion.
- **Comparisons are tables or diagrams**, with the real figures, not prose lists. A
  decision document ends its body with a clear recommendation and what would change it.
- **Separate fact from judgment.** Mark your own inference or recommendation as such
  (e.g. a callout titled *Assessment*), distinct from what the sources say. Where sources
  conflict, show both and say which you weigh more and why.
- **Citations everywhere.** §4.3's rules — every claim links a page you opened, with the
  source's name and bare domain kept in plain text — apply to the **whole** document, not
  one section. **Sources** lists every cited page once: title, domain, and the date
  published or accessed.

### 4.3 The "Best practices & next steps" section (when present)

- Cover three things: where the implementation **aligns** with prevailing practice, where
  it **deliberately diverges** (and why that can be a legitimate choice here), and **2–4
  concrete next steps**.
- **Every claim carries a source link to a page you actually opened during research — no
  citation, no claim.** Never cite a page you did not read.
- **Keep the source visible in plain text**, because the KB's search and MCP surfaces
  index only the *extracted text* and an `href` is not text — a bare "source" link would
  lose its provenance there. Write each citation so the domain survives as text: link
  text that names the source, plus the bare domain in parentheses, e.g.:

      <p>Request-scoped connection pooling is standard practice for this
      (<a href="https://www.postgresql.org/docs/current/runtime-config-connection.html">PostgreSQL
      docs</a> — postgresql.org).</p>

### 4.4 The quiz

- Every mode includes it; in research mode the questions test the findings and the
  reasoning behind them, not trivia from a source.
- **5 medium-difficulty multiple-choice questions** that test substantive understanding
  — hard enough that you must actually understand the subject to answer, but not gotchas.
- Show each question's options as plain buttons/divs. On click, give **immediate
  feedback**: mark correct/incorrect and reveal a one-line "why". **No `<form>`** — wire
  it with a small inline `<script>` and click handlers; keyboard-friendly where easy.

Use the **structural skeleton and one worked quiz item below as the spec** — generate all
the real teaching content and all five real questions in this shape. It is a contract,
not a literal template to paste. In research mode, replace the four content sections and
their ToC entries with your own outline (§4.2a) and add a `#sources` section before the
quiz; the head, styles and quiz script stay the same:

    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <title><!-- matches the H1 --></title>
      <style>
        :root { color-scheme: light dark; }
        body { max-width: 46rem; margin: 2rem auto; padding: 0 1rem;
               font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
               line-height: 1.6; }
        pre  { white-space: pre-wrap; overflow-wrap: anywhere;
               background: #f4f4f4; padding: .75rem; border-radius: 6px; }
        .callout { border-left: 4px solid #4a7; background: #f0f8f4;
                   padding: .75rem 1rem; margin: 1rem 0; border-radius: 4px; }
        .q .opt { display: block; width: 100%; text-align: left; margin: .3rem 0;
                  padding: .5rem .75rem; cursor: pointer; }
        .q .opt.correct   { background: #d6f5d6; }
        .q .opt.incorrect { background: #f7d6d6; }
        .q .why { margin: .4rem 0 0; font-size: .95em; }
      </style>
    </head>
    <body>
      <h1><!-- title --></h1>

      <nav aria-label="Contents">
        <strong>Contents</strong>
        <ol>
          <li><a href="#background">Background</a></li>
          <li><a href="#intuition">Intuition</a></li>
          <li><a href="#code">Code</a></li>
          <!-- include the next line ONLY when the research section is present -->
          <li><a href="#best-practices">Best practices &amp; next steps</a></li>
          <li><a href="#quiz">Quiz</a></li>
        </ol>
      </nav>

      <section id="background"><h2>Background</h2> … </section>
      <section id="intuition"><h2>Intuition</h2> … </section>
      <section id="code"><h2>Code</h2> … </section>
      <!-- include this section ONLY when step 3 ran web research -->
      <section id="best-practices"><h2>Best practices &amp; next steps</h2> … </section>

      <section id="quiz">
        <h2>Quiz</h2>
        <div class="q" id="q1">
          <p><strong>1.</strong> Which statement is true?</p>
          <button class="opt" data-correct="false">Option A</button>
          <button class="opt" data-correct="false">Option B</button>
          <button class="opt" data-correct="true">Option C</button>
          <p class="why" hidden>Because C is the only one that … .</p>
        </div>
        <!-- q2 … q5 in the same shape -->
      </section>

      <script>
        document.querySelectorAll('.q').forEach(function (q) {
          var why = q.querySelector('.why');
          q.querySelectorAll('.opt').forEach(function (btn) {
            btn.addEventListener('click', function () {
              var right = btn.dataset.correct === 'true';
              btn.classList.add(right ? 'correct' : 'incorrect');
              if (why) why.hidden = false;
            });
          });
        });
      </script>
    </body>
    </html>

## 5. Save via the KB document API

- project = the current repo's root directory name, verbatim (e.g. `hi2vi_web`);
  if it contains path-unsafe characters, lowercase it and replace them with `-`.
  Outside a git repo (no repo directory name to use), fall back to `default`; the KB
  get-or-creates any project name on the first write, so `default` always resolves.
- slug = short lowercase-kebab topic name (e.g. `shared-nginx-explained`);
  date = today, `YYYY-MM-DD`.
- Build the request in a temp dir — `<tmp>` below means
  `/tmp/explain-<date>-<slug>/` — so the document body and title never pass
  through shell arguments.
- Write `<tmp>/body.html`: the **raw HTML document you authored in step 4, starting
  exactly at `<!DOCTYPE html>`, with NO frontmatter** (the API writes the `<!--kb …-->`
  comment-frontmatter itself).
- Write `<tmp>/meta.json` with exactly these fields — note `"format": "html"`. Leave
  `date`, `slug`, `overwrite`, and `commit` unset (API defaults). `co_authored_by` is the
  bare attribution value naming the model that actually did the work — the API prepends
  `Co-Authored-By: ` itself:

      {
        "title": "<Title>",
        "project": "<project>",
        "format": "html",
        "tags": ["<2–5 lowercase-kebab topic tags>"],
        "source_repo": "<absolute path to the current repo root>",
        "co_authored_by": "<bare attribution>"
      }

- **Updating an existing document (`PRIOR` from step 3)?** Add exactly these two fields
  to `meta.json` as well — this is what makes the write the next **version** of that
  document instead of a new post:

      "new_version": true,
      "rel_path": "<PRIOR_REL_PATH>"

  The API archives the current body, writes yours at the **same** `rel_path`, and
  answers `version: <PRIOR_VERSION + 1>` alongside `previous_version` and
  `archived_path`. The document's id, URL, links and graph edges never move — and
  neither do its original `date` and `slug`, even if the title changed (the response
  echoes the target's). Keep `project` and `format` identical to the target: changing
  either is a **422**, never a silent move. If `rel_path` no longer resolves, the API
  falls back to a plain new document at today's path, so a stale guess still publishes.

- Merge — run exactly this command, spelled exactly this way (the raw HTML rides the
  existing `markdown` field; `"format": "html"` in the payload tells the API to treat it
  as an HTML explainer and write the comment-frontmatter):

      python3 -c 'import json,sys; m=json.load(open(sys.argv[1])); m["markdown"]=open(sys.argv[2]).read(); json.dump(m, open(sys.argv[3], "w"))' <tmp>/meta.json <tmp>/body.html <tmp>/payload.json

- POST once to `<KB_API_BASE_URL>/api/documents` (the `KB_API_BASE_URL` from step 2).
  When `KB_API_TOKEN` from step 2 is **non-empty**, add the bearer header shown in the
  second form; when it is empty, use the first form. The **30 s** budget is deliberate:
  the API now answers *before* it does any network work (the git push and the embedding
  call moved off the response path), so 30 s comfortably covers uploading a large
  explainer over a slow link — and the `allowed-tools` frontmatter pre-approves this
  exact `--max-time 30` prefix, so spell it exactly this way (any other value prompts
  for permission mid-run):

      curl -sS --max-time 30 -o <tmp>/response.json -w '%{http_code}' --json @<tmp>/payload.json <KB_API_BASE_URL>/api/documents

      curl -sS --max-time 30 -H "Authorization: Bearer <KB_API_TOKEN>" -o <tmp>/response.json -w '%{http_code}' --json @<tmp>/payload.json <KB_API_BASE_URL>/api/documents

- curl exit code ≠ 0 (connection refused, timeout) = **you did not see a response**,
  which is NOT the same as a failed save. Do not re-POST yet →
  go to **§5.1** and find out what actually landed. Exit 0 = the API answered → branch
  on the printed status code, and NEVER fall back to a file write on an HTTP error:
  - **201** — the API wrote the file, inserted the Recent bullet, indexed the
    row, and made the scoped commit. Write NO file, do NOT touch
    `docs/index.md`, run NO git. Record `url`, `version`, `previous_version`,
    `committed`, `commit_error`, `pushed` and `push_pending` from
    `<tmp>/response.json` for step 7. **`pushed: false` with `push_pending: true`
    is the normal, successful result — never an error and never a reason to
    retry**: the document is saved and committed locally, and the push to the
    remote runs in the background right after this response. On a
    version bump `version` is the one just published, and no duplicate Recent
    bullet is added.
  - **409** — a document already exists at that path. This is the plain-create
    collision; a `new_version` write that resolved its target never lands here.
    The detail carries `rel_path`, `existing_title` and — when a real KB
    document is behind it — its `version` and a `hint`. It is the "same topic
    again" case, so the primary retry is a **new version**: report the
    `existing_title` and `rel_path` and ASK the user before retrying; on a yes,
    add `"new_version": true` and `"rel_path": "<the detail's rel_path>"` to
    `meta.json`, re-run the merge command, and re-POST. That archives the
    existing body and publishes yours as the next version, and adds no duplicate
    Recent bullet. `"overwrite": true` still works and is no longer destructive
    (it archives the replaced body too), but use it only when the user
    explicitly wants to replace rather than supersede.
  - **422** — convention violation: if the mistake is in our payload, fix it
    once and re-POST; otherwise report the response detail.
  - **401** — the API requires a bearer token and yours is missing or wrong:
    report that a valid `KB_API_TOKEN` must be configured (via
    `~/.config/knowledge-kb/config.json` `api.token`, or the `KB_API_TOKEN` env
    var). To mint a fresh key, run
    `knowledge init --email <you> --password-stdin --new-key`. Do not fall back.

### 5.1 Transport failure on the POST — verify before you report or retry

A non-zero curl exit tells you only that **this client never saw the response**. The
request may well have been delivered and the document durably saved: the API writes the
file and the database row *before* it answers. So a timeout is **not** proof of failure,
and the two obvious reactions are both wrong — reporting "unreachable" lies about a
published document, and re-POSTing blind creates a duplicate or burns an unwanted extra
version. **Verify first, exactly once.**

- **The target `rel_path`** is `<PRIOR_REL_PATH>` when this was a `new_version` publish
  (step 3), otherwise `<project>/<date>-<slug>.html` — the path the API would have
  written. Ask what is there now (bearer header exactly as in the POST above: include
  the `-H` form when `KB_API_TOKEN` is non-empty, omit it when empty):

      curl -sS --max-time 30 -o <tmp>/verify.json -w '%{http_code}' '<KB_API_BASE_URL>/api/documents/by-path/<rel_path>'

      curl -sS --max-time 30 -H "Authorization: Bearer <KB_API_TOKEN>" -o <tmp>/verify.json -w '%{http_code}' '<KB_API_BASE_URL>/api/documents/by-path/<rel_path>'

- Branch on that verification:
  - **200 and it is this publish** — for a plain create (`PRIOR=none`), a 200 whose
    `title` is the one you just sent is proof (nothing else writes that path); for a
    `new_version` publish, `version` in `<tmp>/verify.json` is `PRIOR_VERSION + 1`.
    → **The save LANDED.** Write NO file, run NO git, do NOT re-POST. Go to step 7 and
    report success from `<tmp>/verify.json` — it carries `id`, `title`, `rel_path` and
    `version` (this read projection has **no `url`** field; the 201 that carried it was
    the response you lost) — adding one honest line: the response never arrived, the
    document is confirmed saved by this follow-up read.
  - **200 but it is plainly the OLD document** — a `new_version` publish whose `version`
    is still `PRIOR_VERSION`. The API is reachable and your write did not land → re-run
    the POST **once**, exactly as spelled above, and branch on its status code as usual.
    If that single retry also fails at the transport layer, STOP: report that the
    publish state could not be established, name the `rel_path`, and write nothing (do
    not attempt a third time).
  - **200 answering a different document** on a plain create — the path is taken by
    something else, i.e. the step-5 **409** case arriving late. Do NOT re-POST blind:
    report the existing title and `rel_path` and ASK the user, exactly as the 409
    branch says, before publishing over it as a new version.
  - **404** — nothing at that path. The API is reachable and the save genuinely failed
    → re-run the POST **once**, same one-retry-then-stop rule as the OLD-document
    bullet above.
  - **5xx — or any other status** (e.g. a **401** when reads are token-guarded and the
    token is wrong): the API answered but could not tell you what happened → STOP,
    report the status and that the publish state is unknown at `<rel_path>` (for 401,
    that a valid `KB_API_TOKEN` is needed to check). Do not retry, do not write a file.
  - **curl exit ≠ 0 on the verification GET too** — the API really is unreachable now.
    **STOP.** Report that the document API at `<KB_API_BASE_URL>` is unreachable and the
    save did not complete, and carry one caveat into the report: the earlier POST may
    still have landed, so check the knowledge base before publishing this again. Write no
    files anywhere — there is no local fallback.
- Never loop this. One verification GET, at most one re-POST, then report what you know.

## 6. Optional copy in the current project

Only when PROJECT_COPY=yes: also write the document — the **raw HTML, no
frontmatter** (starting at `<!DOCTYPE html>`) — to
`<repo-root>/<TOPIC>_EXPLAINED.html` (topic in SCREAMING_SNAKE, e.g.
`SHARED_NGINX_EXPLAINED.html`). Do not commit it; that repo belongs to the user.

## 7. Report

Tell the user:

- API path: the document is saved and committed in the KB; view at the `url`
  from the response (the direct doc page; shareable with others when the project
  is public). If `committed` is `false` with a `commit_error`, say the
  document was saved but the commit failed, and quote the error. Say which
  version this was: `version` from the response — a new document is `v1`; a
  version bump names the `previous_version` it superseded, whose body is kept
  (archived), not lost.
- **Publishing state — do not misreport it.** `pushed: false` together with
  `push_pending: true` is the normal 201: the document is **saved and committed**,
  and the push to the remote runs in the background just after the response, so the
  off-box/site copy follows shortly. Say it that way (e.g. "saved and committed;
  publishing to the remote in the background") — never call it a failure, never
  "not saved", and never retry the POST because of it. A background push failure
  never appears in the response body (there is no `push_error` field any more); it
  lands in the server log and the document publishes on the next successful push.
- **Recovered path (§5.1)**: when the POST's response was lost but the verification
  GET proved the document is there, report it as a plain success from
  `<tmp>/verify.json` — `title`, `rel_path`, `version`, `id`, and the viewable
  location as `<KB_SITE_BASE_URL>/<rel_path>` (the read projection carries no `url`)
  — plus one line: the connection dropped before the response arrived, the save is
  confirmed by a follow-up read, and nothing was written twice. When the verification
  instead proved the save did not land and the single re-POST succeeded, just report
  that success normally.
- The **research-section outcome**, one line: **included**, **skipped-by-judgment**
  (purely-internal subject / trivial fix), or **skipped-offline** (research tools
  unavailable or errored) — with a short why. In research mode, say it was research mode
  and give the outcome as **included**, **prior-only** or **stopped-offline**, with the
  number of sources cited.
- The project copy path, if one was made.
