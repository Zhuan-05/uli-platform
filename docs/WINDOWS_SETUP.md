# Windows Setup Guide

Target: Windows 10 / 11. Local-first, no Docker, no paid services.

> **Verification note.** The Windows `.bat` scripts are provided and use only
> standard tooling, but they were authored in a Linux (WSL2) build environment
> and were **not executed on Windows**. The manual commands below are the
> equivalent fallback if a script misbehaves.

## 1. Prerequisites

| Tool | Version | Install |
|---|---|---|
| Python | 3.11+ (3.14 tested) | <https://www.python.org/downloads/> — tick **Add python.exe to PATH** |
| Node.js | 18+ (26 tested) | <https://nodejs.org/> |
| Git | any | <https://git-scm.com/> |

Verify in a new Command Prompt:

```bat
python --version
node --version
npm --version
```

## 2. Install

```bat
cd path\to\uli-platform
scripts\setup.bat
```

This creates `.venv`, installs Python dependencies, installs frontend
dependencies, and builds the UI into `frontend\dist`.

### Manual equivalent

```bat
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cd frontend
npm install --no-audit --no-fund
npm run build
cd ..
```

## 3. Run

```bat
scripts\run.bat
```

Output:

```
Starting ULI Core on http://127.0.0.1:8787
UI:  http://127.0.0.1:8787/ui/
API: http://127.0.0.1:8787/docs
```

Open <http://127.0.0.1:8787/ui/>. The launcher registers the two example apps
(Order, Inventory) and imports the example static site.

## 4. First-run tour

1. **Applications** → click **Start** on *Inventory App*, then *Order App*.
2. **Visual Builder** → **Load example flow** → **Execute**. You should see an
   order result whose stock came from the Inventory App.
3. **Activity** → observe `order.created`, `inventory.low_stock`,
   `uli.capability.invoked`.
4. **Themes** → switch between the dark Apple-style glass theme and light.

## 5. Configuration

Environment variables (set before launching):

| Variable | Default | Meaning |
|---|---|---|
| `ULI_CORE_HOST` | `127.0.0.1` | Bind host. Keep loopback unless you intend remote access |
| `ULI_CORE_PORT` | `8787` | HTTP port |
| `ULI_CORE_URL` | `http://127.0.0.1:<port>` | URL injected into child apps for callbacks |
| `ULI_DATA_DIR` | `<root>\data` | Registry DB, logs, imports, blueprints |
| `ULI_ENV` | `development` | `production` in `run.bat` |

Change the port:

```bat
set ULI_CORE_PORT=9000
scripts\run.bat
```

## 6. Data & backup

Everything mutable lives in `data\`:

```
data\uli.db            SQLite registry
data\blueprints.json   saved blueprints
data\events.jsonl      append-only event log
data\imports\          imported application packages
data\logs\             per-app stdout/stderr
```

Back up `data\` to preserve registrations, blueprints, and imported sites.

## 7. Windows notes & safety

* ULI Core binds to **127.0.0.1 only** by default. Do not expose it to a LAN
  without adding authentication and TLS (out of MVP scope).
* `local-python` apps run as your Windows user with the same privileges — this is
  **process isolation, not a sandbox**. Only register code you trust as
  `trusted`.
* First launch may trigger a Windows Firewall prompt. For loopback-only use you
  can safely **Cancel** it.
* Long paths: if extraction fails, enable long-path support
  (`git config --system core.longpaths true` and the Windows long-path policy).
* To stop the platform, close the console window or press `Ctrl+C`. Child
  processes are terminated on a clean shutdown; if one is orphaned, end its
  `python.exe` in Task Manager.

## 8. Uninstall / reset

* Reset the platform only: delete `data\`.
* Full removal: delete the project folder (and `data\`).

No registry keys, services, or system changes are made.
