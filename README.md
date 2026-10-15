# Universal LEGO Interface (ULI) Platform

**Build once, reuse everywhere, connect through stable interfaces.**

ULI is a local-first, Windows-oriented platform for hosting independent
applications and connecting their capabilities through stable, versioned,
validated contracts — without rewriting the applications' business logic and
without any paid services.

> This repository is the ULI Platform root. The folder may be named anything;
> all paths are relative. Rename/move it freely, then re-run setup.

---

## What actually works (MVP)

| Capability | Status |
|---|---|
| Application registry with manifest JSON-Schema validation | ✅ working |
| Enable / disable / start / stop / restart / health / uninstall lifecycle | ✅ working |
| Static website import + hosting (`/host/<app-id>/`) | ✅ working |
| External URL registration + embed-feasibility check | ✅ working |
| Trusted local Python runtime (process spawn, health check, port-conflict fallback) | ✅ working |
| Capability registry, discovery, brokered invocation, I/O schema validation | ✅ working |
| Versioned event bus with schema validation + external delivery | ✅ working |
| Two independent example apps (Order + Inventory) doing a real cross-app call | ✅ working |
| Visual builder (React Flow): add nodes, connect typed ports, reject incompatible links, save/load/execute blueprints | ✅ working |
| Independent theme layer (dark Apple-style glass default + light) | ✅ working |
| Automated tests (35) including a live end-to-end test | ✅ 35/35 passing |
| Windows setup/launch scripts | ✅ provided (see `docs/WINDOWS_SETUP.md`) |
| Server / container runtimes | 🔜 documented extension points only |

Never claimed: "every arbitrary website integrates automatically". Hosting a
site is not the same as functionally integrating it. See
`docs/KNOWN_LIMITATIONS.md`.

---

## Quick start (Windows)

```bat
git clone <your-repo> uli-platform
cd uli-platform
scripts\setup.bat      :: creates .venv, installs deps, builds the UI
scripts\run.bat        :: starts Core + UI, registers example apps
```

Then open <http://127.0.0.1:8787/ui/>.

## Quick start (Linux / macOS / WSL)

```bash
cd uli-platform
scripts/setup.sh
scripts/run.sh
```

Or manually:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
(cd frontend && npm install && npm run build)
.venv/bin/python scripts/run.py --seed --seed-static
```

The UI is served at `/ui/`, the OpenAPI docs at `/docs`.

---

## Repository layout

```
core/                ULI Core: registry, capabilities, compatibility, server, importer
uli_sdk/             Native Track SDK (declare capabilities, call the broker)
runtime_adapters/    static-site, external-url, local-python, in-process
module_manager/      lifecycle orchestration + capability broker + event dispatch
applications/        example apps (order_app, inventory_app) — independently packaged
compatibility/       manifest JSON Schema + validator + compatibility rules
event_bus/           versioned event bus
blueprints/          Blueprint schema, store, and execution engine
frontend/            TypeScript + React + Vite + React Flow UI (dist/ committed)
theme_design/        independent design-token themes
examples/            a prebuilt static website used to demo the Legacy Track
tests/               pytest suite (unit + functional + live end-to-end)
docs/                architecture, spec, guides, test report, limitations, roadmap
scripts/             setup/run/dev/build scripts, seeding
```

---

## The three LEGO levels

* **Application LEGO** — register, launch, stop, disable, upgrade, remove apps.
* **Functional LEGO** — publish/consume capabilities and events across apps
  through validated contracts. Fully implemented in the MVP.
* **Component LEGO** — `ui.extensionPoints` in the manifest + a documented
  theme SDK. A working contract + proof-of-concept extension points are
  provided; a general component host is future work.

## Two compatibility tracks

* **Legacy Track** — import an existing prebuilt website and host it unchanged
  via the App Host. Optional Adapter required for deep integration.
* **Native Track** — build new apps with the ULI SDK; they expose capabilities,
  events, and lifecycle metadata directly.

Both tracks speak the **same public contracts** documented in
`docs/ULI_INTERFACE_SPEC.md`.

## Documentation

| Document | Purpose |
|---|---|
| `docs/ARCHITECTURE.md` | Layered architecture and dependency rules |
| `docs/ARCHITECTURE_DECISION_RECORD.md` | Why the stack and boundaries were chosen |
| `docs/ULI_INTERFACE_SPEC.md` | Formal ULI v1.0 interface specification |
| `docs/NATIVE_SDK_GUIDE.md` | Building a native ULI application |
| `docs/MODULE_DEVELOPER_GUIDE.md` | Packaging, manifest, versions, permissions |
| `docs/LEGACY_WEBSITE_IMPORT.md` | Importing existing websites |
| `docs/WINDOWS_SETUP.md` | Reproducible Windows setup |
| `docs/TROUBLESHOOTING.md` | Common failures and fixes |
| `docs/TEST_REPORT.md` | Actual test results (35/35) |
| `docs/KNOWN_LIMITATIONS.md` | Honest limits and disabled-by-design features |
| `docs/ROADMAP.md` | Extension points and future work |

## License

Code in this repository is intended for use under a permissive license
(compatible with the MIT/BSD/Apache-2.0 dependencies it uses). Add your chosen
`LICENSE` file before distribution.
