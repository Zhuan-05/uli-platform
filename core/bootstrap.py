"""Bootstrap helpers: register the bundled example applications.

Bundled apps live inside the repository and are reviewed, so they are
registered as ``trusted`` (which is what allows the local-python runtime to
execute them). Imported third-party apps default to ``untrusted``.
"""
from __future__ import annotations

from pathlib import Path

from compatibility.validator import load_manifest_file
from core import config
from core.models import TrustLevel
from core.registry import ApplicationRegistry

BUILTIN_APPS: list[tuple[str, Path]] = [
    ("uli.examples.order", config.builtin_apps_dir() / "order_app"),
    ("uli.examples.inventory", config.builtin_apps_dir() / "inventory_app"),
]


def ensure_builtin_apps(registry: ApplicationRegistry) -> list[str]:
    registered: list[str] = []
    for app_id, path in BUILTIN_APPS:
        if registry.find(app_id) is not None:
            continue
        if not path.is_dir():
            continue
        manifest = load_manifest_file(path)
        registry.register(manifest, path, trust=TrustLevel.TRUSTED, is_builtin=True)
        registered.append(app_id)
    return registered


def import_example_static_site(registry: ApplicationRegistry) -> str | None:
    """Import the bundled prebuilt static site (idempotent)."""
    from core.importer import generated_static_manifest, import_static_directory
    from compatibility.validator import validate_manifest_dict

    app_id = "uli.imported.acme-catalogue"
    if registry.find(app_id) is not None:
        return app_id
    src = config.examples_dir() / "legacy-static-site"
    if not src.is_dir():
        return None
    target = import_static_directory(src, app_id)
    manifest = validate_manifest_dict(
        generated_static_manifest("Acme Catalogue", app_id), source="<generated>"
    )
    registry.register(manifest, target, trust=TrustLevel.UNTRUSTED)
    return app_id
