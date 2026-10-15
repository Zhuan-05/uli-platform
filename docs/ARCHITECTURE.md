# ULI Architecture

The platform is organised in eight layers. The single most important rule is
**dependency direction**: layers depend downward, and ULI Core never depends on
the internals of a specific business application.

```
┌──────────────────────────────────────────────────────────────────────┐
│ 8. Theme Design Extension Layer          theme_design/                 │
├──────────────────────────────────────────────────────────────────────┤
│ 7. Visual Module Composer                blueprints/ + frontend/       │
├──────────────────────────────────────────────────────────────────────┤
│ 6. Application Host                      core/server.py (/host, /ui)   │
├──────────────────────────────────────────────────────────────────────┤
│ 5. Event & Capability System             event_bus/ + core/capabilities│
├──────────────────────────────────────────────────────────────────────┤
│ 4. Module & Application Manager          module_manager/               │
├──────────────────────────────────────────────────────────────────────┤
│ 3. Runtime Adapter Layer                 runtime_adapters/             │
├──────────────────────────────────────────────────────────────────────┤
│ 2. Universal Interface Contract          compatibility/ + core/models  │
├──────────────────────────────────────────────────────────────────────┤
│ 1. ULI Core                              core/                        │
└──────────────────────────────────────────────────────────────────────┘
        ▲                                             ▲
   Native apps (uli_sdk/)                    Imported/legacy apps (hosted)
```

## Layer responsibilities

### 1. ULI Core (`core/`)
The kernel: configuration, SQLite store, application registry, capability
registry, compatibility checks, JSON-Schema payload validation, the HTTP API
composition root, and the static-site importer. It imports `compatibility`,
`runtime_adapters`, `module_manager`, `event_bus`, `blueprints`, and
`theme_design`, but **never** `applications/`.

Key files: `core/server.py` (API), `core/registry.py`, `core/capabilities.py`,
`core/validation.py`, `core/config.py`, `core/version.py`, `core/importer.py`.

### 2. Universal Interface Contract (`compatibility/`, `core/models.py`)
The manifest schema and validator, typed internal models, and the compatibility
engine (protocol range + requirement resolution). This layer defines what an
application *is* and what it *promises*.

### 3. Runtime Adapter Layer (`runtime_adapters/`)
Every runtime type implements `RuntimeAdapter`: `start`, `stop`, `status`, and
optionally `invoke`. New runtime types are additive. MVP adapters:
`static-site`, `external-url`, `local-python`; plus `in-process` for
Core-internal providers and tests.

`RuntimeAdapterRegistry` is the factory. ULI Core never constructs a runtime
directly.

### 4. Module & Application Manager (`module_manager/`)
The orchestra conductor. It combines the registry, adapters, and event bus to
implement lifecycle transitions, the capability broker (with permission and
schema enforcement), and event dispatch to external subscribers.

### 5. Event & Capability System (`event_bus/`, `core/capabilities.py`)
The versioned event bus (in-process pub/sub + JSONL log) and the capability
registry (discovery + resolution by version range).

### 6. Application Host (`core/server.py`)
Serves imported static websites and native app frontends under
`/host/<app-id>/` with path-traversal protection, and serves the UI bundle under
`/ui/`.

### 7. Visual Module Composer (`blueprints/`, `frontend/`)
Design-time blueprints (versioned JSON) with a separate execution engine. The
UI uses React Flow. Validation used by the UI is the *same code* used at
execution time, so the canvas and the runtime cannot disagree.

### 8. Theme Design Extension Layer (`theme_design/`)
Independent design tokens. Switching themes never touches backend logic. Native
apps may opt in via the theme tokens; imported websites do not inherit them.

## Dependency-direction invariants

1. `applications/*` may import `uli_sdk` only — never ULI Core.
2. `core/*` may not import from `applications/*`.
3. Runtime adapters know nothing about each other or about capabilities.
4. The blueprint engine reaches capabilities **only** through the module
   manager, never through an adapter directly.
5. The frontend talks only to the documented HTTP API.

## Cross-application call flow (Functional LEGO)

```
Order App handler ──(1) HTTP invoke order.create──▶ ULI Core
        ULI Core ──(2) route + validate──▶ Order runtime (local-python)
Order App ──(3) SDK invoke inventory.check──▶ ULI Core broker
        ULI Core ──(4) permission + schema check──▶ Inventory runtime
Inventory App ──(5) return validated output──▶ ULI Core ──▶ Order App
Order App ──(6) validated output──▶ ULI Core ──▶ caller
```

No application imports another application's code. The only coupling is the
published contract and the broker.

## Data ownership

Each application owns its data (`dataOwner` in the manifest). ULI Core's own
state lives in `data/` (SQLite registry, blueprint JSON, event log, imported app
packages). Uninstalling an application never deletes its data unless deletion is
explicitly requested, and only platform-imported source files are eligible for
deletion.
