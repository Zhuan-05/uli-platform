"""Typed views over validated manifests plus the persisted application record.

These dataclasses are the canonical internal representation. Business
applications never touch this module directly; they only interact through the
documented HTTP/JSON contracts of ULI Core and the ULI SDK.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


# --------------------------------------------------------------------------- #
# Lifecycle / trust enums (kept as plain strings for JSON friendliness)
# --------------------------------------------------------------------------- #
class AppState:
    REGISTERED = "registered"   # known to the platform, not runnable yet
    ENABLED = "enabled"         # may be started
    DISABLED = "disabled"       # explicitly off
    STARTING = "starting"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"
    INCOMPATIBLE = "incompatible"  # manifest ok, but requirements unresolved

    ALL = {REGISTERED, ENABLED, DISABLED, STARTING, RUNNING, STOPPED, ERROR, INCOMPATIBLE}


class TrustLevel:
    TRUSTED = "trusted"
    UNTRUSTED = "untrusted"


class RuntimeType:
    STATIC_SITE = "static-site"
    EXTERNAL_URL = "external-url"
    LOCAL_PYTHON = "local-python"
    LOCAL_NODE = "local-node"       # documented extension point (not implemented)
    IN_PROCESS = "in-process"       # used by Core-internal/test providers

    PROCESS_TYPES = {LOCAL_PYTHON, LOCAL_NODE}


@dataclass
class CapabilitySpec:
    id: str
    version: str = "1.0.0"
    description: str = ""
    input_type: str = "*"
    output_type: str = "*"
    input_schema: dict[str, Any] = field(default_factory=dict)
    output_schema: dict[str, Any] = field(default_factory=dict)
    timeout_ms: int = 5000


@dataclass
class RequirementSpec:
    id: str
    version_range: str = "*"
    optional: bool = False


@dataclass
class RuntimeSpec:
    type: str
    entry: str | None = None
    url: str | None = None
    static_dir: str | None = None
    port: int = 0
    health_path: str = "/health"
    working_dir: str | None = None
    env: dict[str, str] = field(default_factory=dict)


@dataclass
class FrontendSpec:
    entry: str | None = None
    embed: bool = True
    extension_points: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class Manifest:
    manifest_version: str
    id: str
    name: str
    version: str
    protocol_range: str
    runtime: RuntimeSpec
    frontend: FrontendSpec
    provides: list[CapabilitySpec] = field(default_factory=list)
    requires: list[RequirementSpec] = field(default_factory=list)
    publishes: list[dict[str, Any]] = field(default_factory=list)
    subscribes: list[dict[str, Any]] = field(default_factory=list)
    permissions: list[str] = field(default_factory=list)
    ui_extension_points: list[dict[str, Any]] = field(default_factory=list)
    config_fields: list[dict[str, Any]] = field(default_factory=list)
    description: str = ""
    data_owner: str = ""
    raw: dict[str, Any] = field(default_factory=dict)

    def provides_map(self) -> dict[str, CapabilitySpec]:
        return {c.id: c for c in self.provides}


@dataclass
class ApplicationRecord:
    """Persisted, platform-owned view of an installed application."""

    app_id: str
    name: str
    version: str
    path: str
    runtime_type: str
    trust: str
    state: str
    manifest: dict[str, Any]
    port: int | None = None
    pid: int | None = None
    registered_at: str = ""
    updated_at: str = ""
    last_error: str | None = None
    is_builtin: bool = False

    def to_row(self) -> dict[str, Any]:
        import json

        d = asdict(self)
        d["manifest"] = json.dumps(self.manifest, separators=(",", ":"))
        return d
