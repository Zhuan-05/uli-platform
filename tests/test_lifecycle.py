from tests.conftest import capability, make_manifest, register_in_process


def _simple_app(services, app_id="uli.test.lifecycle"):
    caps = [capability("life.ping", input_type="*", output_type="*")]
    manifest = make_manifest(app_id, provides=caps)
    register_in_process(services, manifest, {"life.ping": lambda p: {"pong": True}})
    return manifest


def test_lifecycle_operations(services, client):
    _simple_app(services)

    assert client.post("/api/apps/uli.test.lifecycle/enable").json()["app"]["state"] == "enabled"
    assert client.post("/api/apps/uli.test.lifecycle/start").json()["app"]["state"] == "running"
    assert client.get("/api/apps/uli.test.lifecycle/health").json()["state"] == "running"
    assert client.post("/api/apps/uli.test.lifecycle/stop").json()["app"]["state"] == "stopped"
    assert client.post("/api/apps/uli.test.lifecycle/disable").json()["app"]["state"] == "disabled"

    # Starting a disabled app is rejected.
    resp = client.post("/api/apps/uli.test.lifecycle/start")
    assert resp.status_code == 400


def test_uninstall_preserves_data_and_removes_registration(services, client):
    _simple_app(services, "uli.test.uninstall")
    resp = client.delete("/api/apps/uli.test.uninstall")
    assert resp.status_code == 200
    body = resp.json()
    assert body["removedFromRegistry"] is True
    assert body["dataPreserved"] is True
    assert client.get("/api/apps/uli.test.uninstall").status_code == 404


def test_in_process_runtime_cannot_be_registered_publicly(client, tmp_path):
    # A manifest declaring in-process runtime must be refused through the public API.
    import json

    manifest = make_manifest("uli.test.forbidden")
    (tmp_path / "app.manifest.json").write_text(json.dumps(manifest))
    resp = client.post("/api/apps/register", json={"path": str(tmp_path)})
    assert resp.status_code == 400
    assert "in-process" in resp.json()["detail"]
