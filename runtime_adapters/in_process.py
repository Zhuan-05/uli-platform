"""In-process runtime.

Used only for Core-internal providers and for fast, deterministic tests. It runs
handlers in the ULI Core process, which means it offers no isolation and MUST
NOT be used for third-party code. The module manager restricts it accordingly.
"""
from __future__ import annotations

import inspect
from typing import Any, Awaitable, Callable

from core.models import ApplicationRecord, AppState, CapabilitySpec
from runtime_adapters.base import RuntimeAdapter, RuntimeStatus

Handler = Callable[[dict[str, Any]], Any] | Callable[[dict[str, Any]], Awaitable[Any]]


class InProcessRuntime(RuntimeAdapter):
    type = "in-process"
    executes_process = False
    supports_capabilities = True

    # Class-level so tests can register handlers without owning an adapter.
    _handlers: dict[str, dict[str, Handler]] = {}
    _running: set[str] = set()

    @classmethod
    def register_handler(cls, app_id: str, capability_id: str, handler: Handler) -> None:
        cls._handlers.setdefault(app_id, {})[capability_id] = handler
        cls._running.add(app_id)

    @classmethod
    def clear(cls) -> None:
        cls._handlers.clear()
        cls._running.clear()

    async def start(self, record: ApplicationRecord) -> RuntimeStatus:
        self._running.add(record.app_id)
        return RuntimeStatus(state=AppState.RUNNING, detail="in-process")

    async def stop(self, record: ApplicationRecord) -> RuntimeStatus:
        self._running.discard(record.app_id)
        return RuntimeStatus(state=AppState.STOPPED, detail="in-process stopped")

    async def status(self, record: ApplicationRecord) -> RuntimeStatus:
        state = AppState.RUNNING if record.app_id in self._running else AppState.STOPPED
        return RuntimeStatus(state=state, detail="in-process")

    async def invoke(
        self,
        record: ApplicationRecord,
        capability: CapabilitySpec,
        payload: dict[str, Any],
        *,
        token: str | None = None,
    ) -> Any:
        handler = self._handlers.get(record.app_id, {}).get(capability.id)
        if handler is None:
            raise RuntimeError(
                f"in-process app {record.app_id!r} has no handler for {capability.id!r}"
            )
        result = handler(payload)
        if inspect.isawaitable(result):
            result = await result
        return result
