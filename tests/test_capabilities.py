from tests.conftest import capability, make_manifest, register_in_process


def _stock_app(services, version="1.0.0"):
    caps = [
        capability(
            "stock.check",
            version=version,
            input_type="uli.stock.req@1",
            output_type="uli.stock.res@1",
            input_schema={
                "type": "object",
                "required": ["sku"],
                "additionalProperties": False,
                "properties": {"sku": {"type": "string"}},
            },
            output_schema={
                "type": "object",
                "required": ["sku", "ok"],
                "properties": {"sku": {"type": "string"}, "ok": {"type": "boolean"}},
            },
        )
    ]
    manifest = make_manifest("uli.test.stock", provides=caps)
    register_in_process(services, manifest, {"stock.check": lambda p: {"sku": p["sku"], "ok": True}})
    return manifest


def test_capability_discovery(services, client):
    _stock_app(services)
    caps = client.get("/api/capabilities").json()
    assert any(c["id"] == "stock.check" and c["appId"] == "uli.test.stock" for c in caps)


def test_connection_compatibility():
    from core.compatibility import port_types_compatible

    assert port_types_compatible("uli.stock.res@1", "uli.stock.res@1")[0]
    assert port_types_compatible("*", "uli.anything@1")[0]
    assert not port_types_compatible("uli.stock.res@1", "uli.other@1")[0]


def test_validate_connection_api(client):
    ok = client.post(
        "/api/capabilities/validate-connection",
        json={"sourceOutputType": "a@1", "targetInputType": "a@1"},
    ).json()
    assert ok["compatible"] is True
    bad = client.post(
        "/api/capabilities/validate-connection",
        json={"sourceOutputType": "a@1", "targetInputType": "b@1"},
    ).json()
    assert bad["compatible"] is False
    assert "mismatch" in bad["reason"]


def test_invoke_and_schema_validation(services, client):
    _stock_app(services)
    assert client.post("/api/apps/uli.test.stock/start").json()["ok"]
    good = client.post("/api/capabilities/stock.check/invoke", json={"input": {"sku": "ABC"}})
    assert good.status_code == 200
    assert good.json()["output"] == {"sku": "ABC", "ok": True}

    bad = client.post("/api/capabilities/stock.check/invoke", json={"input": {}})
    assert bad.status_code == 422
    assert "sku" in str(bad.json())


def test_missing_capability_returns_404(client):
    resp = client.post("/api/capabilities/nope.missing/invoke", json={"input": {}})
    assert resp.status_code == 404


def test_version_incompatibility_blocks_enable(services, client):
    _stock_app(services, version="2.0.0")
    req = make_manifest(
        "uli.test.consumer",
        requires=[{"id": "stock.check", "version": "^1.0.0"}],
    )
    register_in_process(services, req, {})
    resp = client.post("/api/apps/uli.test.consumer/enable")
    assert resp.status_code == 409
    assert "compatible version" in resp.json()["detail"]
