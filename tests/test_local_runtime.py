import asyncio
import copy
import socket
from pathlib import Path

import pytest

from compatibility.validator import load_manifest_file, validate_manifest_dict
from core import config
from core.models import TrustLevel
from tests.conftest import make_manifest


def test_port_conflict_falls_back_to_free_port(services):
    src = config.builtin_apps_dir() / "inventory_app"
    raw = copy.deepcopy(load_manifest_file(src).raw)
    raw["id"] = "uli.test.portconflict"

    holder = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    holder.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    holder.bind(("127.0.0.1", 0))
    holder.listen(1)
    occupied = holder.getsockname()[1]
    raw["runtime"]["port"] = occupied

    manifest = validate_manifest_dict(raw, source="<t>")
    services.registry.register(manifest, src, trust=TrustLevel.TRUSTED, is_builtin=True)

    try:
        rec, status = asyncio.run(services.manager.start("uli.test.portconflict"))
        assert rec.state == "running", status
        assert rec.port and rec.port != occupied
        assert "was busy" in status["detail"]
    finally:
        asyncio.run(services.manager.stop("uli.test.portconflict"))
        holder.close()


def test_failed_startup_missing_entry_is_handled(services):
    manifest = validate_manifest_dict(
        make_manifest(
            "uli.test.badstart",
            runtime={"type": "local-python", "entry": "backend/missing.py"},
        ),
        source="<t>",
    )
    services.registry.register(manifest, Path("."), trust=TrustLevel.TRUSTED, is_builtin=True)

    rec, status = asyncio.run(services.manager.start("uli.test.badstart"))
    assert rec.state == "error"
    assert "not found" in status["detail"]
    assert rec.last_error


def test_untrusted_local_python_is_refused(services):
    from module_manager import PermissionDenied

    manifest = validate_manifest_dict(
        make_manifest(
            "uli.test.untrusted",
            runtime={"type": "local-python", "entry": "backend/app.py"},
        ),
        source="<t>",
    )
    services.registry.register(manifest, Path("."), trust=TrustLevel.UNTRUSTED)

    with pytest.raises(PermissionDenied):
        asyncio.run(services.manager.enable("uli.test.untrusted"))
