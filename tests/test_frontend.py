from core import config


def test_ui_is_served_when_built(client):
    index = config.frontend_dist_dir() / "index.html"
    if not index.is_file():
        import pytest

        pytest.skip("frontend/dist not built")

    resp = client.get("/ui/")
    assert resp.status_code == 200
    assert 'id="root"' in resp.text

    # Root redirects to the UI when it exists.
    root = client.get("/", follow_redirects=False)
    assert root.status_code in (307, 308)

    # The UI is same-origin with the API it consumes.
    assert client.get("/api/health").status_code == 200


def test_compatibility_guarantees_endpoint(client):
    body = client.get("/api/compatibility/guarantees").json()
    assert body["enforceable"]
    assert body["requires_developer_cooperation"]
