"""Static website import (Legacy Application Track).

Imports an existing, already-built website *without rewriting its source*. The
only added file is a generated ``app.manifest.json`` describing how ULI should
host it. This is "hosting compatibility" - the imported site does not magically
gain access to ULI capabilities unless an Adapter is added.
"""
from __future__ import annotations

import re
import shutil
import zipfile
from pathlib import Path

from compatibility.validator import ManifestValidationError

MAX_ZIP_BYTES = 512 * 1024 * 1024  # 512 MB safety cap


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")
    return slug or "site"


def generated_static_manifest(name: str, app_id: str, static_dir: str = "site") -> dict:
    return {
        "manifestVersion": "1.0",
        "id": app_id,
        "name": name,
        "description": f"Imported static website: {name}",
        "version": "1.0.0",
        "uli": {"protocol": ">=1.0.0 <2.0.0"},
        "runtime": {"type": "static-site", "staticDir": static_dir},
        "frontend": {"entry": f"{static_dir}/index.html", "embed": True},
        "capabilities": {"provides": [], "requires": []},
        "events": {"publishes": [], "subscribes": []},
        "permissions": ["fs.read.assets"],
        "dataOwner": app_id,
    }


def _target_for(app_id: str) -> Path:
    from core import config

    target = config.imports_dir() / slugify(app_id)
    if target.exists():
        # Never destroy data; pick a fresh suffix instead.
        i = 2
        while (config.imports_dir() / f"{slugify(app_id)}-{i}").exists():
            i += 1
        target = config.imports_dir() / f"{slugify(app_id)}-{i}"
    return target


def import_static_directory(source: str | Path, app_id: str, static_dir: str = "site") -> Path:
    """Copy a directory tree into the platform imports area."""
    src = Path(source).expanduser().resolve()
    if not src.is_dir():
        raise ManifestValidationError([f"static source is not a directory: {src}"])

    target = _target_for(app_id)
    (target / static_dir).parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, target / static_dir)
    return target


def safe_extract_zip(zip_path: str | Path, app_id: str, static_dir: str = "site") -> Path:
    """Extract an uploaded zip with zip-slip protection."""
    zip_path = Path(zip_path)
    if zip_path.stat().st_size > MAX_ZIP_BYTES:
        raise ManifestValidationError(["uploaded archive exceeds 512 MB limit"])

    target = _target_for(app_id)
    dest_root = target / static_dir
    dest_root.mkdir(parents=True, exist_ok=True)
    dest_resolved = dest_root.resolve()

    with zipfile.ZipFile(zip_path) as zf:
        for member in zf.infolist():
            name = member.filename
            if name.startswith("/") or ".." in Path(name).parts:
                raise ManifestValidationError([f"unsafe path in archive: {name!r}"])
            out_path = (dest_root / name).resolve()
            if dest_resolved != out_path and dest_resolved not in out_path.parents:
                raise ManifestValidationError([f"archive entry escapes target: {name!r}"])
        zf.extractall(dest_root)

    # If the archive had a single top-level folder, flatten it.
    entries = [p for p in dest_root.iterdir() if p.name not in ("__MACOSX",)]
    if len(entries) == 1 and entries[0].is_dir():
        inner = entries[0]
        for child in inner.iterdir():
            shutil.move(str(child), str(dest_root / child.name))
        inner.rmdir()

    return target
