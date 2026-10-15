"""ULI SDK - the Native Track.

A native ULI application imports this package, declares its capabilities and
event handlers, and runs the returned FastAPI app. The SDK then exposes the
standard ULI service endpoints (``/health``, ``/uli/invoke``, ``/uli/events``)
so ULI Core can drive the application without knowing anything about its
internals. It also provides ``invoke``/``publish`` clients for calling *other*
applications through the Core broker.
"""
from __future__ import annotations

import inspect
import os
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

import httpx
import uvicorn
from fastapi import FastAPI, Header, HTTPException, Request
from jsonschema import Draft202012Validator

Handler = Callable[[dict[str, Any]], Any] | Callable[[dict[str, Any]], Awaitable[Any]]
EventCallback = Callable[[dict[str, Any]], Any] | Callable[[dict[str, Any]], Awaitable[Any]]


@dataclass
class ProvidedCapability:
    id: str
    version: str
    handler: Handler
    input_schema: dict[str, Any] = field(default_factory=dict)
    output_schema: dict[str, Any] = field(default_factory=dict)
    input_type: str = "*"
    output_type: str = "*"
    description: str = ""
    timeout_ms: int = 5000


class ULIClientError(RuntimeError):
    pass


class ULIService:
    def __init__(
        self,
        app_id: str,
        version: str = "1.0.0",
        *,
        core_url: str | None = None,
        token: str | None = None,
        name: str | None = None,
    ) -> None:
        self.app_id = app_id
        self.version = version
        self.name = name or app_id
        self.core_url = (core_url or os.environ.get("ULI_CORE_URL", "http://127.0.0.1:8787")).rstrip("/")
        self.token = token if token is not None else os.environ.get("ULI_APP_TOKEN", "")
        self._providers: dict[str, ProvidedCapability] = {}
        self._event_handlers: dict[str, list[EventCallback]] = {}
        self._startup_hooks: list[Callable[[], Any]] = []

    # ------------------------------------------------------------------ #
    # Declaration API
    # ------------------------------------------------------------------ #
    def provide(
        self,
        capability_id: str,
        version: str,
        handler: Handler,
        *,
        input_schema: dict[str, Any] | None = None,
        output_schema: dict[str, Any] | None = None,
        input_type: str = "*",
        output_type: str = "*",
        description: str = "",
        timeout_ms: int = 5000,
    ) -> None:
        if capability_id in self._providers:
            raise ValueError(f"Capability {capability_id!r} already provided")
        self._providers[capability_id] = ProvidedCapability(
            id=capability_id,
            version=version,
            handler=handler,
            input_schema=input_schema or {},
            output_schema=output_schema or {},
            input_type=input_type,
            output_type=output_type,
            description=description,
            timeout_ms=timeout_ms,
        )

    def on_event(self, event_name: str, callback: EventCallback) -> None:
        self._event_handlers.setdefault(event_name, []).append(callback)

    def on_startup(self, hook: Callable[[], Any]) -> None:
        self._startup_hooks.append(hook)

    def capabilities(self) -> list[ProvidedCapability]:
        return list(self._providers.values())

    # ------------------------------------------------------------------ #
    # Client API (calling other apps via the Core broker)
    # ------------------------------------------------------------------ #
    async def invoke(
        self,
        capability_id: str,
        payload: dict[str, Any],
        *,
        version_range: str = "*",
        correlation_id: str | None = None,
        timeout: float = 30.0,
    ) -> Any:
        url = f"{self.core_url}/api/capabilities/{capability_id}/invoke"
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        if correlation_id:
            headers["X-ULI-Correlation-Id"] = correlation_id
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(
                    url,
                    json={"input": payload, "versionRange": version_range},
                    headers=headers,
                )
        except httpx.HTTPError as exc:
            raise ULIClientError(f"cannot reach ULI Core at {self.core_url}: {exc}") from exc

        if resp.status_code >= 400:
            try:
                detail = resp.json().get("detail")
            except ValueError:
                detail = resp.text
            raise ULIClientError(f"capability {capability_id} failed: {detail}")
        return resp.json()["output"]

    async def publish(
        self,
        name: str,
        payload: dict[str, Any],
        *,
        version: str = "1.0.0",
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{self.core_url}/api/events/publish",
                json={"name": name, "version": version, "payload": payload, "correlationId": correlation_id},
                headers=headers,
            )
        if resp.status_code >= 400:
            detail = resp.json().get("detail") if resp.headers.get("content-type", "").startswith("application/json") else resp.text
            raise ULIClientError(f"publish {name} failed: {detail}")
        return resp.json()

    # ------------------------------------------------------------------ #
    # FastAPI application
    # ------------------------------------------------------------------ #
    def create_app(self) -> FastAPI:
        from contextlib import asynccontextmanager

        service = self

        @asynccontextmanager
        async def lifespan(_app: FastAPI):
            for hook in service._startup_hooks:
                result = hook()
                if inspect.isawaitable(result):
                    await result
            yield

        app = FastAPI(title=f"ULI App: {self.name}", version=self.version, lifespan=lifespan)

        @app.get("/health")
        async def health() -> dict[str, Any]:
            return {
                "status": "ok",
                "appId": service.app_id,
                "version": service.version,
                "capabilities": [c.id for c in service.capabilities()],
            }

        @app.get("/uli/info")
        async def info() -> dict[str, Any]:
            return {
                "appId": service.app_id,
                "version": service.version,
                "capabilities": [
                    {
                        "id": c.id,
                        "version": c.version,
                        "inputType": c.input_type,
                        "outputType": c.output_type,
                        "description": c.description,
                    }
                    for c in service.capabilities()
                ],
            }

        @app.post("/uli/invoke")
        async def invoke_endpoint(
            request: Request,
            authorization: str | None = Header(default=None),
        ) -> dict[str, Any]:
            service._check_token(authorization)
            body = await request.json()
            capability_id = body.get("capability")
            provider = service._providers.get(capability_id)
            if provider is None:
                raise HTTPException(status_code=404, detail=f"unknown capability {capability_id!r}")

            payload = body.get("input", {})
            service._validate(provider.input_schema, payload, "input")
            try:
                result = provider.handler(payload)
                if inspect.isawaitable(result):
                    result = await result
            except Exception as exc:  # noqa: BLE001 - surface handler errors as ULI errors
                raise HTTPException(status_code=500, detail=f"handler error: {exc}") from exc
            service._validate(provider.output_schema, result, "output")
            return {"ok": True, "output": result, "contractVersion": provider.version}

        @app.post("/uli/events")
        async def events_endpoint(
            request: Request,
            authorization: str | None = Header(default=None),
        ) -> dict[str, Any]:
            service._check_token(authorization)
            event = await request.json()
            handlers = service._event_handlers.get(event.get("name", ""), [])
            delivered = 0
            for handler in handlers:
                result = handler(event)
                if inspect.isawaitable(result):
                    await result
                delivered += 1
            return {"ok": True, "delivered": delivered}

        return app

    # ------------------------------------------------------------------ #
    def run(self) -> None:  # pragma: no cover - exercised via subprocess
        port = int(os.environ.get("ULI_APP_PORT", "0"))
        host = os.environ.get("ULI_APP_HOST", "127.0.0.1")
        uvicorn.run(self.create_app(), host=host, port=port, log_level="warning")

    # ------------------------------------------------------------------ #
    @staticmethod
    def _validate(schema: dict[str, Any], payload: Any, label: str) -> None:
        if not schema:
            return
        errors = sorted(Draft202012Validator(schema).iter_errors(payload), key=lambda e: list(e.absolute_path))
        if errors:
            first = errors[0]
            path = "/".join(str(p) for p in first.absolute_path) or "<root>"
            raise HTTPException(status_code=422, detail=f"{label} schema error at {path}: {first.message}")

    def _check_token(self, authorization: str | None) -> None:
        expected = os.environ.get("ULI_APP_TOKEN", "")
        if not expected:
            return  # dev mode: no token configured
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="missing bearer token")
        provided = authorization.removeprefix("Bearer ").strip()
        import hmac

        if not hmac.compare_digest(provided, expected):
            raise HTTPException(status_code=403, detail="invalid bearer token")
