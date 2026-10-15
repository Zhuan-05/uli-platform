# ULI v1.0 Interface Specification

This is the normative description of the Universal LEGO Interface. Any
application — legacy or native — that satisfies this spec can be hosted and
connected by ULI Core.

---

## 1. Versioning model

ULI deliberately separates three version axes:

| Axis | Field | Meaning |
|---|---|---|
| **ULI protocol version** | `uli.protocol` (range) vs. Core's `1.0.0` | The platform contract a manifest targets |
| **Application version** | `version` (exact SemVer) | The app's own release |
| **Capability contract version** | `capabilities.provides[].version` (exact SemVer) | The version of one capability's I/O contract |

Rules:

* All versions use Semantic Versioning `MAJOR.MINOR.PATCH`.
* Requirements use ranges: `1.2.3`, `>=1.0.0 <2.0.0`, `^1.2.3`, `~1.2.3`,
  `1.x`, `*`, and `||` disjunction.
* `^0.y.z` is treated per npm semantics (`^0.2.3` → `>=0.2.3 <0.3.0`).
* A **breaking** capability contract change MUST bump its `MAJOR`.
* A breaking change MUST NOT be silently accepted: a consumer requiring
  `^1.0.0` will fail resolution against a `2.0.0` provider, and vice versa.

### Enforceable vs. cooperation-based guarantees

See `GET /api/compatibility/guarantees` for the live list.

**Enforceable by the platform:** protocol range match; requirement satisfaction;
contract-version ranges; JSON-Schema input/output validation; port-type equality
for blueprint connections; manifest structural validity.

**Requires developer cooperation:** that a handler actually implements the
semantics its schema implies; that an app does not touch data it does not own;
that a remote site permits iframe embedding; that a native app opts into the
theme SDK; correct data migration across major versions.

---

## 2. Unique identifiers

* Application id: `^[a-z0-9](?:[a-z0-9._-]{1,126}[a-z0-9])?$` (recommended:
  reverse-DNS-like, e.g. `uli.examples.order`).
* Capability id: dotted `namespace.action` (e.g. `inventory.check`).
* Event name: same shape as a capability id (e.g. `order.created`).
* UI extension point id: application-id-shape, unique within the app.

Ids are globally unique within a ULI installation. Registering an existing id
requires an explicit upgrade.

---

## 3. Application manifest (`app.manifest.json`)

Normative JSON Schema lives in `compatibility/manifest_schema.py`
(`JSON_SCHEMA`, draft 2020-12). Summary:

```jsonc
{
  "manifestVersion": "1.0",
  "id": "uli.examples.inventory",
  "name": "Inventory App",
  "description": "...",
  "version": "1.0.0",
  "dataOwner": "uli.examples.inventory",
  "uli": { "protocol": ">=1.0.0 <2.0.0" },

  "runtime": {
    "type": "local-python",      // static-site | external-url | local-python | local-node | in-process
    "entry": "backend/app.py",   // required for process runtimes
    "url": "https://...",        // required for external-url
    "staticDir": "site",         // required for static-site
    "port": 0,                   // 0 = OS-allocated
    "healthPath": "/health",
    "workingDir": ".",
    "env": { "KEY": "value" }
  },

  "frontend": {
    "entry": "frontend/index.html",
    "embed": true,
    "extensionPoints": [
      { "id": "inventory.dashboard", "slot": "app.detail.tab", "title": "Inventory" }
    ]
  },

  "capabilities": {
    "provides": [{
      "id": "inventory.check",
      "version": "1.0.0",
      "description": "...",
      "inputType": "uli.inventory.check.request@1",
      "outputType": "uli.inventory.check.response@1",
      "inputSchema": { "type": "object", "required": ["sku"], "...": "..." },
      "outputSchema": { "type": "object", "...": "..." },
      "timeoutMs": 4000
    }],
    "requires": [
      { "id": "inventory.check", "version": "^1.0.0", "optional": false }
    ]
  },

  "events": {
    "publishes":  [{ "name": "inventory.low_stock", "version": "1.0.0", "schema": { } }],
    "subscribes": [{ "name": "order.created",       "version": "1.0.0" }]
  },

  "permissions": ["data.own", "capability.invoke.inventory.check"],
  "ui": { "extensionPoints": [] },
  "config": {
    "fields": [
      { "key": "default_customer", "label": "Default customer", "type": "string", "required": false, "default": "Walk-in" }
    ]
  }
}
```

### Validation
Manifests are validated at registration. Malformed or incompatible manifests are
rejected with a list of precise errors. **Never** execute commands from a
manifest; the `runtime.entry` is only used by a runtime adapter, and only for an
app the operator explicitly marked `trusted`.

---

## 4. Capability contracts

* `inputSchema` / `outputSchema` are JSON Schema (draft 2020-12) objects.
* An empty schema `{}` means "no constraint".
* `inputType` / `outputType` are **nominal contract identifiers**
  (`namespace.contract@major`).
* Two ports connect iff:
  * output type and input type are identical, **or**
  * either side is the wildcard `*`.
* Structurally-compatible but nominally-different contracts must be bridged by
  an **Adapter** (see §8). This is intentional and documented.

Validation occurs at three points: the caller's UI, the broker (input and
output), and the provider SDK.

---

## 5. Event structure

Every event is immutable and versioned:

```json
{
  "id": "hex-uuid",
  "name": "order.created",
  "version": "1.0.0",
  "source": "uli.examples.order",
  "timestamp": "2026-10-15T21:00:00.000+00:00",
  "correlationId": null,
  "payload": { }
}
```

* A publisher may declare a schema; if present, the payload is validated before
  dispatch.
* Subscribers match on event **name** and **major** version.
* Delivery failures are reported but never roll back an event; the event log is
  append-only (`data/events.jsonl`).

---

## 6. Lifecycle states

```
registered ──enable──▶ enabled ──start──▶ starting ──▶ running
    ▲                    │                              │
    │                    └──disable──▶ disabled         │
    │                                                   ▼
    └───────────────────────────────────────────── stopped
                          (any) ──error──▶ error
                        (reqs unmet) ──▶ incompatible
```

* `registered` — known, not runnable.
* `enabled` — requirements resolved; may start.
* `disabled` — explicitly off; `start` is refused.
* `starting` / `running` / `stopped` / `error` / `incompatible`.

Transitions are owned by the Module Manager only.

---

## 7. Health checks

* Process runtimes must expose `GET <healthPath>` returning any `< 500` when
  ready.
* `GET /api/apps/{id}/health` reports state, port, pid, and adapter detail.
* Start fails safely (state `error`, actionable message) if the process crashes
  or does not become healthy within the timeout.

---

## 8. Adapters (Legacy ↔ ULI translation)

An Adapter translates an external/legacy API response into a ULI contract. In
the MVP, adapters are code that lives *inside* the owning application package
(`adapters/`) and calls the ULI SDK. The platform-facing contract is unchanged.
A first-class declarative adapter format is a future extension point.

---

## 9. Permissions and trust

* `trust` ∈ {`untrusted`, `trusted`}. It is set at registration by the operator,
  **not** by the manifest. Default: `untrusted`.
* Any runtime that executes code (`local-python`, `local-node`) requires
  `trust=trusted` to enable.
* Permissions are declared as strings and enforced by the broker:
  * `capability.invoke.<id>` (or `capability.invoke.*`) to call a capability.
  * `events.publish.<name>` / `events.subscribe.<name>`.
  * `net.local`, `net.external`, `fs.read.*`, `fs.write.*`, `data.own`,
    `storage.kv`, `ui.extension`.
  * The manifest schema rejects unknown permission prefixes.

---

## 10. Data ownership & upgrade/migration

* `dataOwner` names the owner of the application's data. The platform never
  writes into another app's data.
* Upgrades: `POST /api/apps/register` with `upgrade=true` replaces a registered
  app; the new `version` must be strictly greater. Registration metadata
  (registered_at) is preserved.
* Uninstall preserves data by default (`dataPreserved: true`). Only
  platform-imported source files can be deleted, and only when
  `deleteFiles=true` is explicitly passed.
* Major-version data migration is the application's responsibility and is
  documented as cooperation-based.

---

## 11. Errors

| Situation | HTTP | Body |
|---|---|---|
| Invalid manifest | 422 | `{ "detail": { "errors": [...] } }` |
| Duplicate app | 409 | message |
| Incompatible version | 409 | message |
| Missing capability | 404 | message |
| Provider not running | 503 | message |
| Missing permission | 403 | message |
| Payload schema failure | 422 | `{ "errors": [...], "label": "..." }` |
| Unsafe/untrusted runtime | 403/400 | message |

Provider handler errors are surfaced as ULI errors, never swallowed.

---

## 12. Runtime adapter interface

```python
class RuntimeAdapter:
    type: str
    executes_process: bool
    supports_capabilities: bool
    async def start(record) -> RuntimeStatus
    async def stop(record)  -> RuntimeStatus
    async def status(record)-> RuntimeStatus
    async def invoke(record, capability, payload, *, token=None) -> Any
```

Register a new adapter in `runtime_adapters/registry.py`. ULI Core requires no
changes to support a new runtime type.
