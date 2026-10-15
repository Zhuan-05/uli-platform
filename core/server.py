"""ULI Core HTTP API (FastAPI).

This module is the platform boundary. Every application - legacy or native -
only ever sees these documented HTTP contracts.
"""
from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from blueprints import (
    BlueprintExecutionError,
    BlueprintNotFound,
    BlueprintValidationError,
)
from compatibility.validator import (
    ManifestValidationError,
    load_manifest_file,
    validate_manifest_dict,
)
from core import config
from core.capabilities import CapabilityError
from core.compatibility import compatibility_summary, port_types_compatible
from core.importer import (
    generated_static_manifest,
    import_static_directory,
    safe_extract_zip,
    slugify,
)
from core.models import AppState, TrustLevel
from core.registry import DuplicateAppError, RegistryError, UnknownAppError
from core.services import Services, get_services
from core import ULI_PROTOCOL_VERSION
from core.validation import PayloadValidationError
from module_manager import (
    ApplicationNotRunning,
    ModuleManagerError,
    PermissionDenied,
    RequirementNotSatisfied,
)
from runtime_adapters import UnsupportedOperation
from theme_design import ThemeNotFound


# --------------------------------------------------------------------------- #
# Request models
# --------------------------------------------------------------------------- #
class RegisterRequest(BaseModel):
    path: str
    trust: str = TrustLevel.UNTRUSTED
    upgrade: bool = False


class ImportStaticRequest(BaseModel):
    name: str
    path: str
    id: str | None = None


class ExternalRequest(BaseModel):
    name: str
    url: str
    id: str | None = None
    trust: str = TrustLevel.UNTRUSTED


class InvokeRequest(BaseModel):
    input: dict[str, Any] = Field(default_factory=dict)
    versionRange: str = "*"


class PublishRequest(BaseModel):
    name: str
    version: str = "1.0.0"
    payload: dict[str, Any] = Field(default_factory=dict)
    correlationId: str | None = None


class ConnectionCheckRequest(BaseModel):
    sourceOutputType: str
    targetInputType: str


class ThemeImportRequest(BaseModel):
    id: str
    name: str
    mode: str = "dark"
    tokens: dict[str, Any]


def _error(status: int, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"detail": message})


def create_app(services: Services | None = None) -> FastAPI:
    svc = services or get_services()

    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        yield
        # Graceful shutdown: stop every running child process so we do not
        # leak orphans when Core exits cleanly.
        for rec in svc.registry.list():
            if rec.state == AppState.RUNNING:
                try:
                    await svc.manager.stop(rec.app_id)
                except Exception:  # noqa: BLE001 - best effort on shutdown
                    pass

    app = FastAPI(title="ULI Core", version=ULI_PROTOCOL_VERSION, lifespan=lifespan)

    # ------------------------------------------------------------------ #
    # Platform
    # ------------------------------------------------------------------ #
    @app.get("/api/health")
    async def platform_health() -> dict[str, Any]:
        apps = svc.registry.list()
        return {
            "status": "ok",
            "service": "uli-core",
            "protocolVersion": ULI_PROTOCOL_VERSION,
            "applications": len(apps),
            "running": sum(1 for a in apps if a.state == AppState.RUNNING),
            "capabilities": len(svc.capabilities.list()),
            "runtimeTypes": svc.runtimes.types(),
        }

    @app.get("/api/compatibility/guarantees")
    async def guarantees() -> dict[str, Any]:
        return compatibility_summary()

    # ------------------------------------------------------------------ #
    # Applications
    # ------------------------------------------------------------------ #
    def _app_summary(rec) -> dict[str, Any]:
        manifest = rec.manifest
        return {
            "id": rec.app_id,
            "name": rec.name,
            "version": rec.version,
            "state": rec.state,
            "trust": rec.trust,
            "runtimeType": rec.runtime_type,
            "path": rec.path,
            "port": rec.port,
            "pid": rec.pid,
            "isBuiltin": rec.is_builtin,
            "lastError": rec.last_error,
            "provides": [c["id"] for c in manifest.get("capabilities", {}).get("provides", [])],
            "requires": [c["id"] for c in manifest.get("capabilities", {}).get("requires", [])],
            "permissions": manifest.get("permissions", []),
            "frontend": manifest.get("frontend", {}).get("entry"),
            "url": manifest.get("runtime", {}).get("url"),
            "description": manifest.get("description", ""),
        }

    @app.get("/api/apps")
    async def list_apps() -> list[dict[str, Any]]:
        return [_app_summary(r) for r in svc.registry.list()]

    @app.get("/api/apps/{app_id}")
    async def get_app(app_id: str) -> dict[str, Any]:
        try:
            rec = svc.registry.get(app_id)
        except UnknownAppError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return {**_app_summary(rec), "manifest": rec.manifest}

    @app.post("/api/apps/register")
    async def register(body: RegisterRequest) -> dict[str, Any]:
        try:
            manifest = load_manifest_file(body.path)
            rec = svc.registry.register(
                manifest, body.path, trust=body.trust, upgrade=body.upgrade
            )
        except ManifestValidationError as exc:
            raise HTTPException(status_code=422, detail={"errors": exc.errors}) from exc
        except DuplicateAppError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except RegistryError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"ok": True, "app": _app_summary(rec)}

    @app.post("/api/apps/import-static")
    async def import_static(body: ImportStaticRequest) -> dict[str, Any]:
        app_id = body.id or f"uli.imported.{slugify(body.name)}"
        try:
            target = import_static_directory(body.path, app_id)
            manifest = validate_manifest_dict(
                generated_static_manifest(body.name, app_id), source="<generated>"
            )
            rec = svc.registry.register(manifest, target, trust=TrustLevel.UNTRUSTED)
        except ManifestValidationError as exc:
            raise HTTPException(status_code=422, detail={"errors": exc.errors}) from exc
        except DuplicateAppError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return {
            "ok": True,
            "app": _app_summary(rec),
            "hostedAt": f"/host/{rec.app_id}/",
            "note": "Source files copied unchanged; only app.manifest.json was generated.",
        }

    @app.post("/api/apps/import-static-upload")
    async def import_static_upload(
        name: str = Form(...),
        app_id: str | None = Form(default=None),
        file: UploadFile = File(...),
    ) -> dict[str, Any]:
        resolved_id = app_id or f"uli.imported.{slugify(name)}"
        tmp = Path(tempfile.mkdtemp(prefix="uli-upload-"))
        try:
            archive = tmp / (file.filename or "upload.zip")
            with archive.open("wb") as fh:
                shutil.copyfileobj(file.file, fh)
            if archive.suffix.lower() != ".zip":
                raise HTTPException(status_code=415, detail="only .zip uploads are supported")
            target = safe_extract_zip(archive, resolved_id)
            manifest = validate_manifest_dict(
                generated_static_manifest(name, resolved_id), source="<generated>"
            )
            rec = svc.registry.register(manifest, target, trust=TrustLevel.UNTRUSTED)
        except ManifestValidationError as exc:
            raise HTTPException(status_code=422, detail={"errors": exc.errors}) from exc
        except DuplicateAppError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        return {"ok": True, "app": _app_summary(rec), "hostedAt": f"/host/{rec.app_id}/"}

    @app.post("/api/apps/register-external")
    async def register_external(body: ExternalRequest) -> dict[str, Any]:
        app_id = body.id or f"uli.external.{slugify(body.name)}"
        raw = {
            "manifestVersion": "1.0",
            "id": app_id,
            "name": body.name,
            "description": f"External web application: {body.url}",
            "version": "1.0.0",
            "uli": {"protocol": ">=1.0.0 <2.0.0"},
            "runtime": {"type": "external-url", "url": body.url},
            "frontend": {"embed": True},
            "capabilities": {"provides": [], "requires": []},
            "events": {"publishes": [], "subscribes": []},
            "permissions": ["net.external"],
            "dataOwner": app_id,
        }
        try:
            manifest = validate_manifest_dict(raw, source="<generated>")
            rec = svc.registry.register(manifest, config.data_dir(), trust=TrustLevel.UNTRUSTED)
        except ManifestValidationError as exc:
            raise HTTPException(status_code=422, detail={"errors": exc.errors}) from exc
        except DuplicateAppError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return {"ok": True, "app": _app_summary(rec)}

    @app.get("/api/apps/{app_id}/embed-check")
    async def embed_check(app_id: str) -> dict[str, Any]:
        rec = _require(app_id)
        if rec.runtime_type != "external-url":
            raise HTTPException(status_code=400, detail="app is not an external-url app")
        return await svc.runtimes.get("external-url").embed_check(rec)  # type: ignore[attr-defined]

    @app.post("/api/apps/{app_id}/enable")
    async def enable_app(app_id: str) -> dict[str, Any]:
        _require(app_id)
        try:
            rec = await svc.manager.enable(app_id)
        except PermissionDenied as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except RequirementNotSatisfied as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return {"ok": True, "app": _app_summary(rec)}

    @app.post("/api/apps/{app_id}/disable")
    async def disable_app(app_id: str) -> dict[str, Any]:
        _require(app_id)
        rec = await svc.manager.disable(app_id)
        return {"ok": True, "app": _app_summary(rec)}

    @app.post("/api/apps/{app_id}/start")
    async def start_app(app_id: str) -> dict[str, Any]:
        _require(app_id)
        try:
            rec, status = await svc.manager.start(app_id)
        except RequirementNotSatisfied as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except UnsupportedOperation as exc:
            raise HTTPException(status_code=501, detail=str(exc)) from exc
        except ModuleManagerError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if rec.state == AppState.ERROR:
            return JSONResponse(
                status_code=502,
                content={"ok": False, "app": _app_summary(rec), "status": status},
            )
        return {"ok": True, "app": _app_summary(rec), "status": status}

    @app.post("/api/apps/{app_id}/stop")
    async def stop_app(app_id: str) -> dict[str, Any]:
        _require(app_id)
        rec, status = await svc.manager.stop(app_id)
        return {"ok": True, "app": _app_summary(rec), "status": status}

    @app.post("/api/apps/{app_id}/restart")
    async def restart_app(app_id: str) -> dict[str, Any]:
        _require(app_id)
        rec, status = await svc.manager.restart(app_id)
        return {"ok": rec.state == AppState.RUNNING, "app": _app_summary(rec), "status": status}

    @app.get("/api/apps/{app_id}/health")
    async def app_health(app_id: str) -> dict[str, Any]:
        _require(app_id)
        return await svc.manager.health(app_id)

    @app.delete("/api/apps/{app_id}")
    async def uninstall_app(app_id: str, deleteFiles: bool = False) -> dict[str, Any]:
        _require(app_id)
        return await svc.manager.uninstall(app_id, delete_files=deleteFiles)

    # ------------------------------------------------------------------ #
    # Capabilities
    # ------------------------------------------------------------------ #
    @app.get("/api/capabilities")
    async def list_capabilities() -> list[dict[str, Any]]:
        return [c.to_dict() for c in svc.capabilities.list()]

    @app.post("/api/capabilities/validate-connection")
    async def validate_connection(body: ConnectionCheckRequest) -> dict[str, Any]:
        ok, reason = port_types_compatible(body.sourceOutputType, body.targetInputType)
        return {"compatible": ok, "reason": reason}

    @app.post("/api/capabilities/{capability_id:path}/invoke")
    async def invoke_capability(
        capability_id: str,
        body: InvokeRequest,
        authorization: str | None = Header(default=None),
        x_uli_correlation_id: str | None = Header(default=None),
    ) -> dict[str, Any]:
        caller = _resolve_caller(authorization)
        try:
            return await svc.manager.invoke_capability(
                capability_id,
                body.input,
                version_range=body.versionRange,
                caller_app_id=caller,
                request_id=x_uli_correlation_id,
            )
        except PermissionDenied as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except PayloadValidationError as exc:
            raise HTTPException(status_code=422, detail={"errors": exc.errors, "label": exc.label}) from exc
        except ApplicationNotRunning as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except ModuleManagerError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    # ------------------------------------------------------------------ #
    # Events
    # ------------------------------------------------------------------ #
    @app.get("/api/events")
    async def recent_events(limit: int = 50) -> list[dict[str, Any]]:
        return svc.bus.recent(limit=limit)

    @app.post("/api/events/publish")
    async def publish_event(
        body: PublishRequest,
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        caller = _resolve_caller(authorization)
        try:
            return await svc.manager.publish_event(
                body.name,
                body.version,
                body.payload,
                source=caller or "uli.ui",
                correlation_id=body.correlationId,
                caller_app_id=caller,
            )
        except PermissionDenied as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except PayloadValidationError as exc:
            raise HTTPException(status_code=422, detail={"errors": exc.errors}) from exc

    # ------------------------------------------------------------------ #
    # Blueprints
    # ------------------------------------------------------------------ #
    @app.get("/api/blueprints")
    async def list_blueprints() -> list[dict[str, Any]]:
        return svc.blueprints.list()

    @app.post("/api/blueprints")
    async def save_blueprint(blueprint: dict[str, Any]) -> dict[str, Any]:
        try:
            return svc.blueprints.save(blueprint)
        except BlueprintValidationError as exc:
            raise HTTPException(status_code=422, detail={"errors": exc.errors}) from exc

    @app.get("/api/blueprints/{blueprint_id}")
    async def get_blueprint(blueprint_id: str) -> dict[str, Any]:
        try:
            return svc.blueprints.get(blueprint_id)
        except BlueprintNotFound as exc:
            raise HTTPException(status_code=404, detail=f"unknown blueprint {blueprint_id!r}") from exc

    @app.delete("/api/blueprints/{blueprint_id}")
    async def delete_blueprint(blueprint_id: str) -> dict[str, Any]:
        return {"ok": svc.blueprints.delete(blueprint_id)}

    @app.post("/api/blueprints/validate")
    async def validate_blueprint(blueprint: dict[str, Any]) -> dict[str, Any]:
        return svc.engine.validate(blueprint)

    @app.post("/api/blueprints/{blueprint_id}/validate")
    async def validate_saved_blueprint(blueprint_id: str) -> dict[str, Any]:
        try:
            return svc.engine.validate(svc.blueprints.get(blueprint_id))
        except BlueprintNotFound as exc:
            raise HTTPException(status_code=404, detail=f"unknown blueprint {blueprint_id!r}") from exc

    @app.post("/api/blueprints/{blueprint_id}/execute")
    async def execute_blueprint(
        blueprint_id: str,
        body: InvokeRequest,
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        try:
            blueprint = svc.blueprints.get(blueprint_id)
        except BlueprintNotFound as exc:
            raise HTTPException(status_code=404, detail=f"unknown blueprint {blueprint_id!r}") from exc
        caller = _resolve_caller(authorization)
        try:
            return await svc.engine.execute(blueprint, body.input, caller_app_id=caller)
        except BlueprintExecutionError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except PayloadValidationError as exc:
            raise HTTPException(status_code=422, detail={"errors": exc.errors}) from exc

    # ------------------------------------------------------------------ #
    # Themes
    # ------------------------------------------------------------------ #
    @app.get("/api/themes")
    async def list_themes() -> dict[str, Any]:
        return {"active": svc.themes.active_id(), "themes": svc.themes.list()}

    @app.get("/api/themes/{theme_id:path}")
    async def get_theme(theme_id: str) -> dict[str, Any]:
        try:
            return svc.themes.get(theme_id)
        except ThemeNotFound as exc:
            raise HTTPException(status_code=404, detail=f"unknown theme {theme_id!r}") from exc

    @app.post("/api/themes/{theme_id:path}/activate")
    async def activate_theme(theme_id: str) -> dict[str, Any]:
        try:
            return {"ok": True, "theme": svc.themes.activate(theme_id)}
        except ThemeNotFound as exc:
            raise HTTPException(status_code=404, detail=f"unknown theme {theme_id!r}") from exc

    @app.get("/api/runtime-types")
    async def runtime_types() -> dict[str, Any]:
        return {
            "implemented": svc.runtimes.types(),
            "documentedExtensions": ["local-node", "server", "container"],
        }

    # ------------------------------------------------------------------ #
    # Static hosting of applications (Legacy Track + native frontends)
    # ------------------------------------------------------------------ #
    @app.get("/host/{app_id}/{path:path}")
    async def host_app(app_id: str, path: str = "") -> Any:
        rec = svc.registry.find(app_id)
        if rec is None:
            raise HTTPException(status_code=404, detail=f"unknown app {app_id!r}")
        base = _host_base(rec)
        if base is None:
            raise HTTPException(status_code=404, detail="app has no hostable frontend")
        candidate = (base / path).resolve() if path else (base / "index.html").resolve()
        base_resolved = base.resolve()
        if base_resolved not in candidate.parents and candidate != base_resolved:
            raise HTTPException(status_code=403, detail="path escapes application root")
        if candidate.is_dir():
            candidate = candidate / "index.html"
        if not candidate.is_file():
            # SPA fallback
            fallback = base / "index.html"
            if fallback.is_file():
                candidate = fallback
            else:
                raise HTTPException(status_code=404, detail=f"not found: {path}")
        return FileResponse(candidate)

    # ------------------------------------------------------------------ #
    # UI
    # ------------------------------------------------------------------ #
    dist = config.frontend_dist_dir()
    if dist.is_dir() and (dist / "index.html").is_file():
        app.mount("/ui", StaticFiles(directory=dist, html=True), name="ui")

        @app.get("/")
        async def root_redirect() -> Any:
            return RedirectResponse(url="/ui/")
    else:
        @app.get("/", response_class=HTMLResponse)
        async def root_info() -> str:
            return (
                "<h1>ULI Core</h1>"
                "<p>Backend is running. The web UI is not built yet. "
                "Run <code>frontend/build</code> or see <code>/docs</code>.</p>"
                f"<p>API docs: <a href='/docs'>/docs</a></p>"
            )

    # ------------------------------------------------------------------ #
    def _require(app_id: str):
        try:
            return svc.registry.get(app_id)
        except UnknownAppError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    def _resolve_caller(authorization: str | None) -> str | None:
        if not authorization:
            return None
        token = authorization.removeprefix("Bearer ").strip() if authorization.startswith("Bearer ") else authorization
        return svc.runtimes.local_python().app_id_for_token(token)

    def _host_base(rec) -> Path | None:
        runtime = rec.manifest.get("runtime", {})
        if runtime.get("type") == "static-site":
            raw = runtime.get("staticDir") or "."
            return (Path(rec.path) / raw).resolve()
        entry = rec.manifest.get("frontend", {}).get("entry")
        if entry:
            # If entry points at index.html, serve its parent directory.
            p = Path(entry)
            parent = p.parent if p.suffix else p
            return (Path(rec.path) / parent).resolve()
        return None

    return app
