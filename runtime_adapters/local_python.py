"""Trusted local Python service runtime.

This is the one MVP runtime that executes application code as a child process.
It is gated on the application being registered with ``trust=trusted``; an
untrusted manifest can never reach this code path. The child gets:

* an OS-allocated loopback port (with fallback on conflict),
* a freshly generated per-app bearer token passed via environment,
* the ULI Core URL for capability callbacks,
* the repository root on ``PYTHONPATH`` so the ULI SDK is importable.

Isolation honesty: this is *process-level* isolation, not a sandbox. A spawned
app runs with the same OS user and can read anything that user can read. It must
therefore only be used with reviewed, trusted applications.
"""
from __future__ import annotations

import asyncio
import os
import secrets
import socket
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from core import config
from core.models import ApplicationRecord, AppState, CapabilitySpec, TrustLevel
from runtime_adapters.base import RuntimeAdapter, RuntimeStatus


@dataclass
class ProcInfo:
    process: subprocess.Popen
    port: int
    token: str
    entry: str
    logfile: Any


def is_port_free(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind((host, port))
            return True
        except OSError:
            return False


def allocate_port(preferred: int = 0, host: str = "127.0.0.1") -> tuple[int, bool]:
    """Return ``(port, conflicted)``.

    If ``preferred`` is free it is used; otherwise an ephemeral free port is
    chosen and ``conflicted=True`` signals the fallback so callers can warn.
    """
    if preferred and is_port_free(preferred, host):
        return preferred, False
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, 0))
        port = s.getsockname()[1]
    return port, bool(preferred)


class LocalPythonRuntime(RuntimeAdapter):
    type = "local-python"
    executes_process = True
    supports_capabilities = True

    def __init__(self, app_root: Path | None = None) -> None:
        super().__init__(app_root)
        self._procs: dict[str, ProcInfo] = {}
        self.core_url = config.core_url()

    # ------------------------------------------------------------------ #
    async def start(self, record: ApplicationRecord) -> RuntimeStatus:
        if record.trust != TrustLevel.TRUSTED:
            return RuntimeStatus(
                state=AppState.ERROR,
                detail=(
                    "refusing to execute local-python application: it is not registered "
                    "as trusted. Re-register with trust='trusted' after reviewing the code."
                ),
            )

        existing = self._procs.get(record.app_id)
        if existing and existing.process.poll() is None:
            return RuntimeStatus(
                state=AppState.RUNNING, port=existing.port, pid=existing.process.pid,
                detail="already running",
            )

        runtime = record.manifest.get("runtime", {})
        entry_rel = runtime.get("entry")
        if not entry_rel:
            return RuntimeStatus(state=AppState.ERROR, detail="no runtime.entry configured")
        entry = (Path(record.path) / entry_rel).resolve()
        if not entry.is_file():
            return RuntimeStatus(state=AppState.ERROR, detail=f"entry point not found: {entry}")

        working_dir = runtime.get("workingDir")
        cwd = (Path(record.path) / working_dir).resolve() if working_dir else Path(record.path)
        if not cwd.is_dir():
            return RuntimeStatus(state=AppState.ERROR, detail=f"workingDir not found: {cwd}")

        preferred = int(runtime.get("port", 0) or 0)
        port, conflicted = allocate_port(preferred)
        token = secrets.token_urlsafe(32)

        env = os.environ.copy()
        env.update({k: str(v) for k, v in runtime.get("env", {}).items()})
        env.update(
            {
                "ULI_APP_ID": record.app_id,
                "ULI_APP_PORT": str(port),
                "ULI_APP_TOKEN": token,
                "ULI_CORE_URL": self.core_url,
                "PYTHONPATH": os.pathsep.join(
                    [str(config.ROOT)] + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else [])
                ),
                "PYTHONUNBUFFERED": "1",
            }
        )

        logfile = open(config.log_dir() / f"{_safe(record.app_id)}.log", "ab")
        creationflags = 0
        if os.name == "nt":  # pragma: no cover - Windows only
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

        try:
            proc = subprocess.Popen(  # noqa: S603 - trusted apps only, by design
                [sys.executable, str(entry)],
                cwd=str(cwd),
                env=env,
                stdout=logfile,
                stderr=subprocess.STDOUT,
                creationflags=creationflags,
            )
        except OSError as exc:
            logfile.close()
            return RuntimeStatus(state=AppState.ERROR, detail=f"failed to spawn process: {exc}")

        self._procs[record.app_id] = ProcInfo(proc, port, token, str(entry), logfile)

        health_path = runtime.get("healthPath", "/health")
        healthy = await self._wait_healthy(proc, port, health_path, timeout=40.0)
        if not healthy:
            detail = (
                f"process {proc.pid} did not become healthy on port {port} "
                f"(path {health_path}); see log"
            )
            await self.stop(record)
            return RuntimeStatus(state=AppState.ERROR, detail=detail)

        extra = f" (port {preferred} was busy; using {port})" if conflicted else ""
        return RuntimeStatus(
            state=AppState.RUNNING,
            port=port,
            pid=proc.pid,
            healthy=True,
            detail=f"running on 127.0.0.1:{port}{extra}",
        )

    async def stop(self, record: ApplicationRecord) -> RuntimeStatus:
        info = self._procs.get(record.app_id)
        if info is None:
            return RuntimeStatus(state=AppState.STOPPED, detail="not running (no tracked process)")
        proc = info.process
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=8)
            except subprocess.TimeoutExpired:
                proc.kill()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    pass
        try:
            info.logfile.close()
        except Exception:  # noqa: BLE001
            pass
        self._procs.pop(record.app_id, None)
        return RuntimeStatus(state=AppState.STOPPED, detail="stopped")

    async def status(self, record: ApplicationRecord) -> RuntimeStatus:
        info = self._procs.get(record.app_id)
        if info is None:
            return RuntimeStatus(state=record.state, detail="no tracked process")
        if info.process.poll() is not None:
            return RuntimeStatus(
                state=AppState.ERROR,
                pid=info.process.pid,
                port=info.port,
                detail=f"process exited with code {info.process.returncode}",
            )
        return RuntimeStatus(
            state=AppState.RUNNING, pid=info.process.pid, port=info.port,
            healthy=True, detail="process alive",
        )

    async def invoke(
        self,
        record: ApplicationRecord,
        capability: CapabilitySpec,
        payload: dict[str, Any],
        *,
        token: str | None = None,
    ) -> Any:
        info = self._procs.get(record.app_id)
        if info is None or info.process.poll() is not None:
            raise RuntimeError(
                f"application {record.app_id!r} is not running; cannot invoke {capability.id!r}"
            )
        timeout = max(capability.timeout_ms, 100) / 1000.0
        url = f"http://127.0.0.1:{info.port}/uli/invoke"
        headers = {"Authorization": f"Bearer {info.token}"}
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                url,
                json={
                    "capability": capability.id,
                    "version": capability.version,
                    "input": payload,
                },
                headers=headers,
            )
        try:
            body = resp.json()
        except ValueError as exc:
            raise RuntimeError(
                f"provider returned non-JSON response (HTTP {resp.status_code})"
            ) from exc
        if resp.status_code >= 400 or not body.get("ok", False):
            raise RuntimeError(
                f"provider error (HTTP {resp.status_code}): {body.get('error') or body}"
            )
        return body.get("output")

    def token_for(self, app_id: str) -> str | None:
        info = self._procs.get(app_id)
        return info.token if info else None

    def app_id_for_token(self, token: str) -> str | None:
        for app_id, info in self._procs.items():
            if secrets.compare_digest(info.token, token):
                return app_id
        return None

    def base_url_for(self, app_id: str) -> str | None:
        info = self._procs.get(app_id)
        return f"http://127.0.0.1:{info.port}" if info else None

    # ------------------------------------------------------------------ #
    async def _wait_healthy(
        self, proc: subprocess.Popen, port: int, health_path: str, timeout: float
    ) -> bool:
        deadline = asyncio.get_event_loop().time() + timeout
        url = f"http://127.0.0.1:{port}{health_path}"
        async with httpx.AsyncClient(timeout=3.0) as client:
            while asyncio.get_event_loop().time() < deadline:
                if proc.poll() is not None:
                    return False  # crashed early
                try:
                    resp = await client.get(url)
                    if resp.status_code < 500:
                        return True
                except httpx.HTTPError:
                    pass
                await asyncio.sleep(0.4)
        return False


def _safe(app_id: str) -> str:
    return "".join(c if c.isalnum() or c in "._-" else "_" for c in app_id)
