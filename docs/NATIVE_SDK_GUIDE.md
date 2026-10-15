# Native SDK Guide

Build an application that speaks ULI natively: it exposes capabilities and
events, receives cross-app calls, and can call other applications through the
Core broker.

## 1. Minimal application

Create the package layout:

```
my-app/
  app.manifest.json
  backend/app.py
  frontend/index.html     # optional
  contracts/              # optional: exported JSON Schemas for docs
  adapters/               # optional
```

`backend/app.py`:

```python
from uli_sdk import ULIService

service = ULIService("com.example.greeter", "1.0.0", name="Greeter")

def hello(payload: dict) -> dict:
    return {"message": f"Hello, {payload['name']}!"}

service.provide(
    "greeter.hello",
    "1.0.0",
    hello,
    input_schema={
        "type": "object",
        "required": ["name"],
        "additionalProperties": False,
        "properties": {"name": {"type": "string", "minLength": 1}},
    },
    output_schema={
        "type": "object",
        "required": ["message"],
        "properties": {"message": {"type": "string"}},
    },
    input_type="example.greeter.hello.request@1",
    output_type="example.greeter.hello.response@1",
)

app = service.create_app()      # FastAPI: /health, /uli/invoke, /uli/events

if __name__ == "__main__":
    service.run()               # binds ULI_APP_PORT, loopback only
```

`app.manifest.json`:

```json
{
  "manifestVersion": "1.0",
  "id": "com.example.greeter",
  "name": "Greeter",
  "version": "1.0.0",
  "uli": { "protocol": ">=1.0.0 <2.0.0" },
  "runtime": { "type": "local-python", "entry": "backend/app.py", "port": 0, "healthPath": "/health" },
  "capabilities": {
    "provides": [{
      "id": "greeter.hello",
      "version": "1.0.0",
      "inputType": "example.greeter.hello.request@1",
      "outputType": "example.greeter.hello.response@1",
      "inputSchema": { "type": "object", "required": ["name"], "properties": { "name": { "type": "string" } } },
      "outputSchema": { "type": "object", "required": ["message"], "properties": { "message": { "type": "string" } } }
    }],
    "requires": []
  },
  "events": { "publishes": [], "subscribes": [] },
  "permissions": ["data.own"]
}
```

## 2. Register, trust, and start

`local-python` executes code, so it must be registered as **trusted**:

```bash
curl -s -X POST http://127.0.0.1:8787/api/apps/register \
  -H 'Content-Type: application/json' \
  -d '{"path":"/abs/path/to/my-app","trust":"trusted"}'
curl -s -X POST http://127.0.0.1:8787/api/apps/com.example.greeter/start
```

Or use the UI: **Applications → register**, then **Start**.

## 3. Call another application

Declare the permission `capability.invoke.<id>` and the requirement, then:

```python
async def create_order(payload):
    stock = await service.invoke("inventory.check", {"sku": payload["sku"], "quantity": 1})
    return {"inStock": stock["inStock"]}
```

The call goes through ULI Core: permission check → provider resolution → input
validation → transport → output validation. You never import the provider.

## 4. Publish and subscribe to events

```python
service.provide(...)                       # capabilities
await service.publish("order.created", {"orderId": "A-1", "customer": "Ada"})  # needs events.publish.order.created

def on_low_stock(event: dict) -> None:      # subscribe
    ...
service.on_event("inventory.low_stock", on_low_stock)
```

Add matching entries under `events.publishes` / `events.subscribes` and the
corresponding permissions.

## 5. Buttons: the platform environment

While running under ULI, the SDK receives:

| Variable | Meaning |
|---|---|
| `ULI_APP_ID` | Your application id |
| `ULI_APP_PORT` | The loopback port to bind |
| `ULI_APP_TOKEN` | Per-run bearer token Core uses to call you |
| `ULI_CORE_URL` | Base URL of the Core broker |
| `PYTHONPATH` | Includes the platform root so `import uli_sdk` works |

Standalone (without Core), the token is empty and validation is relaxed for
local development.

## 6. Rules of thumb

* Validate at the boundary with the schemas you publish — the SDK already does.
* Keep handlers fast; the capability's `timeoutMs` bounds the call.
* Never read another app's files or database.
* Publish a new **major** contract version when you make a breaking change.
