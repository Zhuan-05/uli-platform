"""Manifest validation: JSON Schema validation + semantic checks.

Any failure raises :class:`ManifestValidationError` with a list of clear,
human-readable messages. Malformed manifests never reach the registry.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

from compatibility.manifest_schema import JSON_SCHEMA
from core.models import (
    CapabilitySpec,
    FrontendSpec,
    Manifest,
    RequirementSpec,
    RuntimeSpec,
)
from core.version import VersionError, parse_version, satisfies_range

MANIFEST_FILENAMES = ("app.manifest.json", "manifest.json")

# Permissions the platform is willing to grant. Anything outside this set is
# rejected so a manifest cannot claim broad powers it does not receive.
ALLOWED_PERMISSION_PREFIXES = (
    "fs.read",
    "fs.write",
    "net.local",
    "net.external",
    "capability.invoke",
    "events.publish",
    "events.subscribe",
    "ui.extension",
    "data.own",
    "storage.kv",
)


class ManifestValidationError(ValueError):
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


def _validator() -> Draft202012Validator:
    Draft202012Validator.check_schema(JSON_SCHEMA)
    return Draft202012Validator(JSON_SCHEMA)


def validate_manifest_dict(raw: dict[str, Any], *, source: str = "<memory>") -> Manifest:
    """Validate a manifest mapping and return its typed representation."""
    if not isinstance(raw, dict):
        raise ManifestValidationError([f"{source}: manifest must be a JSON object"])

    errors: list[str] = []
    validator = _validator()
    for err in sorted(validator.iter_errors(raw), key=lambda e: list(e.absolute_path)):
        location = "/".join(str(p) for p in err.absolute_path) or "<root>"
        errors.append(f"{source}: {location}: {err.message}")

    if errors:
        raise ManifestValidationError(errors)

    # ---- Semantic checks that JSON Schema cannot express cleanly -----------
    for cap in raw.get("capabilities", {}).get("provides", []):
        for which, key in (("inputSchema", "inputSchema"), ("outputSchema", "outputSchema")):
            try:
                Draft202012Validator.check_schema(cap[key])
            except SchemaError as exc:
                errors.append(
                    f"{source}: capabilities.provides[{cap.get('id')}].{which}: "
                    f"invalid JSON Schema: {exc.message}"
                )

    try:
        parse_version(raw["version"])
    except VersionError as exc:
        errors.append(f"{source}: version: {exc}")

    try:
        satisfies_range("1.0.0", raw["uli"]["protocol"])  # parseability probe
    except VersionError as exc:
        errors.append(f"{source}: uli.protocol: {exc}")

    for req in raw.get("capabilities", {}).get("requires", []):
        try:
            satisfies_range("1.0.0", req.get("version", "*"))
        except VersionError as exc:
            errors.append(f"{source}: capabilities.requires[{req.get('id')}].version: {exc}")

    for perm in raw.get("permissions", []):
        if not any(perm == p or perm.startswith(p + ".") for p in ALLOWED_PERMISSION_PREFIXES):
            errors.append(
                f"{source}: permissions: {perm!r} is not an allow-listed ULI permission "
                f"(allowed prefixes: {', '.join(ALLOWED_PERMISSION_PREFIXES)})"
            )

    if errors:
        raise ManifestValidationError(errors)

    return _build_manifest(raw)


def _build_manifest(raw: dict[str, Any]) -> Manifest:
    runtime_raw = raw["runtime"]
    runtime = RuntimeSpec(
        type=runtime_raw["type"],
        entry=runtime_raw.get("entry"),
        url=runtime_raw.get("url"),
        static_dir=runtime_raw.get("staticDir"),
        port=int(runtime_raw.get("port", 0)),
        health_path=runtime_raw.get("healthPath", "/health"),
        working_dir=runtime_raw.get("workingDir"),
        env=dict(runtime_raw.get("env", {})),
    )

    fe_raw = raw.get("frontend", {})
    frontend = FrontendSpec(
        entry=fe_raw.get("entry"),
        embed=bool(fe_raw.get("embed", True)),
        extension_points=list(fe_raw.get("extensionPoints", [])),
    )

    caps_raw = raw.get("capabilities", {})
    provides = [
        CapabilitySpec(
            id=c["id"],
            version=c["version"],
            description=c.get("description", ""),
            input_type=c.get("inputType", "*"),
            output_type=c.get("outputType", "*"),
            input_schema=c["inputSchema"],
            output_schema=c["outputSchema"],
            timeout_ms=int(c.get("timeoutMs", 5000)),
        )
        for c in caps_raw.get("provides", [])
    ]
    requires = [
        RequirementSpec(
            id=r["id"],
            version_range=r.get("version", "*"),
            optional=bool(r.get("optional", False)),
        )
        for r in caps_raw.get("requires", [])
    ]

    events_raw = raw.get("events", {})
    ui_raw = raw.get("ui", {})

    return Manifest(
        manifest_version=raw["manifestVersion"],
        id=raw["id"],
        name=raw["name"],
        description=raw.get("description", ""),
        version=raw["version"],
        protocol_range=raw["uli"]["protocol"],
        runtime=runtime,
        frontend=frontend,
        provides=provides,
        requires=requires,
        publishes=list(events_raw.get("publishes", [])),
        subscribes=list(events_raw.get("subscribes", [])),
        permissions=list(raw.get("permissions", [])),
        ui_extension_points=list(ui_raw.get("extensionPoints", [])),
        config_fields=list(raw.get("config", {}).get("fields", [])),
        data_owner=raw.get("dataOwner", ""),
        raw=raw,
    )


def load_manifest_file(path: str | Path) -> Manifest:
    path = Path(path)
    if path.is_dir():
        found = None
        for name in MANIFEST_FILENAMES:
            candidate = path / name
            if candidate.is_file():
                found = candidate
                break
        if found is None:
            raise ManifestValidationError(
                [f"{path}: no manifest found (expected one of: {', '.join(MANIFEST_FILENAMES)})"]
            )
        path = found
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ManifestValidationError([f"{path}: cannot read manifest: {exc}"]) from exc
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ManifestValidationError([f"{path}: invalid JSON: {exc}"]) from exc
    return validate_manifest_dict(raw, source=str(path))
