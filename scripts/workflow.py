#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import stat
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
PHASE_STATUSES = {"planned", "in_progress", "in_review", "blocked", "done"}
SLICE_STATUSES = {"todo", "in_progress", "in_review", "changes_requested", "blocked", "done"}
DEFERRED_STATUSES = {"deferred", "ready", "promoted", "done", "dropped"}
REVIEW_VERDICTS = {"pass", "changes_requested", "blocked"}


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


def resolve_current(phases: list) -> tuple:
    for phase in phases:
        if phase.get("status") == "done":
            continue
        current_phase = phase["id"]
        if phase.get("status") == "blocked":
            return current_phase, None, None
        open_slices = [s for s in phase["slices"] if s.get("status") != "done"]
        if open_slices:
            return current_phase, open_slices[0]["id"], open_slices[1]["id"] if len(open_slices) > 1 else None
        return current_phase, None, None
    return None, None, None


def rebuild_index_and_state() -> None:
    phases = all_active_phases()
    current_phase, current_slice, next_slice = resolve_current(phases)
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
            } for p in phases
        ],
        "deferred_open_count": len(deferred.get("open", [])),
        "deferred_promoted_count": len(deferred.get("promoted", [])),
        "deferred_dropped_count": len(deferred.get("dropped", [])),
        "last_rebuilt_at": rebuilt_at,
    }
    write_json(WORKS / "index.json", index)
    state = {"current_phase": current_phase, "current_slice": current_slice, "next_slice": next_slice, "mode": "phase" if current_phase else "idle", "updated_at": rebuilt_at}
    write_json(WORKS / "state.json", state)
    rebuild_backlog(phases, state, index)
    rebuild_deferred_dashboard(deferred, rebuilt_at)


def rebuild_backlog(phases: list, state: dict, index: dict) -> None:
    lines = [
        "# Backlog", "", "> Generated dashboard. Do not put detailed task context here; edit phase/slice/deferred folders instead.", "",
        "## Pointer", "",
        f"- Current phase: `{state.get('current_phase') or 'none'}`",
        f"- Current slice: `{state.get('current_slice') or 'none'}`",
        f"- Next slice: `{state.get('next_slice') or 'none'}`",
        f"- Open deferred jobs: `{index.get('deferred_open_count', 0)}`",
        f"- Rebuilt at: `{index.get('last_rebuilt_at')}`", "",
        "## Active Phases", "", "| Phase | Status | Review | Objective | Current Slice | Path |", "|---|---|---|---|---|---|",
    ]
    if not phases:
        lines.append("| - | - | - | - | - | - |")
    for p in phases:
        current = next((s["id"] for s in p["slices"] if s.get("status") != "done"), "none")
        objective = clean_cell(p.get("objective", ""))
        review = clean_cell(p.get("review", {}).get("status"))
        lines.append(f"| `{p['id']}` | `{p['status']}` | `{review}` | {objective} | `{current}` | `{p['path']}` |")
    for p in phases:
        lines.extend(["", f"## Phase {p['id']}: {p['name']}", "", "| Slice | Status | Name | Kind | Path |", "|---|---|---|---|---|"])
        for s in p["slices"]:
            checkbox = "x" if s.get("status") == "done" else " "
            name = clean_cell(s.get("name", ""))
            lines.append(f"| [{checkbox}] `{s['id']}` | `{s['status']}` | {name} | `{clean_cell(s.get('kind', ''))}` | `{s['path']}` |")
    lines.append("")
    write_text(WORKS / "backlog.md", "\n".join(lines))


def validate() -> int:
    errors: list = []
    phases = all_active_phases()
    seen_phases, seen_slices = set(), set()
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
        for s in p["slices"]:
            if s["id"] in seen_slices:
                errors.append(f"duplicate slice id: {s['id']}")
            seen_slices.add(s["id"])
            if s["phase_id"] != p["id"]:
                errors.append(f"slice phase mismatch: {s['id']} says {s['phase_id']}, folder phase is {p['id']}")
            if s["status"] not in SLICE_STATUSES:
                errors.append(f"invalid slice status {s['id']}: {s['status']}")
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
    validate_docs(errors)
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


def create_slice(phase_id: str, slice_id: str, name: str, kind: str, order: int, risk: str, source: dict, depends_on=None) -> Path:
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
    common = {"PHASE_ID": phase_id, "SLICE_ID": slice_id, "SLICE_NAME": name, "CREATED_AT": created}
    for name_in in ("plan.md", "result.md"):
        write_text(sdir / name_in, render_template(load_template(name_in), **common))
    return sdir


def new_phase(args: argparse.Namespace) -> None:
    phase_id = args.phase
    if not re.fullmatch(r"P[0-9]+", phase_id):
        raise SystemExit("phase must look like P1, P2, P3")
    pdir = ACTIVE / phase_id
    if pdir.exists():
        raise SystemExit(f"phase already exists: {phase_id}")
    order = args.order if args.order is not None else max([read_json(p / "phase.json").get("order", 0) for p in phase_dirs()], default=0) + 1
    phase_data = {
        "id": phase_id, "name": args.name, "objective": args.objective, "status": "planned", "order": order,
        "created_at": now_iso(), "started_at": None, "completed_at": None,
        "review": {"status": "pending", "reviewed_at": None, "reviewer": None, "note": None},
        "paths": {"phase_md": "phase.md", "slices_dir": "slices"},
        "archive": {"archived": False, "archived_at": None, "archive_path": None},
    }
    write_json(pdir / "phase.json", phase_data)
    write_text(pdir / "phase.md", f"# Phase {phase_id}: {args.name}\n\n## Objective\n\n{args.objective}\n\n## Context\n\n## Decomposition\n\n_Slice breakdown and rationale — filled by the `{phase_id}.DECOMP` slice._\n\n## Findings & Notes\n\n_Durable findings and cross-slice notes; `DECOMP` seeds this, and each slice appends when it finishes._\n\n## Constraints\n\n## Open Questions\n\n-\n")
    create_slice(phase_id, f"{phase_id}.DECOMP", "decompose phase", "decomposition", 0, "low", source={"type": "new_phase", "id": phase_id})
    create_slice(phase_id, f"{phase_id}.REVIEW", "phase review", "review", 9999, "medium", source={"type": "new_phase", "id": phase_id})
    append_event("phase_created", phase=phase_id)
    rebuild_index_and_state()
    print(f"created phase {phase_id}: {pdir.relative_to(ROOT)}")


def _auto_order(pdir: Path, explicit) -> int:
    if explicit is not None:
        return explicit
    orders = [read_json(s / "slice.json").get("order", 0) for s in slice_dirs(pdir) if read_json(s / "slice.json").get("kind") != "review"]
    return max(orders, default=0) + 10


def new_slice(args: argparse.Namespace) -> None:
    pdir = require_phase(args.phase)
    order = _auto_order(pdir, args.order)
    sdir = create_slice(args.phase, args.slice, args.name, args.kind, order, args.risk, source={"type": "manual", "id": None}, depends_on=args.depends_on or [])
    append_event("slice_created", phase=args.phase, slice=args.slice)
    rebuild_index_and_state()
    print(f"created slice {args.slice}: {sdir.relative_to(ROOT)}")


def set_slice_status(slice_id: str, status: str) -> None:
    if status not in SLICE_STATUSES:
        raise SystemExit(f"invalid slice status: {status}")
    sdir = require_slice(slice_id)
    data = read_json(sdir / "slice.json")
    old = data.get("status")
    data["status"] = status
    if status == "in_progress" and not data.get("started_at"):
        data["started_at"] = now_iso()
    if status == "done":
        data["completed_at"] = now_iso()
    write_json(sdir / "slice.json", data)
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
    append_event("phase_reviewed", phase=args.phase, verdict=args.verdict, reviewer=args.reviewer)
    rebuild_index_and_state()
    print(f"phase {args.phase} review: {args.verdict} (status -> {new_status})")
    if args.verdict == "changes_requested":
        print("create fix slices, e.g.: python3 scripts/workflow.py new-slice --phase {0} --slice {0}.F1 --name \"...\" --kind fix".format(args.phase))
    elif args.verdict == "pass":
        print(f"phase {args.phase} is done and stays in active/. Do NOT archive a single phase now.")
        print("Archive all phases together with `archive-all` only once every active phase is done (the last review slice is complete).")


def cmd_next(args: argparse.Namespace) -> None:
    rebuild_index_and_state()
    state = read_json(WORKS / "state.json")
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
    with (sdir / "plan.md").open("a", encoding="utf-8") as f:
        f.write("\n---\n\n## Promoted Deferred Context\n\n")
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

    p = sub.add_parser("next", help="Print the current phase/slice selection")
    p.set_defaults(func=cmd_next)

    p = sub.add_parser("deferred", help="Rebuild and print deferred jobs dashboard summary")
    p.set_defaults(func=cmd_deferred)

    p = sub.add_parser("new-phase", help="Create a new phase with DECOMP and REVIEW slices")
    p.add_argument("--phase", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--objective", required=True)
    p.add_argument("--order", type=int)
    p.set_defaults(func=new_phase)

    p = sub.add_parser("new-slice", help="Create a new slice folder with slice.json + markdown files")
    p.add_argument("--phase", required=True)
    p.add_argument("--slice", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--kind", default="implementation")
    p.add_argument("--risk", default="medium")
    p.add_argument("--order", type=int)
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
    p.add_argument("--risk", default="medium")
    p.add_argument("--order", type=int)
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
