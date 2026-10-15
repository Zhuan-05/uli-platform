"""Runtime Adapter interface.

Every runtime type (static site, external URL, local process, future server /
container) implements this interface. ULI Core only ever talks to runtimes
through these methods, which is what makes new runtime types additive rather
than invasive.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from core.models import ApplicationRecord, CapabilitySpec


@dataclass
class RuntimeStatus:
    state: str
    port: int | None = None
    pid: int | None = None
    detail: str = ""
    healthy: bool | None = None
    embedding: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class RuntimeError_(Exception):
    pass


class UnsupportedOperation(RuntimeError_):
    pass


class RuntimeAdapter(ABC):
    """Base class for runtime adapters."""

    type: str = "abstract"
    #: whether the runtime executes a local process that must be trusted
    executes_process: bool = False
    #: whether the runtime can host ULI capability invocations
    supports_capabilities: bool = False

    def __init__(self, app_root: Path | None = None) -> None:
        self.app_root = app_root

    @abstractmethod
    async def start(self, record: ApplicationRecord) -> RuntimeStatus:
        ...

    @abstractmethod
    async def stop(self, record: ApplicationRecord) -> RuntimeStatus:
        ...

    @abstractmethod
    async def status(self, record: ApplicationRecord) -> RuntimeStatus:
        ...

    async def invoke(
        self,
        record: ApplicationRecord,
        capability: CapabilitySpec,
        payload: dict[str, Any],
        *,
        token: str | None = None,
    ) -> Any:
        raise UnsupportedOperation(
            f"Runtime {self.type!r} cannot invoke capabilities"
        )

    def resolve_path(self, record: ApplicationRecord, relative: str) -> Path:
        return (Path(record.path) / relative).resolve()
