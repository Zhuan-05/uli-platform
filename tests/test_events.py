import pytest

from core.validation import PayloadValidationError
from tests.conftest import make_manifest, register_in_process


def test_event_dispatch_to_subscriber(services, client):
    received = []
    services.bus.subscribe("demo.happened", lambda ev: received.append(ev))

    resp = client.post(
        "/api/events/publish",
        json={"name": "demo.happened", "version": "1.0.0", "payload": {"n": 1}},
    )
    assert resp.status_code == 200
    assert resp.json()["delivered"] == 1
    assert received and received[0].payload == {"n": 1}


def test_versioned_event_schema_validation(services):
    manifest = make_manifest(
        "uli.test.publisher",
        publishes=[
            {
                "name": "demo.strict",
                "version": "1.0.0",
                "schema": {
                    "type": "object",
                    "required": ["value"],
                    "properties": {"value": {"type": "integer"}},
                },
            }
        ],
        permissions=["data.own", "events.publish.demo.strict"],
    )
    register_in_process(services, manifest, {})

    import asyncio

    ok = asyncio.run(
        services.manager.publish_event(
            "demo.strict", "1.0.0", {"value": 5}, source="uli.test.publisher",
            caller_app_id="uli.test.publisher",
        )
    )
    assert ok["delivered"] == 0  # no subscriber, but valid

    with pytest.raises(PayloadValidationError):
        asyncio.run(
            services.manager.publish_event(
                "demo.strict", "1.0.0", {"value": "not-an-int"},
                source="uli.test.publisher", caller_app_id="uli.test.publisher",
            )
        )


def test_publish_permission_enforced(services):
    manifest = make_manifest("uli.test.noperm", permissions=["data.own"])
    register_in_process(services, manifest, {})
    import asyncio

    from module_manager import PermissionDenied

    with pytest.raises(PermissionDenied):
        asyncio.run(
            services.manager.publish_event(
                "demo.any", "1.0.0", {}, source="uli.test.noperm",
                caller_app_id="uli.test.noperm",
            )
        )


def test_event_log_persisted(services, client):
    client.post("/api/events/publish", json={"name": "demo.log", "version": "1.0.0", "payload": {}})
    events = client.get("/api/events").json()
    assert any(e["name"] == "demo.log" for e in events)
