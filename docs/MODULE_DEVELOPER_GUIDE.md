# Module / Application Developer Guide

This guide covers packaging, the manifest, versions, dependencies, permissions,
and testing.

## Package convention

```
my-application/
  app.manifest.json     # required
  frontend/             # optional UI assets (served at /host/<id>/)
  backend/              # optional process entry (local-python)
  adapters/             # optional code translating external APIs → ULI contracts
  contracts/            # optional exported JSON Schemas (documentation)
  assets/               # optional static assets
data/                   # (platform-owned; never inside the app package)
```

The only file ULI requires is `app.manifest.json`. Everything else is
application-defined.

## Manifest essentials

| Field | Required | Notes |
|---|---|---|
| `manifestVersion` | ✅ | must be `"1.0"` |
| `id` | ✅ | lowercase, dotted, unique |
| `name` | ✅ | display name |
| `version` | ✅ | SemVer, bumped on release |
| `uli.protocol` | ✅ | range that includes `1.0.0` |
| `runtime.type` | ✅ | one of the supported runtime types |
| `capabilities.provides[]` | — | each needs `inputSchema` + `outputSchema` |
| `capabilities.requires[]` | — | `version` range, `optional` flag |
| `events.publishes/subscribes` | — | name + SemVer |
| `permissions` | — | allow-listed prefixes only |
| `dataOwner` | recommended | declares your data namespace |

## Runtime types

| Type | Executes code | Capabilities | Notes |
|---|---|---|---|
| `static-site` | no | no | Serve prebuilt assets under `/host/<id>/` |
| `external-url` | no | no | Register a remote web app; embedding is subject to the remote server |
| `local-python` | **yes** | yes | Requires `trust=trusted`; spawned as a child process |
| `local-node` | documented | — | Extension point (not implemented in MVP) |
| `in-process` | **yes** | yes | Core-internal/tests only; refused via public API |

## Versioning discipline

* **Breaking** capability change → bump `MAJOR` of that capability's `version`.
* **Backwards-compatible** addition (new optional field) → bump `MINOR`.
* Bug fix → bump `PATCH`.
* Application `version` and capability versions move independently.
* Never weaken a schema in place; publish a new major contract instead.

## Dependencies

* Required dependency: `requires[].optional = false`. `enable`/`start` fail with
  a clear 409 until a compatible provider is running.
* Optional dependency: `optional = true`. Missing providers produce a warning,
  not a failure. Handle absence in your code.
* Version ranges are checked against the provider's contract version.

## Permissions

Declare only what you need. The broker enforces:

```
capability.invoke.inventory.check
capability.invoke.*
events.publish.order.created
events.subscribe.inventory.low_stock
net.local | net.external | fs.read.assets | fs.write.own | data.own | storage.kv | ui.extension
```

Unknown prefixes are rejected at registration.

## Upgrade & uninstall

* Upgrade: re-register with `upgrade=true` and a strictly greater `version`.
* Uninstall: data is preserved by default. Imported app source may be deleted
  with `deleteFiles=true`.

## Testing your app

1. Unit-test handlers directly (they are plain functions).
2. Integration-test through the broker:
   ```bash
   curl -X POST localhost:8787/api/apps/<id>/start
   curl -X POST localhost:8787/api/capabilities/<cap>/invoke \
        -H 'Content-Type: application/json' -d '{"input": {...}}'
   ```
3. Negative-test schema validation (send malformed input → expect 422).

## Checklist before shipping

- [ ] Manifest validates (`POST /api/apps/register` returns 200).
- [ ] Every provided schema is a valid JSON Schema.
- [ ] Contract types are nominal and stable.
- [ ] Permissions are minimal.
- [ ] Process runtime is only ever registered `trusted` after code review.
- [ ] Health endpoint responds `< 500` when ready.
- [ ] No secrets in the frontend or the manifest.
