"""Central path/configuration resolution for the ULI platform.

All mutable state lives under a single data directory so that the platform can be
relocated and so that tests can point at a temporary directory via
``ULI_DATA_DIR``.
"""
from __future__ import annotations

import os
from pathlib import Path

# Project root = parent of this package directory.
ROOT = Path(__file__).resolve().parent.parent


def _env_path(name: str, default: Path) -> Path:
    raw = os.environ.get(name)
    return Path(raw).expanduser().resolve() if raw else default


def data_dir() -> Path:
    d = _env_path("ULI_DATA_DIR", ROOT / "data")
    d.mkdir(parents=True, exist_ok=True)
    return d


def db_path() -> Path:
    return data_dir() / "uli.db"


def imports_dir() -> Path:
    """Where imported / generated application packages are physically stored."""
    d = data_dir() / "imports"
    d.mkdir(parents=True, exist_ok=True)
    return d


def log_dir() -> Path:
    d = data_dir() / "logs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def builtin_apps_dir() -> Path:
    return ROOT / "applications"


def examples_dir() -> Path:
    return ROOT / "examples"


def frontend_dist_dir() -> Path:
    return ROOT / "frontend" / "dist"


def blueprints_file() -> Path:
    return data_dir() / "blueprints.json"


def themes_active_file() -> Path:
    return data_dir() / "active_theme.json"


def events_file() -> Path:
    return data_dir() / "events.jsonl"


def core_url() -> str:
    """The externally reachable base URL of this ULI Core instance.

    Injected into locally-spawned applications so they can call back into the
    capability broker. Overridable for tests / custom ports.
    """
    return os.environ.get("ULI_CORE_URL", "http://127.0.0.1:8787").rstrip("/")


def core_host() -> str:
    return os.environ.get("ULI_CORE_HOST", "127.0.0.1")


def core_port() -> int:
    return int(os.environ.get("ULI_CORE_PORT", "8787"))


def is_production() -> bool:
    return os.environ.get("ULI_ENV", "development").lower() == "production"
