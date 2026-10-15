# Troubleshooting

## The UI does not load (`/` shows plain text)

The frontend bundle is missing. Build it:

```bash
cd frontend && npm install && npm run build
```

`/ui/` should then serve the app. The backend works without it (API + `/docs`).

## "refusing to execute local-python application: it is not registered as trusted"

A process runtime can only run when the operator marks it trusted:

```bash
curl -X POST http://127.0.0.1:8787/api/apps/register \
  -H 'Content-Type: application/json' \
  -d '{"path":"/abs/app","trust":"trusted","upgrade":true}'
```

Or re-import with trust selected in the UI. Review the code first.

## Start fails: provider not running / 409 / 503

* A required capability's provider is not running. Start the provider first
  (Order App requires the Inventory App). Check **Capabilities** for provider
  state and **Applications** for `running`.
* Version mismatch: the error lists the found versions versus the required
  range. Publish a compatible contract version or relax the requirement.

## Startup returns `state: error` with "did not become healthy"

* The child process crashed. Inspect `data/logs/<app-id>.log`.
* Wrong `runtime.entry` or `workingDir`, or a missing dependency.
* Port conflict: ULI falls back to a free port automatically and says
  `(port N was busy; using M)`. If you rely on a fixed port, choose a free one.

## Connection rejected in the Visual Builder

Read the message in the status bar: e.g.
`Rejected: output uli.a@1 cannot connect to input uli.b@1`. This is by design —
ULI uses nominal contract identifiers, not structural subtyping. Either connect
matching contracts or add an Adapter that translates between them.

## `package not found` / `import uli_sdk` fails when running an app standalone

When Core spawns an app it sets `PYTHONPATH` to the platform root. If you run the
app by hand, set it yourself:

```bash
PYTHONPATH=. ULI_APP_PORT=9001 python applications/inventory_app/backend/app.py
```

## Frontend shows "Failed to load platform state"

* Backend not running, or on a different port. In dev, Vite proxies `/api` to
  `127.0.0.1:8787`; adjust `frontend/vite.config.ts` if your port differs.
* Check `http://127.0.0.1:8787/api/health` directly.

## Imported site's CSS/JS 404s

The site uses root-absolute asset paths. See
`docs/LEGACY_WEBSITE_IMPORT.md` → "Absolute asset paths".

## Embedding an external site shows a blank frame

The remote server forbids framing. Run
`GET /api/apps/<id>/embed-check` for the reason (`X-Frame-Options`,
`CSP frame-ancestors`, cookie policy). ULI cannot override browser security.

## `build_blueprints`/tests fail with a stale database

Tests use a throwaway `ULI_DATA_DIR`. For manual resets, delete `data/` (this
removes registrations, blueprints, logs, and imported apps).

## Port 8787 already in use

```bat
set ULI_CORE_PORT=9000
scripts\run.bat
```

## Python 3.13/3.14 wheel errors on some packages

The MVP's dependency set ships wheels for current CPython. If a transitive
package fails to build, upgrade pip first (`python -m pip install -U pip`) or use
Python 3.12.

## Windows `.bat` script issues

Use the manual equivalent in `docs/WINDOWS_SETUP.md`. Ensure `python`/`node` are
on `PATH` and that you launched the script from an elevated-free, normal shell.
