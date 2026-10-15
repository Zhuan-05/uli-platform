"""Runtime adapter factory / registry.

Adding a new runtime type (server, container) means implementing
:class:`RuntimeAdapter` and registering it here. ULI Core is unchanged.
"""
from __future__ import annotations

from runtime_adapters.base import (
    RuntimeAdapter,
    RuntimeError_,
    RuntimeStatus,
    UnsupportedOperation,
)
from runtime_adapters.external_url import ExternalUrlRuntime
from runtime_adapters.in_process import InProcessRuntime
from runtime_adapters.local_python import LocalPythonRuntime
from runtime_adapters.static_site import StaticSiteRuntime


class RuntimeAdapterRegistry:
    def __init__(self) -> None:
        self._adapters: dict[str, RuntimeAdapter] = {}
        for adapter in (
            StaticSiteRuntime(),
            ExternalUrlRuntime(),
            LocalPythonRuntime(),
            InProcessRuntime(),
        ):
            self._adapters[adapter.type] = adapter

    def get(self, runtime_type: str) -> RuntimeAdapter:
        try:
            return self._adapters[runtime_type]
        except KeyError:
            raise UnsupportedOperation(
                f"No runtime adapter for type {runtime_type!r}. "
                f"Available: {', '.join(sorted(self._adapters))}"
            ) from None

    def types(self) -> list[str]:
        return sorted(self._adapters)

    def local_python(self) -> LocalPythonRuntime:
        return self._adapters["local-python"]  # type: ignore[return-value]


__all__ = [
    "ExternalUrlRuntime",
    "InProcessRuntime",
    "LocalPythonRuntime",
    "RuntimeAdapter",
    "RuntimeAdapterRegistry",
    "RuntimeError_",
    "RuntimeStatus",
    "StaticSiteRuntime",
    "UnsupportedOperation",
]
