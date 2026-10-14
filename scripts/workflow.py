#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
# Nested personal install (P28). The marker `.agentic-nested.json` beside `scripts/` says the engine and all
# workflow state live in a nested repo (`<host>/workflow`, ROOT) inside a host repo the operator does
# not own (HOST_ROOT): product code, git history for phase-scope, and `.claude/agents` are the
# host's, while works/, docs/, executors.toml and the templates stay under ROOT. EVERY nested
# branch below is gated on that marker: with no `.agentic-nested.json`, NESTED is None, HOST_ROOT is None and
# behaviour and output are byte-for-byte the at-root engine's. A marker that exists but is malformed
# is never read as at-root mode -- `validate` reports it as an error and every other command refuses
# (see `main`). The installer writes the marker; this file owns its schema (NESTED_* below).
NESTED_MARKER = ".agentic-nested.json"
NESTED_SCHEMA = 1
NESTED_KEYS = ("schema", "host_root", "commit_convention", "renames")
NESTED_CONVENTION_KEYS = ("inferred", "confirmed", "text", "coauthor_trailers")
NESTED_TRAILERS = ("allowed", "forbidden", "unknown")
NESTED_RENAME_KINDS = ("skills", "agents")
# Optional, but strict when present: the installer's record of which host-side skill directories
# and agent files are the workspace's own (so `--update --nested` never mistakes them for a clash).
NESTED_OPTIONAL_KEYS = ("installed",)
# P35: a nested phase worktree is a pair, and its host half needs a branch the operator names.
NESTED_HOST_BRANCH_REQUIRED = (
    "parallel-start in a nested install needs --host-branch <name>: the host repo's branch for this phase's product commits, "
    "named by the host's own convention for branches (see nested-convention), with no workspace phase/slice IDs in it; "
    "an existing branch is reused when no host worktree has it checked out -- nothing was written")
# phase.json `host_anchors` (nested only): the host HEAD at new-phase and at the passing review --
# phase-scope's range in the host repo, whose commits the nested repo never sees.
HOST_ANCHOR_KEYS = ("created", "review_pass")


def nested_marker_problems(data) -> list:
    """Every way a parsed `.agentic-nested.json` breaks schema 1 -- empty when it is well-formed.

        {"schema": 1,
         "host_root": "..",                       # relative to the engine root; the host repo's root
         "commit_convention": {"inferred": "<text>" | null, "confirmed": false,
                               "text": "<text>" | null, "coauthor_trailers": "allowed" | "forbidden" | "unknown"},
         "renames": {"skills": {"<original>": "<installed>"}, "agents": {"<original>": "<installed>"}},
         "installed": {"skills": ["<installed>", ...], "agents": ["<installed>", ...]}}   # optional

    A confirmed convention carries its text and a decided trailer rule; an installed name is a bare
    file/directory name. `installed` (written by the installer) lists the host-side skill directories
    and agent files that are the workspace's own; when present it has exactly those two lists of
    distinct bare names, and every renamed name appears in it. Other unknown top-level keys are not
    problems (`validate` warns about them)."""
    if not isinstance(data, dict):
        return [f"{NESTED_MARKER} is not a JSON object"]
    problems = []
    missing = [k for k in NESTED_KEYS if k not in data]
    if missing:
        problems.append(f"missing field(s) {', '.join(missing)}")
    if "schema" in data and (data["schema"] is True or data["schema"] != NESTED_SCHEMA):
        problems.append(f"schema {data['schema']!r} is not {NESTED_SCHEMA}")
    if "host_root" in data:
        raw = data["host_root"]
        if not (isinstance(raw, str) and raw.strip()) or os.path.isabs(raw):
            problems.append(f"host_root {raw!r} must be a non-empty path relative to the engine root (normally \"..\")")
        else:
            host = (ROOT / raw).resolve()
            if not host.is_dir():
                problems.append(f"host_root {raw!r} resolves to {host}, which is not a directory")
            elif host == ROOT or host not in ROOT.parents:
                problems.append(f"host_root {raw!r} resolves to {host}, which does not contain the engine root {ROOT}")
    if "commit_convention" in data:
        conv = data["commit_convention"]
        if not isinstance(conv, dict):
            problems.append("commit_convention is not an object")
        else:
            gone = [k for k in NESTED_CONVENTION_KEYS if k not in conv]
            if gone:
                problems.append(f"commit_convention: missing field(s) {', '.join(gone)}")
            for key in ("inferred", "text"):
                if key in conv and conv[key] is not None and not isinstance(conv[key], str):
                    problems.append(f"commit_convention.{key} must be a string or null")
            if "confirmed" in conv and not isinstance(conv["confirmed"], bool):
                problems.append("commit_convention.confirmed must be true or false")
            if "coauthor_trailers" in conv and conv["coauthor_trailers"] not in NESTED_TRAILERS:
                problems.append(f"commit_convention.coauthor_trailers {conv['coauthor_trailers']!r} is not one of {', '.join(NESTED_TRAILERS)}")
            if conv.get("confirmed") is True:
                if not (isinstance(conv.get("text"), str) and conv["text"].strip()):
                    problems.append("commit_convention: a confirmed convention records its text")
                if conv.get("coauthor_trailers") not in ("allowed", "forbidden"):
                    problems.append("commit_convention: a confirmed convention records coauthor_trailers allowed or forbidden")
    if "renames" in data:
        renames = data["renames"]
        if not isinstance(renames, dict):
            problems.append("renames is not an object")
        else:
            for kind in NESTED_RENAME_KINDS:
                table = renames.get(kind)
                if not isinstance(table, dict):
                    problems.append(f"renames.{kind} must be an object mapping an original name to its installed name")
                    continue
                for original, installed in table.items():
                    if not (original and _bare_installed_name(installed)):
                        problems.append(f"renames.{kind}: {original!r} -> {installed!r} is not a bare installed name")
    if "installed" in data:
        inst = data["installed"]
        if not isinstance(inst, dict) or sorted(inst) != sorted(NESTED_RENAME_KINDS):
            problems.append(f"installed must be an object with exactly {' and '.join(NESTED_RENAME_KINDS)} (lists of installed names)")
        else:
            for kind in NESTED_RENAME_KINDS:
                names = inst[kind]
                if not isinstance(names, list):
                    problems.append(f"installed.{kind} must be a list of installed names")
                    continue
                bad = [n for n in names if not _bare_installed_name(n)]
                if bad:
                    problems.append(f"installed.{kind}: {', '.join(repr(n) for n in bad)} is not a bare installed name")
                elif len(set(names)) != len(names):
                    problems.append(f"installed.{kind} lists a name twice")
                table = data.get("renames", {}).get(kind) if isinstance(data.get("renames"), dict) else None
                if isinstance(table, dict) and not bad:
                    missing = sorted(v for v in table.values() if isinstance(v, str) and v not in names)
                    if missing:
                        problems.append(f"installed.{kind} does not list the renamed {', '.join(missing)}")
    return problems


def _bare_installed_name(name) -> bool:
    """A skill directory or agent file stem as installed in the host: one plain path segment."""
    return (isinstance(name, str) and bool(name.strip()) and name == name.strip()
            and "/" not in name and "\\" not in name and not name.startswith("."))


def _load_nested() -> tuple:
    """(marker, problems): (None, []) when ROOT holds no `.agentic-nested.json` -- at-root mode, the only
    case that touches nothing. A marker that cannot be read or parsed comes back as `{}` with its
    problem, so it still counts as nested (never silently at-root)."""
    path = ROOT / NESTED_MARKER
    if not os.path.lexists(path):
        return None, []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return {}, [f"cannot be read as JSON ({exc})"]
    return (data if isinstance(data, dict) else {}), nested_marker_problems(data)


NESTED, NESTED_PROBLEMS = _load_nested()
HOST_ROOT = None
if NESTED is not None and isinstance(NESTED.get("host_root"), str) and NESTED["host_root"].strip() and not os.path.isabs(NESTED["host_root"]):
    HOST_ROOT = (ROOT / NESTED["host_root"]).resolve()
# The command prefix every printed hint uses: from the host root when nested (cwd = <host>), from
# the workspace root otherwise -- so at root it is exactly the literal the hints always printed. A
# nested marker too broken to name its host gets the absolute path, right from any cwd.
if HOST_ROOT is not None:
    WORKFLOW_CMD = f"python3 {Path(os.path.relpath(ROOT, HOST_ROOT)).as_posix()}/scripts/workflow.py"
elif NESTED is not None:
    WORKFLOW_CMD = f"python3 {ROOT / 'scripts' / 'workflow.py'}"
else:
    WORKFLOW_CMD = "python3 scripts/workflow.py"
# Appended to every printed `parallel-start <P>` hint: a nested install's start needs the host branch
# (P35), which the operator names; at root it is empty, so the hints print exactly as before.
NESTED_HOST_BRANCH_ARG = " --host-branch <name>" if NESTED is not None else ""


def shown(path: Path) -> str:
    """A path as the operator's shell must type it: relative to the host root when nested (so
    `workflow/works/...` resolves from a session started at the host), else today's ROOT-relative
    string. OUTPUT ONLY -- a path persisted into index.json, slice.json, phase.json or events.jsonl
    stays ROOT-relative, because the state it points into lives in the nested repo."""
    if HOST_ROOT is not None:
        return os.path.relpath(path, HOST_ROOT)
    if NESTED is not None:  # a marker too broken to name its host: absolute, right from any cwd
        return str(path)
    return str(path.relative_to(ROOT))


def shown_rel(rel: str) -> str:
    """`shown` for a ROOT-relative string read back from stored state (an index or phase path):
    host-relative when nested, and at root the stored string itself, untouched."""
    return shown(ROOT / rel) if HOST_ROOT is not None else rel


WORKS = ROOT / "works"
DOCS = ROOT / "docs"
ACTIVE = WORKS / "phases" / "active"
ARCHIVED = WORKS / "phases" / "archived"
DEFERRED_OPEN = WORKS / "deferred" / "open"
DEFERRED_PROMOTED = WORKS / "deferred" / "promoted"
DEFERRED_DROPPED = WORKS / "deferred" / "dropped"
DOC_TYPES = {"product", "experience", "architecture", "frontend", "backend", "data", "api", "operations", "security", "qa", "decisions"}
# An H2 section in a durable doc past this many bytes has outgrown the read-order rule
# ("read the `docs/current/` SECTIONS the work touches"): at ~4 B/token 10 KB is ~2.5 k tokens,
# and measured across four live adopting repos (P21.S1 §2.8) 10 % of all H2 sections are already
# over it, the worst one 112,619 B / ~28 k tokens in a single section. 10 KB is that measurement's
# own cut line, so the check flags the tail that actually defeats the rule and stays quiet on the
# other 90 %. ADVISORY ONLY -- a warning naming doc, section and size, never an error: splitting is
# per-doc judgment for the next docs phase (small docs measured WORSE when sectioned, §2.4), so
# this only makes the drift visible. One knob, no config plumbing.
DOC_SECTION_WARN_BYTES = 10 * 1024
PHASE_STATUSES = {"planned", "in_progress", "in_review", "pending", "blocked", "done"}
SLICE_STATUSES = {"todo", "ready", "in_progress", "in_review", "changes_requested", "pending", "blocked", "done"}
DEFERRED_STATUSES = {"deferred", "ready", "promoted", "done", "dropped"}
REVIEW_VERDICTS = {"pass", "changes_requested", "blocked"}
# Closed set of slice kinds (workspace v34). `kind` routes real behavior -- `co-work` in
# particular means orchestrator-inline (the round's lifecycle and the operator's words
# stay on the main thread), so a typo like `cowork` used to create a slice that read as
# ordinary implementation and got dispatched to an executor that cannot run a design
# round. Enforced asymmetrically on purpose: a HARD ERROR at creation
# (`new-slice`, `promote-deferred`), only a WARNING in `validate()`, so an adopting repo
# carrying an invented kind in its history survives an update instead of failing validate
# on slices it cannot change. Note `--risk` next door is deliberately NOT validated:
# unrecognized values route to the high tier, which is the safe direction -- do not
# "fix" that asymmetry for symmetry's sake.
# Kinds route by KIND before `risk` is read (`slice_route`; `executor-route <slice>` prints the
# decision): `decomposition`, `review` and `co-work` (its mockup span) to the `high` row, and
# `research` (added in workspace v36) to the `research` row -- both on `slice-executor-high`, never
# the mid or cheap rows. A `research` slice is findings-only -- it writes no product code, and what
# it learned lands in the phase notebook for the `DECOMP2` that usually follows -- so a weak read
# is expensive and it must never be routable to the mid tier by a `low` rating. Set `--risk high`
# on one so the recorded rating cannot contradict the routing; if the two ever disagree, the kind
# wins.
SLICE_KINDS = {"implementation", "review", "decomposition", "research", "fix", "docs", "qa", "co-work"}
# Phase-notebook budget (v35; re-shaped in v39): ONE generous byte cap, ~100k tokens of
# text. The v35 pair (200 lines / 16 KB) was measured in P21 and the line half never bound
# while the byte half squeezed four slices into compressing unrelated notes -- so the line
# ceiling is gone and the byte ceiling is a soft sanity cap, not a working constraint: a
# notebook should stop compressing to fit and simply carry what the next slice needs.
# Still a WARNING, never an error: a hard cap invites truncating exactly the notes that
# matter, so the fix is always to rewrite (state stays in phase.md, detail moves to the
# slice's result.md), never to delete under duress.
PHASE_MD_BUDGET = 400 * 1024
# Execution streams (workspace v24; opt-in again since v43). A phase.json MAY carry an
# optional `execution` block. `mode: "parallel"` = the phase runs on its own branch +
# worktree, stamped by `parallel-start` -- which a phase gets ONLY when the operator asks
# for it. No block = the phase runs on the default stream, which is where every phase runs
# unless asked otherwise; that is the v43 default and it needs no marker.
# `mode: "default"` = a LEGACY pin written by v42's `parallel-skip` / `new-phase --on-main`,
# when the worktree was the default and staying on main needed saying. Both commands are
# now no-ops, so nothing new is ever stamped with it -- but `phase_execution` still returns
# None for it, so a pinned phase IS a default-stream phase everywhere, and `parallel-start`
# still refuses one rather than silently overriding an old deliberate pin.
# See `phase_execution` / `phase_pinned`.
EXECUTION_MODES = {"parallel"}
PINNED_MODE = "default"
# The default worktree home. Nested under the repo so Claude Code's EnterWorktree can enter it
# from anywhere (it accepts `.claude/worktrees/` paths even from inside another worktree), and
# excluded through the repo's own info/exclude so the default checkout never sees it.
WORKTREES_DIR = ".claude/worktrees"
# What the stamp commit carries besides the phase folder: the generated works/ files that
# `rebuild_index_and_state` rewrites, plus the event log. Nothing else on the tree enters it.
STAMP_WORKS_FILES = ("works/state.json", "works/index.json", "works/backlog.md", "works/deferred.md", "works/events.jsonl")
CONSOLIDATION_STATES = {"pending", "done"}
# How many phases must owe durable-doc consolidation before `next` / `validate` say so.
# 1 = always, whenever anything owes -- the deliberate default, because the debt has to be
# visible at ANY docs-phase cadence: deferral traded review cost for operator-paced staleness,
# and silent staleness is the one outcome the trade may not have. This single constant is the
# only "how loud" knob for the *debt* line. v39 settled the cadence question by declining it --
# consolidation runs when the operator wants it, and explicit doc staleness (`stale_docs`) is what
# was taken instead -- so this stays 1; a repo that later states a cadence can still raise it.
CONSOLIDATION_DEBT_MIN_PHASES = 1
# What `docs-debt` calls a note that names no doc from DOC_TYPES -- listed, never guessed at.
UNASSIGNED_DOC = "(unassigned)"
# A default-stream phase in any of these states means main is mid-flight, so a phase
# branch may not be merged into it yet (the quiet-point gate, `parallel-gate`).
BUSY_PHASE_STATUSES = ("in_progress", "in_review", "pending", "blocked")
# Regenerated from works/phases/** and docs/versions/** by `parallel-merge-finish`;
# never merged by hand (see .gitattributes).
GENERATED_FILES = ("works/state.json", "works/index.json", "works/backlog.md", "works/deferred.md", "docs/current/*.md")
# The executor agent files Claude Code loads: the host's `.claude/agents` when nested (Claude Code
# finds agents walking up from the session's cwd, the host root), the workspace's otherwise.
# executors.toml and .env stay at ROOT either way.


def _main_host_checkout_agents(host: Path) -> Path:
    """Nested only (P35): the MAIN host checkout's `.claude/agents`, even when HOST_ROOT is a host
    worktree. A phase worktree pair has no `.claude/` of its own (Claude Code reads agents and
    skills through from the main checkout), so `<host-wt>/.claude/agents` never exists. The main
    checkout is the parent of the host's common git dir when that dir is a plain `.git`; anything
    else (no git, a submodule's `.git/modules/<name>`, a separate GIT_DIR) falls back to `host`."""
    try:
        proc = subprocess.run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
                              cwd=str(host), capture_output=True, text=True, timeout=10)
    except Exception:  # noqa: BLE001 - git is optional; the host's own folder is the honest fallback
        return host / ".claude" / "agents"
    common = Path(proc.stdout.strip()) if proc.returncode == 0 and proc.stdout.strip() else None
    if common is None or common.name != ".git":
        return host / ".claude" / "agents"
    return common.parent / ".claude" / "agents"


CLAUDE_AGENTS = _main_host_checkout_agents(HOST_ROOT) if HOST_ROOT is not None else (HOST_ROOT or ROOT) / ".claude" / "agents"
EXECUTOR_TIERS = ("mid", "high")
RETIRED_EXECUTOR_TIERS = ("low",)  # dropped in workspace v23 — routing is two-tier (mid/high)
# The executor route table (workspace v53): ONE table, owned here, that the orchestrator dispatches
# from. A row is a (model, effort) pair the dispatch passes per call; `executor-route` prints the
# resolved row for a slice and `sync-agents` writes the rows that own an agent file into that
# file's frontmatter, which is only the fallback. Each row is overridable, key by key, under
# [claude.<row>] in the repo-root executors.toml. `cheap` has no defaults of its own: it inherits
# the RESOLVED mid row for every key it does not override, so an unset cheap row is the mid row.
# `explore` is the read-only lookup agent (.claude/agents/Explore.md), not a slice route.
# `research` and `cheap` run another row's agent file (slice-executor-high / -mid) with their model
# passed per call, and the Agent tool's `model` is an enum, so those two rows take an alias only;
# a full model id or "inherit" works only on mid, high and explore, whose frontmatter carries it.
# effort = "" is the escape hatch for a model that rejects the parameter: no effort line in the
# agent file and no per-dispatch effort. Rows, never tiers: two tiers stay (EXECUTOR_TIERS), and the
# cheap row runs the mid file -- which supersedes v46's "haiku is never an executor tier". The
# named modes of v29-v52 (a top-level `mode` key) are retired; read_executors_toml refuses one.
EXECUTOR_ROUTES = ("high", "research", "mid", "cheap", "explore")  # print order
ROUTE_DEFAULTS = {
    "high": {"model": "opus", "effort": "high"},
    "research": {"model": "opus", "effort": "medium"},
    "mid": {"model": "sonnet", "effort": "high"},
    "cheap": None,  # inherits the resolved mid row
    "explore": {"model": "haiku", "effort": "high"},
}
ROUTE_TIER = {"high": "high", "research": "high", "mid": "mid", "cheap": "mid", "explore": None}
# Rows that own an agent file (sync-agents writes their frontmatter). research and cheap dispatch
# to another row's file, so their model must be an Agent-tool alias the dispatch can pass.
ROUTE_AGENT = {"high": "slice-executor-high", "mid": "slice-executor-mid", "explore": "Explore"}
# The design subagent is not a tier and has no row: it follows the high row's model and effort, so
# one [claude.high] override governs it too and design work never lands on the mid row.
DESIGN_DRAFTER_FOLLOWS = "high"
# (label, canonical agent name, row) for the four agent files sync-agents manages, in print order.
MANAGED_AGENT_FILES = (
    ("mid", ROUTE_AGENT["mid"], "mid"),
    ("high", ROUTE_AGENT["high"], "high"),
    ("design-drafter", "design-drafter", DESIGN_DRAFTER_FOLLOWS),
    ("Explore", ROUTE_AGENT["explore"], "explore"),
)
AGENT_MODEL_ALIASES = ("opus", "sonnet", "haiku", "fable")  # the Agent tool's `model` enum
EFFORT_LEVELS = ("low", "medium", "high", "xhigh", "max")  # the Agent tool's `effort` enum
# Commit attribution follows the model a slice actually ran on; anything else prints verbatim.
MODEL_ATTRIBUTION = {"opus": "Claude Opus 5.5", "sonnet": "Claude Sonnet 5.5",
                     "haiku": "Claude Haiku 5.5", "fable": "Claude Fable 5.1"}
# A loopback ANTHROPIC_BASE_URL is a local proxy (ocx's Kiro sidecar listens on 127.0.0.1:10100)
# that serves no Haiku 5.5: there the cheap row falls back to the mid row's model and the explore
# row to EXPLORE_PROXY_MODEL, printed as a `fallback=` line by executor-route.
LOOPBACK_HOSTS = ("127.0.0.1", "localhost", "::1")
EXPLORE_PROXY_MODEL = "sonnet"


def now_iso() -> str:
    return datetime.now().astimezone().replace(microsecond=0).isoformat()


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def slugify(value: str, fallback: str = "item") -> str:
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "_", value.strip().lower()).strip("_")
    return slug or fallback


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_text(path: Path, text: str, executable: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp_", suffix=path.name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        if executable:
            os.chmod(tmp, os.stat(tmp).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        os.replace(tmp, str(path))
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def write_json(path: Path, data: object) -> None:
    write_text(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def append_event(event_type: str, **payload: object) -> None:
    event = {"ts": now_iso(), "type": event_type, **payload}
    WORKS.mkdir(parents=True, exist_ok=True)
    with (WORKS / "events.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def strip_frontmatter(text: str) -> str:
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            return text[end + len("\n---\n"):].lstrip("\n")
    return text


def read_executors_toml() -> dict:
    """{(row, key): value} from the repo-root executors.toml: the per-row overrides of the route table.

    Strict subset of TOML -- [claude.<row>] tables (a row of EXECUTOR_ROUTES) holding model/effort
    keys with double-quoted string values; '#' comments and blanks ignored. Anything else is an
    error naming its line, so a typo surfaces instead of silently keeping a default. A retired shape
    (the v29-v52 `mode` key, [claude.low], [codex.*]) is refused with its migration."""
    path = ROOT / "executors.toml"
    values: dict = {}
    if not path.exists():
        return values
    section = None
    rows = ", ".join(sorted(EXECUTOR_ROUTES))
    for n, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if re.match(r"^mode\s*=", line):
            raise SystemExit(
                f"executors.toml line {n}: the economy/flex presets were retired in workspace v53 — delete this line; "
                "the route table replaces them (flex was xhigh on both tiers: set effort = \"xhigh\" under [claude.mid] "
                f"and [claude.high] to keep it); run: {WORKFLOW_CMD} executor-route"
            )
        if re.match(r"^\[\s*codex\s*\.\s*[^\]]*\]\s*(?:#.*)?$", line):
            raise SystemExit(
                f"executors.toml line {n}: Codex support was removed in workspace v31 — "
                "this workspace ships Claude Code only, so drop this section"
            )
        m = re.match(r"^\[\s*claude\s*\.\s*([^\]\s]*)\s*\]\s*(?:#.*)?$", line)
        if m:
            name = m.group(1)
            if name in RETIRED_EXECUTOR_TIERS:
                raise SystemExit(
                    f"executors.toml line {n}: the {name} executor tier was retired in workspace v23 — "
                    "routing is two-tier now, so drop this section or move its settings to [claude.mid]"
                )
            if name not in EXECUTOR_ROUTES:
                raise SystemExit(f"executors.toml line {n}: unknown route {name} (valid: {rows})")
            section = name
            continue
        m = re.match(r'^(model|effort)\s*=\s*"([^"]*)"\s*(?:#.*)?$', line)
        if m:
            key, value = m.group(1), m.group(2)
            if section is None:
                raise SystemExit(f"executors.toml line {n}: key outside a section — put it under [claude.<row>] ({rows})")
            if (section, key) in values:
                raise SystemExit(f"executors.toml line {n}: duplicate {key} for [claude.{section}]")
            if key == "model" and not value:
                raise SystemExit(f"executors.toml line {n}: [claude.{section}] model must not be empty (efforts may be empty; models may not)")
            if key == "effort" and value and value not in EFFORT_LEVELS:
                raise SystemExit(
                    f"executors.toml line {n}: [claude.{section}] effort must be one of {', '.join(EFFORT_LEVELS)} "
                    f"— or \"\" to write no effort line (got {value!r})"
                )
            if key == "model" and section not in ROUTE_AGENT and value not in AGENT_MODEL_ALIASES:
                raise SystemExit(
                    f"executors.toml line {n}: [claude.{section}] model {value!r}: route {section} dispatches to another row's "
                    f"agent file, so its model must be an Agent-tool alias ({', '.join(AGENT_MODEL_ALIASES)}); a full model id "
                    f"or inherit works only on {', '.join(r for r in EXECUTOR_ROUTES if r in ROUTE_AGENT)}, whose agent files carry it"
                )
            values[(section, key)] = value
            continue
        if re.match(r"^(model|effort)\s*=", line):
            raise SystemExit(f'executors.toml line {n}: values must be double-quoted TOML strings, e.g. model = "sonnet" under [claude.<row>]')
        raise SystemExit(f"executors.toml line {n}: cannot parse {line!r} (expected [claude.<row>] with row one of {rows}, or model/effort = \"...\")")
    return values


def resolve_routes(overrides=None) -> dict:
    """{row: {model, effort, model_source, effort_source}} in EXECUTOR_ROUTES order: the engine
    defaults overlaid key by key with executors.toml. A source is `default`, `executors.toml`, or
    -- for a cheap key it does not override -- `mid row`; cheap resolves after mid, from mid's
    resolved values, so a [claude.mid] override carries over to an unset cheap row."""
    if overrides is None:
        overrides = read_executors_toml()
    resolved: dict = {}
    for row in sorted(EXECUTOR_ROUTES, key=lambda r: ROUTE_DEFAULTS[r] is None):  # inheriting rows last
        default = ROUTE_DEFAULTS[row]
        entry: dict = {}
        for key in ("model", "effort"):
            if (row, key) in overrides:
                entry[key], entry[f"{key}_source"] = overrides[(row, key)], "executors.toml"
            elif default is None:
                entry[key], entry[f"{key}_source"] = resolved["mid"][key], "mid row"
            else:
                entry[key], entry[f"{key}_source"] = default[key], "default"
        resolved[row] = entry
    return {row: resolved[row] for row in EXECUTOR_ROUTES}


def route_source(entry: dict) -> str:
    """One source for a resolved row, or `model <s> / effort <s>` when its two keys differ."""
    if entry["model_source"] == entry["effort_source"]:
        return entry["model_source"]
    return f"model {entry['model_source']} / effort {entry['effort_source']}"


def _patched_agent_md(text: str, model: str, effort: str) -> str:
    """Rewrite only the model:/effort: frontmatter lines of a .claude agent file. Every other line
    is kept verbatim -- `name:` included, which for a renamed agent in a nested install is its
    installed name (the `subagent_type`), so sync-agents never undoes a rename."""
    if not text.startswith("---\n"):
        raise SystemExit("agent file has no frontmatter")
    end = text.find("\n---\n", 4)
    if end == -1:
        raise SystemExit("agent file frontmatter is unterminated")
    lines = [l for l in text[4:end].split("\n") if not l.startswith("model:") and not l.startswith("effort:")]
    insert_at = next((i for i, l in enumerate(lines) if l.startswith("permissionMode:")), len(lines))
    lines[insert_at:insert_at] = [f"model: {model}"] + ([f"effort: {effort}"] if effort else [])
    return "---\n" + "\n".join(lines) + text[end:]


def installed_agent_name(name: str) -> str:
    """The name a managed agent is installed under: its canonical name, or -- in a nested install
    whose host already has an agent of that name -- the rename the installer recorded in
    `.agentic-nested.json` `renames.agents`. The installed file is `<installed name>.md` and its `name:`
    frontmatter (the `subagent_type`) is the installed name too; the installer writes both."""
    if NESTED is None:
        return name
    renames = NESTED.get("renames")
    table = renames.get("agents") if isinstance(renames, dict) else None
    installed = table.get(name) if isinstance(table, dict) else None
    return installed if isinstance(installed, str) and installed else name


def executor_agent_files(routes: dict) -> list:
    """(label, path, model, effort) for the 4 managed agent files (MANAGED_AGENT_FILES): the two
    slice-executor tiers from the mid and high rows, design-drafter from the high row (it is not a
    tier), and Explore from the explore row. research and cheap own no file. Labels stay canonical;
    paths resolve through the nested rename map (`installed_agent_name`)."""
    return [
        (label, CLAUDE_AGENTS / f"{installed_agent_name(agent)}.md", routes[row]["model"], routes[row]["effort"])
        for label, agent, row in MANAGED_AGENT_FILES
    ]


def executor_agent_drift(routes: dict) -> tuple:
    """([(path, desired text)] for agent files that disagree with the routes, [missing paths]); writes nothing."""
    changed, missing = [], []
    for _label, path, model, effort in executor_agent_files(routes):
        if not path.exists():
            missing.append(path)
            continue
        current = path.read_text(encoding="utf-8")
        desired = _patched_agent_md(current, model, effort)
        if desired != current:
            changed.append((path, desired))
    return changed, missing


def sync_agents(args: argparse.Namespace) -> None:
    overrides = read_executors_toml()
    routes = resolve_routes(overrides)
    config_present = (ROOT / "executors.toml").exists()
    legacy_env = ROOT / ".env"
    if legacy_env.exists() and "SLICE_EXECUTOR" in legacy_env.read_text(encoding="utf-8"):
        print("warning: .env holds SLICE_EXECUTOR_* keys, but tier config moved to executors.toml in v8 — .env is no longer read")
    drift, missing_paths = executor_agent_drift(routes)
    if not args.check:
        for path, desired in drift:
            write_text(path, desired)
    # Agent files live in the host when nested, so they are named from there (identical at root).
    changed = [shown(path) for path, _ in drift]
    missing = [shown(path) for path in missing_paths]
    for row in EXECUTOR_ROUTES:
        entry = routes[row]
        value = f"{entry['model']} @ {entry['effort'] or '(no effort line)'}"
        print(f"{row:<9} {value:<16} ({route_source(entry)})")
    print(f"config source: {f'executors.toml ({len(overrides)} override(s))' if config_present else 'defaults (no executors.toml)'}")
    for m in missing:
        print(f"missing agent file: {m}")
    if args.check:
        if changed or missing:
            print("out of sync with executors.toml/defaults:")
            for c in changed:
                print(f"- {c}")
            raise SystemExit(1)
        print("agent files in sync with executors.toml/defaults")
        return
    if changed:
        append_event("agents_synced", changed=changed, config_present=config_present)
        print("updated:")
        for c in changed:
            print(f"- {c}")
    else:
        print("already in sync; nothing written")
    if missing:
        raise SystemExit(1)


def _loopback_base_url():
    """ANTHROPIC_BASE_URL when its host is loopback (a local proxy such as ocx's Kiro sidecar), else None."""
    url = os.environ.get("ANTHROPIC_BASE_URL", "").strip()
    if not url:
        return None
    try:
        host = urlparse(url if "://" in url else f"http://{url}").hostname
    except ValueError:
        return None
    return url if host in LOOPBACK_HOSTS else None


def _route_fallback(row: str, model: str, routes: dict, proxy):
    """(model to dispatch, `fallback=` line or None) for one row under the environment: behind a
    loopback proxy (no Haiku 5.5) cheap takes the mid row's model and explore EXPLORE_PROXY_MODEL."""
    if proxy is None or row not in ("cheap", "explore"):
        return model, None
    target = routes["mid"]["model"] if row == "cheap" else EXPLORE_PROXY_MODEL
    if target == model:
        return model, None
    return target, f"fallback={row} model {model} -> {target} (loopback ANTHROPIC_BASE_URL {proxy}: ocx/Kiro serves no Haiku 5.5)"


def _route_env_warnings() -> list:
    """`warning=` lines for the environment variables that outrank a per-dispatch model or effort."""
    lines = []
    level = os.environ.get("CLAUDE_CODE_EFFORT_LEVEL", "").strip()
    if level:
        lines.append(f"warning=CLAUDE_CODE_EFFORT_LEVEL={level} is set and outranks every per-dispatch effort "
                     "(and every agent file's effort line); unset it for the route table's efforts to apply")
    force = os.environ.get("CLAUDE_CODE_SUBAGENT_MODEL_FORCE", "").strip()
    if force and force.lower() not in ("0", "false", "no"):
        lines.append(f"warning=CLAUDE_CODE_SUBAGENT_MODEL_FORCE={force} is set and overrides every model "
                     "(per-dispatch and frontmatter alike); unset it for the route table's models to apply")
    return lines


def slice_route(kind, risk, retry: bool) -> tuple:
    """(row, reason) for one dispatch: kind first, then risk, then attempt -- bump up, never down.
    A second attempt is always the high row; review, decomposition and co-work (the mockup span)
    route high by kind and research to the research row, whatever `risk` says; otherwise only a
    risk of exactly `low` reaches the mid row (implementation, fix) or the cheap row (docs, qa)."""
    if retry:
        return "high", "second attempt"
    if kind in ("review", "decomposition", "co-work"):
        return "high", f"kind {kind}"
    if kind == "research":
        return "research", "kind research"
    if risk != "low":
        return "high", f"risk {risk if risk not in (None, '') else 'unset'} (not low)"
    if kind in ("implementation", "fix"):
        return "mid", f"kind {kind} rated low"
    if kind in ("docs", "qa"):
        return "cheap", f"kind {kind} rated low"
    return "high", f"unknown kind {kind if kind not in (None, '') else 'unset'}"


def _dispatch_lines(row: str, routes: dict, proxy) -> tuple:
    """(the model..attribution lines for one dispatch on `row`, its fallback line or None)."""
    entry = routes[row]
    model, fallback = _route_fallback(row, entry["model"], routes, proxy)
    effort = entry["effort"]
    lines = [
        f"model={model}",
        f"pass_model={'yes' if model in AGENT_MODEL_ALIASES else 'no'}",
        f"effort={effort}",
        f"pass_effort={'yes' if effort else 'no'}",
        f"attribution={MODEL_ATTRIBUTION.get(model, model)}",
    ]
    return lines, fallback


def cmd_executor_route(args: argparse.Namespace) -> None:
    """Print the deterministic routing decision the orchestrator dispatches from, one key=value per
    line: bare, the resolved route table and the agent files' sync state; with a slice id, that
    slice's route (--retry: its second attempt); --drafter / --explore, the design subagent's and the
    lookup agent's. Reads executors.toml (a malformed one errors here) and writes nothing."""
    forms = [f for f, on in (("<slice_id>", args.slice is not None), ("--drafter", args.drafter), ("--explore", args.explore)) if on]
    if len(forms) > 1:
        raise SystemExit(f"executor-route: {' and '.join(forms)} are mutually exclusive; give at most one")
    if args.retry and args.slice is None:
        raise SystemExit("executor-route: --retry needs a <slice_id> (a second attempt is a slice's)")
    routes = resolve_routes()
    proxy = _loopback_base_url()
    if args.slice is not None:
        sdata = read_json(require_slice(args.slice) / "slice.json")
        kind, risk = sdata.get("kind"), sdata.get("risk")
        row, reason = slice_route(kind, risk, args.retry)
        tier = ROUTE_TIER[row]
        lines, fallback = _dispatch_lines(row, routes, proxy)
        print(f"slice={args.slice}")
        print(f"phase={args.slice.split('.', 1)[0]}")
        print(f"kind={kind if kind not in (None, '') else 'unset'}")
        print(f"risk={risk if risk not in (None, '') else 'unset'}")
        print(f"attempt={2 if args.retry else 1}")
        print(f"route={row}")
        print(f"reason={reason}")
        print(f"tier={tier}")
        print(f"subagent_type={installed_agent_name(ROUTE_AGENT[tier])}")
        print("\n".join(lines))
        extra = [fallback] if fallback else []
    elif args.drafter or args.explore:
        agent, row = ("design-drafter", DESIGN_DRAFTER_FOLLOWS) if args.drafter else (ROUTE_AGENT["explore"], "explore")
        lines, fallback = _dispatch_lines(row, routes, proxy)
        print(f"agent={agent}")
        print(f"route={row}")
        print(f"tier={ROUTE_TIER[row] or '-'}")
        print(f"subagent_type={installed_agent_name(agent)}")
        print("\n".join(lines))
        extra = [fallback] if fallback else []
    else:
        table = [("route", "tier", "model", "effort", "source")] + [
            (row, ROUTE_TIER[row] or "-", routes[row]["model"], routes[row]["effort"] or "(no effort line)", route_source(routes[row]))
            for row in EXECUTOR_ROUTES
        ]
        widths = [max(len(r[i]) for r in table) for i in range(4)]
        for r in table:
            print("  ".join(c.ljust(w) for c, w in zip(r, widths)) + "  " + r[4])
        drift, missing = executor_agent_drift(routes)
        stale = [shown(path) for path, _ in drift] + [f"{shown(path)} (missing)" for path in missing]
        if stale:
            print(f"agent files: out of sync: {', '.join(stale)} (run: {WORKFLOW_CMD} sync-agents)")
        else:
            print("agent files: in sync")
        extra = [f for f in (_route_fallback(row, routes[row]["model"], routes, proxy)[1] for row in EXECUTOR_ROUTES) if f]
        if proxy is None:
            extra.insert(0, "proxy=none")
        else:
            extra.insert(0, f"proxy={proxy} (loopback)")
    for line in extra + _route_env_warnings():
        print(line)


def cmd_record_dispatch(args: argparse.Namespace) -> None:
    """Append one `executor_dispatched` event to works/events.jsonl: the route, model and effort an
    executor ran on (copied from `executor-route`), the measured duration / tokens / tool uses from the
    Agent completion notification, and its verdict. A record, never a route validation: nothing else is
    written, no state changes."""
    sdata = read_json(require_slice(args.slice) / "slice.json")
    if not args.model.strip():
        raise SystemExit("record-dispatch: --model must be a non-empty model (the model= line executor-route printed)")
    tier = args.tier if args.tier is not None else ROUTE_TIER[args.route]
    if args.agent is not None:
        agent = args.agent
    elif tier is not None:
        agent = installed_agent_name(ROUTE_AGENT[tier])
    else:
        agent = installed_agent_name(ROUTE_AGENT[args.route])
    rec = {
        "slice": args.slice, "phase": sdata.get("phase_id") or args.slice.split(".", 1)[0],
        "kind": sdata.get("kind"), "risk": sdata.get("risk"),
        "route": args.route, "tier": tier, "agent": agent,
        "model": args.model, "effort": args.effort,
        "attribution": MODEL_ATTRIBUTION.get(args.model, args.model),
        "attempt": args.attempt, "verdict": args.verdict,
        "duration_ms": args.duration_ms, "tokens": args.tokens, "tool_uses": args.tool_uses,
        "note": args.note,
    }
    append_event("executor_dispatched", **rec)
    print("recorded=executor_dispatched")
    for key in ("slice", "route", "tier", "model", "effort", "attempt", "verdict", "duration_ms", "tokens", "tool_uses"):
        v = rec[key]
        print(f"{key}={'' if v is None else v}")


_DISPATCH_VERDICTS = ("done", "escalate", "needs_operator", "blocked", "failed")


def _dispatch_agg(records: list) -> dict:
    """Counts and sums over a group of executor_dispatched records."""
    durs = [r["duration_ms"] for r in records if isinstance(r.get("duration_ms"), (int, float))]
    toks = [r["tokens"] for r in records if isinstance(r.get("tokens"), (int, float))]
    agg = {"n": len(records)}
    for v in _DISPATCH_VERDICTS:
        agg[v] = sum(1 for r in records if r.get("verdict") == v)
    agg["retries"] = sum(1 for r in records if isinstance(r.get("attempt"), int) and r["attempt"] >= 2)
    agg["mean_min"] = round(sum(durs) / len(durs) / 60000, 1) if durs else None
    agg["total_min"] = round(sum(durs) / 60000, 1) if durs else None
    agg["tokens"] = sum(toks) if toks else None
    return agg


def _dispatch_groups(records: list, keyfn, order=None) -> dict:
    groups: dict = {}
    for r in records:
        groups.setdefault(keyfn(r), []).append(r)
    keys = [k for k in order if k in groups] if order else sorted(groups, key=lambda k: (-len(groups[k]), str(k)))
    return {k: _dispatch_agg(groups[k]) for k in keys}


def _dispatch_table(title: str, groups: dict, cols: list) -> list:
    header = [title] + [c[0] for c in cols]
    rows = [header]
    for key, agg in groups.items():
        rows.append([str(key)] + [("-" if agg[c[1]] is None else str(agg[c[1]])) for c in cols])
    widths = [max(len(r[i]) for r in rows) for i in range(len(header))]
    return ["  ".join(c.ljust(w) if i == 0 else c.rjust(w) for i, (c, w) in enumerate(zip(r, widths))).rstrip() for r in rows]


def cmd_dispatch_summary(args: argparse.Namespace) -> None:
    """Read works/events.jsonl back: the executor_dispatched records by route, by model @ effort and by
    kind (or, with --slice, one line per attempt). Read-only; blank and malformed lines are skipped."""
    records: list = []
    skipped = 0
    ev = WORKS / "events.jsonl"
    if ev.exists():
        for line in ev.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except ValueError:
                skipped += 1
                continue
            if isinstance(obj, dict) and obj.get("type") == "executor_dispatched":
                records.append(obj)
    if args.phase is not None:
        known = (ACTIVE / args.phase).is_dir() or any(r.get("phase") == args.phase for r in records) \
            or (ARCHIVED.is_dir() and any(ARCHIVED.glob(f"**/{args.phase}")))
        if not known:
            raise SystemExit(f"dispatch-summary: no such phase: {args.phase}")
        records = [r for r in records if r.get("phase") == args.phase]
    if args.slice is not None:
        if not any(r.get("slice") == args.slice for r in records) and not (ACTIVE / args.slice.split(".", 1)[0] / "slices" / args.slice).is_dir():
            raise SystemExit(f"dispatch-summary: no such slice: {args.slice}")
        records = [r for r in records if r.get("slice") == args.slice]
    by_route = _dispatch_groups(records, lambda r: r.get("route") or "?", order=EXECUTOR_ROUTES)
    by_model = _dispatch_groups(records, lambda r: f"{r.get('model') or '?'} @ {r.get('effort') or '(none)'}")
    by_kind = _dispatch_groups(records, lambda r: r.get("kind") or "unset")
    if args.json:
        print(json.dumps({"records": len(records), "by_route": by_route, "by_model_effort": by_model, "by_kind": by_kind,
                          "skipped_lines": skipped}, ensure_ascii=False, indent=2))
        return
    phases = sorted({r.get("phase") for r in records if r.get("phase")})
    stamps = [r.get("ts") for r in records if r.get("ts")]
    print(f"records={len(records)}")
    if not records:
        if skipped:
            print(f"skipped_lines={skipped}")
        print(f"hint=record a dispatch with: {WORKFLOW_CMD} record-dispatch <slice_id> --route … --model … --effort … --verdict …")
        return
    print(f"phases={','.join(phases)}")
    print(f"since={stamps[0] if stamps else '-'}")
    print(f"until={stamps[-1] if stamps else '-'}")
    if skipped:
        print(f"skipped_lines={skipped}")
    if args.slice is not None:
        for r in records:
            print(f"attempt={r.get('attempt')} route={r.get('route')} model={r.get('model')} effort={r.get('effort') or '(none)'} "
                  f"verdict={r.get('verdict')} duration_ms={r.get('duration_ms')} tokens={r.get('tokens')} ts={r.get('ts')}")
        return
    full = [("n", "n"), ("done", "done"), ("escalate", "escalate"), ("needs_op", "needs_operator"), ("blocked", "blocked"),
            ("failed", "failed"), ("retries", "retries"), ("mean_min", "mean_min"), ("total_min", "total_min"), ("tokens", "tokens")]
    short = [("n", "n"), ("done", "done"), ("escalate", "escalate"), ("retries", "retries"), ("tokens", "tokens")]
    for label, title, groups, cols in (("by route", "route", by_route, full), ("by model @ effort", "model @ effort", by_model, full),
                                       ("by kind", "kind", by_kind, short)):
        print()
        print(f"[{label}]")
        print("\n".join(_dispatch_table(title, groups, cols)))


def doc_index() -> dict:
    return read_json(DOCS / "index.json")


def write_doc_index(index: dict) -> None:
    index["last_rebuilt_at"] = now_iso()
    write_json(DOCS / "index.json", index)


def rebuild_docs() -> None:
    index = doc_index()
    for doc_id, info in index.get("docs", {}).items():
        latest = next((v for v in info.get("versions", []) if v["id"] == info.get("latest")), None)
        if not latest:
            raise SystemExit(f"latest version missing in docs/index.json for {doc_id}")
        src = ROOT / latest["path"]
        if not src.exists():
            raise SystemExit(f"latest doc file missing: {latest['path']}")
        write_text(ROOT / info["current_path"], src.read_text(encoding="utf-8"))
    write_doc_index(index)


def next_doc_version_id(doc_id: str, index: dict) -> tuple:
    nums = []
    for v in index["docs"][doc_id].get("versions", []):
        m = re.match(r"v(\d+)", v["id"])
        if m:
            nums.append(int(m.group(1)))
    num = max(nums, default=0) + 1
    return f"v{num:04d}", num


def head_commit() -> str:
    """The current HEAD sha, or "" where git cannot answer -- the provenance half of a doc's
    last-updated marker.

    Best effort and NEVER fatal: the engine has to keep working in a tarball copy, a fresh
    unpushed install or any checkout without git, so every failure (missing binary, not a repo,
    an empty repo with no commit yet, a timeout) records nothing instead of raising. Honest
    semantics: this is the commit the version was *created at* -- the version file itself lands
    in a later commit -- so the sha is provenance, while `created_at` and `source` are the
    staleness keys a reader actually judges by.

    Nested install: the HOST's HEAD -- the product state the doc describes -- never the nested
    repo's, which only holds workflow state. The same helper stamps a nested phase's host anchors.
    """
    try:
        proc = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(HOST_ROOT or ROOT), capture_output=True, text=True, timeout=10)
    except Exception:  # noqa: BLE001 - git is optional; a doc version must still be writable without it
        return ""
    sha = proc.stdout.strip()
    return sha if proc.returncode == 0 and re.fullmatch(r"[0-9a-f]{7,40}", sha) else ""


def doc_marker(version: dict) -> str:
    """One doc version's last-updated marker: when it was written, which slice consolidated it,
    and the commit it was written at -- the line `docs` prints under every doc.

    `commit` arrived in v39, so its two absences are reported differently and honestly: a key that
    is *missing* predates the field (pre-v39, and never backfilled -- a backfilled sha would mean
    "the commit that last touched the file", a different fact wearing the same name), while a key
    that is `null` means the write happened where git could not be read. Neither is an error.
    """
    if "commit" in version:
        sha = version.get("commit")
        commit = str(sha)[:12] if sha else "unknown (no git at write time)"
    else:
        commit = "unknown (pre-v39)"
    return f"updated={str(version.get('created_at', ''))[:10]} source={version.get('source') or 'unknown'} commit={commit}"


def new_doc_version(args: argparse.Namespace) -> None:
    doc_id = args.doc
    if doc_id not in DOC_TYPES:
        raise SystemExit(f"doc must be one of: {', '.join(sorted(DOC_TYPES))}")
    # Doc versions are allocated from a single `docs/index.json` (`max+1` per doc), so two streams
    # consolidating at once pick the same vNNNN and collide silently on the merge. Consolidation
    # therefore always runs on the default stream -- refuse here, before any allocation or write,
    # so a refusal leaves zero partial state.
    stream = current_stream(all_active_phases())
    if stream:
        raise SystemExit(f"this checkout is on parallel stream {stream}; doc consolidation runs on the default stream, never on a phase branch -- for a parallel phase defer it to the post-merge step (parallel-merge-finish, then doc-new-version, then parallel-consolidated)")
    index = doc_index()
    info = index["docs"][doc_id]
    latest_id = info["latest"]
    latest = next(v for v in info["versions"] if v["id"] == latest_id)
    base_body = strip_frontmatter((ROOT / latest["path"]).read_text(encoding="utf-8"))
    version_prefix, _ = next_doc_version_id(doc_id, index)
    version_id = f"{version_prefix}_{slugify(args.summary, 'update')}"
    rel = f"docs/versions/{doc_id}/{version_id}.md"
    dest = ROOT / rel
    if dest.exists():
        raise SystemExit(f"doc version already exists: {rel}")
    # The last-updated marker (v39). Written into both the frontmatter -- which `rebuild_docs`
    # copies verbatim into `docs/current`, so the marker reaches the file a reader opens -- and the
    # index entry `docs` reads. Absent git is recorded as `unknown`/null, never raised.
    commit = head_commit()
    frontmatter = (
        f"---\n"
        f"doc_id: {doc_id}\n"
        f"version: {version_prefix}\n"
        f"created_at: {now_iso()}\n"
        f"commit: {commit or 'unknown'}\n"
        f"source: {args.source}\n"
        f"summary: {args.summary}\n"
        f"previous: {latest_id}\n"
        f"---\n\n"
    )
    write_text(dest, frontmatter + base_body)
    info["latest"] = version_id
    info["versions"].append({
        "id": version_id, "path": rel, "created_at": now_iso(), "commit": commit or None,
        "source": args.source, "summary": args.summary, "previous": latest_id,
    })
    write_doc_index(index)
    rebuild_docs()
    append_event("doc_version_created", doc=doc_id, version=version_id, source=args.source)
    print(f"created doc version {doc_id}/{version_id}")
    print(f"edit_path={shown(dest)}")
    print(f"after editing, run: {WORKFLOW_CMD} rebuild-docs")
    # The split can only happen in a new version, and this is one -- so say it here, not only in
    # `validate`, where the reader is nowhere near an editable file.
    hint = oversized_sections_line(oversized_doc_sections([doc_id]))
    if hint:
        print(f"note: {hint}")
        print("note: you are writing that doc now -- if you split, split it in this version file, never in docs/current")


def cmd_docs(args: argparse.Namespace) -> None:
    """The durable-doc listing -- where an agent picks which sections to read, and therefore where
    each doc's last-updated marker and its staleness belong. Writes nothing."""
    index = doc_index()
    stale = stale_docs()
    for doc_id in sorted(index["docs"]):
        info = index["docs"][doc_id]
        latest = next(v for v in info["versions"] if v["id"] == info["latest"])
        print(f"{doc_id}: latest={info['latest']} current={shown_rel(info['current_path'])} latest_path={shown_rel(latest['path'])}")
        line = f"  {doc_marker(latest)}"
        owed = stale.get(doc_id)
        if owed:
            notes = sum(owed.values())
            line += (f" -- STALE: {notes} unconsolidated '## Doc impact' note(s) from {', '.join(sorted(owed))}"
                     f" are newer than this version; read them (docs-debt) before trusting this doc")
        print(line)
    hint = stale_docs_line(stale)
    if hint:
        print(hint)


def h2_sections(text: str) -> list:
    """`(heading, bytes)` for every `## ` section of a markdown document, biggest-unit-first order.

    A section runs from its heading to the next `## `, so deeper headings count as its body -- that
    is the unit a reader actually reads. Fenced blocks are skipped (a `## ` inside a shell example
    is a comment, not a heading), and the size is bytes, because bytes are what the reader pays.
    """
    lines = text.split("\n")
    fenced, starts = False, []
    for i, line in enumerate(lines):
        if line.startswith("```") or line.startswith("~~~"):
            fenced = not fenced
        elif not fenced and line.startswith("## "):
            starts.append(i)
    out = []
    for j, i in enumerate(starts):
        end = starts[j + 1] if j + 1 < len(starts) else len(lines)
        out.append((lines[i].strip(), len("\n".join(lines[i:end]).encode("utf-8"))))
    return out


def oversized_doc_sections(doc_ids=None, threshold: int = DOC_SECTION_WARN_BYTES) -> list:
    """Every `docs/current` H2 section past `threshold` bytes, biggest first: `(doc, heading, bytes)`.

    Measured on the generated current snapshots, because those are what a slice reads. Best effort
    and never fatal: a doc with no current file is skipped rather than reported, so a partial or
    foreign workspace still validates. `doc_ids` narrows it to the doc being written.
    """
    wanted = sorted(DOC_TYPES if doc_ids is None else set(doc_ids) & DOC_TYPES)
    found = []
    for doc_id in wanted:
        path = DOCS / "current" / f"{doc_id}.md"
        if not path.exists():
            continue
        found += [(doc_id, heading, size) for heading, size in h2_sections(path.read_text(encoding="utf-8")) if size > threshold]
    return sorted(found, key=lambda item: -item[2])


def oversized_sections_line(sections: list, limit: int = 3) -> str:
    """One advisory line naming the biggest oversized sections, or "" when there are none -- shared
    by `validate` and `doc-new-version` so the warning and the write-time hint can never word it
    differently (the `consolidation_debt_line` pattern).

    Advisory everywhere, never an error and never a sweep order: splitting is per-doc judgment at
    the next consolidation, and a small doc whose few sections are its whole content is fine as it is.
    """
    if not sections:
        return ""
    def short(heading: str) -> str:
        return heading if len(heading) <= 60 else heading[:57] + "..."
    named = "; ".join(f"{doc}.md '{short(heading)}' {size:,} B" for doc, heading, size in sections[:limit])
    if len(sections) > limit:
        named += f"; +{len(sections) - limit} more"
    return (f"oversized_doc_sections={len(sections)} (H2 sections over {DOC_SECTION_WARN_BYTES:,} B, so"
            f" \"read only the sections the work touches\" is no longer a small read): {named}"
            f" -- split them at the next consolidation (a docs phase), by per-doc judgment, never a sweep")


def validate_docs(errors: list) -> None:
    if not (DOCS / "index.json").exists():
        errors.append("missing docs/index.json")
        return
    index = doc_index()
    for doc_id in DOC_TYPES:
        info = index.get("docs", {}).get(doc_id)
        if not info:
            errors.append(f"missing doc index entry: {doc_id}")
            continue
        # Version numbers must be unique per doc: `next_doc_version_id` allocates `max+1`, so two
        # entries claiming the same vNNNN means a collision already happened (two streams, or a
        # hand-resolved merge of docs/index.json) and one version is silently absent from
        # docs/current. Fail loudly instead.
        seen_nums = {}
        for version in info.get("versions", []):
            m = re.match(r"v(\d+)", str(version.get("id", "")))
            if not m:
                continue
            num = int(m.group(1))
            if num in seen_nums:
                errors.append(f"duplicate doc version number in docs/index.json: {doc_id} v{num:04d} claimed by both {seen_nums[num]} and {version.get('id')}")
            else:
                seen_nums[num] = version.get("id")
        latest = next((v for v in info.get("versions", []) if v.get("id") == info.get("latest")), None)
        if not latest:
            errors.append(f"missing latest doc version entry: {doc_id}")
            continue
        latest_path = ROOT / latest["path"]
        current_path = ROOT / info["current_path"]
        if not latest_path.exists():
            errors.append(f"missing latest doc file: {latest['path']}")
        if not current_path.exists():
            errors.append(f"missing current doc file: {info['current_path']}")
        if latest_path.exists() and current_path.exists() and latest_path.read_text(encoding="utf-8") != current_path.read_text(encoding="utf-8"):
            errors.append(f"current doc is stale; run rebuild-docs: {doc_id}")


def phase_dirs() -> list:
    if not ACTIVE.exists():
        return []
    return sorted([p for p in ACTIVE.iterdir() if p.is_dir() and (p / "phase.json").exists()], key=lambda p: read_json(p / "phase.json").get("order", 999999))


def slice_dirs(phase_dir: Path) -> list:
    slices = phase_dir / "slices"
    if not slices.exists():
        return []
    return sorted([p for p in slices.iterdir() if p.is_dir() and (p / "slice.json").exists()], key=lambda p: read_json(p / "slice.json").get("order", 999999))


def all_active_phases() -> list:
    phases = []
    for pdir in phase_dirs():
        data = read_json(pdir / "phase.json")
        data["path"] = str(pdir.relative_to(ROOT))
        data["slices"] = []
        for sdir in slice_dirs(pdir):
            sdata = read_json(sdir / "slice.json")
            sdata["path"] = str(sdir.relative_to(ROOT))
            data["slices"].append(sdata)
        phases.append(data)
    return phases


def deferred_jobs() -> dict:
    groups = {"open": [], "promoted": [], "dropped": []}
    for label, base in [("open", DEFERRED_OPEN), ("promoted", DEFERRED_PROMOTED), ("dropped", DEFERRED_DROPPED)]:
        if not base.exists():
            continue
        for ddir in sorted([p for p in base.iterdir() if p.is_dir()]):
            djson = ddir / "deferred.json"
            if not djson.exists():
                continue
            data = read_json(djson)
            data["path"] = str(ddir.relative_to(ROOT))
            groups[label].append(data)
    return groups


def clean_cell(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, dict):
        if "slice_id" in value:
            value = value.get("slice_id") or value
        elif "id" in value:
            value = value.get("id") or value
        else:
            value = json.dumps(value, ensure_ascii=False)
    return str(value).replace("|", "\\|").replace("\n", " ")


def status_box(status: object) -> str:
    """Dashboard checkbox glyph: done -> x, pending (waiting on operator) -> ~, ready (plan approved) -> r, else blank."""
    return "x" if status == "done" else "~" if status == "pending" else "r" if status == "ready" else " "


def rebuild_deferred_dashboard(groups=None) -> None:
    groups = groups or deferred_jobs()
    open_count = len(groups.get("open", []))
    promoted_count = len(groups.get("promoted", []))
    dropped_count = len(groups.get("dropped", []))
    lines = [
        "# Deferred Jobs", "", "> Generated dashboard. Do not put detailed deferred context here; edit each `works/deferred/<state>/<DID>/` folder instead.", "",
        "## Summary", "",
        f"- Open: `{open_count}`", f"- Promoted: `{promoted_count}`", f"- Dropped: `{dropped_count}`", "",
        "## Open", "", "| ID | Status | Title | Source | Trigger | Path |", "|---|---|---|---|---|---|",
    ]
    if not groups.get("open"):
        lines.append("| - | - | - | - | - | - |")
    for d in groups.get("open", []):
        lines.append(f"| `{clean_cell(d.get('id'))}` | `{clean_cell(d.get('status'))}` | {clean_cell(d.get('title'))} | {clean_cell(d.get('source'))} | {clean_cell(d.get('trigger'))} | `{clean_cell(d.get('path'))}` |")
    lines.extend(["", "## Promoted", "", "| ID | Status | Title | Promoted To | Path |", "|---|---|---|---|---|"])
    if not groups.get("promoted"):
        lines.append("| - | - | - | - | - |")
    for d in groups.get("promoted", []):
        lines.append(f"| `{clean_cell(d.get('id'))}` | `{clean_cell(d.get('status'))}` | {clean_cell(d.get('title'))} | `{clean_cell(d.get('promoted_to'))}` | `{clean_cell(d.get('path'))}` |")
    lines.extend(["", "## Dropped", "", "| ID | Status | Title | Reason | Path |", "|---|---|---|---|---|"])
    if not groups.get("dropped"):
        lines.append("| - | - | - | - | - |")
    for d in groups.get("dropped", []):
        lines.append(f"| `{clean_cell(d.get('id'))}` | `{clean_cell(d.get('status'))}` | {clean_cell(d.get('title'))} | {clean_cell(d.get('dropped_reason'))} | `{clean_cell(d.get('path'))}` |")
    lines.append("")
    write_text(WORKS / "deferred.md", "\n".join(lines))


def phase_execution(data) -> dict:
    """The phase's parallel-execution block, or None when it belongs to the default stream.

    Shape (all fields optional in the file, absence of the whole block = today's behavior):

        "execution": {
          "mode": "parallel",              # "parallel" = own stream; "default" (pinned, v42) and anything else = default stream
          "branch": "phase/P13-some-slug", # required when parallel; the stream key
          "worktree": "/path or null",     # informational (null on a plain clone)
          "consolidation": "pending"       # "pending" until the post-merge doc consolidation, then "done"
        }

    A nested install (P35) adds the host half of the worktree pair: `host_worktree`, `host_branch`,
    `host_base`, `host_base_sha`, `host_branch_created` and `base_branch`; there `worktree` is the
    NESTED worktree (`<host_worktree>/workflow`). See `_nested_execution_problems`.

    Read the block only through this helper so every caller agrees on what "parallel" means.
    """
    if not isinstance(data, dict):
        return None
    execution = data.get("execution")
    if not isinstance(execution, dict) or execution.get("mode") not in EXECUTION_MODES:
        return None
    return execution


def phase_in_flight(data) -> bool:
    """True when a phase is stamped for its own worktree and is still running there (P35.S7, closes D57).

    It has a parallel execution block (`phase_execution`) AND either still holds a worktree
    (`execution.worktree` is not null: running, or merged but not yet torn down) or has not reached
    `done`. A stamped phase that is `done` with its worktree torn down is history: it is not in
    flight, so `## Streams` and `next`'s `parallel_phases_elsewhere` skip it. Accepts a phase record
    or a `works/index.json` entry; both carry `status` and `execution`.
    """
    execution = phase_execution(data)
    if not execution:
        return False
    return execution.get("worktree") is not None or data.get("status") != "done"


NESTED_EXECUTION_HOST_KEYS = ("host_worktree", "host_branch", "host_base", "host_base_sha", "host_branch_created")


def _nested_execution_problems(phase_id: str, execution: dict) -> list:
    """`validate`'s checks on the host half of a parallel execution block (P35), [] when sound.

    A nested `parallel-start` stamps five host keys -- `host_worktree` (the host worktree; null once
    torn down), `host_branch`, `host_base` (the ref as resolved), `host_base_sha`, `host_branch_created`
    -- plus `base_branch` (the nested repo's branch at start). The five appear together, and only in a
    nested install; `base_branch` comes with them there, and is otherwise only type-checked (a root
    stamp of it is additive). `worktree` is the nested worktree: `<host_worktree>/<workflow>` while
    both are set. A block without any of them (every at-root block, and a legacy one) is untouched."""
    problems = []
    present = [k for k in NESTED_EXECUTION_HOST_KEYS if k in execution]
    if "base_branch" in execution:
        value = execution.get("base_branch")
        if value is not None and not (isinstance(value, str) and value.strip()):
            problems.append(f"phase {phase_id} has invalid execution.base_branch {value!r}; expected the nested repo's branch name or null")
    if not present:
        return problems
    if NESTED is None:
        problems.append(f"phase {phase_id} has nested-only execution keys ({', '.join(present)}) in an at-root install; they are written only by a nested parallel-start")
        return problems
    missing = [k for k in (*NESTED_EXECUTION_HOST_KEYS, "base_branch") if k not in execution]
    if missing:
        problems.append(f"phase {phase_id} has a partial nested execution block: missing {', '.join(missing)} (parallel-start writes all six together)")
    for key in ("host_branch", "host_base"):
        value = execution.get(key)
        if key in execution and not (isinstance(value, str) and value.strip()):
            problems.append(f"phase {phase_id} has invalid execution.{key} {value!r}; expected a non-empty string")
    sha = execution.get("host_base_sha")
    if "host_base_sha" in execution and not (isinstance(sha, str) and re.fullmatch(r"[0-9a-f]{7,64}", sha)):
        problems.append(f"phase {phase_id} has invalid execution.host_base_sha {sha!r}; expected a host commit sha")
    created = execution.get("host_branch_created")
    if "host_branch_created" in execution and not isinstance(created, bool):
        problems.append(f"phase {phase_id} has invalid execution.host_branch_created {created!r}; expected true or false")
    host_wt = execution.get("host_worktree")
    if host_wt is not None and not isinstance(host_wt, str):
        problems.append(f"phase {phase_id} has invalid execution.host_worktree {host_wt!r}; expected a path string or null")
    worktree = execution.get("worktree")
    if isinstance(host_wt, str) and isinstance(worktree, str) and HOST_ROOT is not None:
        expected = os.path.normpath(os.path.join(host_wt, os.path.relpath(ROOT, HOST_ROOT)))
        if os.path.normpath(worktree) != expected:
            problems.append(f"phase {phase_id} has execution.worktree {worktree!r}, but the nested worktree of host_worktree {host_wt!r} is {expected!r}")
    return problems


def phase_pinned(data) -> bool:
    """True when the phase carries v42's legacy pin (`execution.mode == "default"`).

    Since v43 the default stream is the default, so nothing writes this block any more --
    `parallel-skip` and `new-phase --on-main` are no-ops. It is still honoured where it
    exists: `parallel-start` refuses a pinned phase rather than overriding a deliberate pin,
    and the hints skip it. Everything else treats it exactly like a phase with no block,
    because `phase_execution` returns None for it."""
    execution = data.get("execution") if isinstance(data, dict) else None
    return isinstance(execution, dict) and execution.get("mode") == PINNED_MODE


def phase_consolidation(data) -> str:
    """A phase's durable-doc consolidation debt: "pending", "done", or None (nothing owed).

    Every phase defers consolidation: a passing review verifies the `## Doc impact` list and
    creates no doc versions, so the debt is stamped there ("pending") and paid later by an
    operator-created docs phase (`doc-new-version` per note, then `docs-consolidated <P>`).

    Read through this helper only, so every caller agrees on what "owes docs" means:

        "consolidation": "pending" | "done" | absent   # top-level in phase.json

    Backward compatible in both directions. v24-v37 stamped the identical debt inside the
    parallel `execution` block, so that field is the fallback and no phase.json needs migrating;
    a phase.json carrying neither (every phase reviewed before this release, and every adopter
    file) owes nothing and archives exactly as it always did.
    """
    if not isinstance(data, dict):
        return None
    state = data.get("consolidation")
    if state in CONSOLIDATION_STATES:
        return state
    if state is None:
        execution = phase_execution(data)
        if execution and execution.get("consolidation") in CONSOLIDATION_STATES:
            return execution["consolidation"]
    return None  # absent, or malformed -> `validate` reports it; no debt is invented


def set_phase_consolidation(data: dict, state: str) -> None:
    """Write the debt to the top-level key, mirroring it into a parallel `execution` block so the
    parallel commands and `parallel-status` keep reading the same truth from the field they know."""
    data["consolidation"] = state
    execution = phase_execution(data)
    if execution is not None:
        execution["consolidation"] = state


def phase_doc_impact_notes(pdir: Path) -> list:
    """The `## Doc impact` bullets in a phase's notebook -- what a docs phase consolidates from.

    Real notes only: the italic seed line, blanks and an explicit `- (none ...)` placeholder are
    not debt, and a phase with no notebook or no section owes nothing.
    """
    path = pdir / "phase.md"
    if not path.exists():
        return []
    notes, inside = [], False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            inside = line.strip().lower() == "## doc impact"
            continue
        if not inside:
            continue
        text = line.strip()
        if not (text.startswith("- ") or text.startswith("* ")):
            continue
        body = text[2:].strip()
        if not body or body.startswith("_") or re.match(r"\(?none\b", body, re.I):
            continue
        notes.append(body)
    return notes


def doc_impact_docs(note: str) -> list:
    """The durable docs one `## Doc impact` note touches, read off the `<doc>.md: ...` convention.

    A note names its doc(s) in prose, so this is a best-effort read against the known `DOC_TYPES`
    only -- one note may name several docs (`operations.md: ...; qa.md: ...`) and a note naming
    none is reported unassigned rather than guessed at. Nothing routes on it: `docs-debt` groups
    the worklist with it, and the operator still reads the note.
    """
    found = [d for d in sorted(DOC_TYPES) if re.search(rf"\b{re.escape(d)}\.md\b", note, re.I)]
    return found


def phases_owing_consolidation(phases: list) -> list:
    """Every active phase whose doc consolidation is still `pending` -- the debt list, in one place
    so `parallel-merge-finish`, the archiving guard and any later surfacing all read the same set."""
    return [p for p in phases if phase_consolidation(p) == "pending"]


def consolidation_command(phase) -> str:
    """The command that pays one phase's debt. Parallel phases keep their post-merge twin, so
    the archiving guard, `next` and `validate` can never name a command the engine would refuse."""
    return "parallel-consolidated" if phase_execution(phase) else "docs-consolidated"


def phase_consolidates(data) -> list:
    """The phase ids a docs phase declared it pays: the optional top-level `"consolidates"` list that
    `new-phase --consolidates` writes (v51), `[]` when the key is absent or malformed (`validate`
    reports a malformed one). It is the ONLY marker of a docs phase -- nothing reads a phase's name
    or intent text to guess -- and a phase that carries none is simply not one, so no phase.json
    needs migrating."""
    value = data.get("consolidates") if isinstance(data, dict) else None
    if not isinstance(value, list):
        return []
    return [v for v in value if isinstance(v, str)]


def consolidation_cover(phases: list) -> dict:
    """`{debt_phase_id: [covering phase, ...]}` -- which live docs phase already pays which phase's
    debt: every active, not-`done` phase whose `consolidates` names it. A finished docs phase covers
    nothing (it either paid the debt or it did not), so rotate proposes again rather than trusting
    it. Read by `docs-debt` ("paid by") and `rotate-backlog` (no duplicate docs phase)."""
    cover = {}
    for phase in phases:
        if phase.get("status") == "done":
            continue
        for pid in phase_consolidates(phase):
            cover.setdefault(pid, []).append(phase)
    return cover


def next_phase_id() -> str:
    """`P<n>`, one above the highest phase number across the active AND archived phases: an archived
    id is spent, so reusing it would collide in history. Archived phases are read from their
    `archive_manifest.json` `phase_id`, falling back to the `_P<N>_` in the folder name."""
    numbers = []
    for pdir in phase_dirs():
        match = re.fullmatch(r"P([0-9]+)", str(read_json(pdir / "phase.json").get("id", "")))
        if match:
            numbers.append(int(match.group(1)))
    if ARCHIVED.exists():
        for adir in ARCHIVED.iterdir():
            if not adir.is_dir():
                continue
            pid = ""
            manifest = adir / "archive_manifest.json"
            if manifest.exists():
                try:
                    pid = str(read_json(manifest).get("phase_id", ""))
                except (ValueError, OSError):
                    pid = ""
            match = re.fullmatch(r"P([0-9]+)", pid) or re.search(r"_P([0-9]+)_", adir.name)
            if match:
                numbers.append(int(match.group(1)))
    return f"P{max(numbers, default=0) + 1}"


def stale_docs(phases=None) -> dict:
    """`{doc: {phase_id: note_count}}` -- every durable doc named by a `## Doc impact` note that no
    consolidation has paid yet. The doc-side view of the same debt `consolidation_debt_line` states
    phase-side.

    Why it matters: an owed note is evidence *newer* than the doc's latest version, so on that
    subject `docs/current` trails the code. The doc is then stale evidence to read against the
    notes, never current truth -- which is a fact about the doc a reader is choosing, not about the
    phase, so it is surfaced where docs are read.

    Composed from the helpers that already exist (`phases_owing_consolidation`,
    `phase_doc_impact_notes`, `doc_impact_docs`) so `docs`, `validate` and `docs-debt` can never
    disagree about which docs are affected. Best effort, exactly like `doc_impact_docs`: a note
    naming no known doc is counted under `UNASSIGNED_DOC` rather than guessed at, and a phase whose
    notebook is gone contributes nothing instead of raising.
    """
    owing = phases_owing_consolidation(all_active_phases() if phases is None else phases)
    per_doc = {}
    for phase in owing:
        pdir = ROOT / phase["path"] if phase.get("path") else ACTIVE / str(phase.get("id"))
        for note in phase_doc_impact_notes(pdir):
            for doc in doc_impact_docs(note) or [UNASSIGNED_DOC]:
                per_doc.setdefault(doc, {}).setdefault(phase["id"], 0)
                per_doc[doc][phase["id"]] += 1
    return per_doc


def stale_docs_line(stale: dict) -> str:
    """One advisory `key=value` line naming the stale docs, or "" when none are -- shared by `docs`
    and `validate` so the listing and the warning can never word it differently (the
    `consolidation_debt_line` / `oversized_sections_line` pattern).

    Distinct from `consolidation_owed=`, which names the *phases* that owe and the command that
    pays: this names the *docs* a reader must not trust yet. Advisory everywhere, never an error --
    operator-paced consolidation is the design (v39 took explicit staleness instead of a cadence),
    so this must not fail CI or block the loop; it must only stop being silent.

    Deliberately NOT gated on `CONSOLIDATION_DEBT_MIN_PHASES`: that knob tunes how loud the debt is,
    and a debt can reasonably wait for a batch -- but staleness is a fact about the doc a reader is
    holding right now, and no cadence setting may quiet it.
    """
    named = sorted(d for d in stale if d != UNASSIGNED_DOC)
    if not named:
        return ""
    phases = sorted({pid for doc in named for pid in stale[doc]})
    notes = sum(sum(stale[doc].values()) for doc in named)
    return (f"stale_docs={', '.join(named)} ({len(named)} doc(s) named by {notes} unconsolidated"
            f" '## Doc impact' note(s) from {', '.join(phases)}; docs/current is older than those notes, so"
            f" for those subjects it is stale evidence to check against them, never current truth"
            f" -- read them with docs-debt)")


def consolidation_debt_line(phases: list) -> str:
    """One advisory `key=value` line naming every phase that owes durable-doc consolidation, or
    "" when nothing does -- shared by `next` and `validate` so the two can never word it differently.

    Advisory everywhere: this is expected operator-paced state, not a fault. `validate` prints it
    as a warning and still exits 0, and `next` prints it without changing what it selects.
    Accepts either phase records or `works/index.json` entries; both are read through
    `phase_consolidation()` / `phase_execution()`, never off a raw field.
    """
    # A stamped phase still running (not `done`) has stamped `execution.consolidation: "pending"` since
    # parallel-start but owes nothing until its review passes (P35.S7); a `done` one owes, as before.
    owing = [p for p in phases_owing_consolidation(phases) if not (phase_execution(p) and p.get("status") != "done")]
    if len(owing) < CONSOLIDATION_DEBT_MIN_PHASES:
        return ""
    ids = ", ".join(p["id"] for p in owing)
    plural = "phase owes" if len(owing) == 1 else "phases owe"
    line = (f"consolidation_owed={ids} ({len(owing)} {plural} durable-doc consolidation; docs/current trails the code"
            f" until a docs phase runs doc-new-version over each '## Doc impact' list, then: docs-consolidated <P>)")
    merged = [p["id"] for p in owing if consolidation_command(p) == "parallel-consolidated"]
    if merged:
        line += f" -- {', '.join(merged)} came from a parallel branch: pay those with parallel-consolidated, on the default stream"
    return line


def new_acceptance() -> dict:
    """A fresh, undeclared operator acceptance gate. Five fields, no more."""
    return {"required": None, "walkthrough": None, "requested_at": None, "cleared_at": None, "note": None}


def phase_acceptance(data) -> dict:
    """The phase's operator acceptance gate, or None when the phase carries none (legacy).

    Shape (stamped by `new_phase` on every phase created from workspace v32 on):

        "acceptance": {
          "required": null,        # null = undeclared | true = operator-visible | false = waived
          "walkthrough": null,     # the concrete walkthrough text, recorded when the gate opens
          "requested_at": null,    # stamped by `accept-gate <P> --open`
          "cleared_at": null,      # stamped by `accept-gate <P> --clear`
          "note": null             # the operator's clearing note, or the waive reason
        }

    Absence of the whole block means legacy (an installer `--update` never touches `works/`):
    `review-phase --verdict pass` is allowed, with one advisory line and nothing more. Read the
    block only through this helper so every caller agrees on what "gated" means.
    """
    if not isinstance(data, dict):
        return None
    acceptance = data.get("acceptance")
    if not isinstance(acceptance, dict):
        return None
    required = acceptance.get("required")
    if not (required is None or isinstance(required, bool)):
        return None
    return acceptance


def acceptance_gate_is_open(data) -> bool:
    """True when the phase is waiting on the operator to walk the running product."""
    acceptance = phase_acceptance(data)
    return bool(acceptance and acceptance.get("required") is True
                and acceptance.get("requested_at") and not acceptance.get("cleared_at"))


def git_current_branch() -> str:
    """The checkout's current branch name, or None (detached HEAD, no git, not a repo).

    `symbolic-ref` first because it is right on a branch that has no commit yet (where
    `rev-parse --abbrev-ref HEAD` fails); `rev-parse` as the fallback. Any failure is
    silent: a workspace without git, or outside a repo, must keep working unchanged.
    """
    for cmd in (["git", "symbolic-ref", "--short", "-q", "HEAD"], ["git", "rev-parse", "--abbrev-ref", "HEAD"]):
        try:
            proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=10)
        except Exception:  # noqa: BLE001 - git is optional; fall back to the default stream
            return None
        if proc.returncode != 0:
            continue
        branch = proc.stdout.strip()
        if not branch or branch == "HEAD":  # empty, or detached HEAD
            return None
        return branch
    return None


def current_stream(phases: list) -> str:
    """The parallel stream this checkout is in, or None for the default stream.

    Stream membership is the current git branch matched against the phases' stamped
    `execution.branch` -- which works identically in a `git worktree` and in a plain
    clone on another machine, and needs no marker file. Git is consulted only when at
    least one active phase is actually opted in, so an untouched workspace never shells out.
    In a nested install (P35) the key is the NESTED repo's branch -- `git_current_branch()` reads
    ROOT, the repo that owns the state -- never the host's, whose branch names follow the host's
    custom and carry no workspace IDs.
    """
    branches = set()
    for phase in phases:
        execution = phase_execution(phase)
        if execution and execution.get("branch"):
            branches.add(execution["branch"])
    if not branches:
        return None
    branch = git_current_branch()
    return branch if branch in branches else None


def stream_phases(phases: list, stream) -> list:
    """The phases the current stream may select from.

    Default stream (`stream` is None): every phase except the ones running in their own worktree (a pinned phase has no branch and stays here).
    Parallel stream: only the phase stamped with that branch. Selection, and therefore the
    `works/state.json` pointer and the `pending` halt, is scoped to one stream this way;
    the dashboards still list every active phase folder.
    """
    scoped = []
    for phase in phases:
        execution = phase_execution(phase)
        if stream is None:
            if execution is None:
                scoped.append(phase)
        elif execution and execution.get("branch") == stream:
            scoped.append(phase)
    return scoped


def resolve_current(phases: list) -> tuple:
    for phase in phases:
        if phase.get("status") == "done":
            continue
        current_phase = phase["id"]
        if phase.get("status") in ("blocked", "pending"):
            return current_phase, None, None
        open_slices = [s for s in phase["slices"] if s.get("status") != "done"]
        if open_slices:
            return current_phase, open_slices[0]["id"], open_slices[1]["id"] if len(open_slices) > 1 else None
        return current_phase, None, None
    return None, None, None


def operator_wait_target(phases: list, current_phase, current_slice):
    """The phase or slice id awaiting operator co-work (status `pending`), else None.
    `pending` means the operator must validate or run something; selection halts
    until it is cleared back to `in_progress`. Distinct from `blocked`."""
    for phase in phases:
        if phase["id"] != current_phase:
            continue
        if phase.get("status") == "pending":
            return phase["id"]
        cur = next((s for s in phase["slices"] if s["id"] == current_slice), None)
        if cur and cur.get("status") == "pending":
            return current_slice
        break
    return None


SLICES_BEGIN = "<!-- slices:begin -->"
SLICES_END = "<!-- slices:end -->"
# WORKFLOW_CMD is the literal `python3 scripts/workflow.py` at root (so this line stays byte-identical to
# works/templates/phase.md); a nested install's template is installed with the host-relative prefix, so
# its regenerated line carries the same one.
SLICES_GUIDANCE = f"_Generated by `{WORKFLOW_CMD} rebuild` from each slice's `slice.json`; never hand-edit this block._"


def render_slices_block(pdir: Path, phase: dict) -> str:
    """The body of the generated `## Slices` table: one row per slice, in `order`.

    This is the ONLY generated region of a phase notebook -- everything around it is the
    executors' bounded, hand-written state doc, which is why phase.md is deliberately not
    in GENERATED_FILES.
    """
    lines = [SLICES_GUIDANCE, "", "| Slice | Name | Kind / risk | Status | Outcome | Result |", "|---|---|---|---|---|---|"]
    for s in phase.get("slices", []):
        sid = s.get("id", "")
        has_result = (pdir / "slices" / str(sid) / "result.md").exists()
        result = f"[result.md](slices/{clean_cell(sid)}/result.md)" if has_result else "\u2014"
        outcome = clean_cell(s.get("outcome")) or "\u2014"
        lines.append(
            f"| `{clean_cell(sid)}` | {clean_cell(s.get('name', ''))} | "
            f"`{clean_cell(s.get('kind', ''))} / {clean_cell(s.get('risk', ''))}` | "
            f"`{clean_cell(s.get('status', ''))}` | {outcome} | {result} |"
        )
    return "\n".join(lines)


def refresh_phase_md_slices(pdir: Path, phase: dict) -> None:
    """Splice the generated slice table between the two markers of an active phase's notebook.

    A marker counts only when it is alone on its line: notebooks that merely *quote* the
    literals in prose (a plan or a decomposition table describing this very block) must not
    be spliced. No markers -> return untouched, so legacy phases and adopters who deleted
    the block stay a silent no-op, never a migration. Writes only when the spliced text
    actually differs, so plain `next`/`rebuild` calls do not dirty every notebook in the tree.
    """
    path = pdir / "phase.md"
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")
    start = next((i for i, ln in enumerate(lines) if ln.strip() == SLICES_BEGIN), None)
    end = next((i for i in range(start + 1, len(lines)) if lines[i].strip() == SLICES_END), None) if start is not None else None
    if start is None or end is None:
        return
    updated = "\n".join(lines[:start + 1] + render_slices_block(pdir, phase).split("\n") + lines[end:])
    if updated != text:
        write_text(path, updated)


def phase_md_size(pdir: Path) -> tuple:
    """(lines, bytes) of a phase notebook; (0, 0) when absent.

    Both numbers are reported, but only the byte count is judged against
    PHASE_MD_BUDGET (v39). Shared by `validate` (warning) and `finish-slice` (size print)
    so the two can never disagree about what "over budget" means.
    """
    path = pdir / "phase.md"
    if not path.exists():
        return (0, 0)
    text = path.read_text(encoding="utf-8")
    return (len(text.splitlines()), len(text.encode("utf-8")))


def rebuild_index_and_state() -> None:
    phases = all_active_phases()
    # Selection (pointer + operator halt) is scoped to this checkout's stream; the
    # dashboards below still list every active phase, parallel ones included.
    stream = current_stream(phases)
    selectable = stream_phases(phases, stream)
    current_phase, current_slice, next_slice = resolve_current(selectable)
    waiting_on = operator_wait_target(selectable, current_phase, current_slice)
    deferred = deferred_jobs()
    rebuilt_at = now_iso()
    index = {
        "active_phases": [
            {
                "id": p["id"], "name": p["name"], "objective": p["objective"], "status": p["status"],
                "order": p.get("order"), "path": p["path"],
                "review_status": p.get("review", {}).get("status"),
                "current_slice": next((s["id"] for s in p["slices"] if s.get("status") != "done"), None),
                "slice_count": len(p["slices"]),
                "done_slice_count": sum(1 for s in p["slices"] if s.get("status") == "done"),
                **({"execution": phase_execution(p)} if phase_execution(p) else {}),
                **({"pinned": True} if phase_pinned(p) else {}),
                **({"consolidation": phase_consolidation(p)} if phase_consolidation(p) else {}),
            } for p in phases
        ],
        "deferred_open_count": len(deferred.get("open", [])),
        "deferred_promoted_count": len(deferred.get("promoted", [])),
        "deferred_dropped_count": len(deferred.get("dropped", [])),
        "last_rebuilt_at": rebuilt_at,
    }
    write_json(WORKS / "index.json", index)
    mode = "waiting" if waiting_on else ("phase" if current_phase else "idle")
    state = {"current_phase": current_phase, "current_slice": current_slice, "next_slice": next_slice, "waiting_on_operator": waiting_on, "mode": mode}
    if stream:  # only ever present in a parallel-phase checkout
        state["stream"] = stream
    state["updated_at"] = rebuilt_at
    write_json(WORKS / "state.json", state)
    rebuild_backlog(phases, state, index)
    rebuild_deferred_dashboard(deferred)
    for p in phases:  # only the marker-delimited ## Slices block; archived phases are never touched
        refresh_phase_md_slices(ROOT / p["path"], p)


def _phase_progress(phase_like: dict, slices: list) -> tuple:
    """`(current slice id or "none", "n/m")` for one phase as read from some source."""
    slices = slices or []
    cur = next((x.get("id") for x in slices if x.get("status") != "done"), None)
    return (cur or "none", f"{sum(1 for x in slices if x.get('status') == 'done')}/{len(slices)}")


def streams_section(phases: list, state: dict) -> list:
    """The `## Streams` table for `works/backlog.md` (P35.S7): the default stream plus every stamped
    phase still in flight, each read live from where its slices actually advance.

    A parallel phase's slice progress lives on its own branch, so the stamp-time copy in the
    `## Active Phases` table stands still until the merge. Rows: this checkout's own stream first
    when it is a parallel one (from its working tree), then the `default` row (this checkout's
    pointer on the default stream; on a parallel stream the base branch's pointer, from
    `execution.base_branch`, else the local copy), then one row per other in-flight phase, read
    from its branch, then `origin/<branch>`, else the local copy -- labelled so. Git is touched
    only when a stamped phase is in flight (the same gate as `current_stream`); with none, this is
    a single working-tree default row and no git call is made. The Host branch column is nested only.
    """
    nested = NESTED is not None
    stream = state.get("stream")
    own = next((p for p in phases if stream and (phase_execution(p) or {}).get("branch") == stream), None)
    others = [p for p in phases if phase_in_flight(p) and p is not own]
    use_git = bool((own or others) and _git_available())
    rows = []

    base_dir = str(HOST_ROOT or ROOT)

    def where(worktree):  # the default homes sit under the checkout's root: print them relative to it, keeping the tracked file free of home paths
        if worktree and os.path.isabs(worktree) and os.path.commonpath([base_dir, worktree]) == base_dir:
            return os.path.relpath(worktree, base_dir)
        return worktree

    def add(stream_cell, phase_id, status, cur, done, host, worktree, source):
        worktree = where(worktree)
        cells = [f"`{clean_cell(stream_cell)}`", f"`{clean_cell(phase_id)}`" if phase_id else "-", clean_cell(status) or "-",
                 f"`{clean_cell(cur)}`" if cur else "-", done or "-"]
        if nested:
            cells.append(f"`{clean_cell(host)}`" if host else "-")
        cells += [f"`{clean_cell(worktree)}`" if worktree else "-", clean_cell(source)]
        rows.append("| " + " | ".join(cells) + " |")

    if own is not None:
        execution = phase_execution(own)
        cur, done = _phase_progress(own, own["slices"])
        short = _parallel_verdict_pair(own["id"], own.get("status"), (own.get("review") or {}).get("status"), own["slices"],
                                       phase_consolidation(own), None, False, True)[0]
        add(stream, own["id"], short, cur, done, execution.get("host_branch"), execution.get("worktree"), "working tree")

    # The default row.
    if own is None:
        pid, cur_slice = state.get("current_phase"), state.get("current_slice")
        phase = next((p for p in phases if p["id"] == pid), None)
        if phase is None:
            add("default", None, "idle", None, None, None, None, "working tree")
        else:
            _, done = _phase_progress(phase, phase["slices"])
            add("default", pid, phase.get("status"), cur_slice or "none", done, None, None, "working tree")
    else:
        base = (phase_execution(own) or {}).get("base_branch")
        plist, source = None, "local copy"
        if base and use_git:
            plist = _phases_at_ref(base)
            if plist is not None:
                source = f"branch {base}"
        sel = stream_phases(plist if plist is not None else phases, None)
        target = next((q for q in sel if q.get("status") != "done"), None)
        if target is None:
            add("default", None, "idle", None, None, None, None, source)
        else:
            if plist is not None:
                target["slices"] = _slices_at_ref(base, target["id"]) or []
            cur_slice = resolve_current([target])[1]
            _, done = _phase_progress(target, target["slices"])
            add("default", target["id"], target.get("status"), cur_slice or "none", done, None, None, source)

    for p in others:
        execution = phase_execution(p)
        branch = execution.get("branch")
        data, slices, source = p, p["slices"], "local copy"
        branch_gone, merged = False, None
        if use_git and branch:
            for candidate in (branch, f"origin/{branch}"):
                found = _phase_json_at_ref(candidate, p["id"])
                if found is not None:
                    data, slices, source = found, _slices_at_ref(candidate, p["id"]) or [], f"branch {candidate}"
                    break
            branch_gone = not _branch_exists(branch)
            if not branch_gone:
                merged = _git(["merge-base", "--is-ancestor", branch, "HEAD"], check=False).returncode == 0
        short = _parallel_verdict_pair(p["id"], data.get("status"), (data.get("review") or {}).get("status"), slices,
                                       phase_consolidation(p), merged, branch_gone, False)[0]
        cur, done = _phase_progress(data, slices)
        add(branch or "-", p["id"], short, cur, done, execution.get("host_branch"), execution.get("worktree"), source)

    head = ["Stream", "Phase", "Status", "Current slice", "Done"] + (["Host branch"] if nested else []) + ["Worktree", "Source"]
    return ["## Streams", "", "| " + " | ".join(head) + " |", "|" + "---|" * len(head)] + rows + [""]


def rebuild_backlog(phases: list, state: dict, index: dict) -> None:
    lines = [
        "# Backlog", "", "> Generated dashboard. Do not put detailed task context here; edit phase/slice/deferred folders instead.",
        "> Status box: `[x]` done · `[~]` pending — waiting on operator · `[r]` ready — plan approved, awaiting execution · `[ ]` open/in progress.", "",
        "## Pointer", "",
        f"- Current phase: `{state.get('current_phase') or 'none'}`",
        f"- Current slice: `{state.get('current_slice') or 'none'}`",
        f"- Next slice: `{state.get('next_slice') or 'none'}`",
        f"- Waiting on operator: `{state.get('waiting_on_operator') or 'none'}`",
    ]
    if state.get("stream"):  # only in a parallel-phase checkout; absent on the default stream
        lines.append(f"- Stream: `{clean_cell(state['stream'])}` (parallel phase checkout; the pointer above is scoped to it)")
    lines += [
        f"- Open deferred jobs: `{index.get('deferred_open_count', 0)}`", "",
        *streams_section(phases, state),
        "## Active Phases", "", "| Phase | Status | Review | Name | Current Slice | Path |", "|---|---|---|---|---|---|",
    ]
    if not phases:
        lines.append("| - | - | - | - | - | - |")
    for p in phases:
        current = next((s["id"] for s in p["slices"] if s.get("status") != "done"), "none")
        name = clean_cell(p.get("name", ""))
        review = clean_cell(p.get("review", {}).get("status"))
        current_cell = f"`{current}`"
        execution = phase_execution(p)
        if execution:  # runs on its own branch; from another stream the slice state may be behind
            current_cell += f" · parallel: `{clean_cell(execution.get('branch'))}`"
        elif phase_pinned(p):  # v42's legacy pin; since v43 the default stream needs no marker
            current_cell += " · pinned: default stream"
        lines.append(f"| [{status_box(p['status'])}] `{p['id']}` | `{p['status']}` | `{review}` | {name} | {current_cell} | `{p['path']}` |")
    for p in phases:
        lines.extend(["", f"## Phase {p['id']}: {p['name']}", "", "| Slice | Status | Name | Kind | Path |", "|---|---|---|---|---|"])
        for s in p["slices"]:
            checkbox = status_box(s.get("status"))
            name = clean_cell(s.get("name", ""))
            lines.append(f"| [{checkbox}] `{s['id']}` | `{s['status']}` | {name} | `{clean_cell(s.get('kind', ''))}` | `{s['path']}` |")
    lines.append("")
    write_text(WORKS / "backlog.md", "\n".join(lines))


def validate() -> int:
    errors: list = []
    warnings: list = []
    phases = all_active_phases()
    seen_phases, seen_slices = set(), set()
    seen_branches: dict = {}
    all_slice_ids = {s["id"] for p in phases for s in p["slices"]}
    for p in phases:
        if p["id"] in seen_phases:
            errors.append(f"duplicate phase id: {p['id']}")
        seen_phases.add(p["id"])
        if p["status"] not in PHASE_STATUSES:
            errors.append(f"invalid phase status {p['id']}: {p['status']}")
        review_status = p.get("review", {}).get("status")
        if p["status"] == "done" and review_status != "pass":
            errors.append(f"phase {p['id']} is done but review status is {review_status!r}; record a passing review with review-phase")
        if p["status"] == "done":
            unfinished = [s["id"] for s in p["slices"] if s.get("status") != "done"]
            if unfinished:
                errors.append(f"phase {p['id']} is done but has unfinished slices: {', '.join(unfinished)}; a passing review closes the REVIEW slice")
        # Optional doc-consolidation debt. Absent = nothing owed (every phase reviewed before
        # this field existed, and every phase whose `## Doc impact` list was empty).
        if "consolidation" in p and p.get("consolidation") not in CONSOLIDATION_STATES:
            errors.append(f"phase {p['id']} has invalid consolidation {p.get('consolidation')!r}; expected one of {sorted(CONSOLIDATION_STATES)}")
        # Optional docs-phase marker (v51): the active phases a docs phase pays. Absent = not a docs phase.
        if "consolidates" in p:
            paid = p.get("consolidates")
            if not (isinstance(paid, list) and paid and all(isinstance(v, str) and re.fullmatch(r"P[0-9]+", v) for v in paid)):
                errors.append(f"phase {p['id']} has invalid consolidates {paid!r}; expected a non-empty list of phase ids such as [\"P26\", \"P27\"] (written by new-phase --consolidates)")
        # Optional parallel-execution block. Absent = default stream = nothing to check.
        # A phase that merged `done` while its doc consolidation is still pending
        # (`consolidation: "pending"`) is a legitimate state and passes cleanly here.
        if "execution" in p:
            execution = p.get("execution")
            if not isinstance(execution, dict):
                errors.append(f"phase {p['id']} has a non-object execution block: {execution!r}")
            else:
                mode = execution.get("mode")
                if mode not in EXECUTION_MODES and mode != PINNED_MODE:
                    errors.append(f"phase {p['id']} has invalid execution.mode {mode!r}; expected one of {sorted(EXECUTION_MODES | {PINNED_MODE})}")
                elif mode == PINNED_MODE:
                    pass  # v42's legacy pin to the default stream: no branch, no worktree, nothing else to check
                else:
                    branch = execution.get("branch")
                    if not isinstance(branch, str) or not branch.strip():
                        errors.append(f"phase {p['id']} is parallel but has no execution.branch; the branch name is the stream key")
                    elif branch in seen_branches:
                        errors.append(f"duplicate execution.branch {branch!r}: {seen_branches[branch]} and {p['id']}")
                    else:
                        seen_branches[branch] = p["id"]
                    worktree = execution.get("worktree")
                    if worktree is not None and not isinstance(worktree, str):
                        errors.append(f"phase {p['id']} has invalid execution.worktree {worktree!r}; expected a path string or null")
                    consolidation = execution.get("consolidation")
                    if consolidation is not None and consolidation not in CONSOLIDATION_STATES:
                        errors.append(f"phase {p['id']} has invalid execution.consolidation {consolidation!r}; expected one of {sorted(CONSOLIDATION_STATES)} or null")
                    errors.extend(_nested_execution_problems(p["id"], execution))
        # Optional operator acceptance gate. Absent = legacy phase = nothing to check and
        # NO warning: nagging every pre-v32 phase on every run would clutter the dashboards.
        if "acceptance" in p:
            acceptance = p.get("acceptance")
            if not isinstance(acceptance, dict):
                errors.append(f"phase {p['id']} has a non-object acceptance block: {acceptance!r}")
            else:
                required = acceptance.get("required")
                if not (required is None or isinstance(required, bool)):
                    errors.append(f"phase {p['id']} has invalid acceptance.required {required!r}; expected true (operator-visible), false (waived) or null (undeclared)")
                for field in ("walkthrough", "note", "requested_at", "cleared_at"):
                    value = acceptance.get(field)
                    if value is not None and not isinstance(value, str):
                        errors.append(f"phase {p['id']} has invalid acceptance.{field} {value!r}; expected a string or null")
                if p["status"] == "done" and required is True and not acceptance.get("cleared_at"):
                    errors.append(f"phase {p['id']} is done but its operator acceptance gate was never cleared; the operator must walk the running product (accept-gate {p['id']} --open/--clear)")
        # Optional host anchors (P28): written only by a nested install's new-phase / passing review.
        # Absent = an at-root or pre-nested phase = nothing to check.
        if "host_anchors" in p:
            anchors = p.get("host_anchors")
            if not isinstance(anchors, dict):
                errors.append(f"phase {p['id']} has a non-object host_anchors block: {anchors!r}")
            else:
                for key, value in anchors.items():
                    if key not in HOST_ANCHOR_KEYS:
                        errors.append(f"phase {p['id']} has unknown host_anchors.{key}; expected only {', '.join(HOST_ANCHOR_KEYS)}")
                    elif value is not None and not (isinstance(value, str) and re.fullmatch(r"[0-9a-f]{7,64}", value)):
                        errors.append(f"phase {p['id']} has invalid host_anchors.{key} {value!r}; expected a host commit sha or null")
        if not (ACTIVE / p["id"] / "intent.md").exists():
            warnings.append(f"phase {p['id']} has no intent.md (expected {p['id']}/intent.md); capture operator intent via the create-phase skill")
        # Bounded notebook (v35). Warnings only: `validate` prints them and still exits 0.
        # A `done` phase is skipped for the budget: its notebook is closed history waiting
        # to be archived, so "rewrite it under budget" is advice nobody can act on -- the
        # check must bite while the phase is still running (that includes `in_review`).
        notebook = ACTIVE / p["id"] / "phase.md"
        lines_n, bytes_n = phase_md_size(notebook.parent)
        if p["status"] != "done" and bytes_n > PHASE_MD_BUDGET:
            warnings.append(f"phase {p['id']}: phase.md is {lines_n} lines / {bytes_n} bytes, over the notebook budget of {PHASE_MD_BUDGET} bytes; rewrite it under budget (state to phase.md, detail to the slice's result.md)")
        # Heading-line check, not a substring search: notebooks legitimately quote both
        # spellings in prose (this very rule, for one).
        if notebook.exists() and any(re.match(r"## Doc Impact\b", ln) for ln in notebook.read_text(encoding="utf-8").split("\n")):
            warnings.append(f"phase {p['id']}: phase.md has a `## Doc Impact` heading; the canonical section is `## Doc impact` (lowercase i) -- rename it so the review finds the notes")
        for s in p["slices"]:
            if s["id"] in seen_slices:
                errors.append(f"duplicate slice id: {s['id']}")
            seen_slices.add(s["id"])
            if s["phase_id"] != p["id"]:
                errors.append(f"slice phase mismatch: {s['id']} says {s['phase_id']}, folder phase is {p['id']}")
            if s["status"] not in SLICE_STATUSES:
                errors.append(f"invalid slice status {s['id']}: {s['status']}")
            # Warning, never an error: creation is the hard gate (see SLICE_KINDS), and
            # history an adopting repo cannot change must not break its validate.
            if s.get("kind") not in SLICE_KINDS:
                warnings.append(f"slice {s['id']} has unknown kind {s.get('kind')!r}; expected one of {sorted(SLICE_KINDS)} -- edit slice.json to one of them")
            if s["status"] == "ready" and not (ROOT / s["path"] / "plan.md").exists():
                errors.append(f"slice {s['id']} is ready but has no plan.md; ready asserts an operator-approved plan exists")
            for dep in s.get("depends_on", []):
                if dep not in all_slice_ids:
                    errors.append(f"missing dependency for {s['id']}: {dep}")
    state = read_json(WORKS / "state.json") if (WORKS / "state.json").exists() else {}
    if state.get("current_phase") and state["current_phase"] not in seen_phases:
        errors.append(f"state current_phase does not exist: {state['current_phase']}")
    if state.get("current_slice") and state["current_slice"] not in seen_slices:
        errors.append(f"state current_slice does not exist: {state['current_slice']}")
    for base, allowed in [(DEFERRED_OPEN, {"deferred", "ready"}), (DEFERRED_PROMOTED, {"promoted", "done"}), (DEFERRED_DROPPED, {"dropped"})]:
        if not base.exists():
            continue
        for ddir in base.iterdir():
            if not ddir.is_dir():
                continue
            djson = ddir / "deferred.json"
            if not djson.exists():
                errors.append(f"missing deferred.json: {shown(ddir)}")
                continue
            data = read_json(djson)
            if data.get("status") not in DEFERRED_STATUSES:
                errors.append(f"invalid deferred status {data.get('id')}: {data.get('status')}")
            if data.get("status") not in allowed:
                errors.append(f"deferred job in wrong folder: {data.get('id')} status {data.get('status')} under {shown(base)}")
    # Deferred doc consolidation. A WARNING, never an error: the debt is expected operator-paced
    # state (a passing review defers consolidation to a docs phase), so it must not fail CI or
    # block the loop -- it must only stop being silent.
    debt = consolidation_debt_line(phases)
    if debt:
        warnings.append(debt)
    # ...and the doc-side half of the same debt: which docs an agent must not read as current truth
    # while it stands. A separate line because it carries what the debt line cannot -- the doc names
    # a reader chooses by -- and a WARNING for the same reason: staleness is expected, being silent
    # about it is not.
    stale = stale_docs_line(stale_docs(phases))
    if stale:
        warnings.append(stale)
    # Oversized durable-doc sections. A WARNING, never an error, for the same reason: the read-order
    # rule ("read the sections the work touches") degrades silently as sections outgrow the doc they
    # were cut from, and the remedy -- splitting one -- belongs to the next docs phase, not to CI.
    oversized = oversized_sections_line(oversized_doc_sections())
    if oversized:
        warnings.append(oversized)
    # Agent-file drift is advisory only: warn (never error, never crash) when the four managed agent
    # files disagree with the route table (executors.toml/defaults), so a foreign or partial
    # workspace still validates. Skipped when a broken nested marker names no host: the agent files
    # live there, not under ROOT.
    try:
        for _label, path, model, effort in ([] if NESTED is not None and HOST_ROOT is None else executor_agent_files(resolve_routes())):
            if not path.exists():
                warnings.append(f"missing executor agent file: {shown(path)} (run: {WORKFLOW_CMD} sync-agents)")
                continue
            current = path.read_text(encoding="utf-8")
            desired = _patched_agent_md(current, model, effort)
            if desired != current:
                warnings.append(f"executor agent file out of sync with executors.toml/defaults: {shown(path)} (run: {WORKFLOW_CMD} sync-agents)")
    except (SystemExit, Exception) as exc:  # noqa: BLE001 - advisory check must not fail validate
        warnings.append(f"executor tier config check failed: {exc}")
    # Nested personal install (P28): a malformed marker is an ERROR, so a broken nested install is
    # never mistaken for at-root mode; the host must be a git work tree (phase-scope and the
    # product commits read it). Silent at root -- no marker, nothing checked.
    if NESTED is not None:
        marker = shown(ROOT / NESTED_MARKER)
        errors.extend(f"{marker}: {problem}" for problem in NESTED_PROBLEMS)
        unknown = sorted(set(NESTED) - set(NESTED_KEYS) - set(NESTED_OPTIONAL_KEYS))
        if unknown:
            warnings.append(f"{marker}: unknown field(s) {', '.join(unknown)} (schema {NESTED_SCHEMA} reads only {', '.join(NESTED_KEYS + NESTED_OPTIONAL_KEYS)})")
        if HOST_ROOT is not None and HOST_ROOT.is_dir():
            try:
                proc = subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], cwd=str(HOST_ROOT), capture_output=True, text=True, timeout=10)
            except Exception:  # noqa: BLE001 - no git binary: say so, never fail on it
                warnings.append(f"git is not available, so the nested install's host {HOST_ROOT} cannot be confirmed as a git work tree")
            else:
                if proc.returncode != 0 or proc.stdout.strip() != "true":
                    errors.append(f"nested install: the host {HOST_ROOT} is not a git work tree (phase-scope and the host product commits need one)")
    validate_docs(errors)
    for w in warnings:
        print(f"warning: {w}")
    if errors:
        print("Workflow validation failed:")
        for e in errors:
            print(f"- {e}")
        return 1
    print("Workflow validation passed.")
    return 0


def require_phase(phase_id: str) -> Path:
    p = ACTIVE / phase_id
    if not (p / "phase.json").exists():
        raise SystemExit(f"phase not found: {phase_id}")
    return p


def require_slice(slice_id: str) -> Path:
    phase_id = slice_id.split(".", 1)[0]
    s = ACTIVE / phase_id / "slices" / slice_id
    if not (s / "slice.json").exists():
        raise SystemExit(f"slice not found: {slice_id}")
    return s


def load_template(name: str) -> str:
    return (WORKS / "templates" / name).read_text(encoding="utf-8")


def render_template(text: str, **values: str) -> str:
    for k, v in values.items():
        text = text.replace(f"__{k.upper()}__", v)
    return text


# Byte-identical to works/templates/phase.md, which is the live seed. The copy exists so
# `new-phase` still works on a tree that predates the template (an adopter yet to update);
# tests/retrofit_smoke.sh asserts the two stay identical.
PHASE_MD_TEMPLATE_FALLBACK = """# Phase __PHASE_ID__: __NAME__

_Intent: see [intent.md](intent.md)._

## Objective

__OBJECTIVE__

## Slices

<!-- slices:begin -->
_Generated by `python3 scripts/workflow.py rebuild` from each slice's `slice.json`; never hand-edit this block._
<!-- slices:end -->

## Decisions

_Durable cross-slice decisions. Replace a superseded line; never stack versions._

## Doc impact

_One line per durable-truth change: `- <doc>.md: <what changed> (<slice>)`. Append only; the review verifies this list and a later docs phase consolidates it into versions — never per slice, never at the review — a branch review adds its two gate sections here tagged `(gate section — written at merge)`._

## Operator Questions

_Questions only the operator can answer. Append only; every entry is routed at the review — folded into the acceptance walkthrough or filed with `defer-job`. An unrouted entry is a review finding._

## Notes for later slices

_Gotchas and constraints the next slices need, each tagged `**(from <slice>, for <slice>)**`. A slice that consumes a note removes it; the detail stays in that slice's `result.md`._

## Now

_≤ 15 lines, rewritten by every slice at its end: what is done, what the next slice must know, what is open. Last on purpose._
"""


def phase_md_template() -> str:
    """The phase-notebook seed: the shipped template when present, else the embedded copy."""
    try:
        return load_template("phase.md")
    except OSError:
        return PHASE_MD_TEMPLATE_FALLBACK


def require_slice_kind(kind: str) -> str:
    """The one place an unknown slice kind is rejected. Called from create_slice (the shared
    chokepoint for new-slice and promote-deferred) and, additionally, at the very top of
    promote-deferred: its --create-phase branch creates the phase BEFORE the slice, so a
    rejected kind must be caught before that happens rather than after."""
    if kind not in SLICE_KINDS:
        raise SystemExit(f"invalid slice kind: {kind}; expected one of {sorted(SLICE_KINDS)}")
    return kind


def create_slice(phase_id: str, slice_id: str, name: str, kind: str, order, risk: str, source: dict, depends_on=None) -> Path:
    require_slice_kind(kind)
    require_phase(phase_id)
    if not slice_id.startswith(f"{phase_id}."):
        raise SystemExit(f"slice id must start with {phase_id}.")
    sdir = ACTIVE / phase_id / "slices" / slice_id
    if sdir.exists():
        raise SystemExit(f"slice already exists: {slice_id}")
    created = now_iso()
    data = {
        "id": slice_id, "phase_id": phase_id, "name": name, "kind": kind, "status": "todo", "order": order,
        "depends_on": depends_on or [], "created_at": created, "started_at": None, "completed_at": None, "risk": risk, "source": source,
        "paths": {"plan": "plan.md", "result": "result.md"},
        "outcome": None,  # one line, set by `finish-slice --outcome`; rendered in the phase's ## Slices table
        "validation": {"required": [], "last_run": None, "last_status": "pending"},
        "archive": {"archived": False, "archived_at": None, "archive_path": None},
    }
    write_json(sdir / "slice.json", data)
    # Neither context file is scaffolded: the orchestrator writes its free-form native
    # plan to plan.md at the slice's turn, and the executor writes its free-form
    # result.md at slice end — a fresh slice folder holds only slice.json.
    return sdir


def _with_host_anchors(data: dict, anchors: dict) -> dict:
    """`data` with `anchors` merged into its `host_anchors` block, the block placed right after
    `acceptance` (or appended) when it is new, so phase.json keeps reading naturally."""
    current = data.get("host_anchors")
    merged = dict(current) if isinstance(current, dict) else {}
    merged.update(anchors)
    if "host_anchors" in data:
        data["host_anchors"] = merged
        return data
    ordered = {}
    for key, value in data.items():
        ordered[key] = value
        if key == "acceptance":
            ordered["host_anchors"] = merged
    ordered.setdefault("host_anchors", merged)
    data.clear()
    data.update(ordered)
    return data


def _parse_consolidates(raw) -> list:
    """`new-phase --consolidates P26,P27` -> `["P26", "P27"]`: comma-separated, spaces tolerated,
    duplicates dropped in order. Refuses (before `new-phase` writes anything) when the flag names
    nothing, or names an id that is not an ACTIVE phase still owing doc consolidation -- a docs phase
    can only pay debt that stands. `None` (flag absent) is `[]`."""
    if raw is None:
        return []
    ids = []
    for part in raw.split(","):
        part = part.strip()
        if part and part not in ids:
            ids.append(part)
    if not ids:
        raise SystemExit("--consolidates needs at least one phase id (e.g. --consolidates P26,P27)")
    active = {p["id"]: p for p in all_active_phases()}
    bad = []
    for pid in ids:
        if pid not in active:
            bad.append(f"{pid} (not an active phase)")
        elif phase_consolidation(active[pid]) != "pending":
            bad.append(f"{pid} (owes no doc consolidation: consolidation is {phase_consolidation(active[pid])!r})")
    if bad:
        raise SystemExit(f"--consolidates refused, nothing was written: {'; '.join(bad)}. It names only active phases that still owe doc consolidation (see: {WORKFLOW_CMD} docs-debt).")
    return ids


def new_phase(args: argparse.Namespace) -> None:
    phase_id = args.phase
    if not re.fullmatch(r"P[0-9]+", phase_id):
        raise SystemExit("phase must look like P1, P2, P3")
    pdir = ACTIVE / phase_id
    if pdir.exists():
        raise SystemExit(f"phase already exists: {phase_id}")
    consolidates = _parse_consolidates(getattr(args, "consolidates", None))  # refuses before anything is written
    order = _clean_order(args.order) if args.order is not None else max([read_json(p / "phase.json").get("order", 0) for p in phase_dirs()], default=0) + 1
    phase_data = {
        "id": phase_id, "name": args.name, "objective": args.objective, "status": "planned", "order": order,
        "created_at": now_iso(), "started_at": None, "completed_at": None,
        "review": {"status": "pending", "reviewed_at": None, "reviewer": None, "note": None},
        "acceptance": new_acceptance(),
        "paths": {"phase_md": "phase.md", "intent_md": "intent.md", "slices_dir": "slices"},
        "archive": {"archived": False, "archived_at": None, "archive_path": None},
    }
    if consolidates:
        # v51: the one marker of a docs phase -- the owing phases it pays. Absent without the flag.
        phase_data["consolidates"] = consolidates
    if NESTED is not None:
        # The nested repo never sees the host's commits, so phase-scope's base is the host HEAD now
        # (null while the host has no commit). At root this key is never written.
        phase_data = _with_host_anchors(phase_data, {"created": head_commit() or None})
    write_json(pdir / "phase.json", phase_data)
    # Seed the notebook from the template: fixed sections plus an empty generated ## Slices
    # block, which the rebuild at the end of this function fills immediately.
    write_text(pdir / "phase.md", render_template(phase_md_template(), PHASE_ID=phase_id, NAME=args.name, OBJECTIVE=args.objective))
    write_text(pdir / "intent.md", render_template(load_template("intent.md"), PHASE_ID=phase_id, CAPTURED_AT=now_iso(), ORIGIN="operator"))
    create_slice(phase_id, f"{phase_id}.DECOMP", "decompose phase", "decomposition", 0, "high", source={"type": "new_phase", "id": phase_id})
    create_slice(phase_id, f"{phase_id}.REVIEW", "phase review", "review", 9999, "high", source={"type": "new_phase", "id": phase_id})
    append_event("phase_created", phase=phase_id)
    rebuild_index_and_state()
    print(f"created phase {phase_id}: {shown(pdir)}")
    if consolidates:
        print(f"consolidates={', '.join(consolidates)} (docs phase: pays the doc debt of those phases; docs-debt shows it as 'paid by {phase_id}')")
    # v43: a phase runs on this stream unless the operator asks for a worktree, so creation
    # stamps nothing and says nothing -- except where a worktree would actually buy something.
    if getattr(args, "on_main", False):
        print(f"note: --on-main is a no-op since v43 -- the default stream IS the default, so {phase_id} already runs here; nothing was stamped")
    # Proactive opt-in suggestion: a phase created while another one is mid-flight is the
    # first of the two moments a worktree becomes relevant. Suggestion only, never a default.
    # In a nested install (P35) the command also names the host branch the operator must choose.
    busy = next((p for p in all_active_phases() if p["id"] != phase_id and p.get("status") == "in_progress" and phase_execution(p) is None), None)
    if busy:
        print(f"hint: {busy['id']} is in progress -- this phase can run in parallel on its own branch: {WORKFLOW_CMD} parallel-start {phase_id}{NESTED_HOST_BRANCH_ARG}")


def _clean_order(value):
    """Normalize an explicit order: whole numbers stay ints, fractions stay floats so a
    slice/phase can be inserted between two neighbors (e.g. --order 4.5 sorts between 4 and 5)."""
    return int(value) if float(value).is_integer() else float(value)


def _auto_order(pdir: Path, explicit):
    if explicit is not None:
        return _clean_order(explicit)
    orders = [read_json(s / "slice.json").get("order", 0) for s in slice_dirs(pdir) if read_json(s / "slice.json").get("kind") != "review"]
    return max(orders, default=0) + 10


def new_slice(args: argparse.Namespace) -> None:
    pdir = require_phase(args.phase)
    order = _auto_order(pdir, args.order)
    sdir = create_slice(args.phase, args.slice, args.name, args.kind, order, args.risk, source={"type": "manual", "id": None}, depends_on=args.depends_on or [])
    append_event("slice_created", phase=args.phase, slice=args.slice)
    rebuild_index_and_state()
    print(f"created slice {args.slice}: {shown(sdir)}")


def _set_slice_status(sdir: Path, status: str) -> str:
    data = read_json(sdir / "slice.json")
    old = data.get("status")
    data["status"] = status
    if status == "in_progress" and not data.get("started_at"):
        data["started_at"] = now_iso()
    if status == "done":
        data["completed_at"] = now_iso()
    write_json(sdir / "slice.json", data)
    return old


def set_slice_status(slice_id: str, status: str) -> None:
    if status not in SLICE_STATUSES:
        raise SystemExit(f"invalid slice status: {status}")
    sdir = require_slice(slice_id)
    old = _set_slice_status(sdir, status)
    append_event("slice_status_changed", slice=slice_id, old_status=old, new_status=status)
    rebuild_index_and_state()


def start_slice(args: argparse.Namespace) -> None:
    set_slice_status(args.slice, "in_progress")
    print(f"started {args.slice}")


def finish_slice(args: argparse.Namespace) -> None:
    sdir = require_slice(args.slice)
    outcome = (getattr(args, "outcome", None) or "").strip()
    if outcome:  # stored before the status change, so the rebuild it triggers renders the row
        data = read_json(sdir / "slice.json")
        data["outcome"] = outcome
        write_json(sdir / "slice.json", data)
    set_slice_status(args.slice, "done")
    if not outcome:  # a warning, never an error: the slice is still finished
        print(f"warning: no --outcome recorded for {args.slice}; the ## Slices row will be blank")
    print(f"finished {args.slice}")
    lines_n, bytes_n = phase_md_size(sdir.parents[1])  # .../<phase>/slices/<slice> -> <phase>
    if lines_n or bytes_n:  # the notebook is where the next slice reads its state; keep it in view
        over = " \u2014 OVER BUDGET" if bytes_n > PHASE_MD_BUDGET else ""  # bytes judge; lines are informational
        print(f"phase.md: {lines_n} lines / {bytes_n} bytes (budget {PHASE_MD_BUDGET} bytes){over}")


def _set_phase_status(pdir: Path, status: str) -> str:
    data = read_json(pdir / "phase.json")
    old = data.get("status")
    data["status"] = status
    if status == "in_progress" and not data.get("started_at"):
        data["started_at"] = now_iso()
    if status == "done":
        data["completed_at"] = now_iso()
    write_json(pdir / "phase.json", data)
    return old


def set_phase_status(args: argparse.Namespace) -> None:
    if args.status not in PHASE_STATUSES:
        raise SystemExit(f"invalid phase status: {args.status}")
    pdir = require_phase(args.phase)
    old = _set_phase_status(pdir, args.status)
    append_event("phase_status_changed", phase=args.phase, old_status=old, new_status=args.status)
    rebuild_index_and_state()
    print(f"phase {args.phase}: {old} -> {args.status}")


def _require_acceptance_cleared(phase_id: str, data: dict) -> None:
    """Refuse a passing review while the operator acceptance gate is undeclared or uncleared.

    Called before `review_phase` writes anything. Only `pass` is ever refused: an operator's
    failure report must stay recordable as `changes_requested` (or `blocked`).
    """
    acceptance = phase_acceptance(data)
    if acceptance is None:
        if "acceptance" in data:
            print(f"acceptance: phase {phase_id} has a malformed gate block -- treated as legacy (run: {WORKFLOW_CMD} validate)")
        else:
            print("acceptance: legacy phase (no gate block) -- pass recorded without an operator acceptance gate")
        return
    required = acceptance.get("required")
    if required is None:
        raise SystemExit(
            f"phase {phase_id} has not declared whether the operator must accept it; a pass cannot be recorded yet:\n"
            f"  {WORKFLOW_CMD} accept-gate {phase_id} --require                     (operator-visible: the operator walks the running product)\n"
            f"  {WORKFLOW_CMD} accept-gate {phase_id} --waive --note \"why\"          (nothing the operator can see)")
    if required is True and not acceptance.get("cleared_at"):
        raise SystemExit(
            f"phase {phase_id} requires operator acceptance and the gate is not cleared; show the operator the running product first:\n"
            f"  {WORKFLOW_CMD} accept-gate {phase_id} --open --walkthrough \"...\"    (orchestrator, after the review executor's validation and judgment)\n"
            f"  {WORKFLOW_CMD} accept-gate {phase_id} --clear --note \"...\"          (after the operator walks it; --note is optional)")


def review_phase(args: argparse.Namespace) -> None:
    if args.verdict not in REVIEW_VERDICTS:
        raise SystemExit(f"verdict must be one of: {', '.join(sorted(REVIEW_VERDICTS))}")
    pdir = require_phase(args.phase)
    data = read_json(pdir / "phase.json")
    # Gate check first, before anything is written: a refused pass must leave no trace.
    if args.verdict == "pass":
        _require_acceptance_cleared(args.phase, data)
    data["review"] = {"status": args.verdict, "reviewed_at": now_iso(), "reviewer": args.reviewer, "note": args.note}
    if args.verdict == "changes_requested":
        acceptance = phase_acceptance(data)
        if acceptance is not None:
            # The phase is about to change again, so the gate re-opens for the re-review.
            # `required` and the operator's note survive; the walked script does not.
            acceptance.update({"walkthrough": None, "requested_at": None, "cleared_at": None})
    # Verdict drives phase status so the lifecycle stays consistent.
    status_map = {"pass": "done", "changes_requested": "in_progress", "blocked": "blocked"}
    new_status = status_map[args.verdict]
    if new_status == "done":
        data["completed_at"] = now_iso()
    data["status"] = new_status
    if args.verdict == "pass" and NESTED is not None:
        # The end of the phase's host range: phase-scope reads base..review_pass in the host.
        _with_host_anchors(data, {"review_pass": head_commit() or None})
    write_json(pdir / "phase.json", data)
    # Drive the phase's REVIEW slice from the same verdict so the phase and its
    # review slice never diverge (a pass no longer leaves REVIEW stuck in_progress).
    slice_verdict = {"pass": "done", "changes_requested": "changes_requested", "blocked": "blocked"}[args.verdict]
    for sdir in slice_dirs(pdir):
        sdata = read_json(sdir / "slice.json")
        if sdata.get("kind") == "review":
            old = _set_slice_status(sdir, slice_verdict)
            append_event("slice_status_changed", slice=sdata["id"], old_status=old, new_status=slice_verdict)
    append_event("phase_reviewed", phase=args.phase, verdict=args.verdict, reviewer=args.reviewer)
    rebuild_index_and_state()
    print(f"phase {args.phase} review: {args.verdict} (status -> {new_status})")
    if args.verdict == "changes_requested":
        print(f"create fix slices, e.g.: {WORKFLOW_CMD} new-slice --phase {args.phase} --slice {args.phase}.F1 --name \"...\" --kind fix")
    elif args.verdict == "pass":
        notes = phase_doc_impact_notes(pdir)
        if notes:
            # The review verifies the list and creates no versions; the debt is paid by an
            # operator-created docs phase. Stamp it so it is queryable and blocks archiving.
            data = read_json(pdir / "phase.json")
            set_phase_consolidation(data, "pending")
            write_json(pdir / "phase.json", data)
            append_event("phase_consolidation_owed", phase=args.phase, notes=len(notes))
            rebuild_index_and_state()
            done_cmd = "parallel-consolidated" if phase_execution(data) else "docs-consolidated"
            print(f"docs: {len(notes)} '## Doc impact' note(s) recorded -- durable docs are NOT versioned here.")
            print("  consolidation is deferred: the operator creates a docs phase for it (doc-new-version per note, then rebuild-docs).")
            print(f"  when those versions land: {WORKFLOW_CMD} {done_cmd} {args.phase}   (until then {args.phase} is held out of archiving)")
        print(f"phase {args.phase} is done and stays in active/. Do NOT archive a single phase now.")
        print("Archive done phases later, whole phases only: `rotate-backlog` (it pays the doc debt first, then archives every done phase), or `archive-all` once every active phase is done.")


def _ensure_acceptance(data: dict) -> dict:
    """The phase's acceptance block, created on demand -- this is how an adopter opts a legacy
    phase in. Inserted right after `review` so phase.json keeps reading naturally; a malformed
    block is replaced by a fresh one."""
    acceptance = phase_acceptance(data)
    if acceptance is not None:
        return acceptance
    acceptance = new_acceptance()
    ordered = {}
    for key, value in data.items():
        if key == "acceptance":
            continue
        ordered[key] = value
        if key == "review":
            ordered["acceptance"] = acceptance
    ordered.setdefault("acceptance", acceptance)
    data.clear()
    data.update(ordered)
    return acceptance


def _print_acceptance(phase_id: str, acceptance) -> None:
    print(f"phase={phase_id}")
    if acceptance is None:
        print("acceptance=none (legacy phase: no gate block, so review-phase --verdict pass is allowed)")
        print(f"declare one with: {WORKFLOW_CMD} accept-gate {phase_id} --require | --waive --note \"why\"")
        return
    print(f"required={json.dumps(acceptance.get('required'))}")
    print(f"requested_at={acceptance.get('requested_at') or 'none'}")
    print(f"cleared_at={acceptance.get('cleared_at') or 'none'}")
    print(f"note={acceptance.get('note') or 'none'}")
    walkthrough = acceptance.get("walkthrough")
    if walkthrough:
        print("walkthrough:")
        print(walkthrough)
    else:
        print("walkthrough=none")


def accept_gate(args: argparse.Namespace) -> None:
    """Declare, open, clear or show a phase's operator acceptance gate.

    Orchestrator/operator command: executors never run it. The review executor returns the
    walkthrough text; the orchestrator opens the gate with it and STOPS until the operator
    has walked the running product.
    """
    pdir = require_phase(args.phase)
    data = read_json(pdir / "phase.json")
    if args.walkthrough is not None and not args.open_gate:
        raise SystemExit(f"--walkthrough belongs to --open: {WORKFLOW_CMD} accept-gate {args.phase} --open --walkthrough \"...\"")
    if not (args.require or args.waive or args.open_gate or args.clear):
        _print_acceptance(args.phase, phase_acceptance(data))  # show only: writes nothing
        return
    acceptance = phase_acceptance(data)
    message = None
    if args.require:
        acceptance = _ensure_acceptance(data)
        acceptance["required"] = True
        event = "acceptance_required"
        message = f"phase {args.phase}: operator acceptance REQUIRED -- review-phase --verdict pass refuses until the gate is opened and cleared"
    elif args.waive:
        if not args.note:
            raise SystemExit(f"accept-gate {args.phase} --waive requires --note \"why this phase changes nothing the operator can see\"")
        acceptance = _ensure_acceptance(data)
        acceptance["required"] = False
        acceptance["note"] = args.note
        event = "acceptance_waived"
        message = f"phase {args.phase}: operator acceptance WAIVED -- {args.note}"
    elif args.open_gate:
        if acceptance is None or acceptance.get("required") is not True:
            raise SystemExit(
                f"phase {args.phase} has not declared that the operator must accept it; declare it first:\n"
                f"  {WORKFLOW_CMD} accept-gate {args.phase} --require")
        if not (args.walkthrough or "").strip():
            raise SystemExit(f"accept-gate {args.phase} --open requires --walkthrough \"the concrete script: URLs to open, actions to try, in the operator runtime\"")
        acceptance["walkthrough"] = args.walkthrough
        acceptance["requested_at"] = now_iso()
        acceptance["cleared_at"] = None
        event = "acceptance_opened"
    else:  # --clear
        if acceptance is None or not acceptance.get("requested_at"):
            raise SystemExit(
                f"phase {args.phase} has no open acceptance gate (requested_at is unset); nothing to clear:\n"
                f"  {WORKFLOW_CMD} accept-gate {args.phase} --open --walkthrough \"...\"")
        acceptance["cleared_at"] = now_iso()
        if args.note:
            acceptance["note"] = args.note
        event = "acceptance_cleared"
    write_json(pdir / "phase.json", data)
    # Opening/clearing rides the existing `pending` halt -- no second halt state.
    if args.open_gate or args.clear:
        status = "pending" if args.open_gate else "in_progress"
        old = _set_phase_status(pdir, status)
        append_event("phase_status_changed", phase=args.phase, old_status=old, new_status=status)
    append_event(event, phase=args.phase)
    rebuild_index_and_state()
    if args.open_gate:
        print(f"phase {args.phase}: acceptance gate OPEN -- phase is pending [~]; do not start, finish, or advance past it")
        print("WALKTHROUGH (the operator runs this against the running product):")
        print(args.walkthrough)
        print(f"Then clear it: {WORKFLOW_CMD} accept-gate {args.phase} --clear")
        print("Add --note \"...\" to record what the operator reported.")
    elif args.clear:
        print(f"phase {args.phase}: acceptance gate CLEARED -- phase is in_progress again; review-phase --verdict pass is now allowed")
    else:
        print(message)


def _git(cmd: list, cwd=None, check: bool = True):
    """Run a git command in the workspace root. With `check`, a failure raises SystemExit
    carrying git's own message, so every parallel-mode guard fails loudly and in one style."""
    try:
        proc = subprocess.run(["git", *cmd], cwd=str(cwd or ROOT), capture_output=True, text=True)
    except FileNotFoundError:
        raise SystemExit("git is not available; parallel execution needs git")
    if check and proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).strip() or f"exit {proc.returncode}"
        raise SystemExit(f"git {' '.join(cmd)} failed: {detail}")
    return proc


def _require_git_repo() -> None:
    proc = _git(["rev-parse", "--is-inside-work-tree"], check=False)
    if proc.returncode != 0 or proc.stdout.strip() != "true":
        raise SystemExit("not inside a git work tree; parallel execution needs a git repo")


def _branch_exists(branch: str) -> bool:
    return _git(["rev-parse", "--verify", "--quiet", f"refs/heads/{branch}"], check=False).returncode == 0


def _git_available(cwd=None) -> bool:
    """True when this workspace (or `cwd`: a nested install's host) sits inside a usable git work
    tree. Never raises: a workspace without git (or outside a repo) must keep working exactly as before."""
    try:
        proc = subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], cwd=str(cwd or ROOT), capture_output=True, text=True)
    except Exception:  # noqa: BLE001 - git is optional
        return False
    return proc.returncode == 0 and proc.stdout.strip() == "true"


def _git_dir(common: bool = False, cwd=None) -> Path:
    """This checkout's git dir (per-worktree state: HEAD, index, MERGE_HEAD, rebase-*) or, with
    `common`, the dir every worktree shares (refs, info/exclude). Absolute either way: git prints
    `.git` relative to the cwd in the main checkout and an absolute path from a linked worktree,
    and joining onto the cwd (ROOT, or `cwd`: a nested install's host) is right in both cases."""
    flag = "--git-common-dir" if common else "--git-dir"
    base = Path(cwd) if cwd is not None else ROOT
    return (base / _git(["rev-parse", flag], cwd=cwd).stdout.strip()).resolve()


def _git_operation_in_progress(cwd=None):
    """'merge' / 'rebase' while this checkout is mid-operation, else None. `git commit -- <paths>`
    refuses a partial commit during either, so the stamp commit needs a plain HEAD. With `cwd` (a
    nested install's host, P35) a cherry-pick or a bisect counts too: the host is never touched
    mid-operation, and its branch and worktree are cut only from a plain HEAD."""
    gd = _git_dir(cwd=cwd)
    if (gd / "MERGE_HEAD").exists():
        return "merge"
    if (gd / "rebase-merge").exists() or (gd / "rebase-apply").exists():
        return "rebase"
    if cwd is not None:
        if (gd / "CHERRY_PICK_HEAD").exists():
            return "cherry-pick"
        if (gd / "BISECT_LOG").exists():
            return "bisect"
    return None


def _ensure_worktrees_excluded(cwd=None) -> None:
    """Put `.claude/worktrees/` in the common `info/exclude` once, so a nested phase worktree never
    shows as untracked (or gets swept into `git add -A` as an embedded repo) in any checkout of this
    repo. Never `.gitignore`: that file is the adopter's, tracked, and theirs to edit.

    With `cwd` (a nested install's host, P35) the line goes into the HOST's common exclude, anchored
    as `/.claude/worktrees/` like the installer's managed block, and either form counts as present."""
    exclude = _git_dir(common=True, cwd=cwd) / "info" / "exclude"
    line = f"{WORKTREES_DIR}/" if cwd is None else f"/{WORKTREES_DIR}/"
    present = {line} if cwd is None else {line, f"{WORKTREES_DIR}/"}
    existing = exclude.read_text(encoding="utf-8") if exclude.exists() else ""
    if present & {l.strip() for l in existing.splitlines()}:
        return
    sep = "" if not existing or existing.endswith("\n") else "\n"
    exclude.parent.mkdir(parents=True, exist_ok=True)
    exclude.write_text(f"{existing}{sep}# agentic workspace: per-phase git worktrees cut by parallel-start\n{line}\n", encoding="utf-8")


_REPO_PREFIX = None


def _repo_prefix() -> str:
    """The workspace root's path inside the git repo ('' at the repo root).

    `git show <ref>:<path>` and `git ls-tree` take repo-relative paths, so every
    cross-ref read below prefixes the workspace-relative path with this."""
    global _REPO_PREFIX
    if _REPO_PREFIX is None:
        _REPO_PREFIX = _git(["rev-parse", "--show-prefix"], check=False).stdout.strip()
    return _REPO_PREFIX


def _json_at_ref(ref: str, rel: str):
    """A workspace-relative JSON file as recorded at a git ref, or None when unreadable."""
    proc = _git(["show", f"{ref}:{_repo_prefix()}{rel}"], check=False)
    if proc.returncode != 0:
        return None
    try:
        return json.loads(proc.stdout)
    except ValueError:
        return None


def _phase_json_at_ref(ref: str, phase_id: str):
    return _json_at_ref(ref, f"works/phases/active/{phase_id}/phase.json")


def _phases_at_ref(ref: str):
    """Every active phase.json as recorded at a git ref (ordered), or None if the ref is unreadable.

    Lets the gate read another stream's state (main, `origin/main`, a phase branch)
    without switching checkouts -- pre-merge, main's copy of a phase branch's state is stale.
    """
    proc = _git(["ls-tree", "--name-only", ref, f"{_repo_prefix()}works/phases/active/"], check=False)
    if proc.returncode != 0:
        return None
    phases = []
    for line in proc.stdout.splitlines():
        entry = line.strip().rstrip("/")
        if not entry:
            continue
        raw = _git(["show", f"{ref}:{entry}/phase.json"], check=False)
        if raw.returncode != 0:
            continue
        try:
            data = json.loads(raw.stdout)
        except ValueError:
            continue
        data.setdefault("path", entry)
        phases.append(data)
    phases.sort(key=lambda d: d.get("order", 999999))
    return phases


def _slices_at_ref(ref: str, phase_id: str):
    """Every slice.json of one phase as recorded at a git ref (ordered), or None if unreadable.

    The cross-stream half of `_phases_at_ref`: a phase branch's slice progress exists only on
    that branch until the merge, so reading it needs the tree at the ref, not the checkout.
    """
    proc = _git(["ls-tree", "--name-only", ref, f"{_repo_prefix()}works/phases/active/{phase_id}/slices/"], check=False)
    if proc.returncode != 0:
        return None
    slices = []
    for line in proc.stdout.splitlines():
        entry = line.strip().rstrip("/")
        if not entry:
            continue
        raw = _git(["show", f"{ref}:{entry}/slice.json"], check=False)
        if raw.returncode != 0:
            continue
        try:
            data = json.loads(raw.stdout)
        except ValueError:
            continue
        slices.append(data)
    slices.sort(key=lambda d: d.get("order", 999999))
    return slices


def _phase_branch(phase_id: str, name: str, slug_override=None) -> str:
    """`phase/P<N>-<slug>` -- the stream key every other part of parallel mode reads."""
    slug = slugify(slug_override or name, fallback=phase_id.lower())
    if len(slug) > 40:  # branch names stay short enough to type and to read in `git branch`
        slug = slug[:40].rstrip("_-.") or phase_id.lower()
    return f"phase/{phase_id}-{slug}"


def parallel_start(args: argparse.Namespace) -> None:
    """Move a planned phase into its own worktree: stamp it, commit the stamp, cut branch + worktree.

    This is the single place the engine makes a git commit, and it is deliberate. The stamp must
    exist on BOTH the default branch (so this stream's pointer skips the phase) and the phase
    branch (so the worktree session claims the stream), and the branch has to be cut from a commit
    that already contains it. Since v43 running here is the default and this command is the
    opt-in: it runs when the operator asks for a worktree (the do-* skills run it on the
    `worktree` mode word, never on their own), or straight from the operator's hand. It does not
    demand a clean tree -- the operator asks for a worktree mid-stride, not at a quiet point:
    `git add -- <paths>` then `git commit --only -- <paths>` makes the one fixed-message commit
    exact whatever else is dirty or staged -- only the phase folder plus the regenerated works/
    files go in, everything else stays behind in this checkout, and the worktree is cut from that
    commit ("start from the latest commit"). Stamping and asking the operator to commit cannot
    achieve that by construction; this can.

    In a nested personal install (P35) the phase gets a worktree PAIR instead -- see
    `_parallel_start_nested`; `--host-branch` is required there and refused at root.
    """
    host_branch = getattr(args, "host_branch", None)
    host_base = getattr(args, "host_base", None)
    if NESTED is None:
        if host_branch is not None or host_base is not None:
            raise SystemExit("--host-branch and --host-base are for a nested personal install only (they name the host repo's branch and base); "
                             "at root the phase branch is the only branch -- nothing was written")
    elif not (host_branch or "").strip():
        raise SystemExit(NESTED_HOST_BRANCH_REQUIRED)
    pdir = require_phase(args.phase)
    data = read_json(pdir / "phase.json")
    if data.get("status") != "planned":
        raise SystemExit(f"phase {args.phase} is {data.get('status')!r}; a phase enters its worktree before it starts (parallel-start needs status 'planned') -- a phase already in flight finishes on this stream")
    if phase_pinned(data):
        raise SystemExit(f"phase {args.phase} carries v42's legacy pin to the default stream (execution.mode=default, written by the old parallel-skip / new-phase --on-main); it was pinned deliberately, so un-pin it by hand: delete the execution block from {shown(pdir)}/phase.json first")
    if data.get("execution") is not None:
        raise SystemExit(f"phase {args.phase} already carries an execution block: {json.dumps(data['execution'], ensure_ascii=False)}")
    _require_git_repo()
    phases = all_active_phases()
    stream = current_stream(phases)
    if stream:
        raise SystemExit(f"this checkout is on parallel stream {stream}; run parallel-start from the default stream")
    busy = _git_operation_in_progress()
    if busy:
        raise SystemExit(f"a {busy} is in progress in this checkout; finish or abort it first -- the stamp commit must be an ordinary commit on the default branch")
    branch = _phase_branch(args.phase, data.get("name") or args.phase, args.slug)
    if _branch_exists(branch):
        raise SystemExit(f"branch already exists: {branch} (pass --slug to pick another name)")
    for p in phases:
        execution = phase_execution(p)
        if execution and execution.get("branch") == branch:
            raise SystemExit(f"branch {branch} is already stamped on phase {p['id']}")
    if NESTED is not None:
        _parallel_start_nested(args, pdir, data, branch, host_branch.strip(), host_base)
        return
    if args.worktree:
        worktree = Path(os.path.abspath(str(Path(args.worktree).expanduser())))
        if not worktree.parent.exists():
            raise SystemExit(f"worktree parent directory does not exist: {worktree.parent}")
    else:
        worktree = ROOT / WORKTREES_DIR / branch.split("/", 1)[1]  # P<N>-<slug>: the branch's own tail
    if worktree.exists():
        raise SystemExit(f"worktree path already exists: {worktree} (pass --worktree to pick another path)")
    # Every guard is above this line. The exclude line is not repo content and is idempotent, so
    # it goes first; the parent is created only for the default home (an override keeps its guard).
    _ensure_worktrees_excluded()
    if not args.worktree:
        worktree.parent.mkdir(parents=True, exist_ok=True)

    # base_branch (P35.S7, additive): the branch the stamp commit lands on, so a worktree checkout's
    # Streams view can read the default stream's row from it.
    data["execution"] = {"mode": "parallel", "branch": branch, "worktree": str(worktree), "consolidation": "pending", "base_branch": git_current_branch()}
    write_json(pdir / "phase.json", data)
    append_event("phase_parallel_started", phase=args.phase, branch=branch, worktree=str(worktree))
    rebuild_index_and_state()
    stamp_paths = [str(pdir.relative_to(ROOT)), *STAMP_WORKS_FILES]
    _git(["add", "--", *stamp_paths])
    _git(["commit", "--only", "-m", f"chore(works): opt {args.phase} into parallel execution", "--", *stamp_paths])
    proc = _git(["worktree", "add", "-b", branch, str(worktree), "HEAD"], check=False)
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).strip() or f"exit {proc.returncode}"
        raise SystemExit(
            f"git worktree add failed: {detail}\n"
            f"the stamp for {args.phase} is already committed on this branch; fix the cause and finish by hand: "
            f"git worktree add -b {branch} {worktree} HEAD")
    print(f"phase {args.phase} now runs in its own worktree")
    print(f"branch={branch}")
    print(f"worktree={worktree}")
    print(f"stamp committed here: chore(works): opt {args.phase} into parallel execution -- only {shown(pdir)}/ plus the regenerated works/ files "
          f"(a phase not yet committed goes in whole); everything else dirty or staged stayed behind in this checkout, uncommitted")
    print(f"the worktree starts from that commit (HEAD); {WORKTREES_DIR}/ is excluded via the repo's .git/info/exclude")
    print(f"next: enter the worktree in this session (Claude Code: EnterWorktree with path={worktree}) or open a session there, run next, and drive the phase from that checkout")
    print(f"this stream's pointer now skips {args.phase}; after the branch is merged back, run: {WORKFLOW_CMD} parallel-teardown {args.phase}")


def _worktree_entries(cwd=None) -> list:
    """`[(path, ref-or-None)]` for every worktree git registers in the repo at `cwd` (ROOT by default),
    from `git worktree list --porcelain`; `ref` is `refs/heads/<name>`, or None when detached/bare."""
    entries, path, ref = [], None, None
    for line in _git(["worktree", "list", "--porcelain"], cwd=cwd).stdout.splitlines() + [""]:
        if line.startswith("worktree "):
            path, ref = line[len("worktree "):], None
        elif line.startswith("branch "):
            ref = line[len("branch "):]
        elif not line.strip() and path is not None:
            entries.append((path, ref))
            path, ref = None, None
    return entries


def _resolve_host_base(host: Path, explicit):
    """`(ref, sha)` for the host worktree's base (P35, Decision 19), resolved inside the host repo
    with no fetch: `--host-base` when given; else `origin/HEAD`'s target, else `init.defaultBranch`
    when that branch exists locally, else a local `main`, then `master`. Refuses (nothing written)
    when nothing resolves to a commit."""
    def local_branch(name):
        return bool(name) and _git(["rev-parse", "--verify", "--quiet", f"refs/heads/{name}"], cwd=host, check=False).returncode == 0

    if explicit is not None:
        ref = explicit.strip()
        sha = _rev_parse(ref, cwd=host) if ref else None
        if not sha:
            raise SystemExit(f"--host-base {explicit!r} does not resolve to a commit in the host repo {host} "
                             f"(the engine never fetches: fetch first if the ref is remote) -- nothing was written")
        return ref, sha
    ref = None
    proc = _git(["symbolic-ref", "-q", "--short", "refs/remotes/origin/HEAD"], cwd=host, check=False)
    if proc.returncode == 0 and proc.stdout.strip():
        ref = proc.stdout.strip()
    if ref is None:
        configured = _git(["config", "--get", "init.defaultBranch"], cwd=host, check=False).stdout.strip()
        if local_branch(configured):
            ref = configured
    if ref is None:
        ref = next((cand for cand in ("main", "master") if local_branch(cand)), None)
    sha = _rev_parse(ref, cwd=host) if ref else None
    if not sha:
        tried = f"{ref!r} does not resolve to a commit" if ref else "no origin/HEAD, no local init.defaultBranch, main or master"
        raise SystemExit(f"cannot resolve the host's default branch for the host worktree's base ({tried}); "
                         f"pass --host-base <ref> (e.g. --host-base HEAD, or another phase's host branch to stack on it) -- nothing was written")
    return ref, sha


def _parallel_start_nested(args: argparse.Namespace, pdir: Path, data: dict, branch: str, host_branch: str, host_base_arg) -> None:
    """`parallel-start` in a nested personal install (P35): a host worktree with the nested worktree inside.

    The pair is `<host>/.claude/worktrees/P<N>-<slug>` on `host_branch` (the operator names it, by the
    host's custom), with `<host-wt>/workflow` on `phase/P<N>-<slug>` in the nested repo, which owns the
    state and the stream key. Order (P35.S2 (a)): every guard first; the host's common exclude; the
    execution block plus the re-stamped `host_anchors.created`, rebuilt; the nested stamp commit; the
    host worktree; the nested worktree; the copied `CLAUDE.local.md`. Nothing is ever created under
    `<host-wt>/.claude/` (Claude Code reads skills, agents and settings.local.json through from the main
    checkout), and nothing is fetched. A failure after the stamp commit prints the exact remaining
    commands. `execution.worktree` is the NESTED worktree, so removal stays in the repo that owns it."""
    host = HOST_ROOT
    if host is None or not _git_available(cwd=host):
        raise SystemExit(f"the nested install's host {host} is not a git work tree; parallel-start cuts a host worktree, so it needs one -- nothing was written")
    busy = _git_operation_in_progress(cwd=host)
    if busy:
        raise SystemExit(f"a {busy} is in progress in the host checkout {host}; finish or abort it first -- nothing was written")
    if host_branch.startswith("-") or _git(["check-ref-format", "--branch", host_branch], cwd=host, check=False).returncode != 0:
        raise SystemExit(f"--host-branch {host_branch!r} is not a valid branch name in the host repo -- nothing was written")
    host_entries = _worktree_entries(cwd=host)
    holder = next((path for path, ref in host_entries if ref == f"refs/heads/{host_branch}"), None)
    if holder:
        raise SystemExit(f"host branch {host_branch} is checked out in {holder}; a branch lives in one worktree at a time, so pick another --host-branch "
                         f"or switch that checkout off it -- nothing was written")
    host_branch_created = _git(["rev-parse", "--verify", "--quiet", f"refs/heads/{host_branch}"], cwd=host, check=False).returncode != 0
    rel = Path(os.path.relpath(ROOT, host))
    if args.worktree:
        host_wt = Path(os.path.abspath(str(Path(args.worktree).expanduser())))
        if not host_wt.parent.exists():
            raise SystemExit(f"worktree parent directory does not exist: {host_wt.parent}")
    else:
        host_wt = host / WORKTREES_DIR / branch.split("/", 1)[1]  # P<N>-<slug>: the phase branch's own tail
    nested_wt = host_wt / rel
    if host_wt.exists():
        raise SystemExit(f"host worktree path already exists: {host_wt} (pass --slug or --worktree to pick another path) -- nothing was written")
    registered = {os.path.realpath(path) for path, _ref in host_entries} | {os.path.realpath(path) for path, _ref in _worktree_entries()}
    for path in (host_wt, nested_wt):
        if os.path.realpath(str(path)) in registered:
            raise SystemExit(f"{path} is still registered as a git worktree (a stale entry); run `git worktree prune` in that repo first -- nothing was written")
    base_ref, base_sha = _resolve_host_base(host, host_base_arg)
    if host_branch_created:
        anchor = base_sha
    else:
        proc = _git(["merge-base", base_sha, f"refs/heads/{host_branch}"], cwd=host, check=False)
        anchor = proc.stdout.strip()
        if proc.returncode != 0 or not anchor:
            raise SystemExit(f"host branch {host_branch} shares no history with the base {base_ref} ({base_sha}); pass another --host-base -- nothing was written")
    base_branch = git_current_branch()

    # Every guard is above this line. The exclude line is not repo content and is idempotent.
    _ensure_worktrees_excluded(cwd=host)
    if not args.worktree:
        host_wt.parent.mkdir(parents=True, exist_ok=True)
    data["execution"] = {
        "mode": "parallel", "branch": branch, "worktree": str(nested_wt), "consolidation": "pending",
        "host_worktree": str(host_wt), "host_branch": host_branch, "host_base": base_ref, "host_base_sha": base_sha,
        "host_branch_created": host_branch_created, "base_branch": base_branch,
    }
    # phase-scope's base must be where the host worktree starts, not the host HEAD at new-phase
    # (P35.S2 (f)); stamped before the commit so both branches carry it.
    data = _with_host_anchors(data, {"created": anchor})
    write_json(pdir / "phase.json", data)
    append_event("phase_parallel_started", phase=args.phase, branch=branch, worktree=str(nested_wt),
                 host_branch=host_branch, host_worktree=str(host_wt))
    rebuild_index_and_state()
    stamp_paths = [str(pdir.relative_to(ROOT)), *STAMP_WORKS_FILES]
    _git(["add", "--", *stamp_paths])
    _git(["commit", "--only", "-m", f"chore(works): opt {args.phase} into parallel execution", "--", *stamp_paths])

    q = shlex.quote
    host_add = (["worktree", "add", "-b", host_branch, str(host_wt), base_sha] if host_branch_created
                else ["worktree", "add", str(host_wt), host_branch])
    steps = [
        (["git", "-C", str(host), *host_add], host),
        (["git", "-C", str(ROOT), "worktree", "add", "-b", branch, str(nested_wt), "HEAD"], ROOT),
    ]
    local_md = host / "CLAUDE.local.md"
    copy_cmd = f"cp {q(str(local_md))} {q(str(host_wt / 'CLAUDE.local.md'))}"

    def remaining(i):
        cmds = [" ".join(q(part) for part in cmd) for cmd, _cwd in steps[i:]]
        if local_md.is_file():
            cmds.append(copy_cmd)
        return "\n".join(f"  {c}" for c in cmds)

    for i, (cmd, cwd) in enumerate(steps):
        proc = _git(cmd[3:], cwd=cwd, check=False)
        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout).strip() or f"exit {proc.returncode}"
            undo = (f"\nor give up on the pair: git -C {q(str(host))} worktree remove {q(str(host_wt))}, then un-stamp {args.phase} by hand "
                    f"(delete the execution block from {shown(pdir)}/phase.json and commit)" if i == 1 else "")
            raise SystemExit(
                f"{' '.join(cmd[3:5])} failed: {detail}\n"
                f"the stamp for {args.phase} is already committed in the nested repo; fix the cause and finish by hand, in this order:\n"
                f"{remaining(i)}{undo}")
    copied = False
    if local_md.is_file():
        try:
            shutil.copyfile(local_md, host_wt / "CLAUDE.local.md")
            copied = True
        except OSError as exc:
            raise SystemExit(f"copying CLAUDE.local.md failed: {exc}\nboth worktrees exist; without the copy a session there loads no workspace contract. Finish by hand:\n  {copy_cmd}")
    print(f"phase {args.phase} now runs in its own worktree pair (nested install)")
    print(f"branch={branch}")
    print(f"worktree={nested_wt}")
    print(f"host_worktree={host_wt}")
    print(f"host_branch={host_branch} ({'created by parallel-start' if host_branch_created else 'reused: it existed and was not checked out'})")
    print(f"host_base={base_ref} ({base_sha})")
    print(f"host_anchors.created={anchor} ({'the base' if host_branch_created else 'merge-base of the base and the reused branch'}) -- phase-scope's base")
    print(f"stamp committed in the nested repo: chore(works): opt {args.phase} into parallel execution -- only {shown(pdir)}/ plus the regenerated works/ files; "
          f"everything else dirty or staged stayed behind, uncommitted")
    print(f"the nested worktree starts from that commit (HEAD); /{WORKTREES_DIR}/ is excluded via the host's .git/info/exclude")
    print("CLAUDE.local.md copied into the host worktree" if copied else f"note: no {local_md} to copy -- a session in the host worktree loads no workspace contract")
    print(f"next: enter the host worktree in this session (Claude Code: EnterWorktree with path={host_wt}) or open a session there, run "
          f"{WORKFLOW_CMD} next (it prints stream={branch}), and drive the phase from that checkout")
    print(f"there: product commits go to {host_branch} in the host worktree; workflow commits go to git -C {rel.as_posix()} (the nested worktree, on {branch})")
    print(f"this stream's pointer now skips {args.phase}; the host branch is integrated by the host's own custom (nested-convention), never merged by the engine")


def parallel_skip(args: argparse.Namespace) -> None:
    """Retired in v43: a no-op that explains itself and writes nothing.

    This command existed because v42 made the worktree the default, so "run on main" needed a
    marker (`execution: {"mode": "default"}`) that the hints and `parallel-start` could see.
    v43 put the default back on this stream, so there is nothing left to pin -- a phase with no
    execution block already runs here, and only `parallel-start` moves it.

    It stays callable rather than removed so an adopting workspace's habits and scripts (a docs
    phase was always pinned) do not break on upgrade; it reports the phase's real stream and
    exits 0. Phases still carrying v42's pin keep it: `parallel-start` honours it, so an old
    deliberate pin is never silently overridden.
    """
    pdir = require_phase(args.phase)
    data = read_json(pdir / "phase.json")
    execution = phase_execution(data)
    print(f"note: parallel-skip is a no-op since v43 -- the default stream IS the default; nothing was stamped and nothing was written")
    if execution:
        print(f"phase {args.phase} is not on the default stream: it runs in its own worktree on {execution.get('branch')} (asked for with parallel-start)")
        print(f"to bring it back here, merge and retire it: {WORKFLOW_CMD} parallel-teardown {args.phase}")
    elif phase_pinned(data):
        print(f"phase {args.phase} carries v42's legacy pin (execution.mode=default) and runs on the default stream -- as it would with no block at all")
    else:
        print(f"phase {args.phase} already runs on the default stream")
        print(f"to run it in its own worktree instead, ask for one: {WORKFLOW_CMD} parallel-start {args.phase}{NESTED_HOST_BRANCH_ARG}")


def parallel_teardown(args: argparse.Namespace) -> None:
    """Retire a merged parallel phase's worktree and branch, from the default stream.

    Refuses while the branch is unmerged (merging is a separate step). Keeps `mode`/`branch`/
    `consolidation` as history and only nulls `worktree`, which is informational anyway.

    In a nested personal install (P35) the phase has a worktree PAIR -- see `_parallel_teardown_nested`;
    `--discard-ignored` belongs to it and is refused at root.
    """
    discard_ignored = getattr(args, "discard_ignored", False)
    if NESTED is None and discard_ignored:
        raise SystemExit("--discard-ignored is for a nested personal install's paired teardown only; "
                         "at root, teardown removes the worktree as it always has -- nothing was removed")
    pdir = require_phase(args.phase)
    data = read_json(pdir / "phase.json")
    execution = phase_execution(data)
    if not execution:
        raise SystemExit(f"phase {args.phase} is not running in its own worktree (no parallel execution block)")
    branch = execution.get("branch")
    if not branch:
        raise SystemExit(f"phase {args.phase} has a parallel execution block with no branch; fix phase.json first")
    _require_git_repo()
    if git_current_branch() == branch:
        raise SystemExit(f"this checkout is on {branch}; run parallel-teardown from the default stream (a worktree cannot remove itself)")
    branch_exists = _branch_exists(branch)
    if branch_exists and _git(["merge-base", "--is-ancestor", branch, "HEAD"], check=False).returncode != 0:
        raise SystemExit(f"branch {branch} is not merged into HEAD; merge it first, then run: {WORKFLOW_CMD} parallel-teardown {args.phase}")
    if NESTED is not None:
        _parallel_teardown_nested(args, pdir, data, execution, branch, branch_exists, discard_ignored)
        return
    removed = []
    worktree = execution.get("worktree")
    if worktree and Path(worktree).exists():
        proc = _git(["worktree", "remove", str(worktree)], check=False)
        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout).strip() or f"exit {proc.returncode}"
            raise SystemExit(f"git worktree remove {worktree} failed: {detail}\nclean up that checkout (uncommitted work?) or drop it with `git worktree remove --force {worktree}`, then re-run")
        removed.append(f"worktree {worktree}")
    else:
        _git(["worktree", "prune"], check=False)
    if branch_exists:
        _git(["branch", "-d", branch])  # -d refuses an unmerged branch: a free second check
        removed.append(f"branch {branch}")
    data["execution"]["worktree"] = None
    write_json(pdir / "phase.json", data)
    append_event("phase_parallel_torndown", phase=args.phase, branch=branch)
    rebuild_index_and_state()
    print(f"phase {args.phase} parallel checkout retired")
    for item in removed:
        print(f"removed {item}")
    if not removed:
        print("nothing to remove (worktree and branch were already gone)")
    print(f"execution.worktree=null; mode/branch/consolidation kept as history (branch={branch}, consolidation={phase_consolidation(data)})")
    if phase_consolidation(data) == "pending":
        print(f"warning: {args.phase} doc consolidation is still 'pending' -- run the post-merge consolidation on this stream (teardown does not gate on it)")
    print("phase.json changed -- commit it with the rest of the merge cleanup")


def _ignored_worktree_files(path, skip=()) -> list:
    """The ignored, worktree-only files and directories in the checkout at `path`, as git lists them
    (`ls-files --others --ignored --exclude-standard --directory`), minus the entries in `skip`.
    `git worktree remove` deletes these without asking, so the paired teardown lists them first.
    git also lists a directory holding only ignored entries beside those entries; the directory
    line is dropped then, so each path is named once."""
    proc = _git(["ls-files", "-z", "--others", "--ignored", "--exclude-standard", "--directory"], cwd=path)
    entries = [entry for entry in proc.stdout.split("\0") if entry and entry not in skip]
    return [entry for entry in entries
            if not (entry.endswith("/") and any(other != entry and other.startswith(entry) for other in entries))]


def _parallel_teardown_nested(args: argparse.Namespace, pdir: Path, data: dict, execution: dict,
                              branch: str, branch_exists: bool, discard_ignored: bool) -> None:
    """`parallel-teardown` in a nested personal install (P35): retire the host + nested worktree pair.

    Run from the default stream of the nested repo, after `phase/...` is merged there (the caller
    checked it). Order (P35.S2 (d), (e); Decisions 11, 19):

    1. every guard first, in one combined report, with nothing touched: uncommitted work in the
       nested worktree; ignored, worktree-only files in either worktree (`git worktree remove`
       deletes them silently, so they are listed and refused unless `--discard-ignored`); uncommitted
       work in the host worktree; a detached host worktree holding commits no ref keeps (orphaned
       at removal);
    2. the nested worktree, ALWAYS first -- removing the host worktree first exits 0 and silently
       deletes the nested worktree inside it, untracked state included;
    3. the host worktree;
    4. the host branch: deleted (`-D`; `-d` measures against HEAD) only when the engine created it
       and it has 0 commits beyond `host_base_sha`; otherwise kept -- it is the operator's, integrated
       by the host's own custom (Decision 18), and the engine never pushes, opens or merges it;
    5. the nested `phase/...` branch, as at root; a registration left in either repo is pruned.

    `worktree` and `host_worktree` become null; the other host keys and `base_branch` stay as
    history. A failure after the first removal prints the exact remaining commands; a re-run of
    this command resumes too, since every step skips what is already gone."""
    q = shlex.quote
    host = HOST_ROOT
    nested_wt = execution.get("worktree")
    host_wt = execution.get("host_worktree")
    host_branch = execution.get("host_branch")
    base_sha = execution.get("host_base_sha")
    created = execution.get("host_branch_created") is True
    nested_live = bool(nested_wt) and Path(nested_wt).exists()
    host_live = bool(host_wt) and Path(host_wt).exists()
    host_git = host is not None and _git_available(cwd=host)
    if (host_live or host_branch) and not host_git:
        raise SystemExit(f"the nested install's host {host} is not a git work tree; the paired teardown needs it to retire the host worktree "
                         f"and branch -- nothing was removed")

    # 1. Every guard, before anything is removed.
    problems, ignored = [], []
    if nested_live:
        dirty = _git(["status", "--porcelain", "--untracked-files=normal"], cwd=nested_wt).stdout.splitlines()
        if dirty:
            problems.append(f"the nested worktree {nested_wt} has uncommitted work (commit it on {branch} and merge again, or discard it):\n"
                            + "\n".join(f"      {line}" for line in dirty))
        ignored += [(nested_wt, entry) for entry in _ignored_worktree_files(nested_wt)]
    if host_live:
        rel = os.path.relpath(ROOT, host)
        skip = {"CLAUDE.local.md", f"{Path(rel).as_posix().rstrip('/')}/"}  # the engine's copy; the nested worktree (step 2)
        ignored += [(host_wt, entry) for entry in _ignored_worktree_files(host_wt, skip)]
        dirty = _git(["status", "--porcelain", "--untracked-files=normal"], cwd=host_wt).stdout.splitlines()
        if dirty:
            problems.append(f"the host worktree {host_wt} has uncommitted work (commit it on {host_branch}, or move or discard it):\n"
                            + "\n".join(f"      {line}" for line in dirty))
        if _git(["symbolic-ref", "-q", "HEAD"], cwd=host_wt, check=False).returncode != 0:
            keep = [base_sha] if base_sha else []
            proc = _git(["rev-list", "--count", "HEAD", "--not", *keep, "--branches", "--tags", "--remotes"], cwd=host_wt, check=False)
            orphans = int(proc.stdout.strip() or 0) if proc.returncode == 0 else 0
            if orphans:
                head = _git(["rev-parse", "--short", "HEAD"], cwd=host_wt, check=False).stdout.strip()
                problems.append(f"the host worktree {host_wt} is detached at {head} with {orphans} commit(s) beyond the base that no branch, tag or "
                                f"remote ref holds; removing it would orphan them -- put them on a branch first "
                                f"(git -C {q(host_wt)} switch -c <name>, or switch {host_branch} to them)")
    if ignored and not discard_ignored:
        problems.append("ignored, worktree-only files would be deleted with the worktrees (git worktree remove does not ask):\n"
                        + "\n".join(f"      {os.path.join(where, entry)}" for where, entry in ignored)
                        + f"\n    move them out first, or re-run with --discard-ignored to delete them: {WORKFLOW_CMD} parallel-teardown {args.phase} --discard-ignored")
    if problems:
        lines = [f"parallel-teardown {args.phase} refused -- nothing was removed:"]
        lines += [f"{i}. {problem}" for i, problem in enumerate(problems, 1)]
        raise SystemExit("\n".join(lines))

    # The host branch's fate is decided before any removal (its commits do not change).
    delete_host_branch, keep_reason = False, None
    host_branch_exists = bool(host_branch) and host_git and _git(
        ["rev-parse", "--verify", "--quiet", f"refs/heads/{host_branch}"], cwd=host, check=False).returncode == 0
    if host_branch_exists:
        holders = [path for path, ref in _worktree_entries(cwd=host) if ref == f"refs/heads/{host_branch}"
                   and not (host_wt and os.path.realpath(path) == os.path.realpath(host_wt))]
        ahead = None
        if base_sha:
            proc = _git(["rev-list", "--count", f"{base_sha}..refs/heads/{host_branch}"], cwd=host, check=False)
            ahead = int(proc.stdout.strip()) if proc.returncode == 0 and proc.stdout.strip().isdigit() else None
        if holders:
            keep_reason = f"it is checked out in {holders[0]}"
        elif not created:
            keep_reason = "it existed before parallel-start, which reused it"
        elif ahead is None:
            keep_reason = f"its commits beyond the base {base_sha} could not be counted"
        elif ahead:
            keep_reason = f"it has {ahead} commit(s) beyond its base {execution.get('host_base')} ({base_sha[:12]})"
        else:
            delete_host_branch = True

    # 2-5. The removals, nested half first. Each entry: (label, git args, cwd). A worktree already
    # gone from disk but still registered is pruned instead, before the branches: a stale
    # registration still holds its branch, so `branch -D`/`-d` would refuse.
    def registered(repo, path):
        return any(os.path.realpath(p) == os.path.realpath(path) for p, _ref in _worktree_entries(cwd=repo))

    steps = []
    if nested_live:
        steps.append((f"nested worktree {nested_wt}", ["worktree", "remove", str(nested_wt)], ROOT))
    elif nested_wt and registered(ROOT, nested_wt):
        steps.append((f"the stale registration of {nested_wt} (git worktree prune in {ROOT})", ["worktree", "prune"], ROOT))
    if host_live:
        steps.append((f"host worktree {host_wt}", ["worktree", "remove", str(host_wt)], host))
    elif host_wt and host_git and registered(host, host_wt):
        steps.append((f"the stale registration of {host_wt} (git worktree prune in {host})", ["worktree", "prune"], host))
    if delete_host_branch:
        steps.append((f"host branch {host_branch} (created by parallel-start, no commits beyond its base)",
                      ["branch", "-D", host_branch], host))
    if branch_exists:
        steps.append((f"branch {branch}", ["branch", "-d", branch], ROOT))  # -d refuses an unmerged branch: a free second check

    def command(git_args, cwd):
        return f"git -C {q(str(cwd))} " + " ".join(q(part) for part in git_args)

    removed = []
    for i, (label, git_args, cwd) in enumerate(steps):
        proc = _git(git_args, cwd=cwd, check=False)
        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout).strip() or f"exit {proc.returncode}"
            done = "".join(f"\nremoved {item}" for item in removed) or "\nnothing was removed yet"
            rest = "\n".join(f"  {command(a, c)}" for _l, a, c in steps[i:])
            raise SystemExit(
                f"{command(git_args, cwd)} failed: {detail}{done}\n"
                f"fix the cause, then re-run {WORKFLOW_CMD} parallel-teardown {args.phase} (it resumes), or finish by hand, in this order:\n{rest}\n"
                f"  then set execution.worktree and execution.host_worktree to null in {shown(pdir)}/phase.json")
        removed.append(label)

    pruned = []  # a registration a successful `worktree remove` still left behind
    for repo, path in ((ROOT, nested_wt), (host, host_wt)):
        if not path or (repo is host and not host_git):
            continue
        if registered(repo, path):
            _git(["worktree", "prune"], cwd=repo, check=False)
            pruned.append(str(repo))

    data["execution"]["worktree"] = None
    data["execution"]["host_worktree"] = None
    write_json(pdir / "phase.json", data)
    append_event("phase_parallel_torndown", phase=args.phase, branch=branch, host_branch=host_branch)
    rebuild_index_and_state()
    print(f"phase {args.phase} parallel checkout pair retired (nested install)")
    for item in removed:
        print(f"removed {item}")
    if not removed:
        print("nothing to remove (both worktrees and the branch were already gone)")
    for repo in pruned:
        print(f"pruned a stale worktree registration in {repo}")
    if ignored:
        print(f"deleted {len(ignored)} ignored, worktree-only path(s) with the worktrees (--discard-ignored)")
    if host_branch and not delete_host_branch:
        if host_branch_exists:
            print(f"kept host branch {host_branch}: {keep_reason}")
            print(f"the host side follows the host's own custom (nested-convention): the branch is yours for the PR; "
                  f"the engine pushed, opened and merged nothing")
        else:
            print(f"host branch {host_branch} is already gone; nothing to keep")
    print(f"execution.worktree=null, execution.host_worktree=null; mode/branch/consolidation and host_branch/host_base/host_base_sha/"
          f"host_branch_created/base_branch kept as history (branch={branch}, host_branch={host_branch}, consolidation={phase_consolidation(data)})")
    if phase_consolidation(data) == "pending":
        print(f"warning: {args.phase} doc consolidation is still 'pending' -- run the post-merge consolidation on this stream (teardown does not gate on it)")
    print("phase.json changed -- commit it in the nested repo with the rest of the merge cleanup")


def parallel_gate(args: argparse.Namespace) -> None:
    """The quiet-point gate: may this parallel phase's branch be merged into the default stream now?

    Two independent questions, both read at a git ref so no checkout has to be switched:

    * **branch side** -- the phase is `done` with a `pass` review *on its own branch*. Main's copy
      is stale before the merge, so it is never trusted here.
    * **main side** -- the default stream is quiet: every non-parallel active phase is `planned` or
      `done`. Merging into a live phase is what this gate exists to prevent.

    Read-only and CI-shaped: `GATE OPEN` + exit 0, or `GATE CLOSED` + numbered reasons + exit 1.
    In a nested install (P35) both sides are read in the nested repo, which owns the state.
    """
    pdir = require_phase(args.phase)
    data = read_json(pdir / "phase.json")
    execution = phase_execution(data)
    branch_ref = args.branch_ref or (execution or {}).get("branch")
    if not branch_ref:
        raise SystemExit(
            f"phase {args.phase} carries no parallel execution block in this checkout; "
            f"pass --branch-ref <ref> to name the phase branch explicitly")
    _require_git_repo()
    reasons: list = []
    notes: list = []
    print(f"phase={args.phase}")
    print(f"branch_ref={branch_ref}")

    branch_data = _phase_json_at_ref(branch_ref, args.phase)
    if branch_data is None:
        reasons.append(
            f"cannot read works/phases/active/{args.phase}/phase.json at {branch_ref} "
            f"(unknown ref, or the phase folder does not exist there)")
    else:
        branch_status = branch_data.get("status")
        branch_review = (branch_data.get("review") or {}).get("status")
        print(f"branch_phase_status={branch_status}")
        print(f"branch_review={branch_review}")
        if branch_status != "done":
            reasons.append(f"phase {args.phase} is {branch_status!r} on {branch_ref}, not 'done'; finish its slices and record the review first")
        if branch_review != "pass":
            reasons.append(f"phase {args.phase} review is {branch_review!r} on {branch_ref}, not 'pass'; record a passing review with review-phase on the branch")

    if args.main_ref:
        main_phases = _phases_at_ref(args.main_ref)
        if main_phases is None:
            reasons.append(f"cannot read the default stream's phase state at {args.main_ref} (unknown ref?)")
            main_phases = []
        source = args.main_ref
    else:
        # Without --main-ref the working tree stands in for main -- unless it IS the phase
        # branch: checked out by name (its worktree) or detached at its tip (how CI checks out a
        # PR). Then (v42) the local default branch stands in instead, so the gate can run from
        # the worktree before the session exits it; only when no default branch resolves is the
        # operator asked for --main-ref. Sharing a tip with main is normal right after the stamp
        # and does NOT count.
        current = git_current_branch()
        on_phase_branch = current is not None and current in {(execution or {}).get("branch"), branch_ref}
        detached_at_tip = current is None and _git(["rev-parse", "HEAD"], check=False).stdout.strip() == _git(["rev-parse", branch_ref], check=False).stdout.strip() != ""
        if on_phase_branch or detached_at_tip:
            default = _default_branch()
            if not default:
                raise SystemExit(
                    f"this checkout is the phase branch {branch_ref} itself and no default branch (origin/HEAD, main, master) resolves, "
                    f"so nothing can stand in for the default stream; pass --main-ref <ref> (e.g. --main-ref origin/main)")
            main_phases = _phases_at_ref(default)
            if main_phases is None:
                reasons.append(f"cannot read the default stream's phase state at {default} (unknown ref?)")
                main_phases = []
            source = f"{default} (local default branch; this checkout is the phase branch)"
        else:
            main_phases = all_active_phases()
            source = "working tree"
    print(f"main_state_source={source}")
    for p in main_phases:
        if p.get("id") == args.phase or phase_execution(p):
            continue  # parallel phases run on their own stream; they do not make main busy
        if p.get("status") in BUSY_PHASE_STATUSES:
            reasons.append(f"the default stream is not quiet: phase {p.get('id')} is {p.get('status')!r} (finish or park it, then re-run the gate)")
    for p in main_phases:
        other = phase_execution(p)
        if p.get("id") != args.phase and other and phase_consolidation(p) == "pending" and p.get("status") == "done":
            notes.append(f"phase {p.get('id')} is merged but not consolidated yet; consolidation is serialized, so finish it first (parallel-consolidated {p.get('id')})")
    for n in notes:
        print(f"note: {n}")

    if reasons:
        print("GATE CLOSED")
        for i, reason in enumerate(reasons, 1):
            print(f"{i}. {reason}")
        raise SystemExit(1)
    print("GATE OPEN")
    print(f"next: merge {branch_ref} into the default stream, then run: {WORKFLOW_CMD} parallel-merge-finish")


def parallel_merge_finish(args: argparse.Namespace) -> None:
    """Run on the default stream right after a phase branch's merge: regenerate, then report what is left.

    The generated files (`works/state.json`, `works/index.json`, `works/backlog.md`,
    `works/deferred.md`, `docs/current/*.md`) are derived, never authored, so a merge conflict in
    them is resolved by taking either side and regenerating here -- which is why parallel mode
    needs no custom git merge driver (a driver would need per-clone `git config` and would not
    travel with the repo). Makes no commit: the regenerated files belong to the merge commit's
    cleanup, which the orchestrator owns. In a nested install (P35) it runs in the nested repo,
    where `phase/...` was merged (`git -C workflow merge`), and never touches the host repo: the
    host branch is integrated by the host's own custom, never by the engine.
    """
    git_ok = _git_available()
    if git_ok and _git(["rev-parse", "-q", "--verify", "MERGE_HEAD"], check=False).returncode == 0:
        raise SystemExit(
            "this checkout is mid-merge (MERGE_HEAD exists) -- finish the merge first, then re-run.\n"
            f"generated files ({', '.join(GENERATED_FILES)}) are regenerated by this command, so resolve any conflict in them by taking EITHER side.\n"
            f"then: {WORKFLOW_CMD} parallel-merge-finish")
    phases = all_active_phases()
    stream = current_stream(phases)
    if stream:
        print(f"warning: this checkout is on parallel stream {stream}; parallel-merge-finish belongs on the default stream, after the merge")
    rebuild_docs()
    rebuild_index_and_state()
    print(f"regenerated from the merged folders: {', '.join(GENERATED_FILES)}")
    awaiting = []
    for p in phases_owing_consolidation(all_active_phases()):
        execution = phase_execution(p)
        if not execution or p.get("status") != "done":
            continue
        # a deleted branch means the phase was already merged and torn down
        if _parallel_branch_merged(execution, git_ok):
            awaiting.append((p, execution))
    if not awaiting:
        print("no merged phase awaits doc consolidation (merged parallel phases only -- next/validate name every phase that owes)")
    else:
        print(f"{len(awaiting)} merged phase(s) await doc consolidation -- do them ONE AT A TIME, on this stream (doc versions are allocated from a single index):")
        for p, execution in awaiting:
            print(f"- {p['id']}: doc impact notes in {shown_rel(p['path'])}/phase.md (section '## Doc impact')")
            print(f"    per note: {WORKFLOW_CMD} doc-new-version --doc <doc> --summary \"...\" --source {p['id']}.REVIEW -> edit the returned edit_path -> {WORKFLOW_CMD} rebuild-docs")
            print(f"    when that phase's notes are all consolidated: {WORKFLOW_CMD} parallel-consolidated {p['id']}")
            if execution.get("worktree") or (git_ok and execution.get("branch") and _branch_exists(execution["branch"])):
                print(f"    then retire its branch + worktree: {WORKFLOW_CMD} parallel-teardown {p['id']}")
    print("no commit made -- commit the regenerated files with the merge cleanup")


def parallel_consolidated(args: argparse.Namespace) -> None:
    """Record that a merged parallel phase's deferred doc consolidation is finished.

    The engine cannot write the prose: an agent runs `doc-new-version` per "Doc impact" note on the
    default stream and then calls this to flip `execution.consolidation` to "done", which is also
    what unblocks archiving the phase. In a nested install (P35) the same flip runs on the nested
    repo's default stream; the host repo is not read or written.
    """
    pdir = require_phase(args.phase)
    data = read_json(pdir / "phase.json")
    execution = phase_execution(data)
    if not execution:
        raise SystemExit(f"phase {args.phase} is not running in its own worktree (no parallel execution block); record its consolidation with: {WORKFLOW_CMD} docs-consolidated {args.phase}")
    stream = current_stream(all_active_phases())
    if stream:
        raise SystemExit(f"this checkout is on parallel stream {stream}; run parallel-consolidated on the default stream, after the branch is merged")
    if data.get("status") != "done":
        raise SystemExit(f"phase {args.phase} is {data.get('status')!r}, not 'done'; consolidation happens after its review passes and the branch is merged")
    review_status = data.get("review", {}).get("status")
    if review_status != "pass":
        raise SystemExit(f"phase {args.phase} review is {review_status!r}, not 'pass'; record the passing review before consolidating")
    consolidation = phase_consolidation(data)
    if consolidation == "done":
        raise SystemExit(f"phase {args.phase} is already marked consolidated (consolidation='done')")
    if consolidation != "pending":
        raise SystemExit(f"phase {args.phase} has consolidation {consolidation!r}; expected 'pending' (set by parallel-start, or by its passing review)")
    set_phase_consolidation(data, "done")
    write_json(pdir / "phase.json", data)
    append_event("phase_consolidated", phase=args.phase, branch=execution.get("branch"))
    rebuild_index_and_state()
    print(f"phase {args.phase} docs consolidated (consolidation=done)")
    print("phase.json changed -- commit it together with the new doc versions")
    branch = execution.get("branch")
    if execution.get("worktree") or (branch and _git_available() and _branch_exists(branch)):
        print(f"next: {WORKFLOW_CMD} parallel-teardown {args.phase}")
    print(f"{args.phase} is now archivable (archive-phase/rotate-backlog no longer block on pending consolidation)")


def docs_debt(args: argparse.Namespace) -> None:
    """The docs phase's worklist: every phase owing durable-doc consolidation, its `## Doc impact`
    notes, the docs those notes touch, and the commands that pay them. Writes nothing.

    `next` and `validate` say *that* the debt exists; this says *what it is*, so the docs-phase
    intake (`create-phase`) and the docs phase's own `DECOMP` never re-derive it by hand. The
    default cut is one slice per doc -- `doc-new-version` is per doc, and one doc usually collects
    notes from several phases -- which is why the per-doc rollup is printed as well as the
    per-phase blocks.
    """
    phases = all_active_phases()
    owing = phases_owing_consolidation(phases)
    if not owing:
        print("docs_debt=none (no active phase owes durable-doc consolidation)")
        return
    stream = current_stream(phases)
    if stream:
        print(f"warning: this checkout is on parallel stream {stream}; doc consolidation runs on the default stream")
    # The per-doc rollup is the same mapping `docs` and `validate` call stale: one helper, so the
    # worklist and the staleness warning can never name a different set of docs.
    per_doc = stale_docs(owing)
    notes_total, blocks = 0, []
    for phase in owing:
        notes = phase_doc_impact_notes(ROOT / phase["path"])
        notes_total += len(notes)
        blocks.append((phase, notes))
    docs_hit = sorted(d for d in per_doc if d != UNASSIGNED_DOC)
    cover = consolidation_cover(phases)
    print(f"docs_debt={', '.join(p['id'] for p in owing)} ({len(owing)} phase(s), {notes_total} note(s), {len(docs_hit)} doc(s))")
    for phase, notes in blocks:
        print()
        print(f"{phase['id']} {phase.get('name', '')} -- {shown_rel(phase['path'])}/phase.md '## Doc impact'")
        pay = consolidation_command(phase)
        tail = "   (merged parallel phase)" if pay == "parallel-consolidated" else ""
        print(f"  pay: {WORKFLOW_CMD} {pay} {phase['id']}{tail}")
        for docs_phase in cover.get(phase["id"], []):  # a live docs phase already pays this one (v51)
            print(f"  paid by: {docs_phase['id']} ({str(docs_phase.get('status', '')).replace('_', ' ')})")
        if not notes:
            print("  - (no notes in the notebook; the debt was stamped from a list since compressed -- check git history)")
        for note in notes:
            print(f"  - {note}")
    print()
    print(f"docs={', '.join(docs_hit) or 'none named'} (default docs-phase cut: one slice per doc)")
    for doc in docs_hit + ([UNASSIGNED_DOC] if UNASSIGNED_DOC in per_doc else []):
        by_phase = per_doc[doc]
        count = sum(by_phase.values())
        print(f"  {doc}: {count} note(s) from {', '.join(sorted(by_phase))}")
    if UNASSIGNED_DOC in per_doc:
        print(f"  {UNASSIGNED_DOC} = the note names no doc from the known set; read it in the notebook and decide")
    print()
    print(f'per note: {WORKFLOW_CMD} doc-new-version --doc <doc> --summary "..." --source <P>.REVIEW')
    print(f"          -> edit only the returned edit_path -> {WORKFLOW_CMD} rebuild-docs")
    print("per phase, once all of its notes are consolidated: the pay command above (that is also what unblocks archiving)")
    print("read-only: this command wrote nothing")


def docs_consolidated(args: argparse.Namespace) -> None:
    """Record that a phase's deferred durable-doc consolidation has landed.

    Every phase defers: its passing review verified the `## Doc impact` list and created no
    versions, and a docs phase the operator creates later runs `doc-new-version` per note. This
    flips the debt to "done", which is also what unblocks archiving the phase. The engine cannot
    tell whether the prose is right, so this is an explicit operator/orchestrator statement.
    `parallel-consolidated` is the parallel-mode twin, kept for the post-merge sequence.
    """
    pdir = require_phase(args.phase)
    data = read_json(pdir / "phase.json")
    # Doc versions come from one shared index, so consolidation belongs on the default stream --
    # the same refusal `doc-new-version` makes, one step earlier.
    stream = current_stream(all_active_phases())
    if stream:
        raise SystemExit(f"this checkout is on parallel stream {stream}; run docs-consolidated on the default stream, after the branch is merged (parallel phases use: parallel-consolidated {args.phase})")
    consolidation = phase_consolidation(data)
    if consolidation == "done":
        raise SystemExit(f"phase {args.phase} is already marked consolidated (consolidation='done')")
    if consolidation != "pending":
        raise SystemExit(f"phase {args.phase} owes no doc consolidation (consolidation is {consolidation!r}); a passing review records the debt when the phase's '## Doc impact' list is non-empty")
    set_phase_consolidation(data, "done")
    write_json(pdir / "phase.json", data)
    append_event("phase_consolidated", phase=args.phase)
    rebuild_index_and_state()
    print(f"phase {args.phase} docs consolidated (consolidation=done)")
    print("phase.json changed -- commit it together with the new doc versions")
    print(f"{args.phase} is now archivable (archive-phase/rotate-backlog no longer block on pending consolidation)")


def _parallel_verdict(phase_id: str, status, review, slices, consolidation, merged, branch_gone: bool, own_stream: bool) -> str:
    """One line saying where a parallel phase stands, and what the operator does next.

    `merged` is None when the answer is unknown (this checkout is the phase's own stream, so it
    trivially contains its own branch); `branch_gone` means the branch was deleted, which implies
    the phase was merged first -- `parallel-teardown` refuses an unmerged branch.
    """
    return _parallel_verdict_pair(phase_id, status, review, slices, consolidation, merged, branch_gone, own_stream)[1]


def _parallel_verdict_pair(phase_id: str, status, review, slices, consolidation, merged, branch_gone: bool, own_stream: bool) -> tuple:
    """`(short, long)`: the cell `## Streams` shows, and the sentence `parallel-status` prints. One
    decision tree, so the dashboard and the command can never disagree about where a phase stands."""
    if status is None:
        return ("unknown", "unknown -- neither the phase branch nor a local copy could be read")
    slices = slices or []
    total = len(slices)
    done = sum(1 for s in slices if s.get("status") == "done")
    open_slice = next((s.get("id") for s in slices if s.get("status") != "done"), None)
    integrated = merged is True or branch_gone
    if status == "done" and review == "pass":
        if consolidation == "pending":
            if integrated:
                return ("merged \u2014 awaiting consolidation",
                        f"merged, docs still awaiting consolidation -- run on the default stream: "
                        f"parallel-merge-finish, then parallel-consolidated {phase_id}")
            return ("ready to merge",
                    f"ready to merge -- check the quiet point first: parallel-gate {phase_id} (from the default stream)")
        if integrated:
            if not branch_gone:
                return ("merged + consolidated", f"merged + consolidated -- retire the branch and worktree: parallel-teardown {phase_id}")
            return ("torn down", f"merged, consolidated and torn down -- nothing left but archiving ({phase_id} is archivable)")
        return ("ready to merge",
                f"ready to merge -- check the quiet point first: parallel-gate {phase_id} (from the default stream)")
    if status == "done":
        return ("review not passed", f"slices done but review is {review!r} -- record a passing review on its branch (review-phase {phase_id} --verdict pass)")
    if status == "pending":
        return ("pending", "waiting on the operator (phase is pending [~]) -- it halts only its own stream")
    if status == "blocked":
        return ("blocked", "blocked on its own stream -- resolve the impediment there")
    where = " on this checkout's own stream" if own_stream else " on its branch"
    tail = f"; current slice {open_slice}" if open_slice else ""
    return (f"in flight {done}/{total}", f"in flight{where} -- {done}/{total} slices done{tail}")


def parallel_status(args: argparse.Namespace) -> None:
    """Read-only cross-stream view: this checkout's pointer plus every parallel phase's real state.

    A parallel phase's slice progress lives on its own branch, so the default stream's
    `works/backlog.md` stands still until the merge. This reads each phase's truth straight out of
    its branch with `git show` / `git ls-tree` -- no checkout switching, no fetching, and (unlike
    every other command here) no rebuild: nothing on disk is written.
    """
    phases = all_active_phases()
    stream = current_stream(phases)
    # The same in-memory pointer computation `rebuild_index_and_state` does, minus the writes.
    selectable = stream_phases(phases, stream)
    current_phase, current_slice, next_slice = resolve_current(selectable)
    waiting = operator_wait_target(selectable, current_phase, current_slice)
    print(f"stream={stream}" if stream else "stream=default")
    print(f"current_phase={current_phase or 'none'}")
    print(f"current_slice={current_slice or 'none'}")
    print(f"next_slice={next_slice or 'none'}")
    print(f"waiting_on_operator={waiting or 'none'}")
    print("(the pointer above is this stream's; each section below is read from that phase's own branch)")

    pinned = [p["id"] for p in phases if phase_pinned(p)]
    if pinned:
        print(f"pinned_to_default={','.join(pinned)}")
    parallel = [(p, phase_execution(p)) for p in phases if phase_execution(p)]
    if not parallel:
        print("no phase is in its own worktree right now -- every active phase runs on the default stream, which is where a phase runs unless asked otherwise")
        print(f"to run one in its own worktree instead, ask for it: {WORKFLOW_CMD} parallel-start <P>{NESTED_HOST_BRANCH_ARG}")
        return
    if not _git_available():
        raise SystemExit(
            "parallel-status reads each phase branch with git, but this workspace is not inside a git work tree "
            f"({len(parallel)} phase(s) are stamped for parallel execution)")
    print(f"parallel_phases={len(parallel)}")

    for phase, execution in parallel:
        pid = phase.get("id")
        branch = execution.get("branch")
        own_stream = bool(branch) and branch == stream
        note = None
        data = slices = None
        if own_stream:  # our own working tree is fresher than our own last commit
            source = "working tree (this checkout's own stream)"
            data, slices = phase, phase.get("slices", [])
        else:
            ref = None
            for candidate in ([branch, f"origin/{branch}"] if branch else []):
                data = _phase_json_at_ref(candidate, pid)
                if data is not None:
                    ref = candidate
                    break
            if ref:
                source = f"branch {ref}"
                slices = _slices_at_ref(ref, pid) or []
            else:  # torn down after the merge, or a clone that never fetched the branch
                source = "local copy"
                note = (f"(local copy; branch not found{': ' + branch if branch else ''}) -- "
                        f"merged and torn down, or never fetched in this clone")
                data, slices = phase, phase.get("slices", [])
        branch_gone = bool(branch) and not _branch_exists(branch)
        merged = None  # unknowable from the phase's own stream: HEAD *is* the branch there
        if branch and not branch_gone and not own_stream:
            merged = _git(["merge-base", "--is-ancestor", branch, "HEAD"], check=False).returncode == 0
        status = (data or {}).get("status")
        review = ((data or {}).get("review") or {}).get("status")
        worktree = execution.get("worktree")
        print()
        print(f"== {pid}: {phase.get('name', '')} ==")
        print(f"  branch={branch or '- (stamped parallel with no branch; fix phase.json)'}")
        print(f"  worktree={worktree or '- (plain clone, or already torn down)'}")
        if NESTED is not None:  # P35: the host half of the pair, as stamped at parallel-start
            if execution.get("host_branch"):
                print(f"  host_branch={execution['host_branch']}" + (" (created by parallel-start)" if execution.get("host_branch_created") else " (reused)"))
                print(f"  host_base={execution.get('host_base') or '-'} ({execution.get('host_base_sha') or '-'})")
                print(f"  host_worktree={execution.get('host_worktree') or '- (already torn down)'}")
            else:
                print("  host_branch=- (no host half stamped: an execution block written at root, before the nested pair)")
        print(f"  consolidation={phase_consolidation(phase) or '-'}")
        print(f"  source={source}")
        if note:
            print(f"  note: {note}")
        print(f"  status={status} review={review}" + ("" if merged is None else f" merged_into_HEAD={str(merged).lower()}"))
        if slices:
            width = max(len(str(s.get("id", ""))) for s in slices)
            print(f"  slices ({sum(1 for s in slices if s.get('status') == 'done')}/{len(slices)} done):")
            for s in slices:
                name = str(s.get("name", "")).replace("\n", " ")
                print(f"    [{status_box(s.get('status'))}] {str(s.get('id', '')):<{width}}  {str(s.get('status', '')):<17} {name}")
        else:
            print("  slices: none readable at that source")
        print(f"  verdict: {_parallel_verdict(pid, status, review, slices, phase_consolidation(phase), merged, branch_gone, own_stream)}")


def parallel_start_hint(state: dict, index: dict) -> str:
    """The proactive opt-in suggestion for `next`, or None (restored in v43).

    A worktree is opt-in again, so the hint fires only where one actually buys something: on
    the default stream, when the current phase is in_progress and a LATER default-stream phase
    is still `planned` -- exactly the moment a second phase would otherwise queue behind a live
    one. Suggestion only, never a default: the ordinary one-phase-at-a-time run stays silent,
    and so does a worktree checkout. v42's trigger (every planned phase, because the worktree
    was the default) is gone with the default that justified it. In a nested install (P35) the
    printed command also carries `--host-branch <name>`, which the operator names.
    """
    if state.get("stream"):
        return None
    current = state.get("current_phase")
    phases = index.get("active_phases", [])  # already ordered by phase order
    ids = [p.get("id") for p in phases]
    if current not in ids:
        return None
    cur = phases[ids.index(current)]
    if cur.get("status") != "in_progress":
        return None
    waiting = next((p for p in phases[ids.index(current) + 1:] if p.get("status") == "planned" and not p.get("execution")), None)
    if not waiting:
        return None
    return (f"hint: {waiting['id']} is waiting behind {current} -- it can run in parallel on its own branch: "
            f"{WORKFLOW_CMD} parallel-start {waiting['id']}{NESTED_HOST_BRANCH_ARG}")


# ---------------------------------------------------------------------------
# phase-scope: the phase's boundary, read from git (v41)
#
# The review (and a fidelity slice) re-runs the regression checklist only INSIDE the phase's
# boundary -- the product files the phase changed, the surfaces they feed. This command makes
# that boundary a mechanical read instead of a guess: creation commit, base..head range, files.
# Read-only and advisory everywhere: without git it explains itself and exits 0.
# ---------------------------------------------------------------------------

EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"  # `git hash-object -t tree /dev/null`
PRODUCT_PATHSPEC = [".", ":!works", ":!docs"]  # the product: everything but the workflow state and the docs
SCOPE_HINT = ("boundary: these files are what the phase changed; a checklist line whose surface "
              "none of them feed is outside this phase's boundary")


def _find_phase_dir(phase_id: str):
    """`(dir, archived)` for an active or archived phase; SystemExit when neither holds it.

    `require_phase` knows only `active/` on purpose (every state transition is an active-phase
    operation); the boundary of a done, archived phase is still a fair question -- a QA phase or
    a docs phase looks back at it -- so this lookup covers both."""
    if (ACTIVE / phase_id / "phase.json").exists():
        return ACTIVE / phase_id, False
    hits = []
    if ARCHIVED.exists():
        for d in sorted(ARCHIVED.iterdir()):
            pj = d / "phase.json"
            if not pj.is_file():
                continue
            try:
                if read_json(pj).get("id") == phase_id:
                    hits.append(d)
            except Exception:  # noqa: BLE001 - an unreadable archive entry is skipped, never fatal
                continue
    if hits:
        return hits[-1], True
    raise SystemExit(f"phase not found (active or archived): {phase_id}")


def _phase_creation_commit(phase_id: str, pdir: Path, archived: bool):
    """The sha that added the phase's `phase.json`, or None (uncommitted phase, or a shallow clone).

    Pathspecs are cwd-relative and `_git` runs at the workspace root, so no repo prefix here.
    Archiving is a pure rename, so `--follow` on the archived path walks back to the true
    creation commit; the plain active path is the fallback (git keeps a deleted path's history)."""
    active_rel = f"works/phases/active/{phase_id}/phase.json"
    if not archived:
        out = _git(["log", "--diff-filter=A", "--format=%H", "--", active_rel], check=False).stdout.split()
        return out[0] if out else None  # newest: right even if the id was ever reused
    archived_rel = f"{pdir.relative_to(ROOT).as_posix()}/phase.json"
    out = _git(["log", "--follow", "--diff-filter=A", "--format=%H", "--", archived_rel], check=False).stdout.split()
    if not out:
        out = _git(["log", "--diff-filter=A", "--format=%H", "--", active_rel], check=False).stdout.split()
    return out[-1] if out else None  # oldest: the creation, not the archive move


def _default_branch():
    """The default stream's branch: origin/HEAD's target, else a local main/master, else None."""
    proc = _git(["symbolic-ref", "-q", "--short", "refs/remotes/origin/HEAD"], check=False)
    if proc.returncode == 0 and proc.stdout.strip():
        return proc.stdout.strip()
    for cand in ("main", "master"):
        if _branch_exists(cand):
            return cand
    return None


def _rev_parse(ref: str, cwd=None):
    proc = _git(["rev-parse", "-q", "--verify", f"{ref}^{{commit}}"], cwd=cwd, check=False)
    return proc.stdout.strip() if proc.returncode == 0 and proc.stdout.strip() else None


def _diff_product_files(base: str, head: str, cwd=None, pathspec=PRODUCT_PATHSPEC) -> list:
    """`[{status, path[, from]}]` for the product files that differ between two commits."""
    proc = _git(["diff", "--name-status", "--relative", "-M", base, head, "--", *pathspec], cwd=cwd, check=False)
    files = []
    for line in proc.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        status = parts[0][:1]
        if status in ("R", "C") and len(parts) >= 3:
            files.append({"status": status, "path": parts[2], "from": parts[1]})
        else:
            files.append({"status": status, "path": parts[-1]})
    return files


def _status_product_files(cwd=None, pathspec=PRODUCT_PATHSPEC) -> list:
    """`[{status, path}]` for the uncommitted product changes in this checkout (untracked included).
    Porcelain paths are repo-root-relative, so the prefix of the directory measured is stripped."""
    proc = _git(["status", "--porcelain", "--untracked-files=all", "--", *pathspec], cwd=cwd, check=False)
    prefix = _repo_prefix() if cwd is None else _git(["rev-parse", "--show-prefix"], cwd=cwd, check=False).stdout.strip()
    files = []
    for line in proc.stdout.splitlines():
        if len(line) < 4:
            continue
        code, path = line[:2], line[3:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        if prefix and path.startswith(prefix):
            path = path[len(prefix):]
        status = "A" if code == "??" else (code.strip()[:1] or "M")
        files.append({"status": status, "path": path})
    return files


def _phase_review_commit(phase_id: str, base: str, tip: str):
    """The first commit in base..tip whose recorded phase.json says `review.status == "pass"`.

    A done phase's boundary ends where its review was recorded, not at today's HEAD -- otherwise
    every later commit on the stream would leak into it."""
    rng = tip if base == EMPTY_TREE else f"{base}..{tip}"
    proc = _git(["log", "--reverse", "--format=%H", rng, "--", f"works/phases/active/{phase_id}/phase.json"], check=False)
    for sha in proc.stdout.split():
        data = _phase_json_at_ref(sha, phase_id)
        if data and (data.get("review") or {}).get("status") == "pass":
            return sha
    return None


def phase_scope(args: argparse.Namespace) -> None:
    """Read-only: the phase's boundary -- its creation commit, the base..head range and the
    product files that range changed (works/ and docs/ excluded) -- printed for the review and a
    fidelity slice to re-run the regression checklist inside.

    Default stream: base = the creation commit's parent (so a creation commit batched with product
    edits still counts), head = HEAD, or the commit that recorded a passing review on a done phase.
    Parallel mode: base = the merge-base with the default branch, measured on the phase branch.
    Advisory everywhere: no git means one explanatory line and exit 0; an uncommitted phase lists
    the working tree instead; `--base` / `--head` override either end verbatim.
    """
    pdir, archived = _find_phase_dir(args.phase)
    data = read_json(pdir / "phase.json")
    out = {"phase": args.phase, "status": data.get("status"), "archived": archived, "mode": "default",
           "creation_commit": None, "base": None, "base_kind": None, "head": None, "head_kind": None,
           "range": None, "commits": 0, "files": [], "uncommitted": [], "notes": [], "hint": SCOPE_HINT}

    def emit(lines):
        if args.json:
            print(json.dumps(out, indent=2, ensure_ascii=False))
        else:
            for ln in lines:
                print(ln)

    header = [f"phase={args.phase} status={data.get('status')} archived={str(archived).lower()}"]
    if NESTED is not None:
        _phase_scope_nested(args, data, out, header, emit)
        return
    if not _git_available():
        out["mode"] = "no-git"
        out["hint"] = "phase-scope: no git history readable here -- derive the boundary from the slices' result.md files"
        emit([out["hint"]])
        return

    creation = _phase_creation_commit(args.phase, pdir, archived)
    out["creation_commit"] = creation
    execution = phase_execution(data)
    tip, base, base_kind = "HEAD", None, None
    if args.base:
        base = _rev_parse(args.base)
        if not base:
            raise SystemExit(f"--base {args.base}: not a commit")
        base_kind = f"from --base {args.base}"
    elif execution and execution.get("branch"):
        out["mode"] = "parallel"
        branch = execution["branch"]
        default = _default_branch()
        if default is None:
            out["notes"].append("cannot find the default branch (no origin/HEAD, no main/master) -- measured from the creation commit; pass --base <ref> to narrow")
        else:
            if git_current_branch() == branch:
                ref = "HEAD"
            elif _branch_exists(branch):
                ref = branch
            elif _rev_parse(f"origin/{branch}"):
                ref = f"origin/{branch}"
            else:
                ref = None
                out["notes"].append(f"branch {branch} is gone (merged and torn down?) -- measured on this stream from the creation commit; concurrent default-stream work may appear; pass --base to narrow")
            if ref:
                mb = _git(["merge-base", default, ref], check=False)
                if mb.returncode == 0 and mb.stdout.strip():
                    base, tip, base_kind = mb.stdout.strip(), ref, f"merge-base with {default}"
                    if ref != "HEAD":
                        out["notes"].append(f"read from branch {ref}, not this checkout")
    if base is None:
        if creation is None:
            out["uncommitted"] = _status_product_files()
            lines = header + [f"mode={out['mode']}",
                              f"creation_commit=none (works/phases/active/{args.phase}/phase.json has no commit yet -- uncommitted phase, or a shallow clone)",
                              f"uncommitted_product_files={len(out['uncommitted'])} (working tree; works/ and docs/ excluded)"]
            lines += [f"  {f['status']} {f['path']}" for f in out["uncommitted"]]
            lines += [f"note: {n}" for n in out["notes"]] + [SCOPE_HINT]
            emit(lines)
            return
        base = _rev_parse(f"{creation}^")
        if base:
            base_kind = "parent of the creation commit, so that commit's own product edits count"
        else:
            base, base_kind = EMPTY_TREE, "the empty tree: the creation commit has no readable parent (root commit, or a shallow clone)"
    if args.head:
        head = _rev_parse(args.head)
        if not head:
            raise SystemExit(f"--head {args.head}: not a commit")
        head_kind = f"from --head {args.head}"
    else:
        head, head_kind = None, None
        if (data.get("review") or {}).get("status") == "pass":
            head = _phase_review_commit(args.phase, base, tip)
            if head:
                head_kind = "the commit that recorded review.status=pass; pass --head HEAD to read to the tip"
        if not head:
            head, head_kind = _rev_parse(tip), f"the tip of {tip}"
    if not head:
        raise SystemExit(f"cannot resolve {tip} to a commit")
    rng = head if base == EMPTY_TREE else f"{base}..{head}"
    count = _git(["rev-list", "--count", rng], check=False).stdout.strip() or "0"
    files = _diff_product_files(base, head)
    uncommitted = _status_product_files() if head == _rev_parse("HEAD") else []
    out.update({"base": base, "base_kind": base_kind, "head": head, "head_kind": head_kind,
                "range": f"{base[:7]}..{head[:7]}", "commits": int(count), "files": files, "uncommitted": uncommitted})

    tally = {k: sum(1 for f in files if f["status"] == k) for k in ("A", "M", "D", "R")}
    subject = _git(["log", "-1", "--format=%s", creation], check=False).stdout.strip() if creation else ""
    lines = header + [f"mode={out['mode']}"]
    lines.append(f"creation_commit={creation}  {subject}" if creation else "creation_commit=none (measured from --base)")
    lines.append(f"base={base} ({base_kind})")
    lines.append(f"head={head} ({head_kind})")
    lines.append(f"range={out['range']} commits={count}")
    lines.append(f"product_files={len(files)} (added {tally['A']}, modified {tally['M']}, deleted {tally['D']}, renamed {tally['R']}; works/ and docs/ excluded)")
    for f in files:
        lines.append(f"  {f['status']} {f['from']} -> {f['path']}" if f.get("from") else f"  {f['status']} {f['path']}")
    if uncommitted:
        lines.append(f"uncommitted_product_files={len(uncommitted)} (working tree, not in the range above)")
        lines += [f"  {f['status']} {f['path']}" for f in uncommitted]
    lines += [f"note: {n}" for n in out["notes"]] + [SCOPE_HINT]
    emit(lines)


def _host_pathspec() -> list:
    """The host's product: everything but the nested workflow repo. Unlike at root, the host's own
    works/ or docs/ ARE product, so only the nested repo's folder is excluded."""
    return [".", f":(exclude){Path(os.path.relpath(ROOT, HOST_ROOT)).as_posix()}"]


def _phase_scope_nested(args: argparse.Namespace, data: dict, out: dict, header: list, emit) -> None:
    """phase-scope in a nested install: the same answer in the same format, read from the HOST repo.

    The nested repo holding works/ never sees the host's commits, so the range comes from the host
    anchors `new-phase` and the passing review stamped into phase.json: base = `--base`, else
    `host_anchors.created` (the host HEAD at creation, so base..head with no `^`); head = `--head`,
    else `host_anchors.review_pass` once the review passed, else the host HEAD. A phase with no
    usable anchor lists the host working tree only, mirroring the uncommitted-phase path at root."""
    host = HOST_ROOT
    spec = _host_pathspec()
    nested_dir = spec[1].split(")", 1)[1]
    out["mode"] = "nested"
    if not _git_available(cwd=host):
        out["mode"] = "no-git"
        out["hint"] = f"phase-scope: no git history readable in the host {host} -- derive the boundary from the slices' result.md files"
        emit([out["hint"]])
        return
    anchors = data.get("host_anchors") if isinstance(data.get("host_anchors"), dict) else {}
    created = anchors.get("created")
    out["creation_commit"] = created
    base = base_kind = None
    missing = None
    if args.base:
        base = _rev_parse(args.base, cwd=host)
        if not base:
            raise SystemExit(f"--base {args.base}: not a commit in the host repo {host}")
        base_kind = f"from --base {args.base}"
    elif created:
        base = _rev_parse(created, cwd=host)
        if base:
            base_kind = "the host HEAD when the phase was created (or the host worktree's base after parallel-start): phase.json host_anchors.created"
        else:
            missing = f"host_anchors.created {created} is not a commit in the host repo (rewritten history, or a shallow clone)"
    elif "created" in anchors:  # recorded as null: the host had no commit yet when the phase was created
        if _rev_parse("HEAD", cwd=host):
            base, base_kind = EMPTY_TREE, "the empty tree: the host had no commit when the phase was created"
        else:
            missing = "the host had no commit when the phase was created, and still has none"
    else:
        missing = "phase.json carries no host_anchors.created (a phase created at root, or before the nested engine)"
    if base is None:
        out["uncommitted"] = _status_product_files(cwd=host, pathspec=spec)
        lines = header + [f"mode={out['mode']}",
                          f"creation_commit=none ({missing} -- pass --base <host-sha> to measure a range)",
                          f"uncommitted_product_files={len(out['uncommitted'])} (host working tree; {nested_dir}/ excluded)"]
        lines += [f"  {f['status']} {f['path']}" for f in out["uncommitted"]]
        lines += [f"note: {n}" for n in out["notes"]] + [SCOPE_HINT]
        emit(lines)
        return
    host_head = _rev_parse("HEAD", cwd=host)
    if args.head:
        head = _rev_parse(args.head, cwd=host)
        if not head:
            raise SystemExit(f"--head {args.head}: not a commit in the host repo {host}")
        head_kind = f"from --head {args.head}"
    else:
        head, head_kind = None, None
        passed = anchors.get("review_pass")
        if (data.get("review") or {}).get("status") == "pass" and passed:
            head = _rev_parse(passed, cwd=host)
            if head:
                head_kind = "the host HEAD when the review passed: phase.json host_anchors.review_pass; pass --head HEAD to read to the tip"
            else:
                out["notes"].append(f"host_anchors.review_pass {passed} is not a commit in the host repo -- read to the host's tip instead")
        if not head:
            head, head_kind = host_head, "the tip of the host's HEAD"
    if not head:
        raise SystemExit(f"cannot resolve the host's HEAD to a commit in {host}")
    rng = head if base == EMPTY_TREE else f"{base}..{head}"
    count = _git(["rev-list", "--count", rng], cwd=host, check=False).stdout.strip() or "0"
    files = _diff_product_files(base, head, cwd=host, pathspec=spec)
    uncommitted = _status_product_files(cwd=host, pathspec=spec) if head == host_head else []
    out.update({"base": base, "base_kind": base_kind, "head": head, "head_kind": head_kind,
                "range": f"{base[:7]}..{head[:7]}", "commits": int(count), "files": files, "uncommitted": uncommitted})
    tally = {k: sum(1 for f in files if f["status"] == k) for k in ("A", "M", "D", "R")}
    lines = header + [f"mode={out['mode']}"]
    if created:
        lines.append(f"creation_commit={created}  (the host HEAD at new-phase, or the host worktree's base after parallel-start)")
    elif "created" in anchors and not args.base:
        lines.append("creation_commit=none (the host had no commit at new-phase)")
    else:
        lines.append("creation_commit=none (measured from --base)")
    lines.append(f"base={base} ({base_kind})")
    lines.append(f"head={head} ({head_kind})")
    lines.append(f"range={out['range']} commits={count}")
    lines.append(f"product_files={len(files)} (added {tally['A']}, modified {tally['M']}, deleted {tally['D']}, renamed {tally['R']}; read from the host repo, {nested_dir}/ excluded)")
    for f in files:
        lines.append(f"  {f['status']} {f['from']} -> {f['path']}" if f.get("from") else f"  {f['status']} {f['path']}")
    if uncommitted:
        lines.append(f"uncommitted_product_files={len(uncommitted)} (host working tree, not in the range above)")
        lines += [f"  {f['status']} {f['path']}" for f in uncommitted]
    lines += [f"note: {n}" for n in out["notes"]] + [SCOPE_HINT]
    emit(lines)


def _one_line(text) -> str:
    """A stored free-text value collapsed onto one printable line."""
    return " ".join(str(text).split())


def nested_next_lines() -> list:
    """`next`'s nested-install lines: the host, and the host conventions' state (commits, branches, PRs) -- loud
    while it is unconfirmed, because the first product commit must wait for the operator. Empty
    at root, so an at-root `next` prints exactly what it always printed."""
    if NESTED is None:
        return []
    conv = NESTED.get("commit_convention") if isinstance(NESTED.get("commit_convention"), dict) else {}
    lines = [f"nested_host={HOST_ROOT}"]
    if conv.get("confirmed") is True:
        lines.append(f"host_commit_convention=confirmed (coauthor_trailers={conv.get('coauthor_trailers')}) "
                     f"-- follow it for host commits, branches and pull requests; read it with: {WORKFLOW_CMD} nested-convention")
    else:
        inferred = _one_line(conv.get("inferred")) if conv.get("inferred") else "nothing"
        lines.append(f"host_commit_convention=UNCONFIRMED (inferred: {inferred}) -- confirm the host's conventions (commits, branches and pull requests) with the operator before the first product commit, "
                     f"then: {WORKFLOW_CMD} nested-convention --confirm --text \"<conventions>\" --trailers allowed|forbidden")
    return lines


def cmd_nested_convention(args: argparse.Namespace) -> None:
    """Show (bare) or record (--confirm) a nested install's host conventions for commits, branches and pull requests.

    The installer cannot ask (it runs non-interactively), so it records what it inferred from the
    host's git log and CONTRIBUTING with `confirmed: false`; the orchestrator asks the operator
    before the first product commit and records the answer here -- the convention text and whether
    Claude `Co-Authored-By` trailers are allowed in the host repo. Writes only `.agentic-nested.json`."""
    if NESTED is None:
        raise SystemExit(f"nested-convention: refused -- this is not a nested personal install (no {NESTED_MARKER} beside scripts/); "
                         "commits here follow the workspace's own Commit Convention")
    if (args.text is not None or args.trailers is not None) and not args.confirm:
        raise SystemExit(f"--text and --trailers belong to --confirm: {WORKFLOW_CMD} nested-convention --confirm --text \"...\" --trailers allowed|forbidden")
    path = ROOT / NESTED_MARKER
    if args.confirm:
        if not (args.text or "").strip():
            raise SystemExit("nested-convention --confirm needs --text \"<the host's conventions for commits, branches and pull requests, as the operator confirmed them>\"")
        if args.trailers is None:
            raise SystemExit("nested-convention --confirm needs --trailers allowed|forbidden (may Claude Co-Authored-By trailers appear in host commits?)")
        data = read_json(path)
        previous = dict(data["commit_convention"])
        data["commit_convention"] = dict(previous, text=args.text, confirmed=True, coauthor_trailers=args.trailers)
        problems = nested_marker_problems(data)
        if problems:  # cannot happen from a valid marker, but never write a marker validate would reject
            raise SystemExit(f"nested-convention: refused -- the result would be malformed: {'; '.join(problems)}")
        write_json(path, data)
        append_event("nested_convention_confirmed", coauthor_trailers=args.trailers, previously_confirmed=previous.get("confirmed") is True)
        print(f"nested-convention: confirmed{' (replacing the earlier confirmation)' if previous.get('confirmed') is True else ''} -- written to {shown(path)}")
        conv = data["commit_convention"]
    else:
        conv = NESTED["commit_convention"]
    print(f"nested_host={HOST_ROOT}")
    print(f"commit_convention={'confirmed' if conv.get('confirmed') is True else 'UNCONFIRMED'}")
    print(f"coauthor_trailers={conv.get('coauthor_trailers')}")
    print("inferred:")
    print(conv.get("inferred") or "(nothing inferred)")
    print("text:")
    print(conv.get("text") or "(none -- not confirmed yet)")
    if conv.get("confirmed") is not True:
        print(f"confirm the host's conventions (commits, branches and pull requests) with the operator before the first product commit, then: {WORKFLOW_CMD} nested-convention --confirm --text \"<conventions>\" --trailers allowed|forbidden")


def cmd_next(args: argparse.Namespace) -> None:
    rebuild_index_and_state()
    state = read_json(WORKS / "state.json")
    # Nested install: name the host, and hold the first product commit until the operator has
    # confirmed the host's commit convention. Printed before every return below; silent at root.
    for line in nested_next_lines():
        print(line)
    # Stream context. Both lines are silent on the default stream with no parallel
    # phases, so an untouched workspace sees exactly the output it saw before.
    stream = state.get("stream")
    if stream:
        print(f"stream={stream} (parallel phase checkout; the pointer below is scoped to this phase)")
    index = read_json(WORKS / "index.json")
    elsewhere = [
        f"{p['id']}:{p['execution'].get('branch')}"
        for p in index.get("active_phases", [])
        if phase_in_flight(p) and p["execution"].get("branch") != stream
    ]
    if elsewhere:
        print(f"parallel_phases_elsewhere={', '.join(elsewhere)} (not in this stream; each runs from its own branch)")
    # Deferred doc consolidation, printed before every return below so no path hides it. Purely
    # advisory: it names the debt and the command, selects nothing, and is silent when nothing owes.
    debt = consolidation_debt_line(index.get("active_phases", []))
    if debt:
        print(debt)
    waiting = state.get("waiting_on_operator")
    if waiting:
        kind = "slice" if "." in waiting else "phase"
        clear = f"set-slice-status {waiting} in_progress" if kind == "slice" else f"set-phase-status {waiting} in_progress"
        # An open acceptance gate is the same `pending` halt with a concrete script attached:
        # print the walkthrough, and clear through accept-gate so cleared_at gets stamped.
        gate = None
        if kind == "phase" and (ACTIVE / waiting / "phase.json").exists():
            pdata = read_json(ACTIVE / waiting / "phase.json")
            if acceptance_gate_is_open(pdata):
                gate = phase_acceptance(pdata)
                clear = f"accept-gate {waiting} --clear"
        print(f"current_phase={state.get('current_phase')}")
        print(f"waiting_on_operator={waiting}")
        print(f"WAITING ON OPERATOR: {kind} {waiting} is pending [~] -- operator co-work needed (validation or an operator-run action).")
        print("Do not start, finish, or advance past it. Report what you need, then wait for the operator.")
        if gate:
            print(f"acceptance_gate=open (requested_at={gate.get('requested_at')}) -- the operator must walk the running product before this phase's review can pass.")
            print("WALKTHROUGH:")
            print(gate.get("walkthrough") or "(none recorded)")
        print(f"After the operator approves, clear it: {WORKFLOW_CMD} {clear}")
        if gate:
            print("Add --note \"...\" to record what the operator reported.")
        return
    current_slice = state.get("current_slice")
    if not current_slice:
        if state.get("current_phase"):
            print(f"current_phase={state['current_phase']}")
            print("no open slice in the current phase; review/archive it or create a new phase")
        else:
            print("no active slice; create a phase or promote deferred work")
        return
    sdir = require_slice(current_slice)
    print(f"current_phase={current_slice.split('.', 1)[0]}")
    print(f"current_slice={current_slice}")
    print(f"slice_path={shown(sdir)}")
    print(f"next_slice={state.get('next_slice') or 'none'}")
    hint = parallel_start_hint(state, index)
    if hint:
        print(hint)


# Boundary-gated compaction (P34, v55). Two hook commands: `compact-gate` (the PreCompact hook, matcher
# `auto`) vetoes an auto-compaction while a slice is open or the tree is dirty, so compaction lands at a
# slice boundary; `compact-resume` (the SessionStart hook, matcher `compact`) re-injects the pointer and a
# resume line after one. The gate FAILS OPEN: every path exits 0, a block is only ever the stdout JSON
# `{"decision": "block", ...}` (exit 2 would also block, so it is never used), anything unexpected allows,
# and two fail-safes bound the veto -- the fill ceiling (the transcript's last usage) and the cap on
# consecutive blocks per session. It writes nothing in the tree (a counter there would itself be dirt).
COMPACT_CEILING_ENV = "AGENTIC_COMPACT_CEILING"
COMPACT_CAP_ENV = "AGENTIC_COMPACT_BLOCK_CAP"
COMPACT_CEILING_1M = 850_000   # 85% of a 1M window
COMPACT_CEILING_200K = 170_000  # 85% of a 200k window
COMPACT_BLOCK_CAP = 8
# The 1M-window family: every Claude 5 model id as the transcript records it (`claude-opus-5-5`,
# `claude-fable-5-1`, `claude-opus-5`, `claude-haiku-5-5`, `claude-opus-5-5[1m]`); anything else
# (a Claude 4 id, `<synthetic>`) gets the 200k ceiling. A wrong guess only moves the ceiling: the cap
# still releases the veto.
COMPACT_1M_MODEL_RE = re.compile(r"^claude-[a-z]+-5(?:[-\[]|$)")
# Generated files a read-only command (next, rebuild) may rewrite with no real change; they never make
# the tree dirty for the gate. `docs/index.json` because `rebuild`/`rebuild-docs` restamp its
# `last_rebuilt_at` on every run; a real doc change also writes docs/versions/ and docs/current/.
COMPACT_DIRTY_EXCLUDE = ("works/state.json", "works/index.json", "works/backlog.md", "works/deferred.md", "docs/index.json")
COMPACT_TRANSCRIPT_TAIL = 4 * 1024 * 1024
COMPACT_RESUME_LINE = (
    "Context was compacted. Re-read the running skill's SKILL.md from disk (.claude/skills/<name>/SKILL.md -- only "
    "its first 5,000 tokens were re-injected), the active slice folder (plan.md, result.md) and phase.md's `## Now`; "
    "executors still running are listed by the harness."
)
# The hooks follow the session (P35): `$CLAUDE_PROJECT_DIR` stays at the main checkout after EnterWorktree,
# but the hook's stdin `cwd` follows the session into the worktree. So each hook first walks up from that
# `cwd` to the engine that owns it -- `d/workflow/scripts/workflow.py` (nested) or `d/scripts/workflow.py`
# (at root), with `works/` beside it -- and, when that is another copy of the engine, re-runs it with the
# same stdin and relays its output. The env var is the recursion guard; every failure falls back to today.
HOOK_REDIRECT_ENV = "AGENTIC_HOOK_REDIRECTED"
HOOK_REDIRECT_TIMEOUT = 12  # the hooks' own timeout is 15 s


def _hook_owning_engine(cwd: str):
    """(engine, run_dir) for the first ancestor of `cwd` (itself included) that holds a workspace engine with
    `works/` beside it -- nested (`workflow/`) checked before at root at each level -- or None."""
    start = Path(cwd).resolve()
    if not start.is_dir():
        return None
    for d in (start, *start.parents):
        for base in (d / "workflow", d):
            engine = base / "scripts" / "workflow.py"
            if engine.is_file() and (base / "works").is_dir():
                return engine, d
    return None


def _hook_stdin_or_redirect(subcommand: str):
    """Read the hook's stdin once. Return its text for this engine to handle, or None when the engine that
    owns the hook's `cwd` is another copy and already answered (its stdout/stderr relayed unchanged). Never
    raises: a missing or bad `cwd`, no engine, this engine, the guard set, a timeout, an error or a
    non-zero exit all return the text, and the caller carries on as before."""
    try:
        raw = sys.stdin.read()
    except Exception:  # noqa: BLE001 - the hooks never fail
        return ""
    try:
        if os.environ.get(HOOK_REDIRECT_ENV):
            return raw
        hook = json.loads(raw or "null")
        cwd = hook.get("cwd") if isinstance(hook, dict) else None
        if not isinstance(cwd, str) or not cwd.strip():
            return raw
        found = _hook_owning_engine(cwd)
        if found is None or found[0].resolve() == Path(__file__).resolve():
            return raw
        engine, run_dir = found
        proc = subprocess.run([sys.executable, str(engine), subcommand], input=raw, capture_output=True, text=True,
                              cwd=str(run_dir), env={**os.environ, HOOK_REDIRECT_ENV: "1"}, timeout=HOOK_REDIRECT_TIMEOUT)
        if proc.returncode != 0:
            return raw
        sys.stdout.write(proc.stdout)
        sys.stderr.write(proc.stderr)
        sys.stdout.flush()
        sys.stderr.flush()
        return None
    except Exception:  # noqa: BLE001 - fail open: this engine answers instead
        return raw


def _compact_env_int(name: str):
    raw = os.environ.get(name, "").strip()
    try:
        value = int(raw)
    except ValueError:
        return None
    return value if value > 0 else None


def _compact_last_usage(transcript_path):
    """(fill, model) from the last main-thread assistant line in the transcript that carries a non-zero
    `message.usage`, or (None, None) when the file or the usage cannot be read. Reads the file's tail
    first (transcripts run to tens of MB) and the whole file only when the tail holds no such line."""
    if not transcript_path or not isinstance(transcript_path, str):
        return None, None
    path = Path(transcript_path)
    try:
        size = path.stat().st_size
        starts = [max(0, size - COMPACT_TRANSCRIPT_TAIL)] + ([0] if size > COMPACT_TRANSCRIPT_TAIL else [])
        for start in starts:
            with path.open("rb") as f:
                f.seek(start)
                lines = f.read().splitlines()
            if start:
                lines = lines[1:]  # the first line of a tail read is cut mid-way
            for raw in reversed(lines):
                try:
                    entry = json.loads(raw)
                except ValueError:
                    continue
                if not isinstance(entry, dict) or entry.get("type") != "assistant" or entry.get("isSidechain") is True:
                    continue
                message = entry.get("message")
                usage = message.get("usage") if isinstance(message, dict) else None
                if not isinstance(usage, dict):
                    continue
                fill = 0
                for key in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"):
                    value = usage.get(key)
                    fill += value if isinstance(value, int) else 0
                if fill <= 0:  # a synthetic or errored turn: no reading, keep looking
                    continue
                model = message.get("model")
                return fill, (model if isinstance(model, str) else "")
    except OSError:
        return None, None
    return None, None


def _compact_counter_path(hook: dict) -> Path:
    """The per-session block counter: never inside the tree (an untracked file there is dirt)."""
    sid = re.sub(r"[^A-Za-z0-9_.-]", "_", str(hook.get("session_id") or "")) or "nosession"
    base = hook.get("scratchpad_dir")
    base = Path(base) if isinstance(base, str) and base.strip() and Path(base).is_dir() else Path(tempfile.gettempdir())
    return base / f"agentic-compact-gate-{sid}.json"


def _compact_read_blocks(path: Path) -> int:
    try:
        value = json.loads(path.read_text(encoding="utf-8")).get("blocks")
    except (OSError, ValueError, AttributeError):
        return 0
    return value if isinstance(value, int) and value > 0 else 0


def _compact_dirty_count():
    """How many files are uncommitted where the workspace lives, or None when there is no git to ask.
    At root: this repo, minus the generated dashboards. Nested: the workspace repo the same way, plus the
    host's product (everything but the nested folder)."""
    checks = []
    if _git_available(cwd=ROOT):
        checks.append((ROOT, [".", *(f":(exclude){p}" for p in COMPACT_DIRTY_EXCLUDE)]))
    if HOST_ROOT is not None and _git_available(cwd=HOST_ROOT):
        checks.append((HOST_ROOT, _host_pathspec()))
    if not checks:
        return None
    paths = set()
    for cwd, spec in checks:
        proc = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all", "--", *spec],
                              cwd=str(cwd), capture_output=True, text=True, timeout=10)
        if proc.returncode != 0:
            continue
        top = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=str(cwd), capture_output=True, text=True, timeout=10).stdout.strip()
        paths.update(f"{top}/{line[3:]}" for line in proc.stdout.splitlines() if len(line) > 3)
    return len(paths)


def cmd_compact_gate(args: argparse.Namespace) -> None:
    """PreCompact hook: block an auto-compaction mid-slice, allow it at a clean slice boundary.
    Decision order: (a) not `auto` -> allow; (a') fired inside a subagent (`agent_id`) -> allow; (b) fill >=
    ceiling -> allow; (c) consecutive blocks >= cap -> allow; (d) current slice in_progress/in_review -> block,
    dirty tree -> block, else allow. A block prints the JSON and counts (a block it cannot count allows
    instead); an allow prints nothing and resets the count. Fails open: exit 0 always."""
    trace = {"decision": "allow", "rule": "error", "slice": "-", "status": "-", "dirty": "-", "fill": "-", "ceiling": "-"}
    cap, blocks, counter, reason, error = COMPACT_BLOCK_CAP, 0, None, None, None
    raw = _hook_stdin_or_redirect("compact-gate")
    if raw is None:  # the engine that owns the session's cwd answered
        return
    try:
        try:
            hook = json.loads(raw or "null")
        except ValueError:
            hook = None
        if not isinstance(hook, dict):
            raise ValueError("stdin is not a hook JSON object")
        cap = _compact_env_int(COMPACT_CAP_ENV) or COMPACT_BLOCK_CAP
        counter = _compact_counter_path(hook)
        blocks = _compact_read_blocks(counter)
        if hook.get("trigger") != "auto":  # (a) a manual /compact is never blocked
            trace["rule"] = "manual"
        elif isinstance(hook.get("agent_id"), str) and hook["agent_id"].strip():
            # (a') a subagent's own compaction (an executor, an Explore lookup): its slice is in_progress for
            # its whole life, so the veto would only defer it to the cap -- the boundary is the main thread's.
            # It leaves the main thread's block count alone (the subagent shares the session id).
            trace["rule"], counter = "subagent", None
        else:
            fill, model = _compact_last_usage(hook.get("transcript_path"))  # (b)
            ceiling = _compact_env_int(COMPACT_CEILING_ENV) or (COMPACT_CEILING_1M if model and COMPACT_1M_MODEL_RE.match(model) else COMPACT_CEILING_200K)
            trace["fill"], trace["ceiling"] = ("-" if fill is None else fill), ceiling
            if fill is not None and fill >= ceiling:
                trace["rule"] = "ceiling"
            elif blocks >= cap:  # (c)
                trace["rule"] = "cap"
            else:  # (d) the pointer `next` prints, read without next's rewrite of the dashboards
                phases = all_active_phases()
                _phase, current, _next = resolve_current(stream_phases(phases, current_stream(phases)))
                status = None
                if current:
                    status = next((s.get("status") for p in phases for s in p["slices"] if s.get("id") == current), None)
                    trace["slice"], trace["status"] = current, status or "-"
                release = (f"block {blocks + 1}/{cap}; compaction is allowed at a clean slice boundary, "
                           f"above {ceiling} tokens, or after {cap} blocks in a row")
                if status in ("in_progress", "in_review"):
                    trace["rule"], trace["decision"] = "slice_in_progress", "block"
                    reason = f"slice {current} {status} -- compaction waits for the slice boundary ({release})"
                else:
                    dirty = _compact_dirty_count()
                    trace["dirty"] = "-" if dirty is None else dirty
                    if dirty:
                        trace["rule"], trace["decision"] = "dirty", "block"
                        reason = (f"dirty: {dirty} file{'s' if dirty != 1 else ''} uncommitted (your own uncommitted work counts too) "
                                  f"-- compaction waits for a committed boundary ({release})")
                    else:
                        trace["rule"] = "boundary"
    except Exception as exc:  # noqa: BLE001 - the gate fails open, always
        trace.update(decision="allow", rule="error")
        reason, error = None, f"{type(exc).__name__}: {exc}"
    try:
        if trace["decision"] == "block":
            try:
                counter.write_text(json.dumps({"blocks": blocks + 1, "updated_at": now_iso()}) + "\n", encoding="utf-8")
                blocks += 1
            except Exception as exc:  # noqa: BLE001 - a block the cap cannot count could repeat forever: allow
                trace.update(decision="allow", rule="error")
                error = f"block counter unwritable ({type(exc).__name__}: {exc})"
        if trace["decision"] == "block":
            print(json.dumps({"decision": "block", "reason": reason}))
        elif counter is not None:  # every allow resets the count, bar a subagent's
            blocks = 0
            try:
                counter.unlink()
            except Exception:  # noqa: BLE001 - nothing to reset
                pass
        line = "compact-gate: " + " ".join(f"{k}={v}" for k, v in trace.items()) + f" blocks={blocks}/{cap}"
        if error:
            line += f" error={_one_line(error)}"
        print(line, file=sys.stderr)
    except Exception:  # noqa: BLE001 - never fail the request
        pass


def cmd_compact_resume(args: argparse.Namespace) -> None:
    """SessionStart hook (source `compact`): print the pointer and the resume line as facts. Always exit 0."""
    if _hook_stdin_or_redirect("compact-resume") is None:  # the engine that owns the session's cwd answered
        return
    print("compaction=done source=compact")
    try:
        cmd_next(args)
    except BaseException as exc:  # noqa: BLE001 - SystemExit included: the hook must never fail
        print(f"pointer unavailable: {_one_line(str(exc)) or type(exc).__name__}")
    print(COMPACT_RESUME_LINE)
def cmd_deferred(args: argparse.Namespace) -> None:
    rebuild_index_and_state()
    groups = deferred_jobs()
    print(f"open={len(groups.get('open', []))}")
    print(f"promoted={len(groups.get('promoted', []))}")
    print(f"dropped={len(groups.get('dropped', []))}")
    print(f"dashboard={shown(WORKS / 'deferred.md')}")


def next_deferred_id() -> str:
    max_n = 0
    for base in (DEFERRED_OPEN, DEFERRED_PROMOTED, DEFERRED_DROPPED):
        if not base.exists():
            continue
        for p in base.iterdir():
            m = re.fullmatch(r"D(\d+)", p.name)
            if m:
                max_n = max(max_n, int(m.group(1)))
    return f"D{max_n + 1}"


def defer_job(args: argparse.Namespace) -> None:
    did = args.id or next_deferred_id()
    ddir = DEFERRED_OPEN / did
    if ddir.exists():
        raise SystemExit(f"deferred job already exists: {did}")
    created = now_iso()
    data = {"id": did, "title": args.title, "status": "deferred", "source": args.source, "reason": args.reason, "trigger": args.trigger, "created_at": created, "promoted_to": None, "dropped_reason": None}
    write_json(ddir / "deferred.json", data)
    text = load_template("deferred_brief.md").replace("__DEFERRED_ID__", did).replace("__TITLE__", args.title)
    text = text.replace("## Why Deferred\n", f"## Why Deferred\n\n{args.reason}\n")
    text = text.replace("## Trigger to Promote\n", f"## Trigger to Promote\n\n{args.trigger}\n")
    write_text(ddir / "brief.md", text)
    append_event("deferred_created", deferred=did, source=args.source)
    rebuild_index_and_state()
    print(f"created deferred job {did}: {shown(ddir)}")


def promote_deferred(args: argparse.Namespace) -> None:
    did = args.deferred_id
    ddir = DEFERRED_OPEN / did
    if not (ddir / "deferred.json").exists():
        raise SystemExit(f"open deferred job not found: {did}")
    data = read_json(ddir / "deferred.json")
    require_slice_kind(args.kind)  # before --create-phase, so a bad kind leaves no half-created phase
    if not (ACTIVE / args.phase / "phase.json").exists():
        if not args.create_phase:
            raise SystemExit(f"phase does not exist: {args.phase}. Use --create-phase to create it.")
        ns = argparse.Namespace(phase=args.phase, name=args.phase_name or data["title"], objective=args.phase_objective or data["title"], order=None)
        new_phase(ns)
    pdir = require_phase(args.phase)
    order = _auto_order(pdir, args.order)
    sdir = create_slice(args.phase, args.slice, args.name or data["title"], args.kind, order, args.risk, source={"type": "deferred", "id": did, "path": str(ddir.relative_to(ROOT))}, depends_on=args.depends_on or [])
    plan_path = sdir / "plan.md"
    # plan.md has no template, so it may not exist yet; only prepend a separator when it does.
    sep = "\n---\n\n" if plan_path.exists() and plan_path.read_text(encoding="utf-8").strip() else ""
    with plan_path.open("a", encoding="utf-8") as f:
        f.write(f"{sep}## Promoted Deferred Context\n\n")
        f.write((ddir / "brief.md").read_text(encoding="utf-8"))
    data["status"] = "promoted"
    data["promoted_to"] = {"phase_id": args.phase, "slice_id": args.slice, "path": str(sdir.relative_to(ROOT))}
    write_json(ddir / "deferred.json", data)
    target = DEFERRED_PROMOTED / did
    if target.exists():
        raise SystemExit(f"promoted destination already exists: {shown(target)}")
    shutil.move(str(ddir), str(target))
    append_event("deferred_promoted", deferred=did, phase=args.phase, slice=args.slice)
    rebuild_index_and_state()
    print(f"promoted {did} -> {args.slice}: {shown(sdir)}")


def drop_deferred(args: argparse.Namespace) -> None:
    did = args.deferred_id
    ddir = DEFERRED_OPEN / did
    if not (ddir / "deferred.json").exists():
        raise SystemExit(f"open deferred job not found: {did}")
    data = read_json(ddir / "deferred.json")
    data["status"] = "dropped"
    data["dropped_reason"] = args.reason
    write_json(ddir / "deferred.json", data)
    target = DEFERRED_DROPPED / did
    if target.exists():
        raise SystemExit(f"dropped destination already exists: {shown(target)}")
    shutil.move(str(ddir), str(target))
    append_event("deferred_dropped", deferred=did, reason=args.reason)
    rebuild_index_and_state()
    print(f"dropped {did}: {shown(target)}")


def _phase_blocker_kinds(pdir: Path) -> list:
    """Reasons a phase is not cleanly archivable, typed: `[(kind, text)]`, kind one of "slices",
    "review" or "consolidation". Empty list means ready. `_phase_blockers` is this list's text, so
    every refusal prints exactly what it always did; the kind lets `rotate-backlog` ask "is the
    doc debt the ONLY thing holding this phase?" without matching strings."""
    phase = read_json(pdir / "phase.json")
    slices = [read_json(s / "slice.json") for s in slice_dirs(pdir)]
    reasons = []
    not_done = [s["id"] for s in slices if s.get("status") != "done"]
    if not_done:
        reasons.append(("slices", f"unfinished slices: {', '.join(not_done)}"))
    review_status = phase.get("review", {}).get("status")
    if review_status != "pass":
        reasons.append(("review", f"review is {review_status!r}, not pass"))
    # The phase still owes its deferred doc consolidation. Archiving would move its
    # `## Doc impact` list -- the sole input to that consolidation -- out of active/, so it
    # blocks (parallel teardown only warns, because teardown is reversible).
    if phase_consolidation(phase) == "pending":
        cmd = consolidation_command(phase)
        reasons.append(("consolidation", f"docs not consolidated -- run a docs phase over its '## Doc impact' notes, then: {WORKFLOW_CMD} {cmd} {phase['id']}"))
    return reasons


def _phase_blockers(pdir: Path) -> list:
    """Reasons a phase is not cleanly archivable; empty list means ready."""
    return [text for _, text in _phase_blocker_kinds(pdir)]


def _parallel_branch_merged(execution: dict, git_ok: bool = None) -> bool:
    """True when a parallel phase's branch is merged into HEAD. No branch, a deleted branch (merged
    and torn down) and a workspace without git all count as merged; otherwise the branch must be an
    ancestor of HEAD. The one test `parallel-merge-finish` and `rotate-backlog` share."""
    git_ok = _git_available() if git_ok is None else git_ok
    branch = execution.get("branch")
    if git_ok and branch and _branch_exists(branch):
        return _git(["merge-base", "--is-ancestor", branch, "HEAD"], check=False).returncode == 0
    return True


def _debt_only(pdir: Path) -> bool:
    """True when doc consolidation is the ONLY thing holding this phase from archiving: every slice
    done, review `pass`, `consolidation: pending`. A parallel phase whose branch is not yet merged is
    never debt-only -- its docs cannot be consolidated until the merge lands."""
    if [kind for kind, _ in _phase_blocker_kinds(pdir)] != ["consolidation"]:
        return False
    execution = phase_execution(read_json(pdir / "phase.json"))
    return execution is None or _parallel_branch_merged(execution)


def _archive_one(pdir: Path, forced: bool) -> Path:
    """Move a single phase folder to archived/, writing its manifest. No rebuild."""
    phase = read_json(pdir / "phase.json")
    phase_id = phase["id"]
    slices = [read_json(s / "slice.json") for s in slice_dirs(pdir)]
    review_status = phase.get("review", {}).get("status")
    base_name = f"{timestamp()}_{phase_id}_{slugify(phase.get('name', phase_id))}"
    archive_name = base_name
    suffix = 1
    while (ARCHIVED / archive_name).exists():
        suffix += 1
        archive_name = f"{base_name}_{suffix}"
    dest = ARCHIVED / archive_name
    manifest = {
        "phase_id": phase_id, "archived_at": now_iso(),
        "archive_reason": "forced" if forced else "phase_review_passed",
        "review_verdict": review_status,
        "source_path": str(pdir.relative_to(ROOT)), "archive_path": str(dest.relative_to(ROOT)),
        "slices": [s["id"] for s in slices],
    }
    write_json(pdir / "archive_manifest.json", manifest)
    shutil.move(str(pdir), str(dest))
    append_event("phase_archived", phase=phase_id, archive_path=str(dest.relative_to(ROOT)))
    return dest


def archive_phase(args: argparse.Namespace) -> None:
    # First-class single-phase archive: archive one review-passed phase on request.
    # Useful when only some phases are done. For the partial sweep of every done
    # phase use rotate-backlog; for the end-of-batch sweep of everything use
    # archive-all. --force is for exceptional cleanup of an unfinished phase only.
    pdir = require_phase(args.phase)
    if not args.force:
        reasons = _phase_blockers(pdir)
        if reasons:
            raise SystemExit(f"phase {args.phase} is not archivable ({'; '.join(reasons)}). Finish/review it, or use --force for exceptional cleanup.")
    dest = _archive_one(pdir, forced=args.force)
    rebuild_index_and_state()
    print(f"archived phase {args.phase}: {shown(dest)}")


def archive_all(args: argparse.Namespace) -> None:
    # Batch-archive every active phase at once. Gated so archiving only happens
    # once the last review slice across all active phases is done.
    pdirs = phase_dirs()
    if not pdirs:
        print("no active phases to archive")
        return
    if not args.force:
        blockers = []
        for pdir in pdirs:
            reasons = _phase_blockers(pdir)
            if reasons:
                blockers.append(f"{read_json(pdir / 'phase.json')['id']}: {'; '.join(reasons)}")
        if blockers:
            print("not archiving: every active phase must be done (the last review slice complete) before a batch archive.")
            for b in blockers:
                print(f"- {b}")
            raise SystemExit("Finish the open phases first, or use --force for exceptional cleanup.")
    archived = []
    for pdir in pdirs:
        phase_id = read_json(pdir / "phase.json")["id"]
        dest = _archive_one(pdir, forced=args.force)
        archived.append((phase_id, dest))
    rebuild_index_and_state()
    print(f"archived {len(archived)} phase(s):")
    for phase_id, dest in archived:
        print(f"- {phase_id}: {shown(dest)}")


def _phase_range_label(ids: list) -> str:
    """`P26`, the en-dash range `P26–P29` when the numbers run consecutively, else `P26, P28, P29`."""
    if len(ids) == 1:
        return ids[0]
    numbers = [int(i[1:]) for i in ids]
    if all(b - a == 1 for a, b in zip(numbers, numbers[1:])):
        return f"{ids[0]}\u2013{ids[-1]}"
    return ", ".join(ids)


def _shell_arg(text: str) -> str:
    """One command argument, copy-pasteable. Double quotes keep the generated name and objective
    readable (the objective carries `'## Doc impact'`); `shlex.quote` takes over for any text a
    double-quoted shell word would expand or break on."""
    if re.search(r'["$`\\!]', text):
        return shlex.quote(text)
    return f'"{text}"'


# v54 (P33): `rotate-backlog` is the one resumable step of the one-shot /rotate-backlog chain. These
# are the boundary statuses its mid-flight check reads: a default-stream slice outside the first set,
# or a phase in the second, is running or waiting on someone, and the docs phase never interleaves.
ROTATE_BOUNDARY_SLICE_STATUSES = ("todo", "ready", "done")
ROTATE_MIDFLIGHT_PHASE_STATUSES = ("pending", "blocked", "in_review")


def _live_docs_phases(phases: list) -> list:
    """The docs phases `rotate-backlog` resumes, in phase order: every not-`done` DEFAULT-stream phase
    whose `consolidates` is non-empty. Keyed on the marker itself, not through the debt it covers, so
    a docs phase that has already paid every phase it names but has not passed its own review yet
    still resumes. A docs phase stamped onto a parallel stream is never live here."""
    return [p for p in stream_phases(phases, None) if p.get("status") != "done" and phase_consolidates(p)]


def _midflight(phases: list, live: list) -> list:
    """`<id>:<status>` for everything on the default stream that is not at a boundary -- a phase that
    is pending, blocked or in_review, then each of its slices whose status is not todo, ready or
    done -- in phase order. The live docs phases and their slices are left out (resuming them IS the
    run, and their own stops end it); parallel streams are never counted."""
    skip = {p["id"] for p in live}
    found = []
    for phase in stream_phases(phases, None):
        if phase["id"] in skip:
            continue
        if phase.get("status") in ROTATE_MIDFLIGHT_PHASE_STATUSES:
            found.append(f"{phase['id']}:{phase.get('status')}")
        found.extend(f"{s['id']}:{s.get('status')}" for s in phase["slices"] if s.get("status") not in ROTATE_BOUNDARY_SLICE_STATUSES)
    return found


def _open_orders(phases: list, exclude: str = None) -> list:
    """The orders of the not-`done` default-stream phases (but `exclude`); a missing order counts as
    999999, where `phase_dirs` sorts it."""
    return [p.get("order", 999999) for p in stream_phases(phases, None) if p.get("status") != "done" and p["id"] != exclude]


def _queue_jump_order(phases: list, exclude: str = None):
    """The order that sorts a docs phase ahead of every other not-`done` default-stream phase:
    `min(their orders) - 1`, `_clean_order`-normalised (0 and negative orders are valid and
    round-trip; the rounding only trims float noise such as 1.3 - 1), or None when there is no such
    phase. `next` then selects the docs phase first -- the queue jump is an order, not a new state."""
    orders = _open_orders(phases, exclude)
    return _clean_order(round(min(orders) - 1, 6)) if orders else None


def _reassert_queue_jump(docs_phase: dict, phases: list):
    """Re-assert the queue jump on a live docs phase that does not already sort strictly first among
    the not-`done` default-stream phases (one created before the jump existed carries the default
    `max + 1`, behind planned work). One `order` write in its phase.json, logged as
    `phase_reordered`, then a rebuild. Returns `(old, new)` when it wrote, None when it did not."""
    others = _open_orders(phases, exclude=docs_phase["id"])
    old = docs_phase.get("order")
    if not others or docs_phase.get("order", 999999) < min(others):
        return None
    new = _queue_jump_order(phases, exclude=docs_phase["id"])
    pjson = ROOT / docs_phase["path"] / "phase.json"
    data = read_json(pjson)
    data["order"] = new
    write_json(pjson, data)
    append_event("phase_reordered", phase=docs_phase["id"], old_order=old, new_order=new, reason="rotate-backlog queue jump")
    rebuild_index_and_state()
    return old, new


def _docs_debt_split(phases: list) -> tuple:
    """`(covered_by, uncovered)` over the CURRENT active set, from the phases held back ONLY by doc
    debt (`_debt_only`): `{covering docs phase id: [the debt-only ids it pays]}` -- every not-`done`
    phase whose `consolidates` names one, whatever its stream -- and the debt-only phases no such
    docs phase covers yet, sorted by number."""
    debt_only = [p for p in phases if _debt_only(ROOT / p["path"])]
    cover = consolidation_cover(phases)
    covered_by = {}
    for p in debt_only:
        for docs_phase in cover.get(p["id"], []):
            covered_by.setdefault(docs_phase["id"], []).append(p["id"])
    uncovered = sorted((p for p in debt_only if not cover.get(p["id"])), key=lambda p: int(p["id"][1:]))
    return covered_by, uncovered


def _print_docs_phase_covered(covered_by: dict) -> None:
    for docs_phase_id, pays in covered_by.items():
        print(f"docs_phase_covered={docs_phase_id} (pays {', '.join(pays)})")


def _print_docs_phase_proposal(uncovered: list, order) -> None:
    """The one docs phase to create for the uncovered debt-only phases, printed as the block
    `/rotate-backlog` runs as is: the invocation is the operator's yes (create-phase's docs-phase
    route), so the `create:` line is the whole command, its `--order` the queue jump (omitted when no
    other phase is open), written before `--consolidates`. Prints, never writes."""
    ids = [p["id"] for p in uncovered]
    docs = sorted(d for d in stale_docs(uncovered) if d != UNASSIGNED_DOC)
    listing = ", ".join(ids)
    name = f"Consolidate the doc impact of {_phase_range_label(ids)}"
    objective = (f"consolidate the '## Doc impact' notes from {listing} into new versions of "
                 f"{', '.join(docs) if docs else 'the docs their notes name'}")
    phase_id = next_phase_id()
    order_arg = f" --order {order}" if order is not None else ""
    print(f"docs_phase_proposal={listing}")
    print(f"phase={phase_id}")
    print(f"name={name}")
    print(f"objective={objective}")
    print(f"create: {WORKFLOW_CMD} new-phase --phase {phase_id} --name {_shell_arg(name)} --objective {_shell_arg(objective)}{order_arg} --consolidates {','.join(ids)}")
    print(f"scope: {WORKFLOW_CMD} docs-debt")
    print("proposal only: nothing was created -- /rotate-backlog runs the create: line as is (the invocation is the operator's yes; create-phase's docs-phase route)")


def _rotate_sweep() -> None:
    """The archive sweep: archive every phase that is cleanly archivable right now (every slice done,
    review `pass`, no consolidation owed) and leave the rest active, then rebuild. Whole phases, never
    forced, archive-phase's manifest -- the partial sweep archive-all cannot do, since archive-all
    refuses unless EVERY active phase is done. Its output is `--archive-only`'s, verbatim."""
    pdirs = phase_dirs()
    if not pdirs:
        print("no active phases to rotate")
        return
    ready, blocked = [], []
    for pdir in pdirs:
        phase_id = read_json(pdir / "phase.json")["id"]
        (blocked if _phase_blockers(pdir) else ready).append((phase_id, pdir))
    if not ready:
        rebuild_index_and_state()
        print(f"no done phases to rotate; {len(blocked)} phase(s) still active: {', '.join(p for p, _ in blocked)}")
        return
    archived = []
    for phase_id, pdir in ready:
        dest = _archive_one(pdir, forced=False)
        archived.append((phase_id, dest))
    rebuild_index_and_state()
    print(f"rotated {len(archived)} done phase(s) to archived:")
    for phase_id, dest in archived:
        print(f"- {phase_id}: {shown(dest)}")
    if blocked:
        print(f"left {len(blocked)} phase(s) active: {', '.join(p for p, _ in blocked)}")


def rotate_backlog(args: argparse.Namespace) -> None:
    # v54 (P33): the one resumable step of the one-shot /rotate-backlog chain. The doc debt is
    # checked FIRST and nothing is archived while it stands; the skill branches on the first stdout
    # line, `rotate=<branch>`, chosen in this precedence:
    #   refused         a parallel-stream checkout: writes nothing, exits non-zero.
    #   archive         nothing owes (no uncovered debt-only phase, no live docs phase): the sweep,
    #                   then `docs_phase=none`. Archiving interleaves with nothing, so mid-flight work
    #                   does not hold it.
    #   stop_midflight  debt stands and default-stream work is off a boundary: writes nothing.
    #   resume          a live docs phase exists (it beats create: uncovered debt waits for it);
    #                   re-asserts its queue-jump order, the only write outside the sweep.
    #   create          the docs-phase proposal, its `create:` line carrying the queue-jump --order;
    #                   writes nothing -- the skill runs that line as is.
    # --archive-only is the sweep alone, output unchanged since v51 (no rotate= line, no docs line).
    if getattr(args, "archive_only", False):
        _rotate_sweep()
        return
    phases = all_active_phases()
    stream = current_stream(phases)
    if stream is not None:
        print(f"rotate=refused stream={stream}")
        raise SystemExit("rotate-backlog wrote nothing: doc consolidation and archiving run on the default stream only -- run it from the main checkout, not this phase's worktree")
    live = _live_docs_phases(phases)
    covered_by, uncovered = _docs_debt_split(phases)
    if not live and not uncovered:
        # Nothing owes here. Debt covered with no live docs phase can only be paid by a docs phase
        # stamped onto another stream -- not this stream's to pay, so it never holds the sweep.
        print("rotate=archive")
        _rotate_sweep()
        for docs_phase_id, pays in covered_by.items():
            print(f"docs_phase_elsewhere={docs_phase_id} (pays {', '.join(pays)}; on another stream, not resumed here)")
        print("docs_phase=none")
        return
    owing = ", ".join(p["id"] for p in uncovered)
    midflight = _midflight(phases, live)
    if midflight:
        print(f"rotate=stop_midflight midflight={', '.join(midflight)}")
        print(f"stopped_before=resume docs_phase={live[0]['id']}" if live else f"stopped_before=create owing={owing}")
        print("nothing was archived, created or reordered: the docs phase never interleaves with running work -- "
              "re-run rotate-backlog once every listed slice is todo, ready or done and no listed phase is pending, blocked or in_review")
        return
    if live:
        docs_phase = live[0]
        print(f"rotate=resume docs_phase={docs_phase['id']}")
        moved = _reassert_queue_jump(docs_phase, phases)
        if moved:
            print(f"docs_phase_order={docs_phase['id']} {moved[0]} -> {moved[1]}")
        _print_docs_phase_covered(covered_by)
        if uncovered:
            print(f"docs_debt_waiting={owing} (no docs phase pays it yet; rotate-backlog proposes one once {docs_phase['id']} is done)")
        return
    print("rotate=create")
    _print_docs_phase_covered(covered_by)
    _print_docs_phase_proposal(uncovered, _queue_jump_order(phases))


# ---------------------------------------------------------------------------
# The design contract (workspace v47). A product repo keeps its visual design as plain files under
# DESIGN_ROOT_REL -- a project manifest, a numbered card library, tokens, and one folder per design
# round -- and a separate, READ-ONLY web dashboard (its own repo, served from the operator's Mac)
# reads them straight from disk, finding repos through a registry that lives OUTSIDE every repo.
# The contract itself (paths, manifest fields, the @dsCard grammar, the round lifecycle, the
# registry) is written out in design-cowork/SKILL.md "The design record"; that section and these
# commands must move together. The commands are the only writers of the machine-readable parts
# (design.json, round.json, the close-time snapshots, the registry), and `design-check` enforces
# the rest. Two invariants carry the weight: the regroup rewrites ONE label on line 1 of a card
# and asserts every byte after line 1 identical, and `design-register` writes only the registry
# path (env-overridable, so tests never touch the operator's real one), atomically. Stdlib only.
# Since v48 a phase may pick the `claude-design` tool instead; its records keep the pre-v47 layout
# under DESIGN_LEGACY_DIR, which the scan never reads, and `design-migrate` moves a pre-v47 root
# there (moves only, all-or-nothing, never a delete, never git).
DESIGN_ROOT_REL = "docs/reference/design"
# The design root as printed: under the nested repo when nested (`workflow/docs/reference/design`,
# where the record stays -- private workflow files, never the host's docs/), identical at root.
DESIGN_ROOT_SHOWN = shown_rel(DESIGN_ROOT_REL)
# The `claude-design` tool's record home, in the pre-v47 layout, never read by the engine.
DESIGN_LEGACY_DIR = "claude-design"
DESIGN_SCHEMA = 1
DESIGN_REGISTRY_ENV = "AGENTIC_DESIGN_REGISTRY"
DESIGN_REGISTRY_DEFAULT = "~/.config/agentic-workspace/design-registry.json"
# The design-deck URL design-register prints when set; the engine never guesses one.
DESIGN_DECK_URL_ENV = "AGENTIC_DESIGN_DECK_URL"
DESIGN_ROUND_STATUSES = ("open", "signed", "superseded")
DESIGN_MANIFEST_KEYS = ("schema", "id", "name")
DESIGN_ROUND_KEYS = ("schema", "round", "title", "slice", "status", "opened_at", "closed_at",
                     "cards", "supersedes", "signoff_words")
DESIGN_MARKER_KEYS = ("group", "viewport", "title")
DESIGN_SLUG = r"[a-z0-9]+(?:-[a-z0-9]+)*"
DESIGN_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")
DESIGN_SLUG_RE = re.compile(rf"^{DESIGN_SLUG}$")
DESIGN_CARD_RE = re.compile(rf"^(\d{{2,}})-({DESIGN_SLUG})\.html$")
DESIGN_ROUND_RE = re.compile(rf"^(\d{{2,}})-({DESIGN_SLUG})$")
DESIGN_CARD_REL_RE = re.compile(rf"^cards/(\d{{2,}})-{DESIGN_SLUG}\.html$")
DESIGN_SLICE_RE = re.compile(r"^P\d+\.[A-Z][A-Z0-9]*$")
DESIGN_MARKER_RE = re.compile(r'^<!-- @dsCard((?: [a-z]+="[^"]*")+) -->$')
DESIGN_ATTR_RE = re.compile(r' ([a-z]+)="([^"]*)"')
DESIGN_VIEWPORT_RE = re.compile(r"^[1-9]\d*x[1-9]\d*$")
DESIGN_REVIEW_MARK = "⏳"  # the hourglass that opens a review-time group
DESIGN_ADDRESS_RE = re.compile("^⏳ (\\S+) · (.+)$")
DESIGN_REF_RE = re.compile(r"""\b(?:src|href)\s*=\s*["']([^"']*)["']|url\(\s*["']?([^"')]+?)["']?\s*\)""", re.I)
# What a card may reference besides ../tokens.css -- exactly the contract's "inline SVG or `data:`, and
# anything else an absolute `https:` URL", plus in-page `#` fragments (a same-document reference
# resolves inside the card's own bytes wherever it is opened, and inline SVG's url(#id) / <use
# href="#id"> rely on it). Nothing else: a protocol-relative `//host/x` resolves against file:// when
# the operator opens a card file directly, and `http:`, `mailto:`, `tel:`, `javascript:` or `about:`
# are not what the contract names.
DESIGN_ALLOWED_REFS = ("#", "data:", "https://")
DESIGN_REF_WHY = (("//", "protocol-relative: it resolves against file:// when a card file is opened directly"),
                  ("http://", "plain http, not https"))


def design_root() -> Path:
    return ROOT / DESIGN_ROOT_REL


def design_legacy_record(root: Path) -> list:
    """The pre-v47 (Claude Design) record's parts in a design root: rounds/<name>/ folders without a
    round.json, the root SIGNOFF.md and grounding/ -- design-migrate's own rule for a root that has a
    design.json, so the hints, design-init's refusal and the migration cannot disagree. Empty for a
    root with no design.json whose rounds/ holds a schema-1 round: design-migrate refuses that root
    until design-init restores the manifest, so the steer to design-migrate must stay out of its way."""
    rounds_dir = root / "rounds"
    entries = sorted(rounds_dir.iterdir()) if rounds_dir.is_dir() else []
    if not (root / "design.json").exists() and any((e / "round.json").exists() for e in entries):
        return []
    parts = [e for e in entries if not e.name.startswith(".") and e.is_dir() and not (e / "round.json").exists()]
    return parts + [root / name for name in ("SIGNOFF.md", "grounding") if os.path.lexists(root / name)]


def design_legacy_hint(root: Path) -> str:
    """One line steering a root that holds a pre-v47 record to design-migrate (ahead of design-init),
    or "" when it holds none."""
    if not design_legacy_record(root):
        return ""
    then = "" if (root / "design.json").exists() else ", then design-init if this repo will use the drafter"
    return f"pre-v47 record: run {WORKFLOW_CMD} design-migrate (dry run first){then}"


def design_number(text: str):
    """The integer behind a canonical NN prefix (01, 42, 100), or None for 0, 1-digit or extra zeros."""
    number = int(text)
    return number if number >= 1 and f"{number:02d}" == text else None


def design_line1(data: bytes):
    head = data.split(b"\n", 1)[0]
    if head.endswith(b"\r"):
        head = head[:-1]
    try:
        return head.decode("utf-8")
    except UnicodeDecodeError:
        return None


def design_parse_marker(line) -> tuple:
    """(attrs, None) for a valid line-1 @dsCard marker, else (None, why)."""
    match = DESIGN_MARKER_RE.match(line or "")
    if not match:
        return None, 'line 1 is not an @dsCard marker (<!-- @dsCard group="…" viewport="WxH" -->)'
    attrs: dict = {}
    for key, value in DESIGN_ATTR_RE.findall(match.group(1)):
        if key in attrs:
            return None, f"duplicate attribute {key!r}"
        attrs[key] = value
    unknown = sorted(set(attrs) - set(DESIGN_MARKER_KEYS))
    if unknown:
        return None, f"unknown attribute(s) {', '.join(unknown)} (the set is closed: group, viewport, title)"
    for key in ("group", "viewport"):
        if key not in attrs:
            return None, f"missing {key}"
    for key, value in attrs.items():
        if not value or value != value.strip():
            return None, f"{key} is empty or padded with spaces"
        if any(bad in value for bad in ("<", ">", "--")):
            return None, f"{key} contains <, > or --"
    if not DESIGN_VIEWPORT_RE.match(attrs["viewport"]):
        return None, f"viewport {attrs['viewport']!r} is not WxH in positive integers"
    return attrs, None


def design_address(group: str):
    """Split a card's group: (slice, library group) under review, (None, group) in the library,
    None when it opens with the review mark but is not a well-formed address."""
    if not group.startswith(DESIGN_REVIEW_MARK):
        return None, group
    match = DESIGN_ADDRESS_RE.match(group)
    if not match or not DESIGN_SLICE_RE.match(match.group(1)) or match.group(2) != match.group(2).strip():
        return None
    return match.group(1), match.group(2)


def design_reference_problems(data: bytes, root: Path, allow_tokens: bool) -> list:
    """A card is self-contained except for ../tokens.css; tokens.css is self-contained outright."""
    problems = set()
    for first, second in DESIGN_REF_RE.findall(data.decode("utf-8", errors="replace")):
        ref = (first or second).strip()
        if not ref or ref.lower().startswith(DESIGN_ALLOWED_REFS):
            continue
        if allow_tokens and ref == "../tokens.css":
            if not (root / "tokens.css").exists():
                problems.add("links ../tokens.css but the design root has no tokens.css")
            continue
        why = next((f" ({text})" for prefix, text in DESIGN_REF_WHY if ref.lower().startswith(prefix)), "")
        allowed = "../tokens.css, an in-page `#` fragment, `data:` or an absolute https URL" if allow_tokens \
            else "an in-page `#` fragment, `data:` or an absolute https URL"
        problems.add(f"references {ref!r}{why}: only {allowed} may be referenced (the same bytes must render from a round snapshot)")
    return sorted(problems)


def design_manifest_problems(data) -> list:
    if not isinstance(data, dict):
        return ["design.json is not a JSON object"]
    problems = []
    missing = [k for k in DESIGN_MANIFEST_KEYS if k not in data]
    extra = sorted(set(data) - set(DESIGN_MANIFEST_KEYS))
    if missing:
        problems.append(f"design.json: missing field(s) {', '.join(missing)}")
    if extra:
        problems.append(f"design.json: unknown field(s) {', '.join(extra)} (schema {DESIGN_SCHEMA} is closed)")
    if "schema" in data and (data["schema"] is True or data["schema"] != DESIGN_SCHEMA):
        problems.append(f"design.json: schema {data['schema']!r} is not {DESIGN_SCHEMA}")
    if "id" in data and not (isinstance(data["id"], str) and DESIGN_ID_RE.match(data["id"])):
        problems.append(f"design.json: id {data['id']!r} is not lowercase [a-z0-9-], starting alphanumeric, at most 63 characters")
    if "name" in data and not (isinstance(data["name"], str) and data["name"].strip()):
        problems.append("design.json: name must be a non-empty string")
    return problems


def design_round_problems(rid: str, data, rdir: Path) -> list:
    """Problems with one round folder, its round.json read as `data`."""
    if not isinstance(data, dict):
        return ["round.json is not a JSON object"]
    missing = [k for k in DESIGN_ROUND_KEYS if k not in data]
    extra = sorted(set(data) - set(DESIGN_ROUND_KEYS))
    problems = []
    if missing:
        problems.append(f"round.json: missing field(s) {', '.join(missing)}")
    if extra:
        problems.append(f"round.json: unknown field(s) {', '.join(extra)} (schema {DESIGN_SCHEMA} is closed)")
    if missing:
        return problems
    status = data["status"]
    if data["schema"] is True or data["schema"] != DESIGN_SCHEMA:
        problems.append(f"round.json: schema {data['schema']!r} is not {DESIGN_SCHEMA}")
    if data["round"] != rid:
        problems.append(f"round.json: round {data['round']!r} does not match its folder name")
    if not (isinstance(data["title"], str) and data["title"].strip()):
        problems.append("round.json: title must be a non-empty string")
    if not (isinstance(data["slice"], str) and DESIGN_SLICE_RE.match(data["slice"])):
        problems.append(f"round.json: slice {data['slice']!r} is not a slice id (P<N>.<ID>)")
    if status not in DESIGN_ROUND_STATUSES:
        problems.append(f"round.json: status {status!r} is not one of {', '.join(DESIGN_ROUND_STATUSES)}")
    if not (isinstance(data["opened_at"], str) and data["opened_at"]):
        problems.append("round.json: opened_at must be an ISO-8601 string")
    closed = status in ("signed", "superseded")
    if closed and not (isinstance(data["closed_at"], str) and data["closed_at"]):
        problems.append(f"round.json: a {status} round needs closed_at")
    if status == "open" and data["closed_at"] is not None:
        problems.append("round.json: an open round has closed_at null")
    words = data["signoff_words"]
    if status == "signed" and not (isinstance(words, str) and words.strip()):
        problems.append("round.json: a signed round records the operator's literal signoff_words")
    if status != "signed" and words is not None:
        problems.append("round.json: signoff_words is null unless the round is signed")
    cards = data["cards"]
    if not (isinstance(cards, list) and all(isinstance(c, str) and DESIGN_CARD_REL_RE.match(c) for c in cards)):
        problems.append("round.json: cards must be a list of cards/NN-slug.html paths")
        cards = []
    elif len(set(cards)) != len(cards):
        problems.append("round.json: cards lists a path twice")
    sup = data["supersedes"]
    if not (isinstance(sup, list) and all(isinstance(s, str) and DESIGN_ROUND_RE.match(s) for s in sup)):
        problems.append("round.json: supersedes must be a list of round ids (NN-slug)")
    if status == "signed" and not cards:
        problems.append("round.json: a signed round lists the cards it touched")
    if not (rdir / "handoff.md").exists():
        problems.append("handoff.md missing (every round has its brief)")
    if status == "signed" and not (rdir / "SIGNOFF.md").exists():
        problems.append("SIGNOFF.md missing (a signed round records the operator's literal words)")
    if closed:
        for rel in cards:
            snap = rdir / rel
            if not snap.is_file():
                problems.append(f"snapshot {rel} missing (a closed round keeps its cards as they were at close)")
                continue
            attrs, _ = design_parse_marker(design_line1(snap.read_bytes()))
            split = design_address(attrs["group"]) if attrs else None
            if not split or split[0] != data["slice"]:
                problems.append(f"snapshot {rel}: line 1 does not carry the round address \"{DESIGN_REVIEW_MARK} {data['slice']} · …\"")
    return problems


def design_scan(root: Path) -> dict:
    """Read the whole design root once: the manifest, the cards, the rounds, and every problem."""
    problems: list = []
    scan = {"manifest": None, "cards": [], "rounds": [], "problems": problems}
    if not root.is_dir():
        problems.append(f"no design root at {DESIGN_ROOT_SHOWN}/ (run: {WORKFLOW_CMD} design-init)")
        return scan
    mpath = root / "design.json"
    hint = design_legacy_hint(root)  # said once, on the first legacy-related problem
    if not mpath.exists():
        problems.append(f"design.json missing; {hint}" if hint else f"design.json missing (run: {WORKFLOW_CMD} design-init)")
        hint = ""
    else:
        try:
            manifest = read_json(mpath)
        except (ValueError, OSError) as exc:
            problems.append(f"design.json is not valid JSON: {exc}")
        else:
            found = design_manifest_problems(manifest)
            problems.extend(found)
            if not found:
                scan["manifest"] = manifest
    numbers: dict = {}
    cards_dir = root / "cards"
    for entry in sorted(cards_dir.iterdir()) if cards_dir.is_dir() else []:
        if entry.name.startswith("."):
            continue
        rel = f"cards/{entry.name}"
        match = DESIGN_CARD_RE.match(entry.name)
        if entry.is_dir() or not match:
            kind = "unnumbered card path" if entry.suffix.lower() in (".html", ".htm") else "not a card file"
            problems.append(f"{rel}: {kind} (cards/ holds NN-slug.html files only)")
            continue
        number = design_number(match.group(1))
        if number is None:
            problems.append(f"{rel}: non-canonical number {match.group(1)!r} (01, 02, … 99, 100: zero-padded to two digits, from 01)")
            continue
        if number in numbers:
            problems.append(f"{rel}: duplicate card number {number:02d} (also {numbers[number]})")
            continue
        numbers[number] = rel
        data = entry.read_bytes()
        card = {"number": number, "rel": rel, "path": entry, "attrs": None, "address": None}
        attrs, why = design_parse_marker(design_line1(data))
        if why:
            problems.append(f"{rel}: invalid @dsCard marker: {why}")
        else:
            split = design_address(attrs["group"])
            if split is None:
                problems.append(f"{rel}: malformed round address in group {attrs['group']!r} (expected \"{DESIGN_REVIEW_MARK} <slice> · <Group>\")")
            else:
                card["attrs"], card["address"] = attrs, split[0]
        problems.extend(f"{rel}: {p}" for p in design_reference_problems(data, root, allow_tokens=True))
        scan["cards"].append(card)
    problems.extend(f"gap in the card numbering: no card numbered {n:02d}"
                    for n in range(1, max(numbers, default=0) + 1) if n not in numbers)
    if (root / "tokens.css").is_file():
        problems.extend(f"tokens.css: {p}" for p in design_reference_problems((root / "tokens.css").read_bytes(), root, allow_tokens=False))
    for page in sorted(root.rglob("*.htm*")):
        parts = page.relative_to(root).parts
        if parts[0] == DESIGN_LEGACY_DIR:  # the claude-design tool's record, whatever it holds
            continue
        if any(part.startswith(".") for part in parts) or page.suffix.lower() not in (".html", ".htm"):
            continue
        if (parts[0] == "cards" and len(parts) == 2) or (parts[0] == "rounds" and len(parts) >= 4 and parts[2] in ("cards", "import")):
            continue
        problems.append(f"{'/'.join(parts)}: HTML outside cards/ -- a monolith or a stray page (one numbered card per reviewable unit)")
    rnumbers: dict = {}
    rounds_dir = root / "rounds"
    for entry in sorted(rounds_dir.iterdir()) if rounds_dir.is_dir() else []:
        if entry.name.startswith("."):
            continue
        rel = f"rounds/{entry.name}"
        match = DESIGN_ROUND_RE.match(entry.name)
        number = design_number(match.group(1)) if match else None
        if not entry.is_dir() or number is None:
            problems.append(f"{rel}: not a round folder (rounds/ holds NN-slug/ folders only)")
            continue
        if number in rnumbers:
            problems.append(f"{rel}: duplicate round number {number:02d} (also {rnumbers[number]})")
            continue
        rnumbers[number] = rel
        rnd = {"number": number, "id": entry.name, "path": entry, "data": None}
        jpath = entry / "round.json"
        if not jpath.is_file():
            problems.append(f"{rel}: round.json missing" + (f"; {hint}" if hint else ""))
            hint = ""
        else:
            try:
                data = read_json(jpath)
            except (ValueError, OSError) as exc:
                problems.append(f"{rel}: round.json is not valid JSON: {exc}")
            else:
                found = design_round_problems(entry.name, data, entry)
                problems.extend(f"{rel}: {p}" for p in found)
                if not any(p.startswith("round.json:") for p in found):
                    rnd["data"] = data
        scan["rounds"].append(rnd)
    problems.extend(f"gap in the round numbering: no round numbered {n:02d}"
                    for n in range(1, max(rnumbers, default=0) + 1) if n not in rnumbers)
    known = {r["id"]: r["number"] for r in scan["rounds"]}
    for rnd in scan["rounds"]:
        for sid in (rnd["data"] or {}).get("supersedes", []):
            if known.get(sid, rnd["number"]) >= rnd["number"]:
                problems.append(f"rounds/{rnd['id']}: supersedes {sid!r}, which is not an earlier round")
    opened = design_open_rounds(scan)
    if len(opened) > 1:
        problems.append(f"more than one open round: {', '.join(r['id'] for r in opened)} (at most one round is open per project)")
    open_slices = {r["data"]["slice"] for r in opened}
    for card in scan["cards"]:
        if card["address"] and card["address"] not in open_slices:
            problems.append(f"{card['rel']}: carries the review address of {card['address']}, which has no open round (sign it with design-close, or open that slice's next round)")
    return scan


def design_open_rounds(scan: dict) -> list:
    return [r for r in scan["rounds"] if r["data"] and r["data"]["status"] == "open"]


def design_expected_problems(scan: dict, paths: list) -> list:
    """The read-back half: the handoff's numbered card list against the open round."""
    opened = design_open_rounds(scan)
    if len(opened) != 1:
        return ["card paths were named, but there is no single open round to check them against"]
    address = opened[0]["data"]["slice"]
    by_rel = {c["rel"]: c for c in scan["cards"]}
    prefixes = (DESIGN_ROOT_REL + "/", DESIGN_ROOT_SHOWN + "/")  # the same string at root
    named, problems = set(), []
    for raw in paths:
        rel = raw[2:] if raw.startswith("./") else raw
        prefix = next((pre for pre in prefixes if rel.startswith(pre)), "")
        rel = rel[len(prefix):]
        if not DESIGN_CARD_REL_RE.match(rel):
            problems.append(f"{raw}: not a numbered card path (cards/NN-slug.html)")
            continue
        named.add(rel)
        card = by_rel.get(rel)
        if card is None:
            problems.append(f"{rel}: named by the handoff but missing")
        elif card["address"] != address:
            problems.append(f"{rel}: named by the handoff but its group does not carry the round address \"{DESIGN_REVIEW_MARK} {address} · …\"")
    top = max((by_rel[r]["number"] for r in named if r in by_rel), default=0)
    for card in scan["cards"]:
        if card["address"] == address and card["rel"] not in named and card["number"] < top:
            problems.append(f"{card['rel']}: added beyond the handoff's list but numbered before its last card ({top:02d}); added cards take the next numbers")
    return problems


def design_check(args: argparse.Namespace) -> int:
    scan = design_scan(design_root())
    problems = list(scan["problems"])
    if args.paths:
        problems.extend(design_expected_problems(scan, args.paths))
    if problems:
        print(f"design-check: {len(problems)} problem(s) in {DESIGN_ROOT_SHOWN}/")
        for problem in problems:
            print(f"- {problem}")
        return 1
    opened = design_open_rounds(scan)
    print(f"design-check: OK -- {len(scan['cards'])} card(s), {len(scan['rounds'])} round(s), "
          f"open round: {opened[0]['id'] if opened else 'none'}")
    return 0


def design_write_bytes(path: Path, data: bytes) -> None:
    """Atomic like write_text, and keeps the file's permission bits (mkstemp would leave 0600)."""
    mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else None
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp_", suffix=path.name)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        if mode is not None:
            os.chmod(tmp, mode)
        os.replace(tmp, str(path))
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def design_readdress(data: bytes, old_group: str, new_group: str) -> bytes:
    """Rewrite the group value on line 1 and nothing else -- asserted, not assumed."""
    head, sep, rest = data.partition(b"\n")
    old_attr = f'group="{old_group}"'.encode("utf-8")
    if head.count(old_attr) != 1:
        raise SystemExit(f"design: line 1 does not carry {old_attr.decode('utf-8')} exactly once; nothing written")
    new = head.replace(old_attr, f'group="{new_group}"'.encode("utf-8")) + sep + rest
    new_head = new.partition(b"\n")[0]
    if new[len(new_head):] != data[len(head):] or new_head.replace(f'group="{new_group}"'.encode("utf-8"), old_attr) != head:
        raise SystemExit("design: the regroup would change more than the group label on line 1; nothing written")
    return new


def design_require(scan: dict, what: str) -> None:
    if scan["problems"]:
        lines = "\n".join(f"- {p}" for p in scan["problems"])
        raise SystemExit(f"{what}: refused -- design-check finds {len(scan['problems'])} problem(s):\n{lines}")


def design_init(args: argparse.Namespace) -> None:
    root = design_root()
    mpath = root / "design.json"
    rel = f"{DESIGN_ROOT_SHOWN}/design.json"
    if not mpath.exists() and design_legacy_hint(root):  # a refusal only: nothing moves, nothing is written
        raise SystemExit(f"design-init: refused -- {design_legacy_hint(root)}")
    if mpath.exists():
        try:
            current = read_json(mpath)
        except (ValueError, OSError) as exc:
            raise SystemExit(f"design-init: {rel} is not valid JSON ({exc}); fix it by hand")
        wanted = dict(current)
    else:
        current = None
        repo = HOST_ROOT or ROOT  # nested: the project is the host, not the `workflow` folder
        default_id = re.sub(r"[^a-z0-9]+", "-", repo.name.lower()).strip("-")[:63].strip("-") or "design"
        wanted = {"schema": DESIGN_SCHEMA, "id": default_id, "name": repo.name}
    if args.id:
        wanted["id"] = args.id
    if args.name:
        wanted["name"] = args.name
    problems = design_manifest_problems(wanted)
    if problems:
        raise SystemExit("design-init: refused -- " + "; ".join(problems))
    if wanted == current:
        print(f"design-init: {rel} unchanged (id={wanted['id']})")
        return
    write_json(mpath, wanted)
    print(f"design-init: {'updated' if current is not None else 'wrote'} {rel}")
    print(json.dumps(wanted, ensure_ascii=False, indent=2))


def design_open(args: argparse.Namespace) -> None:
    root = design_root()
    scan = design_scan(root)
    hint = design_legacy_hint(root)
    if scan["manifest"] is None:
        raise SystemExit(f"design-open: refused -- no valid {DESIGN_ROOT_SHOWN}/design.json; {hint}" if hint else
                         f"design-open: refused -- no valid {DESIGN_ROOT_SHOWN}/design.json (run: {WORKFLOW_CMD} design-init)")
    if not DESIGN_SLUG_RE.match(args.slug):
        raise SystemExit(f"design-open: --slug {args.slug!r} is not lowercase words joined by hyphens")
    if not DESIGN_SLICE_RE.match(args.slice):
        raise SystemExit(f"design-open: --slice {args.slice!r} is not a slice id (P<N>.<ID>)")
    broken = [r["id"] for r in scan["rounds"] if r["data"] is None]
    if broken:
        raise SystemExit(f"design-open: refused -- round(s) {', '.join(broken)} have no well-formed round.json; {hint}" if hint else
                         f"design-open: refused -- round(s) {', '.join(broken)} have no well-formed round.json (run design-check)")
    opened = design_open_rounds(scan)
    for rnd in opened:
        if rnd["id"].split("-", 1)[1] == args.slug and rnd["data"]["slice"] == args.slice:
            print(f"design-open: {rnd['id']} is already open for {args.slice} (nothing written)")
            return
    if opened:
        raise SystemExit(f"design-open: refused -- {opened[0]['id']} is open; close it first "
                         f"(design-close {opened[0]['id']} --words \"…\" when signed, --superseded when a design question replaces it)")
    stale = sorted({c["address"] for c in scan["cards"] if c["address"] and c["address"] != args.slice})
    if stale:
        raise SystemExit(f"design-open: refused -- cards still carry the review address of {', '.join(stale)}; "
                         f"a superseded round's cards are taken over by the next round of the same slice")
    number = max((r["number"] for r in scan["rounds"]), default=0) + 1
    rid = f"{number:02d}-{args.slug}"
    data = {
        "schema": DESIGN_SCHEMA, "round": rid, "title": args.title or args.slug.replace("-", " "),
        "slice": args.slice, "status": "open", "opened_at": now_iso(), "closed_at": None,
        "cards": [], "supersedes": [], "signoff_words": None,
    }
    write_json(root / "rounds" / rid / "round.json", data)
    print(f"design-open: opened {DESIGN_ROOT_SHOWN}/rounds/{rid}/ for {args.slice}")
    print(f"next: write rounds/{rid}/handoff.md; this round's cards carry "
          f"group=\"{DESIGN_REVIEW_MARK} {args.slice} · <Group>\" on line 1 until design-close")


def design_close(args: argparse.Namespace) -> None:
    root = design_root()
    status = "signed" if args.words is not None else "superseded"
    if args.words is not None and not args.words.strip():
        raise SystemExit("design-close: --words must carry the operator's literal words")
    scan = design_scan(root)
    rnd = next((r for r in scan["rounds"] if r["id"] == args.round), None)
    if rnd is None:
        raise SystemExit(f"design-close: no round {args.round!r} under {DESIGN_ROOT_SHOWN}/rounds/")
    data = rnd["data"]
    if data is not None and data["status"] == status:
        print(f"design-close: {args.round} is already {status} (nothing written)")
        return
    if data is not None and data["status"] != "open":
        raise SystemExit(f"design-close: {args.round} is already {data['status']}; a closed round is immutable")
    design_require(scan, "design-close")
    rdir, address = rnd["path"], data["slice"]
    if status == "signed" and not (rdir / "SIGNOFF.md").is_file():
        raise SystemExit(f"design-close: write rounds/{args.round}/SIGNOFF.md (the operator's literal words) first")
    touched = {c["rel"] for c in scan["cards"] if c["address"] == address} | set(data["cards"])
    order = {c["rel"]: c["number"] for c in scan["cards"]}
    missing = sorted(rel for rel in touched if rel not in order)
    if missing:
        raise SystemExit(f"design-close: refused -- listed card(s) no longer in the library: {', '.join(missing)}")
    touched = sorted(touched, key=order.__getitem__)
    if status == "signed" and not touched:
        raise SystemExit(f"design-close: no card carries the address \"{DESIGN_REVIEW_MARK} {address} · …\"; nothing to sign")
    jpath = rdir / "round.json"
    if data["cards"] != touched:  # persist the list before any card moves, so a half-landed close resumes
        data = dict(data, cards=touched)
        write_json(jpath, data)
    # 1. The snapshot: every touched card as it is under review, address on, plus the tokens.
    by_rel = {c["rel"]: c for c in scan["cards"]}
    for rel in touched:
        card, snap = by_rel[rel], rdir / rel
        live = card["path"].read_bytes()
        if card["address"] == address:
            if not snap.is_file() or snap.read_bytes() != live:
                design_write_bytes(snap, live)
        elif not snap.is_file():  # already regrouped by a half-landed run: put the address back exactly
            group = card["attrs"]["group"]
            design_write_bytes(snap, design_readdress(live, group, f"{DESIGN_REVIEW_MARK} {address} · {group}"))
    if (root / "tokens.css").is_file():
        tokens = (root / "tokens.css").read_bytes()
        if not (rdir / "tokens.css").is_file() or (rdir / "tokens.css").read_bytes() != tokens:
            design_write_bytes(rdir / "tokens.css", tokens)
    # 2. The regroup (signed only): the review address comes off line 1, every later byte identical.
    regrouped = 0
    if status == "signed":
        for rel in touched:
            card = by_rel[rel]
            if card["address"] != address:
                continue
            group = card["attrs"]["group"]
            live = card["path"].read_bytes()
            design_write_bytes(card["path"], design_readdress(live, group, design_address(group)[1]))
            regrouped += 1
    # 3. The manifest: supersedes is derived -- the latest earlier closed round that listed each card.
    earlier = sorted((r for r in scan["rounds"] if r["number"] < rnd["number"] and r["data"]
                      and r["data"]["status"] != "open"), key=lambda r: r["number"])
    supersedes = set()
    for rel in touched:
        last = [r["id"] for r in earlier if rel in r["data"]["cards"]]
        if last:
            supersedes.add(last[-1])
    data = dict(data, status=status, closed_at=now_iso(), cards=touched, supersedes=sorted(supersedes),
                signoff_words=args.words if status == "signed" else None)
    write_json(jpath, data)
    print(f"design-close: {args.round} {status} -- {len(touched)} card(s) snapshotted to "
          f"{DESIGN_ROOT_SHOWN}/rounds/{args.round}/cards/"
          + (f", {regrouped} regrouped (line 1 only)" if status == "signed" else ", left under review for the slice's next round"))
    if data["supersedes"]:
        print(f"supersedes: {', '.join(data['supersedes'])}")


def design_registry_path() -> Path:
    raw = os.environ.get(DESIGN_REGISTRY_ENV, "").strip()
    return Path(os.path.abspath(os.path.expanduser(raw or DESIGN_REGISTRY_DEFAULT)))


def design_register(args: argparse.Namespace) -> None:
    root = design_root()
    mpath = root / "design.json"
    try:
        manifest = read_json(mpath)
    except (ValueError, OSError):
        manifest = None
    if manifest is None or design_manifest_problems(manifest):
        hint = design_legacy_hint(root)
        raise SystemExit(f"design-register: refused -- no valid {DESIGN_ROOT_SHOWN}/design.json; {hint}" if hint else
                         f"design-register: refused -- no valid {DESIGN_ROOT_SHOWN}/design.json (run: {WORKFLOW_CMD} design-init)")
    path = design_registry_path()
    registry = {"schema": DESIGN_SCHEMA, "projects": []}
    if path.exists():
        try:
            registry = read_json(path)
        except (ValueError, OSError) as exc:
            raise SystemExit(f"design-register: refused -- the registry {path} is not valid JSON ({exc}); fix or remove it by hand")
        if not isinstance(registry, dict) or registry.get("schema") != DESIGN_SCHEMA:
            raise SystemExit(f"design-register: refused -- the registry {path} is not a schema-{DESIGN_SCHEMA} object; fix or remove it by hand")
        projects = registry.get("projects")
        if not (isinstance(projects, list) and all(isinstance(p, dict) for p in projects)):
            raise SystemExit(f"design-register: refused -- the registry {path} has no projects list; fix or remove it by hand")
    # Nested: the registered repo is the host (the record itself stays under the nested repo).
    entry = {"id": manifest["id"], "name": manifest["name"], "repo": str(HOST_ROOT or ROOT), "root": str(root)}
    projects = registry["projects"]
    holder = next((p for p in projects if p.get("id") == entry["id"]), None)
    if holder and holder.get("root") != entry["root"] and Path(str(holder.get("root"))).exists():
        raise SystemExit(f"design-register: refused -- id {entry['id']!r} is already registered to {holder.get('root')}; "
                         f"give this project another id (design-init --id <new-id>)")
    same_root = next((p for p in projects if p.get("root") == entry["root"]), None)
    kept = {**same_root, **entry} if same_root else dict(entry)
    kept["registered_at"] = (same_root or {}).get("registered_at") or now_iso()
    replaced = [p for p in projects if p is not same_root and (p.get("id") == entry["id"] or p.get("root") == entry["root"])]
    rest = [p for p in projects if p is not same_root and p not in replaced]
    updated = dict(registry, schema=DESIGN_SCHEMA, projects=sorted(rest + [kept], key=lambda p: str(p.get("id"))))
    if updated == registry:
        print(f"design-register: {entry['id']} already registered in {path} (nothing written)")
        design_deck_hint()
        return
    write_json(path, updated)
    print(f"design-register: wrote {path}")
    for gone in replaced:
        print(f"replaced a stale entry: {gone.get('id')} at {gone.get('root')}")
    print(json.dumps(kept, ensure_ascii=False, indent=2))
    design_deck_hint()


def design_deck_hint() -> None:
    """design-register's closing hint: the dashboard reads this registry, where it is served, and
    which repos it can see -- design-deck's own mounted projects folder, $DECK_PROJECTS_DIR (its
    deck.sh variable), default ~/projects. Prints only; the engine never guesses a URL."""
    url = os.environ.get(DESIGN_DECK_URL_ENV, "").strip()
    print(f"design-deck reads this registry: {url}" if url
          else f"design-deck reads this registry (set ${DESIGN_DECK_URL_ENV} to print its URL here)")
    projects = Path(os.path.expanduser(os.environ.get("DECK_PROJECTS_DIR", "").strip() or "~/projects")).resolve()
    print(f"design-deck only sees repos under its mounted projects folder ({projects})")
    try:
        (HOST_ROOT or ROOT).resolve().relative_to(projects)
    except ValueError:
        print(f"warning: this repo is outside {projects}, so design-deck will show it as unavailable")


def design_migrate(args: argparse.Namespace) -> None:
    """Move a pre-v47 design record into DESIGN_LEGACY_DIR, unchanged. With no design.json the whole
    root is the old record, so every top-level entry moves (dot-entries stay); with design.json the
    repo already uses the drafter, so only the old record's parts move -- rounds without round.json,
    the root SIGNOFF.md and grounding/. Every check runs before the first move (a refusal moves
    nothing); a dry run unless --apply; never a delete (only an empty rounds/ is rmdir'ed), never git."""
    root = design_root()
    if not root.is_dir():
        raise SystemExit(f"design-migrate: refused -- no design root at {DESIGN_ROOT_SHOWN}/; nothing to migrate")
    legacy = root / DESIGN_LEGACY_DIR
    rounds_dir = root / "rounds"
    rel = lambda p: Path(shown(p)).as_posix()
    moves, left, problems = [], [], []
    outside = "not part of either contract; move it by hand if it belongs to the old record"
    if not (root / "design.json").exists():
        mixed = [e.name for e in sorted(rounds_dir.iterdir()) if (e / "round.json").exists()] if rounds_dir.is_dir() else []
        if mixed:
            problems.append(f"{rel(rounds_dir)} holds schema-1 round(s) {', '.join(mixed)} (they carry a round.json) but there is "
                            f"no design.json; if this repo uses the drafter, restore it with design-init first")
        for entry in sorted(root.iterdir()):
            if entry.name == DESIGN_LEGACY_DIR:
                continue
            if entry.name.startswith("."):
                left.append((entry, "a dot-entry"))
                continue
            moves.append((entry, legacy / entry.name))
    else:
        left.extend((e, outside) for e in (sorted(rounds_dir.iterdir()) if rounds_dir.is_dir() else [])
                    if not e.name.startswith(".") and not e.is_dir())
        moves.extend((part, legacy / part.relative_to(root)) for part in design_legacy_record(root))
        if moves and (root / "tokens.css").is_file():  # schema 1's own file: kept, but said out loud
            left.append((root / "tokens.css", "kept as schema 1's tokens.css; if it belongs to the old record, move it into claude-design/ by hand"))
        schema1 = {"design.json", "cards", "tokens.css", "rounds", DESIGN_LEGACY_DIR, "SIGNOFF.md", "grounding"}
        left.extend((e, outside) for e in sorted(root.iterdir()) if e.name not in schema1 and not e.name.startswith("."))
    folders = [legacy] + ([legacy / "rounds"] if any(dst.parent == legacy / "rounds" for _, dst in moves) else [])
    for folder in folders:
        if os.path.lexists(folder) and not folder.is_dir():
            problems.append(f"{rel(folder)} exists and is not a folder")
    started = ("; a claude-design round was started first -- move each legacy round into claude-design/rounds/ by hand, "
               "renumbering after the existing ones, remove the emptied rounds/, then re-run")
    problems.extend(f"{rel(dst)} already exists" + (started if dst == legacy / "rounds" else "")
                    for _, dst in moves if os.path.lexists(dst))
    if problems:
        raise SystemExit("design-migrate: refused -- nothing moved:\n" + "\n".join(f"- {p}" for p in problems))
    stayed = [f"design-migrate: left in place {rel(path)} ({why})" for path, why in left]
    if not moves:
        print("\n".join(stayed + ["design-migrate: nothing to migrate"]))
        return
    if not args.apply:
        print("\n".join([f"design-migrate: would move {rel(src)} -> {rel(dst)}" for src, dst in moves] + stayed
                        + ["design-migrate: dry run -- nothing moved; re-run with --apply"]))
        return
    created, done = [], []
    try:
        for src, dst in moves:
            for folder in folders:
                if folder in dst.parents and not folder.is_dir():
                    folder.mkdir()
                    created.append(folder)
            os.replace(src, dst)
            done.append((src, dst))
    except OSError as exc:  # all-or-nothing: put back what already moved, then drop only the folders made here
        undo = []
        for src, dst in reversed(done):
            try:
                os.replace(dst, src)
            except OSError as again:
                undo.append(f"- could not move {rel(dst)} back to {rel(src)}: {again}")
        for folder in reversed(created):
            try:
                folder.rmdir()
            except OSError:
                pass
        raise SystemExit(f"design-migrate: failed -- {exc}; " + (
            "rolled back, nothing moved" if not undo else "rollback incomplete:\n" + "\n".join(undo)))
    for src, dst in moves:
        print(f"design-migrate: moved {rel(src)} -> {rel(dst)}")
    if any(src.parent == rounds_dir for src, _ in moves) and rounds_dir.is_dir():
        try:
            rounds_dir.rmdir()  # only ever succeeds on a truly empty folder
            print(f"design-migrate: removed the now-empty {rel(rounds_dir)}/")
        except OSError:
            pass
    if stayed:
        print("\n".join(stayed))
    print("commit the move yourself (git sees it as renames)"
          + ("" if (root / "design.json").exists() else "; run design-init only if this repo will use the drafter"))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Manage the agentic workflow state.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("rebuild", help="Rebuild workflow dashboards/index/state and docs snapshots")
    p.set_defaults(func=lambda args: (rebuild_docs(), rebuild_index_and_state(), print("rebuilt workflow and docs")))

    p = sub.add_parser("rebuild-docs", help="Regenerate docs/current/*.md from docs/index.json latest versions")
    p.set_defaults(func=lambda args: (rebuild_docs(), print("rebuilt docs/current from latest versions")))

    p = sub.add_parser("docs", help="Print latest doc versions")
    p.set_defaults(func=cmd_docs)

    p = sub.add_parser("doc-new-version", help="Create a new durable doc version from the latest version")
    p.add_argument("--doc", required=True, choices=sorted(DOC_TYPES))
    p.add_argument("--summary", required=True)
    p.add_argument("--source", required=True)
    p.set_defaults(func=new_doc_version)

    p = sub.add_parser("validate", help="Validate workflow and docs structure")
    p.set_defaults(func=lambda args: sys.exit(validate()))

    p = sub.add_parser("sync-agents", help="Write the route table's rows (engine defaults overlaid by the repo-root executors.toml) into the model/effort frontmatter of the four managed agent files: slice-executor-mid, slice-executor-high, design-drafter (the high row) and Explore (the explore row)")
    p.add_argument("--check", action="store_true", help="Report drift without writing; exit 1 if out of sync")
    p.set_defaults(func=sync_agents)

    p = sub.add_parser("executor-route", help="Print the executor routing decision, one key=value per line, writing nothing: bare, the resolved route table (high, research, mid, cheap, explore) and the agent files' sync state; with a slice id, the route, tier, subagent_type, model, effort and attribution its dispatch uses (kind first, then risk, then attempt); plus fallback= and warning= lines for the environment")
    p.add_argument("slice", nargs="?", help="the slice to route; omit for the table")
    p.add_argument("--retry", action="store_true", help="the slice's second attempt (an escalation, a failed or empty return, a fix of mid-row work): always the high row")
    p.add_argument("--drafter", action="store_true", help="the design-drafter's dispatch (it follows the high row)")
    p.add_argument("--explore", action="store_true", help="the read-only Explore lookup agent's dispatch (the explore row)")
    p.set_defaults(func=cmd_executor_route)

    p = sub.add_parser("record-dispatch", help="Append one executor_dispatched record to works/events.jsonl (slice, kind, risk, route, tier, agent, model, effort, attribution, attempt, verdict, and the measured duration / tokens / tool uses from the Agent completion notification); copy route / model / effort from executor-route; writes nothing else")
    p.add_argument("slice", help="the slice that was dispatched")
    p.add_argument("--route", required=True, choices=EXECUTOR_ROUTES, help="the route row dispatched on (the route= line executor-route printed)")
    p.add_argument("--model", required=True, help="the model the dispatch ran on (the model= line)")
    p.add_argument("--effort", required=True, help="the effort the dispatch ran on (the effort= line; empty when none was passed)")
    p.add_argument("--verdict", required=True, choices=_DISPATCH_VERDICTS, help="how the executor returned; failed = an empty or failed return")
    p.add_argument("--attempt", type=int, default=1, help="1 for the first dispatch, 2 for the retry (default 1)")
    p.add_argument("--tier", choices=EXECUTOR_TIERS, help="the tier (default: the route's tier; none for explore)")
    p.add_argument("--agent", help="the subagent_type dispatched (default: the tier's installed agent; --agent design-drafter for the drafter span)")
    p.add_argument("--duration-ms", type=int, dest="duration_ms", help="duration_ms from the completion notification")
    p.add_argument("--tokens", type=int, help="subagent_tokens from the completion notification")
    p.add_argument("--tool-uses", type=int, dest="tool_uses", help="tool_uses from the completion notification")
    p.add_argument("--note", help="free text, e.g. back-filled from the completion notification")
    p.set_defaults(func=cmd_record_dispatch)

    p = sub.add_parser("dispatch-summary", help="Read-only: summarize the executor_dispatched records in works/events.jsonl by route, by model @ effort and by kind (dispatches, verdict counts, retries, mean / total minutes, tokens); --slice lists one slice's attempts; --json for tooling")
    p.add_argument("--phase", help="keep one phase's records")
    p.add_argument("--slice", help="keep one slice's records (its attempts, in order) and print them one per line")
    p.add_argument("--json", action="store_true", help="print the aggregates as one JSON object")
    p.set_defaults(func=cmd_dispatch_summary)

    p = sub.add_parser("next", help="Print the current phase/slice selection")
    p.set_defaults(func=cmd_next)

    p = sub.add_parser("compact-gate", help="The PreCompact hook (matcher auto): read the hook JSON on stdin and veto an auto-compaction while this checkout's current slice is in_progress or in_review or the tree is dirty, so compaction lands at a slice boundary; fails open -- a manual /compact, a fill at or above the ceiling (AGENTIC_COMPACT_CEILING), the cap of consecutive blocks (AGENTIC_COMPACT_BLOCK_CAP) and any error all allow, a block is only the stdout {\"decision\": \"block\"} JSON, and it always exits 0 (one trace line on stderr)")
    p.set_defaults(func=cmd_compact_gate)

    p = sub.add_parser("compact-resume", help="The SessionStart hook (matcher compact): print the next pointer and the resume line (re-read the running skill, the active slice folder and phase.md's ## Now) after a compaction; never fails, always exits 0")
    p.set_defaults(func=cmd_compact_resume)

    p = sub.add_parser("deferred", help="Rebuild and print deferred jobs dashboard summary")
    p.set_defaults(func=cmd_deferred)

    p = sub.add_parser("new-phase", help="Create a new phase with DECOMP and REVIEW slices")
    p.add_argument("--phase", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--objective", required=True)
    p.add_argument("--order", type=float, help="sort position among phases; a fractional value (e.g. 4.5) inserts between two neighbors without renumbering")
    p.add_argument("--on-main", action="store_true", dest="on_main",
                   help="no-op since v43 (the default stream is the default); accepted so v42 habits and scripts keep working")
    p.add_argument("--consolidates", metavar="P26,P27",
                   help="docs phase: the comma-separated ids of active phases whose doc consolidation debt this phase pays; refused (nothing written) for an id that is not an active phase owing consolidation. Stored as `consolidates` in phase.json -- the only docs-phase marker; `docs-debt` shows it as 'paid by' and `rotate-backlog` proposes no second docs phase for what it covers")
    p.set_defaults(func=new_phase)

    p = sub.add_parser("new-slice", help="Create a new slice folder with slice.json + markdown files")
    p.add_argument("--phase", required=True)
    p.add_argument("--slice", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--kind", default="implementation", help="one of implementation, review, decomposition, research, fix, docs, qa, co-work (closed set; unknown kinds are rejected). research is findings-only: no product code, findings land in phase.md, and it always routes to the research row on slice-executor-high")
    p.add_argument("--risk", default="high", help="low (the mid row for implementation and fix, the cheap row for docs and qa -- both on slice-executor-mid, the default tier since v46, real code included) or high (the high row on slice-executor-high: only for a named trigger -- open design, a core invariant, an unlocated root cause, a wide blast radius -- or a fix to mid-row work); unset or unrecognized values route to high; kind decomposition, review, co-work and research route by kind whatever this says; `executor-route <slice>` prints the decision")
    p.add_argument("--order", type=float, help="sort position within the phase; a fractional value (e.g. 4.5) inserts between two neighbors without renumbering (default: 10 past the last non-review slice)")
    p.add_argument("--depends-on", action="append", help="advisory: validate checks only that the named slice exists; selection still follows --order")
    p.set_defaults(func=new_slice)

    p = sub.add_parser("start-slice", help="Mark a slice in_progress")
    p.add_argument("slice")
    p.set_defaults(func=start_slice)

    p = sub.add_parser("finish-slice", help="Mark a slice done")
    p.add_argument("slice")
    p.add_argument("--outcome", help="one line recorded in slice.json and rendered in the phase's generated ## Slices table")
    p.set_defaults(func=finish_slice)

    p = sub.add_parser("set-slice-status", help="Set any valid slice status")
    p.add_argument("slice")
    p.add_argument("status")
    p.set_defaults(func=lambda args: (set_slice_status(args.slice, args.status), print(f"slice {args.slice}: {args.status}")))

    p = sub.add_parser("set-phase-status", help="Set any valid phase status")
    p.add_argument("phase")
    p.add_argument("status")
    p.set_defaults(func=set_phase_status)

    p = sub.add_parser("review-phase", help="Record a phase review verdict (pass/changes_requested/blocked)")
    p.add_argument("phase")
    p.add_argument("--verdict", required=True, choices=sorted(REVIEW_VERDICTS))
    p.add_argument("--reviewer", default=None)
    p.add_argument("--note", default=None)
    p.set_defaults(func=review_phase)

    p = sub.add_parser("accept-gate", help="Operator acceptance gate for a phase: declare (--require/--waive), open it at the review (--open), clear it (--clear), or show it (bare). Orchestrator/operator command -- executors never run it")
    p.add_argument("phase")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--require", action="store_true", help="declare the phase operator-visible: review-phase --verdict pass refuses until the gate is opened and cleared (creates the gate block on a legacy phase). No status change")
    g.add_argument("--waive", action="store_true", help="declare the phase NOT operator-visible; --note is mandatory and records why")
    g.add_argument("--open", action="store_true", dest="open_gate", help="open the gate at the review: record --walkthrough, set the phase pending, print the operator instructions (needs --require first)")
    g.add_argument("--clear", action="store_true", help="the operator walked the product: stamp cleared_at, return the phase to in_progress")
    p.add_argument("--walkthrough", default=None, help="the concrete script the operator runs (URLs to open, actions to try, in the operator runtime); use with --open")
    p.add_argument("--note", default=None, help="mandatory reason with --waive; optional record of what the operator reported with --clear")
    p.set_defaults(func=accept_gate)

    p = sub.add_parser("docs-debt", help="Read-only worklist for a docs phase: which phases owe durable-doc consolidation, their '## Doc impact' notes, the docs they touch and the paying commands")
    p.set_defaults(func=docs_debt)

    p = sub.add_parser("docs-consolidated", help="Record that a phase's deferred durable-doc consolidation landed (run after a docs phase creates the versions; also unblocks archiving)")
    p.add_argument("phase")
    p.set_defaults(func=docs_consolidated)

    p = sub.add_parser("parallel-start", help="Ask for a worktree: move a planned phase out of the default stream into its own -- stamp it, commit the stamp (phase folder + works/ files only; a dirty tree is fine), cut phase/P<N>-<slug> and .claude/worktrees/P<N>-<slug>")
    p.add_argument("phase")
    p.add_argument("--worktree", default=None, help="worktree path (default: <repo>/.claude/worktrees/P<N>-<slug>, which EnterWorktree can enter in the same session; elsewhere means opening a second session there)")
    p.add_argument("--slug", default=None, help="branch slug override (default: slugified phase name); branch is phase/<phase>-<slug>")
    p.add_argument("--host-branch", default=None, help="nested install only, and required there: the host repo's branch for this phase's product commits, named by the host's convention (no workspace IDs); reused when it exists and no host worktree has it checked out. In nested the pair is <host>/.claude/worktrees/P<N>-<slug> on this branch, with the nested worktree inside it (--worktree overrides the host worktree's path)")
    p.add_argument("--host-base", default=None, help="nested install only: the host ref the host branch starts from (default: origin/HEAD, else init.defaultBranch if it exists locally, else main, then master; never fetched)")
    p.set_defaults(func=parallel_start)

    p = sub.add_parser("parallel-skip", help="No-op since v43 (the default stream is the default, so there is nothing to pin): reports where the phase runs and writes nothing")
    p.add_argument("phase")
    p.set_defaults(func=parallel_skip)

    p = sub.add_parser("parallel-status", help="Read-only cross-stream view: this checkout's pointer plus every parallel phase's branch-side slice state (never writes anything)")
    p.set_defaults(func=parallel_status)

    p = sub.add_parser("parallel-gate", help="Quiet-point gate: is this parallel phase's branch mergeable now (branch done+pass, default stream quiet)? Exit 0 = open")
    p.add_argument("phase")
    p.add_argument("--branch-ref", default=None, help="git ref holding the phase branch's state (default: the phase's stamped execution.branch; e.g. HEAD or origin/phase/P2-x in CI)")
    p.add_argument("--main-ref", default=None, help="git ref holding the default stream's state (default: this working tree; e.g. origin/main when running from a PR checkout)")
    p.set_defaults(func=parallel_gate)

    p = sub.add_parser("parallel-merge-finish", help="Run on the default stream right after merging a phase branch: regenerate the generated files and list phases awaiting doc consolidation")
    p.set_defaults(func=parallel_merge_finish)

    p = sub.add_parser("parallel-consolidated", help="Mark a merged parallel phase's deferred doc consolidation done (run on the default stream, after the doc versions land)")
    p.add_argument("phase")
    p.set_defaults(func=parallel_consolidated)

    p = sub.add_parser("parallel-teardown", help="Retire a merged parallel phase's worktree and branch; run from the default stream")
    p.add_argument("phase")
    p.add_argument("--discard-ignored", action="store_true", help="nested install only: delete the ignored, worktree-only files the paired teardown lists (it refuses without this flag)")
    p.set_defaults(func=parallel_teardown)

    p = sub.add_parser("nested-convention", help="Nested personal install only: show the host repo's conventions for commits, branches and pull requests (bare), or record the operator's confirmation of them -- the text and whether Claude Co-Authored-By trailers are allowed in host commits (--confirm --text ... --trailers allowed|forbidden); refuses outside a nested install")
    p.add_argument("--confirm", action="store_true", help="record the operator-confirmed conventions (needs --text and --trailers)")
    p.add_argument("--text", default=None, help="the host's conventions as the operator confirmed them: commit subjects and trailers; branch naming and base (e.g. from fresh main); PR shape (one per ticket or per phase) and who merges")
    p.add_argument("--trailers", default=None, choices=("allowed", "forbidden"), help="may Claude Co-Authored-By trailers appear in host product commits")
    p.set_defaults(func=cmd_nested_convention)

    p = sub.add_parser("phase-scope", help="Read-only: the phase's boundary from git -- creation commit, base..head range and the product files it changed (works/ and docs/ excluded); advisory, exit 0 without git")
    p.add_argument("phase")
    p.add_argument("--base", default=None, help="use this ref as the range base verbatim (skips creation-commit / merge-base detection)")
    p.add_argument("--head", default=None, help="use this ref as the range head (default: HEAD, or the commit that recorded a passing review on a done phase)")
    p.add_argument("--json", action="store_true", help="print the same answer as one JSON object")
    p.set_defaults(func=phase_scope)

    # The design contract (v47): the on-disk layout lives in design-cowork/SKILL.md "The design record".
    p = sub.add_parser("design-init", help=f"Write the design project manifest {DESIGN_ROOT_REL}/design.json (schema {DESIGN_SCHEMA}: id, name); idempotent -- an unchanged manifest is not rewritten",
                       description=f"Create or update {DESIGN_ROOT_REL}/design.json, the one design project this repo holds. Defaults: id = the repo folder's name, slugified; name = the folder's name.")
    p.add_argument("--id", default=None, help="the project id: lowercase [a-z0-9-], starting alphanumeric, at most 63 characters; unique across the operator's registry")
    p.add_argument("--name", default=None, help="the display name the dashboard shows")
    p.set_defaults(func=design_init)

    p = sub.add_parser("design-open", help=f"Open the next design round: {DESIGN_ROOT_REL}/rounds/NN-<slug>/round.json, status open; refuses while another round is open or a card still carries another slice's review address",
                       description="Open the next design round (numbered max + 1). Its cards carry the review address on line 1 -- group=\"\u23f3 <slice> \u00b7 <Group>\" -- until design-close. The orchestrator writes the round's handoff.md next.")
    p.add_argument("--slug", required=True, help="the round's slug: lowercase words joined by hyphens")
    p.add_argument("--slice", required=True, help="the co-work slice that owns the round (e.g. P48.S1); its id is the review address the round's cards carry")
    p.add_argument("--title", default=None, help="display title (default: the slug)")
    p.set_defaults(func=design_open)

    p = sub.add_parser("design-check", help=f"Check {DESIGN_ROOT_REL}/ against the design contract -- numbered contiguous cards, no unnumbered card or monolith, valid @dsCard markers, self-contained cards, well-formed design.json and round.json, snapshots of closed rounds; exit 1 with every problem named",
                       description="Read-only. With card paths (the handoff's numbered list), also check that each is present and carries the open round's address, and that cards added beyond the list are numbered after it.")
    p.add_argument("paths", nargs="*", help="card paths the handoff named, e.g. cards/03-button.html (optional)")
    p.set_defaults(func=design_check)

    p = sub.add_parser("design-close", help="Close the open design round: snapshot its cards and tokens.css into the round folder (address on), then with --words regroup the live cards (line 1 only, every later byte asserted identical) and mark it signed, or with --superseded mark it superseded; idempotent",
                       description="--words needs rounds/<round>/SIGNOFF.md written first. A superseded round's cards stay under review for the same slice's next round. Re-run a half-landed close; a closed round is never rewritten.")
    p.add_argument("round", help="the round id, e.g. 03-signin")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--words", default=None, help="the operator's literal signoff words, recorded verbatim in round.json")
    g.add_argument("--superseded", action="store_true", help="a design question replaces the round before it is signed: snapshot and close it, no regroup")
    p.set_defaults(func=design_close)

    p = sub.add_parser("design-register", help=f"Register this repo's design project with the operator's dashboard: upsert it into the registry OUTSIDE the repo (${DESIGN_REGISTRY_ENV}, default {DESIGN_REGISTRY_DEFAULT}) with absolute paths; idempotent, atomic, prints what it wrote and a design-deck hint (its URL from ${DESIGN_DECK_URL_ENV} when set)",
                       description=f"Writes only the registry file: ${DESIGN_REGISTRY_ENV} when set, else {DESIGN_REGISTRY_DEFAULT}. Refuses an id another live repo holds; replaces an entry whose root has vanished (a moved repo). Tests must point ${DESIGN_REGISTRY_ENV} at a scratch path. On success it also prints a design-deck hint: the deck URL from ${DESIGN_DECK_URL_ENV} when set (never guessed), and a warning when this repo is outside the deck's mounted projects folder ($DECK_PROJECTS_DIR, default ~/projects).")
    p.set_defaults(func=design_register)

    p = sub.add_parser("design-migrate", help=f"Move a pre-v47 (Claude Design) design record into {DESIGN_ROOT_REL}/{DESIGN_LEGACY_DIR}/, unchanged: with no design.json every top-level entry, else only rounds without round.json, SIGNOFF.md and grounding/; a dry run unless --apply",
                       description=f"All-or-nothing: every check runs before the first move, and an existing destination, or a design.json-less root whose rounds/ holds a round.json, refuses with nothing moved. Dot-entries, and with design.json anything outside both contracts, are listed as left in place. Never deletes (only an emptied rounds/ is rmdir'ed), never runs git, never writes design.json (design-init stays separate). The engine never reads {DESIGN_LEGACY_DIR}/.")
    p.add_argument("--apply", action="store_true", help="perform the moves (default: print them and move nothing)")
    p.set_defaults(func=design_migrate)

    p = sub.add_parser("defer-job", help="Create a deferred job folder")
    p.add_argument("--id")
    p.add_argument("--title", required=True)
    p.add_argument("--reason", required=True)
    p.add_argument("--trigger", required=True)
    p.add_argument("--source", required=True)
    p.set_defaults(func=defer_job)

    p = sub.add_parser("promote-deferred", help="Promote an open deferred job into an active slice")
    p.add_argument("deferred_id")
    p.add_argument("--phase", required=True)
    p.add_argument("--slice", required=True)
    p.add_argument("--name")
    p.add_argument("--kind", default="implementation", help="one of implementation, review, decomposition, research, fix, docs, qa, co-work (closed set; unknown kinds are rejected). research is findings-only: no product code, findings land in phase.md, and it always routes to the research row on slice-executor-high")
    p.add_argument("--risk", default="high", help="low (the mid row for implementation and fix, the cheap row for docs and qa -- both on slice-executor-mid, the default tier since v46, real code included) or high (the high row on slice-executor-high: only for a named trigger -- open design, a core invariant, an unlocated root cause, a wide blast radius -- or a fix to mid-row work); unset or unrecognized values route to high; kind decomposition, review, co-work and research route by kind whatever this says; `executor-route <slice>` prints the decision")
    p.add_argument("--order", type=float, help="sort position within the phase; a fractional value (e.g. 4.5) inserts between two neighbors without renumbering (default: 10 past the last non-review slice)")
    p.add_argument("--depends-on", action="append", help="advisory: validate checks only that the named slice exists; selection still follows --order")
    p.add_argument("--create-phase", action="store_true")
    p.add_argument("--phase-name")
    p.add_argument("--phase-objective")
    p.set_defaults(func=promote_deferred)

    p = sub.add_parser("drop-deferred", help="Drop an open deferred job")
    p.add_argument("deferred_id")
    p.add_argument("--reason", required=True)
    p.set_defaults(func=drop_deferred)

    p = sub.add_parser("archive-phase", help="Archive a single review-passed phase (first-class; use when only some phases are done)")
    p.add_argument("phase")
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=archive_phase)

    p = sub.add_parser("archive-all", help="Batch-archive ALL active phases at once; only when every phase is done (last review slice complete)")
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=archive_all)

    p = sub.add_parser("rotate-backlog", help="The one resumable step of /rotate-backlog: checks the doc debt FIRST and prints its decision as the first line, rotate=<refused|archive|stop_midflight|resume|create>. archive: nothing owes, so archive every currently-done phase (whole phases, the partial archive-all) and rebuild. While debt stands it archives nothing: stop_midflight when default-stream work is off a boundary, resume the live docs phase (re-asserting its queue-jump order), or print the docs phase to create, its create: line carrying the queue-jump --order. refused (writes nothing, non-zero exit) on a parallel stream")
    p.add_argument("--archive-only", action="store_true", dest="archive_only",
                   help="archive only: the sweep of every currently-done phase and its report, with no rotate= line and no docs-phase line (unchanged since v51)")
    p.set_defaults(func=rotate_backlog)

    args = parser.parse_args(argv)
    if NESTED is not None and NESTED_PROBLEMS and args.cmd not in ("validate", "compact-gate", "compact-resume"):  # the hooks fail open
        # Never fall back to at-root mode on a broken marker: refuse, and let validate list it all.
        raise SystemExit(f"{shown(ROOT / NESTED_MARKER)} is malformed, so this nested install cannot run {args.cmd}: "
                         f"{'; '.join(NESTED_PROBLEMS)} -- fix the file (run: {WORKFLOW_CMD} validate)")
    result = args.func(args)
    if isinstance(result, tuple):
        return 0
    return 0 if result is None else int(result or 0)


if __name__ == "__main__":
    raise SystemExit(main())
