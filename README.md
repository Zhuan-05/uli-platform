# ULI Platform — Universal LEGO Interface

**English** | [中文文档](README.zh-CN.md)

> Imagine LEGO for software: small apps that snap together through standard
> connectors. Build once, reuse everywhere.

ULI is a **local-first** platform that runs on your own computer. It lets you:

- Run several independent apps side by side,
- Let them talk to each other through safe, checked "plugs",
- Paste in a ready-made website and host it without changing its code,
- Drag apps onto a canvas and connect them, then press **Execute**.

No cloud, no accounts, no monthly fees. Everything stays on `127.0.0.1`.

---

## 😀 Never used a terminal before? Start here

You will copy and paste a few commands. That's it. Follow the steps in order.

### Step 1 — Install two free programs

| Program | Why | Download | How to check |
|---|---|---|---|
| **Python 3.11 or newer** | Runs the platform backend | <https://www.python.org/downloads/> | `python --version` |
| **Node.js 18 or newer** | Builds the user interface | <https://nodejs.org/> | `node --version` |

> ⚠️ **Windows users:** on the Python installer's first screen, tick
> **“Add python.exe to PATH”** before clicking Install. If you forget, the setup
> script will tell you Python was not found.

### Step 2 — Get the project

**Option A — Download ZIP (easiest):**

1. On the GitHub page click the green **`Code`** button.
2. Click **Download ZIP** and unpack it somewhere simple, e.g.
   `C:\uli-platform`.

**Option B — Git clone (if you have Git):**

```bash
git clone https://github.com/Zhuan-05/uli-platform.git
```

### Step 3 — Open a terminal in the project folder

- **Windows:** open the `uli-platform` folder in File Explorer, click the address
  bar, type `cmd`, press Enter. A black window opens already “inside” the folder.
- **macOS:** right-click the folder → **Services** → **New Terminal at Folder**.
- **Linux:** open a terminal and `cd` into the folder.

### Step 4 — Install (one command)

**Windows:**

```bat
scripts\setup.bat
```

**macOS / Linux:**

```bash
chmod +x scripts/*.sh
scripts/setup.sh
```

This creates a private Python environment, downloads what it needs, and builds
the web page. First run takes a few minutes. When it says **Setup complete**,
you're ready.

### Step 5 — Start it

**Windows:**

```bat
scripts\run.bat
```

**macOS / Linux:**

```bash
scripts/run.sh
```

Leave this window open — it *is* the platform. You'll see:

```
Starting ULI Core on http://127.0.0.1:8787
UI:  http://127.0.0.1:8787/ui/
```

### Step 6 — Open the app

In your browser go to:

## 👉 http://127.0.0.1:8787/ui/

---

## 🧭 Your first 5 minutes (guided tour)

1. **Left menu → Applications.** You'll see three "LEGO blocks":
   - *Inventory App* and *Order App* (two independent apps), and
   - *Acme Catalogue* (a ready-made website that was pasted in unchanged).
2. Click **Start** on **Inventory App**, then **Start** on **Order App**.
   Their badges turn green → `running`.
3. **Left menu → Visual Builder.**
4. Click **Load example flow**. Three boxes appear, connected by arrows.
   The middle box is `order.create`.
5. Click **Execute**.
   The Result panel shows an order. Notice the stock number came from the
   **Inventory App** — the two apps talked to each other through ULI. 🎉
6. **Left menu → Themes** and switch between the dark glass look and light.
7. **Left menu → Activity** to watch the events the apps produced.

### What each menu does

| Menu | What it's for |
|---|---|
| **Applications** | Install / start / stop / remove apps |
| **Capabilities** | See what each app can *do* (its "plugs") |
| **Visual Builder** | Drag blocks onto a canvas, connect them, run the flow |
| **Blueprints** | Saved flows — reopen or re-run them |
| **Themes** | Change the look; backend logic is untouched |
| **Activity** | A log of everything that happened |

---

## 🧩 Try the two "wow" features

### A. Paste in an existing website

**Applications → Import a prebuilt static website**, type a **folder path** on
your computer that contains an `index.html`, give it a name, click **Import
folder**, then **Open**. The site's files are copied **exactly as they are** —
ULI does not rewrite your code.

### B. Connect two apps

In **Visual Builder**, click the capability `inventory.check` in the left palette
to drop it on the canvas, then drag from one box's right dot to another box's
left dot. If the two "plugs" don't match, ULI **refuses the link and tells you
why** — that's a feature, not a bug.

---

## ⏹ Stopping, restarting, resetting

| I want to… | Do this |
|---|---|
| Stop the platform | Close the terminal window, or press `Ctrl + C` in it |
| Start again | Run `scripts\run.bat` (Windows) / `scripts/run.sh` (macOS/Linux) |
| Use a different port | Windows: `set ULI_CORE_PORT=9000` then `scripts\run.bat` |
| Wipe everything back to fresh | Delete the `data` folder, then start again |

`data/` holds the registry, your blueprints, the event log, and imported sites.

---

## 🆘 Common beginner problems

| Symptom | Fix |
|---|---|
| “`python` is not recognized” | Reinstall Python and tick **Add python.exe to PATH** |
| “`node` is not recognized” | Reinstall Node.js, reopen the terminal |
| `setup.bat` says `.venv` missing when running | Run `scripts\setup.bat` first |
| `/` shows plain text, no UI | The UI wasn't built: run `scripts\setup.bat` again |
| Page won't load | Make sure the `run` window is still open; check the port (8787) |
| Port already in use | Set `ULI_CORE_PORT` to another number (e.g. 9000) |
| Imported site has broken images/CSS | That site uses root-absolute links; see `docs/LEGACY_WEBSITE_IMPORT.md` |
| Something crashed | Look in `data/logs/` — each app writes its own log file |

More: [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md)

---

## 👩‍💻 For developers

- **Tests:** `.venv/bin/python -m pytest tests -v` (35 tests, all passing) —
  see [`docs/TEST_REPORT.md`](docs/TEST_REPORT.md).
- **API docs (live):** <http://127.0.0.1:8787/docs>
- **Architecture:** [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- **Interface specification:** [`docs/ULI_INTERFACE_SPEC.md`](docs/ULI_INTERFACE_SPEC.md)
- **Build a native app:** [`docs/NATIVE_SDK_GUIDE.md`](docs/NATIVE_SDK_GUIDE.md)
- **Package & version apps:** [`docs/MODULE_DEVELOPER_GUIDE.md`](docs/MODULE_DEVELOPER_GUIDE.md)
- **Import legacy sites:** [`docs/LEGACY_WEBSITE_IMPORT.md`](docs/LEGACY_WEBSITE_IMPORT.md)
- **Windows setup details:** [`docs/WINDOWS_SETUP.md`](docs/WINDOWS_SETUP.md)
- **Known limits (read this):** [`docs/KNOWN_LIMITATIONS.md`](docs/KNOWN_LIMITATIONS.md)
- **Roadmap:** [`docs/ROADMAP.md`](docs/ROADMAP.md)

Project layout:

```
core/                The kernel (registry, API, validation)
uli_sdk/             SDK for building new ("native") apps
runtime_adapters/    How apps are hosted (static site, local process, URL…)
module_manager/      Lifecycle + the safe "broker" between apps
compatibility/       Manifest rules & version checking
event_bus/           Versioned events
blueprints/          Flows: schema, storage, execution
frontend/            The web UI (built into frontend/dist)
theme_design/        Themes
applications/        Example apps (Order, Inventory)
examples/            A ready-made website to import
tests/               Automated tests
docs/                All the detailed guides
scripts/             Setup / run / build helpers
```

## License

Add your chosen `LICENSE` before distributing. Dependencies are permissively
licensed (MIT / BSD / Apache-2.0).
