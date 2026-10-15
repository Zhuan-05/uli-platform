# Legacy Website Import Guide

Import an existing, already-built website into ULI **without rewriting its
source**. ULI copies the files and generates a manifest; the original HTML/CSS/JS
is untouched.

## What you get

* Hosting at `/host/<app-id>/` from the ULI origin.
* Optional embedding in the platform UI (subject to the site's own policies).
* Hosting compatibility only. The site does **not** automatically gain ULI
  capabilities — that requires an Adapter or the Native Track.

## Import via the UI

1. Open `http://127.0.0.1:8787/ui/`.
2. **Applications → Import a prebuilt static website**.
3. Enter a display name and the **server-side** folder path (a folder that
   contains an `index.html`).
4. Click **Import folder**. Open it with the **Open** button.

## Import via the API

### From a server-side folder

```bash
curl -X POST http://127.0.0.1:8787/api/apps/import-static \
  -H 'Content-Type: application/json' \
  -d '{"name":"Acme Catalogue","path":"/abs/path/to/site"}'
```

### From a zip upload

```bash
curl -X POST http://127.0.0.1:8787/api/apps/import-static-upload \
  -F name="Acme Catalogue" \
  -F file=@site.zip
```

Zip extraction is protected against path traversal ("zip-slip") and size-capped
at 512 MB.

## What ULI generates

The importer creates `data/imports/<slug>/site/` containing your files and a
generated `app.manifest.json`:

```json
{
  "manifestVersion": "1.0",
  "id": "uli.imported.acme-catalogue",
  "name": "Acme Catalogue",
  "version": "1.0.0",
  "uli": { "protocol": ">=1.0.0 <2.0.0" },
  "runtime": { "type": "static-site", "staticDir": "site" },
  "frontend": { "entry": "site/index.html", "embed": true },
  "capabilities": { "provides": [], "requires": [] },
  "permissions": ["fs.read.assets"]
}
```

Imported sites are registered **untrusted** — which is fine because no code is
executed on the server.

## SPA routing

If a requested path does not exist, ULI serves `index.html` (SPA fallback).
Client-side routers work out of the box for hash and history routing.

## Absolute asset paths

A site that uses root-absolute asset URLs (`/style.css`) will request them from
the *platform* origin, not under `/host/<id>/`, and they will 404. Fixes:

* Rebuild with relative asset paths, **or**
* Add a tiny Adapter/rewrite at build time, **or**
* Serve such sites via `external-url` behind your own reverse proxy instead.

ULI does not silently rewrite source files.

## Embedding external sites (`external-url`)

Registering a remote URL and embedding it in an iframe may be blocked by the
remote server. ULI reports the truth:

```bash
curl http://127.0.0.1:8787/api/apps/<id>/embed-check
# → { "embeddable": false, "blockers": ["X-Frame-Options: deny"], ... }
```

Browsers enforce `X-Frame-Options`, `Content-Security-Policy: frame-ancestors`,
and cookie policies. ULI cannot override them.

## Turning a legacy site into Functional LEGO

Hosting is step one. To make the site a first-class capability consumer/provider:

1. Wrap the existing backend/API with a small ULI service (`uli_sdk`) —
   this is an **Adapter**. The legacy code stays as-is behind it.
2. Declare the capabilities the adapter exposes in the manifest.
3. The original frontend can call the ULI broker for cross-app capabilities.

See `docs/NATIVE_SDK_GUIDE.md` and `docs/MODULE_DEVELOPER_GUIDE.md`.
