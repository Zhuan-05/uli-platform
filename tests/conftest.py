"""Shared pytest fixtures for the ULI test suite."""
from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest

from core.models import TrustLevel


@pytest.fixture()
def uli_env(tmp_path, monkeypatch):
    """Isolated data dir + fresh service graph for every test."""
    data = tmp_path / "data"
    monkeypatch.setenv("ULI_DATA_DIR", str(data))
    monkeypatch.setenv("ULI_CORE_URL", "http://127.0.0.1:9")  # unreachable unless overridden
    monkeypatch.delenv("ULI_APP_TOKEN", raising=False)

    from core.services import reset_services

    reset_services()
    from runtime_adapters.in_process import InProcessRuntime

    InProcessRuntime.clear()
    yield tmp_path
    InProcessRuntime.clear()
    reset_services()


@pytest.fixture()
def services(uli_env):
    from core.services import Services

    return Services()


@pytest.fixture()
def client(services):
    from fastapi.testclient import TestClient

    from core.server import create_app

    return TestClient(create_app(services))


# --------------------------------------------------------------------------- #
# Manifest helpers
# --------------------------------------------------------------------------- #
def make_manifest(
    app_id: str = "uli.test.app",
    *,
    runtime: dict[str, Any] | None = None,
    provides: list[dict[str, Any]] | None = None,
    requires: list[dict[str, Any]] | None = None,
    permissions: list[str] | None = None,
    publishes: list[dict[str, Any]] | None = None,
    subscribes: list[dict[str, Any]] | None = None,
    version: str = "1.0.0",
) -> dict[str, Any]:
    return {
        "manifestVersion": "1.0",
        "id": app_id,
        "name": app_id,
        "version": version,
        "uli": {"protocol": ">=1.0.0 <2.0.0"},
        "runtime": runtime or {"type": "in-process"},
        "frontend": {},
        "capabilities": {
            "provides": provides or [],
            "requires": requires or [],
        },
        "events": {"publishes": publishes or [], "subscribes": subscribes or []},
        "permissions": permissions or ["data.own"],
        "dataOwner": app_id,
    }


def capability(
    cap_id: str,
    *,
    version: str = "1.0.0",
    input_type: str = "uli.test.req@1",
    output_type: str = "uli.test.res@1",
    input_schema: dict[str, Any] | None = None,
    output_schema: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "id": cap_id,
        "version": version,
        "inputType": input_type,
        "outputType": output_type,
        "inputSchema": input_schema or {"type": "object"},
        "outputSchema": output_schema or {"type": "object"},
    }


def register_in_process(services, manifest: dict[str, Any], handler_map: dict[str, Any]) -> None:
    """Register + start an in-process app with the given capability handlers."""
    from compatibility.validator import validate_manifest_dict
    from runtime_adapters.in_process import InProcessRuntime

    parsed = validate_manifest_dict(manifest, source="<test>")
    services.registry.register(parsed, Path("."), trust=TrustLevel.TRUSTED, is_builtin=True)
    for cap_id, handler in handler_map.items():
        InProcessRuntime.register_handler(manifest["id"], cap_id, handler)
