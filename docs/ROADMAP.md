# Future Roadmap & Extension Points

The MVP preserves the following extension points so the platform can grow without
rewriting ULI Core.

## Runtimes

* **`local-node`** — implement `RuntimeAdapter` for Node.js services; the
  manifest already accepts the type and requires an `entry`.
* **Server runtime** — deploy an app to a remote host over SSH/HTTP; the adapter
  interface (`start/stop/status/invoke`) is unchanged.
* **Container runtime** — spawn a container instead of a process. Needed
  additions: image reference in `runtime`, resource limits, network policy.
* **Per-app sandboxing** — OS-level (job objects on Windows, cgroups/seccomp on
  Linux) to replace the current trust-based process isolation.

## Compatibility & integration

* **Declarative adapters** — a data-only adapter format (maps + transforms)
  instead of code, for translating legacy APIs to ULI contracts.
* **Schema-based subtyping** — optional structural matching of JSON Schemas on
  top of the current nominal contract identifiers.
* **Capability composition** — one capability implemented as a pipeline of
  others (a persisted Blueprint exposed as a new capability).
* **Contract registry service** — publish/version contract schemas and detect
  breaking changes across an installation.

## Visual builder

* Branching, conditionals, mapping, fan-out/fan-in, retries, compensation.
* Sub-blueprints and versioned blueprint migrations.
* Undo/redo, auto-layout, per-node configuration forms generated from schemas.
* Live execution tracing on the canvas.

## Theme / Component LEGO

* Theme package import/export with validation and preview.
* A component host that loads native apps' `ui.extensionPoints` into named slots
  safely (sandboxed web components / iframes with postMessage).
* A permissioned bridge so extensions can call the ULI API on behalf of the user.

## Platform hardening

* API authentication + TLS, multi-user accounts and roles.
* Secrets store for `config.fields` of type `secret`.
* Process supervision, restart policies, and per-app quotas.
* Structured audit log; signed manifests; package integrity checks.
* Database migration to a server RDBMS when scale demands it.

## Developer experience

* CLI (`uli` command) for scaffold/register/start/logs.
* Manifest + blueprint authoring via JSON Schema autocompletion.
* CI template running the full suite on Windows and Linux runners.
* A public plugin marketplace (explicitly out of MVP scope).

## Compatibility promise for future work

New runtime types and adapters are additive. Existing manifests targeting
`>=1.0.0 <2.0.0` remain valid within the 1.x line. Breaking changes to the
platform contract will ship as ULI `2.0` with an explicit migration guide.
