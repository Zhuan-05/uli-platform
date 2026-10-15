"""True end-to-end integration test.

Boots a *real* ULI Core under uvicorn, then drives it over HTTP exactly like the
frontend would. The Order App calls back into Core to run inventory.check, which
Core brokers to the Inventory App process. Nothing is mocked.
"""
from __future__ import annotations

import socket
import threading
import time

import httpx
import pytest

from core.bootstrap import ensure_builtin_apps
from core.services import Services


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture()
def live_core(tmp_path, monkeypatch):
    port = _free_port()
    monkeypatch.setenv("ULI_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("ULI_CORE_HOST", "127.0.0.1")
    monkeypatch.setenv("ULI_CORE_PORT", str(port))
    monkeypatch.setenv("ULI_CORE_URL", f"http://127.0.0.1:{port}")

    from core.services import reset_services

    reset_services()

    from core.server import create_app

    services = Services()
    ensure_builtin_apps(services.registry)
    app = create_app(services)

    import uvicorn

    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    base = f"http://127.0.0.1:{port}"
    deadline = time.time() + 20
    while time.time() < deadline:
        try:
            if httpx.get(f"{base}/api/health", timeout=1.0).status_code == 200:
                break
        except httpx.HTTPError:
            time.sleep(0.2)
    else:
        raise RuntimeError("ULI Core did not start in time")

    yield base, services

    try:
        for rec in services.registry.list():
            try:
                httpx.post(f"{base}/api/apps/{rec.app_id}/stop", timeout=10)
            except httpx.HTTPError:
                pass
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        reset_services()


def test_order_to_inventory_cross_application_flow(live_core):
    base, _ = live_core
    with httpx.Client(base_url=base, timeout=60) as c:
        assert c.get("/api/health").json()["applications"] >= 2

        # Start the provider first, then the consumer.
        inv = c.post("/api/apps/uli.examples.inventory/start")
        assert inv.status_code == 200 and inv.json()["ok"], inv.text
        order = c.post("/api/apps/uli.examples.order/start")
        assert order.status_code == 200 and order.json()["ok"], order.text

        # Order in stock -> confirmed, availability comes from the Inventory App.
        resp = c.post(
            "/api/capabilities/order.create/invoke",
            json={"input": {"customer": "Ada", "items": [{"sku": "SKU-001", "quantity": 2}]}},
        )
        assert resp.status_code == 200, resp.text
        out = resp.json()["output"]
        assert out["status"] == "confirmed"
        assert out["lines"][0]["available"] == 5
        assert out["lines"][0]["inStock"] is True

        # Order beyond stock -> backorder.
        resp2 = c.post(
            "/api/capabilities/order.create/invoke",
            json={"input": {"customer": "Bob", "items": [{"sku": "SKU-003", "quantity": 1}]}},
        )
        out2 = resp2.json()["output"]
        assert out2["status"] == "backorder"
        assert out2["lines"][0]["available"] == 0

        # The order app recorded both orders via its own capability.
        orders = c.post("/api/capabilities/order.list/invoke", json={"input": {}}).json()["output"]
        assert len(orders["orders"]) == 2

        # Events from the cross-app flow are visible on the Core event log.
        names = {e["name"] for e in c.get("/api/events").json()}
        assert "uli.capability.invoked" in names
        assert "order.created" in names

        # The UI is reachable over the same backend.
        assert c.get("/api/apps").status_code == 200
        assert c.get("/host/uli.examples.order/").status_code == 200


def test_blueprint_executes_real_order_workflow(live_core):
    base, _ = live_core
    with httpx.Client(base_url=base, timeout=60) as c:
        c.post("/api/apps/uli.examples.inventory/start")
        c.post("/api/apps/uli.examples.order/start")

        blueprint = {
            "blueprintVersion": "1.0",
            "id": "uli.blueprint.order-demo",
            "name": "Order pipeline",
            "version": "1.0.0",
            "nodes": [
                {
                    "id": "request",
                    "kind": "input",
                    "label": "Order request",
                    "outputType": "uli.order.create.request@1",
                    "sample": {
                        "customer": "Blueprint",
                        "items": [{"sku": "SKU-002", "quantity": 3}],
                    },
                },
                {"id": "create", "kind": "capability", "capability": "order.create"},
                {"id": "result", "kind": "output", "label": "Order result"},
            ],
            "edges": [
                {"id": "e1", "source": "request", "target": "create"},
                {"id": "e2", "source": "create", "target": "result"},
            ],
        }
        assert c.post("/api/blueprints", json=blueprint).status_code == 200
        run = c.post("/api/blueprints/uli.blueprint.order-demo/execute", json={"input": {}})
        assert run.status_code == 200, run.text
        result = run.json()["result"]
        assert result["status"] == "confirmed"
        assert result["lines"][0]["available"] == 50
