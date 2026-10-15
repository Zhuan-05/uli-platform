# Architecture Decision Record — ULI MVP

Status: Accepted · Scope: MVP

## ADR-001 — Backend: Python + FastAPI + SQLite
**Context:** RM0 budget, Windows-first, local-first, no Docker requirement.
**Decision:** FastAPI (MIT) + Starlette, SQLite (public domain) with WAL.
**Rationale:** Zero-cost, single-process, no external services, excellent
Windows support, and a first-class typed HTTP layer. SQLite removes any need for
a database server while remaining migratable later.

## ADR-002 — Frontend: TypeScript + React + Vite + React Flow
**Context:** Need a real visual composer, not a mockup.
**Decision:** React + Vite + `@xyflow/react`.
**Rationale:** React Flow is the de-facto node editor and is MIT-licensed. The
built bundle is committed so end users need no Node toolchain.

## ADR-003 — Inter-application transport: HTTP/JSON over loopback + bearer tokens
**Context:** Applications are separate processes. A message broker would be
over-engineering for a local MVP.
**Decision:** The Core capability broker performs HTTP/JSON calls to local
services; each spawned app receives a per-run random bearer token.
**Consequences:** Simple, debuggable, no broker to operate. Downside: in-process
Python plugins share the Core process (documented limitation).

## ADR-004 — Trust model: explicit, registration-time, conservative default
**Context:** Executing third-party code is dangerous.
**Decision:** Any runtime that executes code (`local-python`) requires
`trust=trusted`, set explicitly by the operator. Imported websites and external
URLs default to untrusted (they execute no platform-side code). Public
registration of the `in-process` runtime is refused.
**Consequences:** The default is safe. Trust is an operator decision, not a
manifest claim.

## ADR-005 — Contracts: JSON Schema (draft 2020-12) + SemVer ranges
**Context:** Capability inputs/outputs and manifests need a machine-checkable,
language-neutral description.
**Decision:** JSON Schema for payloads and manifests; a small dependency-free
SemVer range engine for version axes.
**Consequences:** No runtime type coupling between apps; validation errors are
explicit and testable.

## ADR-006 — Connection typing: nominal contract identifiers, not structural subtyping
**Context:** Full JSON-Schema subtyping is complex and error-prone.
**Decision:** Each capability declares `inputType`/`outputType` contract IDs.
Two ports connect iff the IDs match or either is `*`.
**Consequences:** Predictable and explainable ("contract mismatch: X vs Y").
Downside: structurally compatible but nominally different contracts must be
bridged by an Adapter (documented).

## ADR-007 — Design-time vs run-time separation for blueprints
**Context:** Workflow definitions must be stable and versioned independently of
execution.
**Decision:** Blueprints are versioned JSON artifacts with their own schema; the
execution engine is a separate module. The same validation function serves the
UI and the engine.

## ADR-008 — Theme layer independence
**Context:** Third-party websites cannot be forcibly restyled.
**Decision:** Themes are design tokens applied to the platform shell and to
native apps that opt in. Imported sites are explicitly out of scope for theming.

## ADR-009 — Verified environment (at build time)
Python 3.14.4, Node 26.5.0, npm 12.0.2, git 2.53.0, on WSL2. FastAPI 0.143.2,
Pydantic 2.14.1, jsonschema 4.26.0, pytest 9.1.1, Vite 8.3.4,
`@xyflow/react` 12.12.0. The Windows `.bat` scripts are provided but were not
executed in the Linux build environment (see Known Limitations).
