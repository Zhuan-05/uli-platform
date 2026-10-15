"""Application registry: the authoritative list of installed applications.

The registry is a thin, well-tested layer over the SQLite store. It performs
registration-time validation but delegates process control to the runtime
adapters and module manager.
"""
from __future__ import annotations

from pathlib import Path

from compatibility.validator import ManifestValidationError, _build_manifest
from core import db
from core.compatibility import check_protocol_range
from core.models import ApplicationRecord, AppState, CapabilitySpec, Manifest, TrustLevel
from core.version import parse_version


class RegistryError(Exception):
    pass


class DuplicateAppError(RegistryError):
    pass


class UnknownAppError(RegistryError):
    pass


def _now() -> str:
    return db.utcnow()


class ApplicationRegistry:
    def __init__(self) -> None:
        db.init_db()

    # ------------------------------------------------------------------ #
    # Registration
    # ------------------------------------------------------------------ #
    def register(
        self,
        manifest: Manifest,
        path: str | Path,
        *,
        trust: str = TrustLevel.UNTRUSTED,
        is_builtin: bool = False,
        upgrade: bool = False,
    ) -> ApplicationRecord:
        if trust not in (TrustLevel.TRUSTED, TrustLevel.UNTRUSTED):
            raise RegistryError(f"Invalid trust level: {trust!r}")

        if manifest.runtime.type == "in-process" and not is_builtin:
            raise RegistryError(
                "in-process runtime is reserved for Core-internal providers and tests; "
                "it cannot be registered through the public API"
            )

        proto = check_protocol_range(manifest.protocol_range)
        if not proto.ok:
            raise RegistryError("; ".join(proto.errors))

        existing = db.get_app(manifest.id)
        if existing and not upgrade:
            raise DuplicateAppError(
                f"Application {manifest.id!r} is already registered "
                f"(use upgrade=true to replace version {existing.version})"
            )
        if existing and upgrade:
            if parse_version(manifest.version) <= parse_version(existing.version):
                raise RegistryError(
                    f"Upgrade rejected: new version {manifest.version} must be greater "
                    f"than installed version {existing.version}"
                )

        resolved_path = str(Path(path).resolve())
        record = ApplicationRecord(
            app_id=manifest.id,
            name=manifest.name,
            version=manifest.version,
            path=resolved_path,
            runtime_type=manifest.runtime.type,
            trust=trust,
            state=AppState.REGISTERED,
            manifest=manifest.raw,
            port=manifest.runtime.port or None,
            pid=None,
            registered_at=existing.registered_at if existing else _now(),
            updated_at=_now(),
            last_error=None,
            is_builtin=is_builtin,
        )
        db.upsert_app(record)
        return record

    # ------------------------------------------------------------------ #
    # Reads
    # ------------------------------------------------------------------ #
    def get(self, app_id: str) -> ApplicationRecord:
        rec = db.get_app(app_id)
        if rec is None:
            raise UnknownAppError(f"Unknown application: {app_id!r}")
        return rec

    def find(self, app_id: str) -> ApplicationRecord | None:
        return db.get_app(app_id)

    def list(self) -> list[ApplicationRecord]:
        return db.list_apps()

    def set_state(
        self,
        app_id: str,
        state: str,
        *,
        port: int | None = None,
        pid: int | None = None,
        last_error: str | None = None,
    ) -> None:
        if state not in AppState.ALL:
            raise RegistryError(f"Unknown state: {state!r}")
        db.set_state(
            app_id, state, port=port, pid=pid, last_error=last_error,
            clear_error=last_error is None,
        )

    def remove(self, app_id: str) -> ApplicationRecord:
        rec = self.get(app_id)
        db.delete_app(app_id)
        return rec

    # ------------------------------------------------------------------ #
    # Capability discovery
    # ------------------------------------------------------------------ #
    def available_capabilities(
        self, *, only_running: bool = False
    ) -> dict[str, list[tuple[str, CapabilitySpec]]]:
        result: dict[str, list[tuple[str, CapabilitySpec]]] = {}
        for rec in self.list():
            if only_running and rec.state != AppState.RUNNING:
                continue
            try:
                manifest = _build_manifest(rec.manifest)
            except Exception:
                continue
            for cap in manifest.provides:
                result.setdefault(cap.id, []).append((rec.app_id, cap))
        return result
