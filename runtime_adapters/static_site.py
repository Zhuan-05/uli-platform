"""Static website runtime.

Serves a directory of already-built web assets from the ULI Core origin. The
original website is *not* rewritten - it is hosted as-is under
``/host/<app-id>/``. This is "hosting compatibility", not "functional
integration"; deep integration still requires the Native Track / an Adapter.
"""
from __future__ import annotations

from pathlib import Path

from core.models import ApplicationRecord, AppState
from runtime_adapters.base import RuntimeAdapter, RuntimeStatus


class StaticSiteRuntime(RuntimeAdapter):
    type = "static-site"
    executes_process = False
    supports_capabilities = False

    def _site_dir(self, record: ApplicationRecord) -> Path:
        manifest = record.manifest
        runtime = manifest.get("runtime", {})
        raw = runtime.get("staticDir") or "."
        return (Path(record.path) / raw).resolve()

    async def start(self, record: ApplicationRecord) -> RuntimeStatus:
        site = self._site_dir(record)
        if not site.is_dir():
            return RuntimeStatus(
                state=AppState.ERROR,
                detail=f"static site directory not found: {site}",
            )
        index = site / "index.html"
        if not index.is_file():
            # Not fatal, but worth surfacing clearly.
            return RuntimeStatus(
                state=AppState.RUNNING,
                detail=f"served at /host/{record.app_id}/ (no index.html found)",
            )
        return RuntimeStatus(
            state=AppState.RUNNING,
            detail=f"served at /host/{record.app_id}/",
        )

    async def stop(self, record: ApplicationRecord) -> RuntimeStatus:
        # Nothing to tear down; static hosting is stateless.
        return RuntimeStatus(state=AppState.STOPPED, detail="static host released")

    async def status(self, record: ApplicationRecord) -> RuntimeStatus:
        site = self._site_dir(record)
        if not site.is_dir():
            return RuntimeStatus(state=AppState.ERROR, detail=f"missing directory: {site}")
        return RuntimeStatus(
            state=record.state,
            detail=f"served at /host/{record.app_id}/",
        )
