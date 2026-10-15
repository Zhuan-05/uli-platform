from tests.conftest import capability, make_manifest, register_in_process


def _fetch_and_double(services):
    fetch = make_manifest(
        "uli.test.fetch",
        provides=[capability("test.fetch", input_type="uli.test.start@1", output_type="uli.test.mid@1")],
    )
    double = make_manifest(
        "uli.test.double",
        provides=[capability("test.double", input_type="uli.test.mid@1", output_type="uli.test.res@1")],
    )
    register_in_process(services, fetch, {"test.fetch": lambda p: {"value": 21}})
    register_in_process(services, double, {"test.double": lambda p: {"value": p["value"] * 2}})
    import asyncio

    asyncio.run(services.manager.start("uli.test.fetch"))
    asyncio.run(services.manager.start("uli.test.double"))


def _chain_blueprint(result_cap="test.double"):
    return {
        "blueprintVersion": "1.0",
        "id": "uli.blueprint.test-chain",
        "name": "Test chain",
        "version": "1.0.0",
        "nodes": [
            {"id": "in", "kind": "input", "outputType": "uli.test.start@1", "sample": {}},
            {"id": "f", "kind": "capability", "capability": "test.fetch"},
            {"id": "d", "kind": "capability", "capability": result_cap},
            {"id": "out", "kind": "output"},
        ],
        "edges": [
            {"id": "e1", "source": "in", "target": "f"},
            {"id": "e2", "source": "f", "target": "d"},
            {"id": "e3", "source": "d", "target": "out"},
        ],
    }


def test_blueprint_save_load_and_execute(services, client):
    _fetch_and_double(services)
    bp = _chain_blueprint()

    assert client.post("/api/blueprints", json=bp).status_code == 200
    loaded = client.get("/api/blueprints/uli.blueprint.test-chain").json()
    assert loaded["id"] == bp["id"]

    check = client.post("/api/blueprints/validate", json=bp).json()
    assert check["valid"] is True, check

    run = client.post("/api/blueprints/uli.blueprint.test-chain/execute", json={"input": {}})
    assert run.status_code == 200, run.text
    assert run.json()["result"] == {"value": 42}
    assert [s["nodeId"] for s in run.json()["steps"]] == ["f", "d", "out"]


def test_incompatible_connection_rejected(services, client):
    _fetch_and_double(services)
    bp = _chain_blueprint()
    # Point the second capability at one whose input contract does not match.
    reg = make_manifest(
        "uli.test.text",
        provides=[capability("test.text", input_type="uli.text@1", output_type="uli.text@1")],
    )
    register_in_process(services, reg, {"test.text": lambda p: p})

    bp["nodes"][2]["capability"] = "test.text"
    bp["id"] = "uli.blueprint.bad"
    report = client.post("/api/blueprints/validate", json=bp).json()
    assert report["valid"] is False
    assert any("mismatch" in i["reason"] for i in report["issues"])

    run = client.post("/api/blueprints/validate", json=bp)  # sanity
    assert run.status_code == 200
    exec_resp = client.post("/api/blueprints/uli.blueprint.bad/execute", json={"input": {}})
    # blueprint wasn't saved, so unknown -> 404
    assert exec_resp.status_code == 404


def test_missing_provider_blueprint_invalid(services, client):
    bp = _chain_blueprint(result_cap="does.not.exist")
    report = client.post("/api/blueprints/validate", json=bp).json()
    assert report["valid"] is False
    assert any("no installed provider" in i["reason"] for i in report["issues"])
