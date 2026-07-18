"""On-disk config/credential store for the ``vocky`` CLI.

Holds the CLI session token and preferred base URL in a small JSON file under a
per-user config directory, written with tight permissions (dir ``0700``, file
``0600``). This is the repo's first home-directory convention — there was no
prior XDG/config store — so later CLI slices (auth/projects/feedback) reuse this
module as the single home for on-disk session state.

Directory precedence: ``VOCKY_CONFIG_DIR`` override, else ``$XDG_CONFIG_HOME/vocky``,
else ``~/.config/vocky``.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

CONFIG_FILENAME = "config.json"

_DIR_MODE = 0o700
_FILE_MODE = 0o600


def config_dir() -> Path:
    """Resolve the CLI config directory (never touching disk).

    ``VOCKY_CONFIG_DIR`` wins when set; otherwise ``$XDG_CONFIG_HOME/vocky`` when
    ``XDG_CONFIG_HOME`` is set; otherwise ``~/.config/vocky``.
    """

    override = os.environ.get("VOCKY_CONFIG_DIR", "").strip()
    if override:
        return Path(override).expanduser()

    xdg_config_home = os.environ.get("XDG_CONFIG_HOME", "").strip()
    if xdg_config_home:
        return Path(xdg_config_home).expanduser() / "vocky"

    return Path.home() / ".config" / "vocky"


def config_path() -> Path:
    """Return the path to the CLI ``config.json`` file."""

    return config_dir() / CONFIG_FILENAME


def load() -> dict:
    """Return the stored config as a dict, or ``{}`` when absent/unreadable."""

    path = config_path()
    try:
        raw = path.read_text(encoding="utf-8")
    except (FileNotFoundError, OSError):
        return {}

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}

    return data if isinstance(data, dict) else {}


def save(data: dict) -> None:
    """Persist ``data`` to ``config.json`` with dir ``0700`` / file ``0600``.

    The file is created (or truncated) via ``os.open`` with mode ``0o600`` and
    re-``chmod``-ed afterwards so an existing looser-permissioned file is
    tightened too. The token never lands on disk world-readable.
    """

    directory = config_dir()
    directory.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(directory, _DIR_MODE)
    except OSError:
        pass

    path = config_path()
    payload = json.dumps(data, indent=2, sort_keys=True) + "\n"
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, _FILE_MODE)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
    finally:
        try:
            os.chmod(path, _FILE_MODE)
        except OSError:
            pass


def _get_str(key: str) -> str | None:
    value = load().get(key)
    return value if isinstance(value, str) and value else None


def get_token() -> str | None:
    """Return the stored session token, or ``None`` when not signed in."""

    return _get_str("token")


def set_token(token: str) -> None:
    """Store the session token (merging with any existing config)."""

    data = load()
    data["token"] = token
    save(data)


def clear_token() -> None:
    """Remove the stored session token, leaving other config intact."""

    data = load()
    if data.pop("token", None) is not None:
        save(data)


def get_base_url() -> str | None:
    """Return the stored preferred base URL, or ``None`` when unset."""

    return _get_str("base_url")


def set_base_url(base_url: str) -> None:
    """Store the preferred base URL (merging with any existing config)."""

    data = load()
    data["base_url"] = base_url
    save(data)
