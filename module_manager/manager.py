"""Module & Application Manager.

Orchestrates application lifecycle (enable/disable/start/stop/uninstall) and
acts as the capability broker and event dispatcher. This is the only place that
combines the registry, runtime adapters and event bus.
"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import httpx

from compatibility.validator import _build_manifest
from core import config
from core.capabilities import (
    CapabilityError,
    CapabilityIncompatibleError,
    CapabilityNotFoundError,
    CapabilityRegistry,
    CapabilityUnavailableError,
)
from core.compatibility import resolve_requirements
from core.models import ApplicationRecord, AppState, TrustLevel
from core.registry import ApplicationRegistry
from core.validation import PayloadValidationError, validate_payload
from core.version import parse_version
from event_bus import Event, EventBus
from runtime_adapters import RuntimeAdapterRegistry, UnsupportedOperation


class ModuleManagerError(Exception):
    pass


class RequirementNotSatisfied(ModuleManagerError):
    pass


class PermissionDenied(ModuleManagerError):
    pass


class ApplicationNotRunning(ModuleManagerError):
    pass


class ModuleManager:
    def __init__(
        self,
        registry: ApplicationRegistry,
        capabilities: CapabilityRegistry,
        runtimes: RuntimeAdapterRegistry,
        bus: EventBus,
    ) -> None:
        self.registry = registry
        self.capabilities = capabilities
        self.runtimes = runtimes
        self.bus = bus

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #
    async def enable(self, app_id: str) -> ApplicationRecord:
        rec = self.registry.get(app_id)
        manifest = _build_manifest(rec.manifest)

        if manifest.runtime.type in ("local-python", "local-node") and rec.trust != TrustLevel.TRUSTED:
            self.registry.set_state(app_id, AppState.INCOMPATIBLE,
                                    last_error="local runtime requires trust='trusted'")
            raise PermissionDenied(
                f"Application {app_id!r} uses runtime {manifest.runtime.type!r} but is not trusted"
            )

        available = self.registry.available_capabilities()
        result = resolve_requirements(manifest, available)
        if not result.ok:
            self.registry.set_state(app_id, AppState.INCOMPATIBLE, last_error="; ".join(result.errors))
            raise RequirementNotSatisfied("; ".join(result.errors))

        self.registry.set_state(app_id, AppState.ENABLED)
        return self.registry.get(app_id)

    async def disable(self, app_id: str) -> ApplicationRecord:
        rec = self.registry.get(app_id)
        if rec.state == AppState.RUNNING:
            await self.stop(app_id)
        self.registry.set_state(app_id, AppState.DISABLED)
        return self.registry.get(app_id)

    async def start(self, app_id: str) -> tuple[ApplicationRecord, dict[str, Any]]:
        rec = self.registry.get(app_id)
        if rec.state == AppState.DISABLED:
            raise ModuleManagerError(
                f"Application {app_id!r} is disabled; enable it before starting"
            )
        if rec.state not in (AppState.ENABLED, AppState.REGISTERED, AppState.STOPPED, AppState.ERROR):
            if rec.state == AppState.RUNNING:
                status = await self.runtimes.get(rec.runtime_type).status(rec)
                return rec, status.to_dict()

        # Re-check requirements against *running* providers for capability apps.
        manifest = _build_manifest(rec.manifest)
        if manifest.requires:
            running = self.registry.available_capabilities(only_running=True)
            check = resolve_requirements(manifest, running)
            if not check.ok:
                self.registry.set_state(app_id, AppState.ERROR, last_error="; ".join(check.errors))
                raise RequirementNotSatisfied("; ".join(check.errors))

        self.registry.set_state(app_id, AppState.STARTING)
        try:
            adapter = self.runtimes.get(rec.runtime_type)
            status = await adapter.start(rec)
        except UnsupportedOperation as exc:
            self.registry.set_state(app_id, AppState.ERROR, last_error=str(exc))
            raise

        if status.state == AppState.RUNNING:
            self.registry.set_state(app_id, AppState.RUNNING, port=status.port, pid=status.pid)
        else:
            self.registry.set_state(app_id, AppState.ERROR, last_error=status.detail)
        return self.registry.get(app_id), status.to_dict()

    async def stop(self, app_id: str) -> tuple[ApplicationRecord, dict[str, Any]]:
        rec = self.registry.get(app_id)
        adapter = self.runtimes.get(rec.runtime_type)
        status = await adapter.stop(rec)
        self.registry.set_state(app_id, AppState.STOPPED, last_error=None)
        return self.registry.get(app_id), status.to_dict()

    async def restart(self, app_id: str) -> tuple[ApplicationRecord, dict[str, Any]]:
        await self.stop(app_id)
        return await self.start(app_id)

    async def health(self, app_id: str) -> dict[str, Any]:
        rec = self.registry.get(app_id)
        adapter = self.runtimes.get(rec.runtime_type)
        status = await adapter.status(rec)
        return {"appId": app_id, "state": rec.state, **status.to_dict()}

    async def uninstall(self, app_id: str, *, delete_files: bool = False) -> dict[str, Any]:
        rec = self.registry.get(app_id)
        if rec.state == AppState.RUNNING:
            await self.stop(app_id)

        removed_files = False
        if delete_files:
            app_path = Path(rec.path).resolve()
            imports = config.imports_dir().resolve()
            if imports in app_path.parents:
                shutil.rmtree(app_path, ignore_errors=True)
                removed_files = True

        self.registry.remove(app_id)
        return {
            "appId": app_id,
            "removedFromRegistry": True,
            "deletedSourceFiles": removed_files,
            "dataPreserved": True,
            "note": (
                "Application data was preserved by design. Source files are only deleted "
                "for platform-imported apps when delete_files=true."
            ),
        }

    # ------------------------------------------------------------------ #
    # Capability broker
    # ------------------------------------------------------------------ #
    async def invoke_capability(
        self,
        capability_id: str,
        payload: dict[str, Any],
        *,
        version_range: str = "*",
        caller_app_id: str | None = None,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        if caller_app_id is not None:
            self._check_permission(caller_app_id, "capability.invoke", capability_id)

        try:
            rec, cap = self.capabilities.resolve(capability_id, version_range, require_running=True)
        except CapabilityNotFoundError as exc:
            raise ModuleManagerError(str(exc)) from exc
        except CapabilityIncompatibleError as exc:
            raise ModuleManagerError(str(exc)) from exc
        except CapabilityUnavailableError as exc:
            raise ApplicationNotRunning(str(exc)) from exc

        validate_payload(cap.input_schema, payload, f"input for capability {cap.id}")

        adapter = self.runtimes.get(rec.runtime_type)
        if not adapter.supports_capabilities:
            raise ModuleManagerError(
                f"Provider {rec.app_id!r} runtime {rec.runtime_type!r} cannot serve capabilities"
            )

        try:
            output = await adapter.invoke(rec, cap, payload)
        except httpx.HTTPError as exc:
            self.bus.publish(
                Event(
                    name="uli.capability.failed",
                    version="1.0.0",
                    source="uli.core",
                    payload={"capability": capability_id, "provider": rec.app_id, "error": str(exc)},
                    correlation_id=request_id,
                )
            )
            raise ModuleManagerError(f"transport error invoking {capability_id}: {exc}") from exc

        validate_payload(cap.output_schema, output, f"output of capability {cap.id}")

        self.bus.publish(
            Event(
                name="uli.capability.invoked",
                version="1.0.0",
                source="uli.core",
                payload={
                    "capability": capability_id,
                    "provider": rec.app_id,
                    "caller": caller_app_id,
                    "contractVersion": cap.version,
                },
                correlation_id=request_id,
            )
        )
        return {
            "capability": capability_id,
            "contractVersion": cap.version,
            "provider": rec.app_id,
            "output": output,
        }

    # ------------------------------------------------------------------ #
    # Events
    # ------------------------------------------------------------------ #
    def publish_declared_schema(self, app_id: str, event_name: str) -> dict[str, Any] | None:
        try:
            manifest = _build_manifest(self.registry.get(app_id).manifest)
        except Exception:  # noqa: BLE001
            return None
        for decl in manifest.publishes:
            if decl.get("name") == event_name:
                return decl.get("schema")
        return None

    async def publish_event(
        self,
        name: str,
        version: str,
        payload: dict[str, Any],
        *,
        source: str,
        correlation_id: str | None = None,
        caller_app_id: str | None = None,
    ) -> dict[str, Any]:
        if caller_app_id is not None:
            self._check_permission(caller_app_id, "events.publish", name)

        schema = self.publish_declared_schema(caller_app_id, name) if caller_app_id else None
        event = Event(
            name=name,
            version=version,
            source=source,
            payload=payload,
            correlation_id=correlation_id,
        )
        result = self.bus.publish(event, schema=schema)

        # Deliver to external (subprocess) subscribers.
        external = await self._deliver_external(event)
        result["external"] = external
        return result

    async def _deliver_external(self, event: Event) -> dict[str, Any]:
        delivered: list[str] = []
        errors: list[str] = []
        for rec in self.registry.list():
            if rec.state != AppState.RUNNING:
                continue
            try:
                manifest = _build_manifest(rec.manifest)
            except Exception:  # noqa: BLE001
                continue
            if not self._subscribes_to(manifest, event.name, event.version):
                continue
            if rec.runtime_type != "local-python":
                continue
            lp = self.runtimes.local_python()
            base = lp.base_url_for(rec.app_id)
            if not base:
                continue
            token = lp.token_for(rec.app_id)
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(
                        f"{base}/uli/events",
                        json=event.to_dict(),
                        headers={"Authorization": f"Bearer {token}"},
                    )
                if resp.status_code < 400:
                    delivered.append(rec.app_id)
                else:
                    errors.append(f"{rec.app_id}: HTTP {resp.status_code}")
            except httpx.HTTPError as exc:
                errors.append(f"{rec.app_id}: {exc}")
        return {"deliveredTo": delivered, "errors": errors}

    @staticmethod
    def _subscribes_to(manifest, name: str, version: str) -> bool:
        for decl in manifest.subscribes:
            if decl.get("name") != name:
                continue
            try:
                if parse_version(decl["version"]).major == parse_version(version).major:
                    return True
            except Exception:  # noqa: BLE001
                return True
        return False

    # ------------------------------------------------------------------ #
    def _check_permission(self, app_id: str, action: str, target: str) -> None:
        try:
            manifest = _build_manifest(self.registry.get(app_id).manifest)
        except Exception as exc:  # noqa: BLE001
            raise PermissionDenied(f"cannot verify permissions for {app_id!r}: {exc}") from exc

        perms = set(manifest.permissions)
        if action in perms or f"{action}.{target}" in perms:
            return
        # prefix wildcard, e.g. "capability.invoke.*"
        for perm in perms:
            if perm.endswith(".*") and (action == perm[:-2] or f"{action}.{target}".startswith(perm[:-1])):
                return
        raise PermissionDenied(
            f"Application {app_id!r} lacks permission {action}.{target!r} "
            f"(declared: {sorted(perms) or 'none'})"
        )
