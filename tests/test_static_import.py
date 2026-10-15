from core import config


def test_import_static_website_and_serve(client):
    src = str(config.examples_dir() / "legacy-static-site")
    resp = client.post(
        "/api/apps/import-static",
        json={"name": "Acme Catalogue", "path": src, "id": "uli.imported.acme"},
    )
    assert resp.status_code == 200, resp.text
    app = resp.json()["app"]
    assert app["runtimeType"] == "static-site"
    assert app["trust"] == "untrusted"  # no code is executed
    assert app["id"] == "uli.imported.acme"

    page = client.get("/host/uli.imported.acme/")
    assert page.status_code == 200
    assert "Acme Catalogue" in page.text

    css = client.get("/host/uli.imported.acme/assets/style.css")
    assert css.status_code == 200
    assert "--accent" in css.text

    # SPA fallback for an unknown nested path returns index.html, still 200.
    assert client.get("/host/uli.imported.acme/unknown/route").status_code == 200


def test_static_import_missing_source(client):
    resp = client.post(
        "/api/apps/import-static",
        json={"name": "Ghost", "path": "/definitely/not/here"},
    )
    assert resp.status_code == 422
