#!/usr/bin/env python3
"""Verify that a built wheel contains the packaged Admin Web UI assets."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from zipfile import BadZipFile, ZipFile

ADMIN_ASSET_DIR = "vocky/admin_assets"
REQUIRED_ASSETS = ("index.html", "app.css", "app.js", "docs.json")


def read_wheel_text(wheel: ZipFile, path: str) -> str:
    """Read a UTF-8 text file from a wheel archive."""

    return wheel.read(path).decode("utf-8")


def validate_admin_assets(wheel_path: Path) -> list[str]:
    """Return validation errors for missing or invalid Admin UI wheel assets."""

    errors: list[str] = []
    try:
        with ZipFile(wheel_path) as wheel:
            names = set(wheel.namelist())
            asset_paths = {
                asset_name: f"{ADMIN_ASSET_DIR}/{asset_name}" for asset_name in REQUIRED_ASSETS
            }

            for asset_name, asset_path in asset_paths.items():
                if asset_path not in names:
                    errors.append(f"missing packaged asset: {asset_path}")
                    continue

                if not read_wheel_text(wheel, asset_path).strip():
                    errors.append(f"packaged asset is empty: {asset_path}")

            if errors:
                return errors

            index_html = read_wheel_text(wheel, asset_paths["index.html"])
            app_css = read_wheel_text(wheel, asset_paths["app.css"])
            app_js = read_wheel_text(wheel, asset_paths["app.js"])
            docs_json = read_wheel_text(wheel, asset_paths["docs.json"])
    except BadZipFile:
        return [f"not a readable wheel archive: {wheel_path}"]
    except UnicodeDecodeError as exc:
        return [f"packaged Admin UI asset is not valid UTF-8: {exc}"]

    for expected in (
        '<div id="app" class="admin-app"',
        'href="/admin/assets/app.css"',
        'src="/admin/assets/app.js"',
    ):
        if expected not in index_html:
            errors.append(f"index.html does not contain expected markup: {expected}")

    for expected in (".admin-app", ".feedback-review-layout", ".docs-layout"):
        if expected not in app_css:
            errors.append(f"app.css does not contain expected selector: {expected}")

    for expected in (
        'ADMIN_API_PREFIX = "/admin/api/"',
        'DOCS_ASSET_PATH = "/admin/assets/docs.json"',
        "fetch(DOCS_ASSET_PATH",
    ):
        if expected not in app_js:
            errors.append(f"app.js does not contain expected behavior: {expected}")

    try:
        docs_payload = json.loads(docs_json)
    except json.JSONDecodeError as exc:
        errors.append(f"docs.json is not valid JSON: {exc}")
        return errors

    if docs_payload.get("version") != 1:
        errors.append("docs.json version must be 1")

    sections = docs_payload.get("sections")
    if not isinstance(sections, list) or not sections:
        errors.append("docs.json must contain non-empty sections")
        return errors

    topic_ids = {
        topic.get("id")
        for section in sections
        if isinstance(section, dict)
        for topic in section.get("topics", [])
        if isinstance(topic, dict)
    }
    for topic_id in ("operator-overview", "local-self-hosting", "public-custom-domain"):
        if topic_id not in topic_ids:
            errors.append(f"docs.json missing topic: {topic_id}")

    return errors


def main() -> None:
    """Run the Admin UI package verification."""

    if len(sys.argv) != 2:
        raise SystemExit("Usage: check_admin_ui_package.py <wheel-path>")

    wheel_path = Path(sys.argv[1])
    if not wheel_path.is_file():
        raise SystemExit(f"wheel not found: {wheel_path}")

    errors = validate_admin_assets(wheel_path)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        raise SystemExit(1)

    print(f"Admin UI package assets ok: {wheel_path.name}")


if __name__ == "__main__":
    main()
