#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKS = ROOT / "works"
DOCS = ROOT / "docs"
ACTIVE = WORKS / "phases" / "active"
ARCHIVED = WORKS / "phases" / "archived"
DEFERRED_OPEN = WORKS / "deferred" / "open"
DEFERRED_PROMOTED = WORKS / "deferred" / "promoted"
DEFERRED_DROPPED = WORKS / "deferred" / "dropped"
DOC_TYPES = {"product", "experience", "architecture", "frontend", "backend", "data", "api", "operations", "security", "qa", "decisions"}
PHASE_STATUSES = {"planned", "in_progress", "in_review", "pending", "blocked", "done"}
SLICE_STATUSES = {"todo", "ready", "in_progress", "in_review", "changes_requested", "pending", "blocked", "done"}
DEFERRED_STATUSES = {"deferred", "ready", "promoted", "done", "dropped"}
REVIEW_VERDICTS = {"pass", "changes_requested", "blocked"}
# Opt-in parallel execution (workspace v24). A phase.json MAY carry an optional
# `execution` block; its absence means the phase belongs to the default stream and
# every behavior is exactly as before, byte for byte. See `phase_execution`.
EXECUTION_MODES = {"parallel"}
CONSOLIDATION_STATES = {"pending", "done"}
# A default-stream phase in any of these states means main is mid-flight, so a phase
# branch may not be merged into it yet (the quiet-point gate, `parallel-gate`).
BUSY_PHASE_STATUSES = ("in_progress", "in_review", "pending", "blocked")
# Regenerated from works/phases/** and docs/versions/** by `parallel-merge-finish`;
# never merged by hand (see .gitattributes).
GENERATED_FILES = ("works/state.json", "works/index.json", "works/backlog.md", "works/deferred.md", "docs/current/*.md")
CLAUDE_AGENTS = ROOT / ".claude" / "agents"
CODEX_AGENTS = ROOT / ".codex" / "agents"
EXECUTOR_TIERS = ("mid", "high")
RETIRED_EXECUTOR_TIERS = ("low",)  # dropped in workspace v23 — routing is two-tier (mid/high)
# Shipped presets for the slice-executor tiers. A top-level mode = "<preset>" key in
# the repo-root executors.toml picks one (absent file or key -> economy); per-tier
# [claude.<tier>] / [codex.<tier>] tables with model/effort keys override the active
# preset field by field; apply with `sync-agents`. An empty effort means "write no
# effort line" — the escape hatch for models that reject the effort parameter
# (e.g. haiku). Models may not be empty. Codex tiers are identical in both presets.
DEFAULT_EXECUTOR_MODE = "economy"
EXECUTOR_PRESETS = {
    "flex": {
        "mid": {"model": "sonnet", "effort": "xhigh", "codex_model": "gpt-5.5", "codex_effort": "high"},
        "high": {"model": "opus", "effort": "xhigh", "codex_model": "gpt-5.5", "codex_effort": "xhigh"},
    },
    "economy": {
        "mid": {"model": "sonnet", "effort": "high", "codex_model": "gpt-5.5", "codex_effort": "high"},
        "high": {"model": "opus", "effort": "high", "codex_model": "gpt-5.5", "codex_effort": "xhigh"},
    },
}


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


def read_executors_toml() -> tuple:
    """(mode, {(harness, tier, key): value}) from the repo-root executors.toml.

    Strict subset of TOML — an optional top-level mode = "<preset>" line (before
    any section) plus [claude.<tier>] / [codex.<tier>] tables holding
    model/effort keys with double-quoted string values; '#' comments and blanks
    ignored. Anything else is an error, so typos surface instead of silently
    keeping a default."""
    path = ROOT / "executors.toml"
    mode = None
    values: dict = {}
    if not path.exists():
        return mode, values
    section = None
    for n, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r'^mode\s*=\s*"([^"]*)"\s*(?:#.*)?$', line)
        if m:
            if section is not None:
                raise SystemExit(f"executors.toml line {n}: mode must be set at the top level, before any [claude.*]/[codex.*] section")
            if mode is not None:
                raise SystemExit(f"executors.toml line {n}: duplicate mode")
            if m.group(1) not in EXECUTOR_PRESETS:
                raise SystemExit(f"executors.toml line {n}: unknown mode {m.group(1)!r} (valid: {', '.join(sorted(EXECUTOR_PRESETS))})")
            mode = m.group(1)
            continue
        m = re.match(r"^\[\s*(claude|codex)\s*\.\s*(mid|high)\s*\]\s*(?:#.*)?$", line)
        if m:
            section = (m.group(1), m.group(2))
            continue
        m = re.match(r"^\[\s*(claude|codex)\s*\.\s*(" + "|".join(RETIRED_EXECUTOR_TIERS) + r")\s*\]\s*(?:#.*)?$", line)
        if m:
            raise SystemExit(
                f"executors.toml line {n}: the {m.group(2)} executor tier was retired in workspace v23 — "
                f"routing is two-tier now, so drop this section or move its settings to [{m.group(1)}.mid]"
            )
        m = re.match(r'^(model|effort)\s*=\s*"([^"]*)"\s*(?:#.*)?$', line)
        if m:
            if section is None:
                raise SystemExit(f"executors.toml line {n}: key outside a section — put it under [claude.<tier>] or [codex.<tier>]")
            key = (section[0], section[1], m.group(1))
            if key in values:
                raise SystemExit(f"executors.toml line {n}: duplicate {m.group(1)} for [{section[0]}.{section[1]}]")
            values[key] = m.group(2)
            continue
        if re.match(r"^(model|effort|mode)\s*=", line):
            raise SystemExit(f'executors.toml line {n}: values must be double-quoted TOML strings, e.g. model = "haiku"')
        raise SystemExit(f"executors.toml line {n}: cannot parse {line!r} (expected mode = \"...\", [claude.<mid|high>], [codex.<mid|high>], or model/effort = \"...\")")
    return mode, values


def executor_config() -> dict:
    """The active preset (top-level mode in executors.toml; default economy) overlaid with any per-tier overrides; values pass through verbatim."""
    mode, overrides = read_executors_toml()
    preset = EXECUTOR_PRESETS[mode or DEFAULT_EXECUTOR_MODE]
    config = {tier: dict(preset[tier]) for tier in EXECUTOR_TIERS}
    for (harness, tier, key), value in overrides.items():
        field = key if harness == "claude" else f"codex_{key}"
        config[tier][field] = value
    for tier in EXECUTOR_TIERS:
        for field, label in (("model", f"[claude.{tier}] model"), ("codex_model", f"[codex.{tier}] model")):
            if not config[tier][field]:
                raise SystemExit(f"executors.toml: {label} must not be empty (efforts may be empty; models may not)")
    return config


def _patched_agent_md(text: str, model: str, effort: str) -> str:
    """Rewrite only the model:/effort: frontmatter lines of a .claude agent file."""
    if not text.startswith("---\n"):
        raise SystemExit("agent file has no frontmatter")
    end = text.find("\n---\n", 4)
    if end == -1:
        raise SystemExit("agent file frontmatter is unterminated")
    lines = [l for l in text[4:end].split("\n") if not l.startswith("model:") and not l.startswith("effort:")]
    insert_at = next((i for i, l in enumerate(lines) if l.startswith("permissionMode:")), len(lines))
    lines[insert_at:insert_at] = [f"model: {model}"] + ([f"effort: {effort}"] if effort else [])
    return "---\n" + "\n".join(lines) + text[end:]


def _patched_agent_toml(text: str, model: str, effort: str) -> str:
    """Rewrite only the model/model_reasoning_effort keys of a .codex agent file."""
    head, sep, tail = text.partition('developer_instructions = """')
    out = []
    for line in head.split("\n"):
        if line.startswith("model = "):
            out.append(f'model = "{model}"')
            if effort:
                out.append(f'model_reasoning_effort = "{effort}"')
            continue
        if line.startswith("model_reasoning_effort = "):
            continue
        out.append(line)
    return "\n".join(out) + sep + tail


def executor_agent_files(config: dict) -> list:
    """(tier, path, kind, model, effort) for the 4 tier agent files."""
    entries = []
    for tier in EXECUTOR_TIERS:
        cfg = config[tier]
        entries.append((tier, CLAUDE_AGENTS / f"slice-executor-{tier}.md", "md", cfg["model"], cfg["effort"]))
        entries.append((tier, CODEX_AGENTS / f"slice-executor-{tier}.toml", "toml", cfg["codex_model"], cfg["codex_effort"]))
    return entries


def sync_agents(args: argparse.Namespace) -> None:
    config = executor_config()
    config_present = (ROOT / "executors.toml").exists()
    mode, overrides = read_executors_toml()
    override_count = len(overrides)
    legacy_env = ROOT / ".env"
    if legacy_env.exists() and "SLICE_EXECUTOR" in legacy_env.read_text(encoding="utf-8"):
        print("warning: .env holds SLICE_EXECUTOR_* keys, but tier config moved to executors.toml in v8 — .env is no longer read")
    changed, missing = [], []
    for tier, path, kind, model, effort in executor_agent_files(config):
        if not path.exists():
            missing.append(str(path.relative_to(ROOT)))
            continue
        current = path.read_text(encoding="utf-8")
        desired = _patched_agent_md(current, model, effort) if kind == "md" else _patched_agent_toml(current, model, effort)
        if desired != current:
            changed.append(str(path.relative_to(ROOT)))
            if not args.check:
                write_text(path, desired)
    for tier in EXECUTOR_TIERS:
        cfg = config[tier]
        print(f"{tier:<5} claude={cfg['model']} @ {cfg['effort'] or '(no effort line)'}  codex={cfg['codex_model']} @ {cfg['codex_effort']}")
    mode_str = f"mode {mode}" if mode else f"mode {DEFAULT_EXECUTOR_MODE} (default)"
    print(f"config source: {f'executors.toml ({mode_str}, {override_count} override(s))' if config_present else f'{DEFAULT_EXECUTOR_MODE} defaults (no executors.toml)'}")
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


def new_doc_version(args: argparse.Namespace) -> None:
    doc_id = args.doc
    if doc_id not in DOC_TYPES:
        raise SystemExit(f"doc must be one of: {', '.join(sorted(DOC_TYPES))}")
    # Doc versions are allocated from a single `docs/index.json` (`max+1` per doc), so two streams
    # consolidating at once pick the same vNNNN and collide silently on the merge. A parallel phase
    # defers consolidation to the serialized post-merge step on the default stream -- refuse here,
    # before any allocation or write, so a refusal leaves zero partial state.
    stream = current_stream(all_active_phases())
    if stream:
        raise SystemExit(f"this checkout is on parallel stream {stream}; doc consolidation runs on the default stream, after the branch is merged -- defer it to the post-merge step (parallel-merge-finish, then doc-new-version, then parallel-consolidated)")
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
    frontmatter = (
        f"---\n"
        f"doc_id: {doc_id}\n"
        f"version: {version_prefix}\n"
        f"created_at: {now_iso()}\n"
        f"source: {args.source}\n"
        f"summary: {args.summary}\n"
        f"previous: {latest_id}\n"
        f"---\n\n"
    )
    write_text(dest, frontmatter + base_body)
    info["latest"] = version_id
    info["versions"].append({
        "id": version_id, "path": rel, "created_at": now_iso(),
        "source": args.source, "summary": args.summary, "previous": latest_id,
    })
    write_doc_index(index)
    rebuild_docs()
    append_event("doc_version_created", doc=doc_id, version=version_id, source=args.source)
    print(f"created doc version {doc_id}/{version_id}")
    print(f"edit_path={rel}")
    print("after editing, run: python3 scripts/workflow.py rebuild-docs")


def cmd_docs(args: argparse.Namespace) -> None:
    index = doc_index()
    for doc_id in sorted(index["docs"]):
        info = index["docs"][doc_id]
        latest = next(v for v in info["versions"] if v["id"] == info["latest"])
        print(f"{doc_id}: latest={info['latest']} current={info['current_path']} latest_path={latest['path']}")


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


def rebuild_deferred_dashboard(groups=None, rebuilt_at=None) -> None:
    groups = groups or deferred_jobs()
    rebuilt_at = rebuilt_at or now_iso()
    open_count = len(groups.get("open", []))
    promoted_count = len(groups.get("promoted", []))
    dropped_count = len(groups.get("dropped", []))
    lines = [
        "# Deferred Jobs", "", "> Generated dashboard. Do not put detailed deferred context here; edit each `works/deferred/<state>/<DID>/` folder instead.", "",
        "## Summary", "",
        f"- Open: `{open_count}`", f"- Promoted: `{promoted_count}`", f"- Dropped: `{dropped_count}`", f"- Rebuilt at: `{rebuilt_at}`", "",
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
          "mode": "parallel",              # only recognized mode; anything else = default stream
          "branch": "phase/P13-some-slug", # required when parallel; the stream key
          "worktree": "/path or null",     # informational (null on a plain clone)
          "consolidation": "pending"       # "pending" until the post-merge doc consolidation, then "done"
        }

    Read the block only through this helper so every caller agrees on what "parallel" means.
    """
    if not isinstance(data, dict):
        return None
    execution = data.get("execution")
    if not isinstance(execution, dict) or execution.get("mode") not in EXECUTION_MODES:
        return None
    return execution


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

    Default stream (`stream` is None): every phase except the ones opted out to a branch.
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
    rebuild_deferred_dashboard(deferred, rebuilt_at)


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
        f"- Open deferred jobs: `{index.get('deferred_open_count', 0)}`",
        f"- Rebuilt at: `{index.get('last_rebuilt_at')}`", "",
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
        # Optional parallel-execution block. Absent = default stream = nothing to check.
        # A phase that merged `done` while its doc consolidation is still pending
        # (`consolidation: "pending"`) is a legitimate state and passes cleanly here.
        if "execution" in p:
            execution = p.get("execution")
            if not isinstance(execution, dict):
                errors.append(f"phase {p['id']} has a non-object execution block: {execution!r}")
            else:
                mode = execution.get("mode")
                if mode not in EXECUTION_MODES:
                    errors.append(f"phase {p['id']} has invalid execution.mode {mode!r}; expected one of {sorted(EXECUTION_MODES)}")
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
        if not (ACTIVE / p["id"] / "intent.md").exists():
            warnings.append(f"phase {p['id']} has no intent.md (expected {p['id']}/intent.md); capture operator intent via the create-phase skill")
        for s in p["slices"]:
            if s["id"] in seen_slices:
                errors.append(f"duplicate slice id: {s['id']}")
            seen_slices.add(s["id"])
            if s["phase_id"] != p["id"]:
                errors.append(f"slice phase mismatch: {s['id']} says {s['phase_id']}, folder phase is {p['id']}")
            if s["status"] not in SLICE_STATUSES:
                errors.append(f"invalid slice status {s['id']}: {s['status']}")
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
                errors.append(f"missing deferred.json: {ddir.relative_to(ROOT)}")
                continue
            data = read_json(djson)
            if data.get("status") not in DEFERRED_STATUSES:
                errors.append(f"invalid deferred status {data.get('id')}: {data.get('status')}")
            if data.get("status") not in allowed:
                errors.append(f"deferred job in wrong folder: {data.get('id')} status {data.get('status')} under {base.relative_to(ROOT)}")
    # Executor-tier drift is advisory only: warn (never error, never crash) when the agent
    # files disagree with executors.toml/defaults, so a foreign or partial workspace still validates.
    try:
        for tier, path, kind, model, effort in executor_agent_files(executor_config()):
            if not path.exists():
                warnings.append(f"missing executor agent file: {path.relative_to(ROOT)} (run: python3 scripts/workflow.py sync-agents)")
                continue
            current = path.read_text(encoding="utf-8")
            desired = _patched_agent_md(current, model, effort) if kind == "md" else _patched_agent_toml(current, model, effort)
            if desired != current:
                warnings.append(f"executor agent file out of sync with executors.toml/defaults: {path.relative_to(ROOT)} (run: python3 scripts/workflow.py sync-agents)")
    except (SystemExit, Exception) as exc:  # noqa: BLE001 - advisory check must not fail validate
        warnings.append(f"executor tier config check failed: {exc}")
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


def create_slice(phase_id: str, slice_id: str, name: str, kind: str, order, risk: str, source: dict, depends_on=None) -> Path:
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
        "validation": {"required": [], "last_run": None, "last_status": "pending"},
        "archive": {"archived": False, "archived_at": None, "archive_path": None},
    }
    write_json(sdir / "slice.json", data)
    # Neither context file is scaffolded: the orchestrator writes its free-form native
    # plan to plan.md at the slice's turn, and the executor writes its free-form
    # result.md at slice end — a fresh slice folder holds only slice.json.
    return sdir


def new_phase(args: argparse.Namespace) -> None:
    phase_id = args.phase
    if not re.fullmatch(r"P[0-9]+", phase_id):
        raise SystemExit("phase must look like P1, P2, P3")
    pdir = ACTIVE / phase_id
    if pdir.exists():
        raise SystemExit(f"phase already exists: {phase_id}")
    order = _clean_order(args.order) if args.order is not None else max([read_json(p / "phase.json").get("order", 0) for p in phase_dirs()], default=0) + 1
    phase_data = {
        "id": phase_id, "name": args.name, "objective": args.objective, "status": "planned", "order": order,
        "created_at": now_iso(), "started_at": None, "completed_at": None,
        "review": {"status": "pending", "reviewed_at": None, "reviewer": None, "note": None},
        "paths": {"phase_md": "phase.md", "intent_md": "intent.md", "slices_dir": "slices"},
        "archive": {"archived": False, "archived_at": None, "archive_path": None},
    }
    write_json(pdir / "phase.json", phase_data)
    write_text(pdir / "phase.md", f"# Phase {phase_id}: {args.name}\n\n_Intent: see [intent.md](intent.md)._\n\n## Objective\n\n{args.objective}\n\n## Context\n\n## Decomposition\n\n_Slice breakdown and rationale — filled by the `{phase_id}.DECOMP` slice._\n\n## Findings & Notes\n\n_Durable findings and cross-slice notes; `DECOMP` seeds this, and each slice appends when it finishes._\n\n## Constraints\n\n## Open Questions\n\n-\n")
    write_text(pdir / "intent.md", render_template(load_template("intent.md"), PHASE_ID=phase_id, CAPTURED_AT=now_iso(), ORIGIN="operator"))
    create_slice(phase_id, f"{phase_id}.DECOMP", "decompose phase", "decomposition", 0, "high", source={"type": "new_phase", "id": phase_id})
    create_slice(phase_id, f"{phase_id}.REVIEW", "phase review", "review", 9999, "high", source={"type": "new_phase", "id": phase_id})
    append_event("phase_created", phase=phase_id)
    rebuild_index_and_state()
    print(f"created phase {phase_id}: {pdir.relative_to(ROOT)}")
    # Proactive opt-in suggestion: a phase created while another one is mid-flight is the
    # first of the two moments parallel mode becomes relevant. Suggestion only, never a default.
    busy = next((p for p in all_active_phases() if p["id"] != phase_id and p.get("status") == "in_progress" and phase_execution(p) is None), None)
    if busy:
        print(f"hint: {busy['id']} is in progress -- this phase can run in parallel on its own branch: python3 scripts/workflow.py parallel-start {phase_id}")


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
    print(f"created slice {args.slice}: {sdir.relative_to(ROOT)}")


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
    set_slice_status(args.slice, "done")
    print(f"finished {args.slice}")


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


def review_phase(args: argparse.Namespace) -> None:
    if args.verdict not in REVIEW_VERDICTS:
        raise SystemExit(f"verdict must be one of: {', '.join(sorted(REVIEW_VERDICTS))}")
    pdir = require_phase(args.phase)
    data = read_json(pdir / "phase.json")
    data["review"] = {"status": args.verdict, "reviewed_at": now_iso(), "reviewer": args.reviewer, "note": args.note}
    # Verdict drives phase status so the lifecycle stays consistent.
    status_map = {"pass": "done", "changes_requested": "in_progress", "blocked": "blocked"}
    new_status = status_map[args.verdict]
    if new_status == "done":
        data["completed_at"] = now_iso()
    data["status"] = new_status
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
        print("create fix slices, e.g.: python3 scripts/workflow.py new-slice --phase {0} --slice {0}.F1 --name \"...\" --kind fix".format(args.phase))
    elif args.verdict == "pass":
        print(f"phase {args.phase} is done and stays in active/. Do NOT archive a single phase now.")
        print("Archive all phases together with `archive-all` only once every active phase is done (the last review slice is complete).")


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


def _git_available() -> bool:
    """True when this workspace sits inside a usable git work tree. Never raises: a
    workspace without git (or outside a repo) must keep working exactly as before."""
    try:
        proc = subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], cwd=str(ROOT), capture_output=True, text=True)
    except Exception:  # noqa: BLE001 - git is optional
        return False
    return proc.returncode == 0 and proc.stdout.strip() == "true"


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
    """Opt a planned phase into parallel execution: stamp it, commit the stamp, cut branch + worktree.

    This is the single place the engine makes a git commit, and it is deliberate. The stamp must
    exist on BOTH the default branch (so this stream's pointer skips the phase) and the phase
    branch (so the worktree session claims the stream), and the branch has to be cut from a commit
    that already contains it. One fixed-message commit, made only after a clean-tree guard so it
    can contain nothing but the stamp plus the regenerated dashboards, achieves that by
    construction; stamping and asking the operator to commit cannot.
    """
    pdir = require_phase(args.phase)
    data = read_json(pdir / "phase.json")
    if data.get("status") != "planned":
        raise SystemExit(f"phase {args.phase} is {data.get('status')!r}; opt in before it starts (parallel-start needs status 'planned')")
    if data.get("execution") is not None:
        raise SystemExit(f"phase {args.phase} already carries an execution block: {json.dumps(data['execution'], ensure_ascii=False)}")
    _require_git_repo()
    phases = all_active_phases()
    stream = current_stream(phases)
    if stream:
        raise SystemExit(f"this checkout is on parallel stream {stream}; run parallel-start from the default stream")
    if _git(["status", "--porcelain"]).stdout.strip():
        raise SystemExit("working tree is not clean; commit or stash first -- parallel-start makes one commit and it must contain only the opt-in stamp")
    branch = _phase_branch(args.phase, data.get("name") or args.phase, args.slug)
    if _branch_exists(branch):
        raise SystemExit(f"branch already exists: {branch} (pass --slug to pick another name)")
    for p in phases:
        execution = phase_execution(p)
        if execution and execution.get("branch") == branch:
            raise SystemExit(f"branch {branch} is already stamped on phase {p['id']}")
    default_worktree = ROOT.parent / f"{ROOT.name}-{args.phase}"
    worktree = Path(os.path.abspath(str(Path(args.worktree).expanduser()))) if args.worktree else default_worktree
    if worktree.exists():
        raise SystemExit(f"worktree path already exists: {worktree} (pass --worktree to pick another path)")
    if not worktree.parent.exists():
        raise SystemExit(f"worktree parent directory does not exist: {worktree.parent}")

    data["execution"] = {"mode": "parallel", "branch": branch, "worktree": str(worktree), "consolidation": "pending"}
    write_json(pdir / "phase.json", data)
    append_event("phase_parallel_started", phase=args.phase, branch=branch, worktree=str(worktree))
    rebuild_index_and_state()
    _git(["add", "--", str(pdir.relative_to(ROOT)), "works/state.json", "works/index.json", "works/backlog.md", "works/deferred.md", "works/events.jsonl"])
    _git(["commit", "-m", f"chore(works): opt {args.phase} into parallel execution"])
    proc = _git(["worktree", "add", "-b", branch, str(worktree), "HEAD"], check=False)
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).strip() or f"exit {proc.returncode}"
        raise SystemExit(
            f"git worktree add failed: {detail}\n"
            f"the opt-in stamp for {args.phase} is already committed on this branch; fix the cause and finish by hand: "
            f"git worktree add -b {branch} {worktree} HEAD")
    print(f"phase {args.phase} opted into parallel execution")
    print(f"branch={branch}")
    print(f"worktree={worktree}")
    print(f"stamp committed here: chore(works): opt {args.phase} into parallel execution (present on both this branch and {branch})")
    print(f"next: open a session in {worktree} and run /do-whole-phase there -- the phase runs entirely from that checkout")
    print(f"this stream's pointer now skips {args.phase}; after the branch is merged back, run: python3 scripts/workflow.py parallel-teardown {args.phase}")


def parallel_teardown(args: argparse.Namespace) -> None:
    """Retire a merged parallel phase's worktree and branch, from the default stream.

    Refuses while the branch is unmerged (merging is a separate step). Keeps `mode`/`branch`/
    `consolidation` as history and only nulls `worktree`, which is informational anyway.
    """
    pdir = require_phase(args.phase)
    data = read_json(pdir / "phase.json")
    execution = phase_execution(data)
    if not execution:
        raise SystemExit(f"phase {args.phase} is not opted into parallel execution (no parallel execution block)")
    branch = execution.get("branch")
    if not branch:
        raise SystemExit(f"phase {args.phase} has a parallel execution block with no branch; fix phase.json first")
    _require_git_repo()
    if git_current_branch() == branch:
        raise SystemExit(f"this checkout is on {branch}; run parallel-teardown from the default stream (a worktree cannot remove itself)")
    branch_exists = _branch_exists(branch)
    if branch_exists and _git(["merge-base", "--is-ancestor", branch, "HEAD"], check=False).returncode != 0:
        raise SystemExit(f"branch {branch} is not merged into HEAD; merge it first, then run: python3 scripts/workflow.py parallel-teardown {args.phase}")
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
    print(f"execution.worktree=null; mode/branch/consolidation kept as history (branch={branch}, consolidation={execution.get('consolidation')})")
    if execution.get("consolidation") == "pending":
        print(f"warning: {args.phase} doc consolidation is still 'pending' -- run the post-merge consolidation on this stream (teardown does not gate on it)")
    print("phase.json changed -- commit it with the rest of the merge cleanup")


def parallel_gate(args: argparse.Namespace) -> None:
    """The quiet-point gate: may this parallel phase's branch be merged into the default stream now?

    Two independent questions, both read at a git ref so no checkout has to be switched:

    * **branch side** -- the phase is `done` with a `pass` review *on its own branch*. Main's copy
      is stale before the merge, so it is never trusted here.
    * **main side** -- the default stream is quiet: every non-parallel active phase is `planned` or
      `done`. Merging into a live phase is what this gate exists to prevent.

    Read-only and CI-shaped: `GATE OPEN` + exit 0, or `GATE CLOSED` + numbered reasons + exit 1.
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
        # Without --main-ref the working tree stands in for main. Refuse when it is the phase
        # branch itself -- either checked out by name (its worktree) or checked out detached at
        # its tip (how CI checks out a PR). Sharing a tip with main is normal right after
        # opt-in and does NOT count.
        current = git_current_branch()
        on_phase_branch = current is not None and current in {(execution or {}).get("branch"), branch_ref}
        detached_at_tip = current is None and _git(["rev-parse", "HEAD"], check=False).stdout.strip() == _git(["rev-parse", branch_ref], check=False).stdout.strip() != ""
        if on_phase_branch or detached_at_tip:
            raise SystemExit(
                f"this checkout is the phase branch {branch_ref} itself, so the working tree cannot stand in for the default stream; "
                f"pass --main-ref <ref> (e.g. --main-ref origin/main) to say where the default stream's state is read from")
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
        if p.get("id") != args.phase and other and other.get("consolidation") == "pending" and p.get("status") == "done":
            notes.append(f"phase {p.get('id')} is merged but not consolidated yet; consolidation is serialized, so finish it first (parallel-consolidated {p.get('id')})")
    for n in notes:
        print(f"note: {n}")

    if reasons:
        print("GATE CLOSED")
        for i, reason in enumerate(reasons, 1):
            print(f"{i}. {reason}")
        raise SystemExit(1)
    print("GATE OPEN")
    print(f"next: merge {branch_ref} into the default stream, then run: python3 scripts/workflow.py parallel-merge-finish")


def parallel_merge_finish(args: argparse.Namespace) -> None:
    """Run on the default stream right after a phase branch's merge: regenerate, then report what is left.

    The generated files (`works/state.json`, `works/index.json`, `works/backlog.md`,
    `works/deferred.md`, `docs/current/*.md`) are derived, never authored, so a merge conflict in
    them is resolved by taking either side and regenerating here -- which is why parallel mode
    needs no custom git merge driver (a driver would need per-clone `git config` and would not
    travel with the repo). Makes no commit: the regenerated files belong to the merge commit's
    cleanup, which the orchestrator owns.
    """
    git_ok = _git_available()
    if git_ok and _git(["rev-parse", "-q", "--verify", "MERGE_HEAD"], check=False).returncode == 0:
        raise SystemExit(
            "this checkout is mid-merge (MERGE_HEAD exists) -- finish the merge first, then re-run.\n"
            f"generated files ({', '.join(GENERATED_FILES)}) are regenerated by this command, so resolve any conflict in them by taking EITHER side.\n"
            "then: python3 scripts/workflow.py parallel-merge-finish")
    phases = all_active_phases()
    stream = current_stream(phases)
    if stream:
        print(f"warning: this checkout is on parallel stream {stream}; parallel-merge-finish belongs on the default stream, after the merge")
    rebuild_docs()
    rebuild_index_and_state()
    print(f"regenerated from the merged folders: {', '.join(GENERATED_FILES)}")
    awaiting = []
    for p in all_active_phases():
        execution = phase_execution(p)
        if not execution or execution.get("consolidation") != "pending" or p.get("status") != "done":
            continue
        branch = execution.get("branch")
        merged = True  # a deleted branch means the phase was already merged and torn down
        if git_ok and branch and _branch_exists(branch):
            merged = _git(["merge-base", "--is-ancestor", branch, "HEAD"], check=False).returncode == 0
        if merged:
            awaiting.append((p, execution))
    if not awaiting:
        print("nothing awaiting doc consolidation")
    else:
        print(f"{len(awaiting)} merged phase(s) await doc consolidation -- do them ONE AT A TIME, on this stream (doc versions are allocated from a single index):")
        for p, execution in awaiting:
            print(f"- {p['id']}: doc impact notes in {p['path']}/phase.md (section '## Doc Impact')")
            print(f"    per note: python3 scripts/workflow.py doc-new-version --doc <doc> --summary \"...\" --source {p['id']}.REVIEW -> edit the returned edit_path -> python3 scripts/workflow.py rebuild-docs")
            print(f"    when that phase's notes are all consolidated: python3 scripts/workflow.py parallel-consolidated {p['id']}")
            if execution.get("worktree") or (git_ok and execution.get("branch") and _branch_exists(execution["branch"])):
                print(f"    then retire its branch + worktree: python3 scripts/workflow.py parallel-teardown {p['id']}")
    print("no commit made -- commit the regenerated files with the merge cleanup")


def parallel_consolidated(args: argparse.Namespace) -> None:
    """Record that a merged parallel phase's deferred doc consolidation is finished.

    The engine cannot write the prose: an agent runs `doc-new-version` per "Doc Impact" note on the
    default stream and then calls this to flip `execution.consolidation` to "done", which is also
    what unblocks archiving the phase.
    """
    pdir = require_phase(args.phase)
    data = read_json(pdir / "phase.json")
    execution = phase_execution(data)
    if not execution:
        raise SystemExit(f"phase {args.phase} is not opted into parallel execution (no parallel execution block); default-stream phases consolidate docs in their own REVIEW slice")
    stream = current_stream(all_active_phases())
    if stream:
        raise SystemExit(f"this checkout is on parallel stream {stream}; run parallel-consolidated on the default stream, after the branch is merged")
    if data.get("status") != "done":
        raise SystemExit(f"phase {args.phase} is {data.get('status')!r}, not 'done'; consolidation happens after its review passes and the branch is merged")
    review_status = data.get("review", {}).get("status")
    if review_status != "pass":
        raise SystemExit(f"phase {args.phase} review is {review_status!r}, not 'pass'; record the passing review before consolidating")
    consolidation = execution.get("consolidation")
    if consolidation == "done":
        raise SystemExit(f"phase {args.phase} is already marked consolidated (execution.consolidation='done')")
    if consolidation != "pending":
        raise SystemExit(f"phase {args.phase} has execution.consolidation {consolidation!r}; expected 'pending' (set at opt-in by parallel-start)")
    data["execution"]["consolidation"] = "done"
    write_json(pdir / "phase.json", data)
    append_event("phase_consolidated", phase=args.phase, branch=execution.get("branch"))
    rebuild_index_and_state()
    print(f"phase {args.phase} docs consolidated (execution.consolidation=done)")
    print("phase.json changed -- commit it together with the new doc versions")
    branch = execution.get("branch")
    if execution.get("worktree") or (branch and _git_available() and _branch_exists(branch)):
        print(f"next: python3 scripts/workflow.py parallel-teardown {args.phase}")
    print(f"{args.phase} is now archivable (archive-phase/rotate-backlog no longer block on pending consolidation)")


def _parallel_verdict(phase_id: str, status, review, slices, consolidation, merged, branch_gone: bool, own_stream: bool) -> str:
    """One line saying where a parallel phase stands, and what the operator does next.

    `merged` is None when the answer is unknown (this checkout is the phase's own stream, so it
    trivially contains its own branch); `branch_gone` means the branch was deleted, which implies
    the phase was merged first -- `parallel-teardown` refuses an unmerged branch.
    """
    if status is None:
        return "unknown -- neither the phase branch nor a local copy could be read"
    slices = slices or []
    total = len(slices)
    done = sum(1 for s in slices if s.get("status") == "done")
    open_slice = next((s.get("id") for s in slices if s.get("status") != "done"), None)
    integrated = merged is True or branch_gone
    if status == "done" and review == "pass":
        if consolidation == "pending":
            if integrated:
                return (f"merged, docs still awaiting consolidation -- run on the default stream: "
                        f"parallel-merge-finish, then parallel-consolidated {phase_id}")
            return f"ready to merge -- check the quiet point first: parallel-gate {phase_id} (from the default stream)"
        if integrated:
            if not branch_gone:
                return f"merged + consolidated -- retire the branch and worktree: parallel-teardown {phase_id}"
            return f"merged, consolidated and torn down -- nothing left but archiving ({phase_id} is archivable)"
        return f"ready to merge -- check the quiet point first: parallel-gate {phase_id} (from the default stream)"
    if status == "done":
        return f"slices done but review is {review!r} -- record a passing review on its branch (review-phase {phase_id} --verdict pass)"
    if status == "pending":
        return "waiting on the operator (phase is pending [~]) -- it halts only its own stream"
    if status == "blocked":
        return "blocked on its own stream -- resolve the impediment there"
    where = " on this checkout's own stream" if own_stream else " on its branch"
    tail = f"; current slice {open_slice}" if open_slice else ""
    return f"in flight{where} -- {done}/{total} slices done{tail}"


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

    parallel = [(p, phase_execution(p)) for p in phases if phase_execution(p)]
    if not parallel:
        print("no parallel phases -- every active phase runs on the default stream")
        print("opt one in with: python3 scripts/workflow.py parallel-start <P>")
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
        print(f"  consolidation={execution.get('consolidation') or '-'}")
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
        print(f"  verdict: {_parallel_verdict(pid, status, review, slices, execution.get('consolidation'), merged, branch_gone, own_stream)}")


def parallel_start_hint(state: dict, index: dict) -> str:
    """The proactive opt-in suggestion for `next`, or None.

    Fires only on the default stream when the current phase is in_progress and a later
    default-stream phase is still `planned` -- i.e. exactly when the operator is about to
    start a second phase behind a live one. Suggestion only, never a default.
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
            f"python3 scripts/workflow.py parallel-start {waiting['id']}")


def cmd_next(args: argparse.Namespace) -> None:
    rebuild_index_and_state()
    state = read_json(WORKS / "state.json")
    # Stream context. Both lines are silent on the default stream with no parallel
    # phases, so an untouched workspace sees exactly the output it saw before.
    stream = state.get("stream")
    if stream:
        print(f"stream={stream} (parallel phase checkout; the pointer below is scoped to this phase)")
    index = read_json(WORKS / "index.json")
    elsewhere = [
        f"{p['id']}:{p['execution'].get('branch')}"
        for p in index.get("active_phases", [])
        if p.get("execution") and p["execution"].get("branch") != stream
    ]
    if elsewhere:
        print(f"parallel_phases_elsewhere={', '.join(elsewhere)} (not in this stream; each runs from its own branch)")
    waiting = state.get("waiting_on_operator")
    if waiting:
        kind = "slice" if "." in waiting else "phase"
        clear = f"set-slice-status {waiting} in_progress" if kind == "slice" else f"set-phase-status {waiting} in_progress"
        print(f"current_phase={state.get('current_phase')}")
        print(f"waiting_on_operator={waiting}")
        print(f"WAITING ON OPERATOR: {kind} {waiting} is pending [~] -- operator co-work needed (validation or an operator-run action).")
        print("Do not start, finish, or advance past it. Report what you need, then wait for the operator.")
        print(f"After the operator approves, clear it: python3 scripts/workflow.py {clear}")
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
    print(f"slice_path={sdir.relative_to(ROOT)}")
    print(f"next_slice={state.get('next_slice') or 'none'}")
    hint = parallel_start_hint(state, index)
    if hint:
        print(hint)


def cmd_deferred(args: argparse.Namespace) -> None:
    rebuild_index_and_state()
    groups = deferred_jobs()
    print(f"open={len(groups.get('open', []))}")
    print(f"promoted={len(groups.get('promoted', []))}")
    print(f"dropped={len(groups.get('dropped', []))}")
    print("dashboard=works/deferred.md")


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
    print(f"created deferred job {did}: {ddir.relative_to(ROOT)}")


def promote_deferred(args: argparse.Namespace) -> None:
    did = args.deferred_id
    ddir = DEFERRED_OPEN / did
    if not (ddir / "deferred.json").exists():
        raise SystemExit(f"open deferred job not found: {did}")
    data = read_json(ddir / "deferred.json")
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
        raise SystemExit(f"promoted destination already exists: {target.relative_to(ROOT)}")
    shutil.move(str(ddir), str(target))
    append_event("deferred_promoted", deferred=did, phase=args.phase, slice=args.slice)
    rebuild_index_and_state()
    print(f"promoted {did} -> {args.slice}: {sdir.relative_to(ROOT)}")


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
        raise SystemExit(f"dropped destination already exists: {target.relative_to(ROOT)}")
    shutil.move(str(ddir), str(target))
    append_event("deferred_dropped", deferred=did, reason=args.reason)
    rebuild_index_and_state()
    print(f"dropped {did}: {target.relative_to(ROOT)}")


def _phase_blockers(pdir: Path) -> list:
    """Reasons a phase is not cleanly archivable; empty list means ready."""
    phase = read_json(pdir / "phase.json")
    slices = [read_json(s / "slice.json") for s in slice_dirs(pdir)]
    reasons = []
    not_done = [s["id"] for s in slices if s.get("status") != "done"]
    if not_done:
        reasons.append(f"unfinished slices: {', '.join(not_done)}")
    review_status = phase.get("review", {}).get("status")
    if review_status != "pass":
        reasons.append(f"review is {review_status!r}, not pass")
    # A merged parallel phase still owes the default stream its deferred doc consolidation.
    # Teardown only warns about this (it is reversible); archiving is not, so it blocks.
    execution = phase_execution(phase)
    if execution and execution.get("consolidation") == "pending":
        reasons.append(f"docs not consolidated -- run the post-merge consolidation, then: python3 scripts/workflow.py parallel-consolidated {phase['id']}")
    return reasons


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
    print(f"archived phase {args.phase}: {dest.relative_to(ROOT)}")


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
        print(f"- {phase_id}: {dest.relative_to(ROOT)}")


def rotate_backlog(args: argparse.Namespace) -> None:
    # Partial rotation: archive every phase that is cleanly archivable right now
    # (all slices done with a passing review) and leave the rest active, then
    # rebuild the dashboards. This is the partial sweep archive-all cannot do,
    # since archive-all refuses unless EVERY active phase is done.
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
        print(f"- {phase_id}: {dest.relative_to(ROOT)}")
    if blocked:
        print(f"left {len(blocked)} phase(s) active: {', '.join(p for p, _ in blocked)}")


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

    p = sub.add_parser("sync-agents", help="Apply the repo-root executors.toml executor-tier config (models/efforts) to the slice-executor agent files")
    p.add_argument("--check", action="store_true", help="Report drift without writing; exit 1 if out of sync")
    p.set_defaults(func=sync_agents)

    p = sub.add_parser("next", help="Print the current phase/slice selection")
    p.set_defaults(func=cmd_next)

    p = sub.add_parser("deferred", help="Rebuild and print deferred jobs dashboard summary")
    p.set_defaults(func=cmd_deferred)

    p = sub.add_parser("new-phase", help="Create a new phase with DECOMP and REVIEW slices")
    p.add_argument("--phase", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--objective", required=True)
    p.add_argument("--order", type=float)
    p.set_defaults(func=new_phase)

    p = sub.add_parser("new-slice", help="Create a new slice folder with slice.json + markdown files")
    p.add_argument("--phase", required=True)
    p.add_argument("--slice", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--kind", default="implementation")
    p.add_argument("--risk", default="high", help="low (a one-line code edit or docs -> slice-executor-mid) or high (everything else -> slice-executor-high); unrecognized values route to high")
    p.add_argument("--order", type=float)
    p.add_argument("--depends-on", action="append")
    p.set_defaults(func=new_slice)

    p = sub.add_parser("start-slice", help="Mark a slice in_progress")
    p.add_argument("slice")
    p.set_defaults(func=start_slice)

    p = sub.add_parser("finish-slice", help="Mark a slice done")
    p.add_argument("slice")
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

    p = sub.add_parser("parallel-start", help="Opt a planned phase into parallel execution: stamp it, commit the stamp, and cut its phase branch + git worktree")
    p.add_argument("phase")
    p.add_argument("--worktree", default=None, help="worktree path (default: a sibling of the repo root, ../<repo>-<phase>)")
    p.add_argument("--slug", default=None, help="branch slug override (default: slugified phase name); branch is phase/<phase>-<slug>")
    p.set_defaults(func=parallel_start)

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
    p.set_defaults(func=parallel_teardown)

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
    p.add_argument("--kind", default="implementation")
    p.add_argument("--risk", default="high", help="low (a one-line code edit or docs -> slice-executor-mid) or high (everything else -> slice-executor-high); unrecognized values route to high")
    p.add_argument("--order", type=float)
    p.add_argument("--depends-on", action="append")
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

    p = sub.add_parser("rotate-backlog", help="Archive every currently-done phase and leave in-progress phases active, then rebuild (partial archive-all)")
    p.set_defaults(func=rotate_backlog)

    args = parser.parse_args(argv)
    result = args.func(args)
    if isinstance(result, tuple):
        return 0
    return 0 if result is None else int(result or 0)


if __name__ == "__main__":
    raise SystemExit(main())
