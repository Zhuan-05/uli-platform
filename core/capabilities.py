"""Capability Registry: discovery and resolution of published capabilities.

Applications never import each other. They discover capabilities here and invoke
them through the broker, which enforces contracts and permissions.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from compatibility.validator import _build_manifest
from core.models import ApplicationRecord, AppState, CapabilitySpec
from core.registry import ApplicationRegistry
from core.version import VersionError, parse_version, satisfies_range


class CapabilityError(Exception):
    pass


class CapabilityNotFoundError(CapabilityError):
    pass


class CapabilityIncompatibleError(CapabilityError):
    pass


class CapabilityUnavailableError(CapabilityError):
    """Provider exists but is not currently running."""


@dataclass
class CapabilityDescriptor:
    id: str
    version: str
    app_id: str
    app_name: str
    app_state: str
    description: str
    input_type: str
    output_type: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    timeout_ms: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "version": self.version,
            "appId": self.app_id,
            "appName": self.app_name,
            "appState": self.app_state,
            "description": self.description,
            "inputType": self.input_type,
            "outputType": self.output_type,
            "inputSchema": self.input_schema,
            "outputSchema": self.output_schema,
            "timeoutMs": self.timeout_ms,
        }


class CapabilityRegistry:
    def __init__(self, apps: ApplicationRegistry) -> None:
        self.apps = apps

    def list(self) -> list[CapabilityDescriptor]:
        out: list[CapabilityDescriptor] = []
        for rec in self.apps.list():
            for cap in self._caps_of(rec):
                out.append(self._describe(rec, cap))
        return sorted(out, key=lambda d: (d.id, d.app_id))

    def providers(self, capability_id: str) -> list[CapabilityDescriptor]:
        return [d for d in self.list() if d.id == capability_id]

    def resolve(
        self,
        capability_id: str,
        version_range: str = "*",
        *,
        require_running: bool = True,
    ) -> tuple[ApplicationRecord, CapabilitySpec]:
        candidates: list[tuple[ApplicationRecord, CapabilitySpec]] = []
        for rec in self.apps.list():
            for cap in self._caps_of(rec):
                if cap.id == capability_id:
                    candidates.append((rec, cap))

        if not candidates:
            raise CapabilityNotFoundError(f"No application provides capability {capability_id!r}")

        try:
            compatible = [
                (rec, cap) for rec, cap in candidates
                if satisfies_range(cap.version, version_range)
            ]
        except VersionError as exc:
            raise CapabilityIncompatibleError(f"Invalid version range {version_range!r}: {exc}") from exc

        if not compatible:
            found = ", ".join(f"{r.app_id}@{c.version}" for r, c in candidates)
            raise CapabilityIncompatibleError(
                f"No provider of {capability_id!r} satisfies range {version_range!r} "
                f"(found: {found})"
            )

        # Highest version wins; ties broken deterministically by app id.
        compatible.sort(key=lambda rc: (parse_version(rc[1].version), rc[0].app_id), reverse=True)
        rec, cap = compatible[0]

        if require_running and rec.state != AppState.RUNNING:
            raise CapabilityUnavailableError(
                f"Provider {rec.app_id!r} of {capability_id!r} is {rec.state}, not running"
            )
        return rec, cap

    @staticmethod
    def _caps_of(rec: ApplicationRecord) -> list[CapabilitySpec]:
        try:
            return _build_manifest(rec.manifest).provides
        except Exception:
            return []

    @staticmethod
    def _describe(rec: ApplicationRecord, cap: CapabilitySpec) -> CapabilityDescriptor:
        return CapabilityDescriptor(
            id=cap.id,
            version=cap.version,
            app_id=rec.app_id,
            app_name=rec.name,
            app_state=rec.state,
            description=cap.description,
            input_type=cap.input_type,
            output_type=cap.output_type,
            input_schema=cap.input_schema,
            output_schema=cap.output_schema,
            timeout_ms=cap.timeout_ms,
        )
