"""Order App backend - a native ULI application.

Demonstrates Functional LEGO integration: to create an order it asks ULI Core
to run the ``inventory.check`` capability. The Order App has no dependency on
the Inventory App's code, only on the published contract.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from uli_sdk import ULIService, ULIClientError

APP_ID = "uli.examples.order"
VERSION = "1.0.0"

service = ULIService(APP_ID, VERSION, name="Order App")

_ORDERS: list[dict] = []


async def create_order(payload: dict) -> dict:
    customer = payload["customer"]
    lines: list[dict] = []
    all_in_stock = True

    for item in payload["items"]:
        try:
            stock = await service.invoke(
                "inventory.check",
                {"sku": item["sku"], "quantity": item["quantity"]},
            )
        except ULIClientError as exc:
            # The inventory capability is mandatory; fail loudly and clearly.
            raise RuntimeError(f"inventory.check unavailable: {exc}") from exc

        in_stock = bool(stock.get("inStock"))
        all_in_stock = all_in_stock and in_stock
        lines.append(
            {
                "sku": item["sku"],
                "quantity": item["quantity"],
                "available": int(stock.get("available", 0)),
                "inStock": in_stock,
            }
        )

    order = {
        "orderId": "ORD-" + uuid.uuid4().hex[:10].upper(),
        "status": "confirmed" if all_in_stock else "backorder",
        "customer": customer,
        "createdAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "lines": lines,
    }
    _ORDERS.append(order)

    try:
        await service.publish(
            "order.created",
            {
                "orderId": order["orderId"],
                "customer": customer,
                "status": order["status"],
                "lineCount": len(lines),
            },
        )
    except Exception:  # noqa: BLE001 - event publishing is best-effort
        pass
    return order


async def list_orders(payload: dict) -> dict:
    return {"orders": list(reversed(_ORDERS))}


service.provide(
    "order.create",
    "1.0.0",
    create_order,
    input_schema={
        "type": "object",
        "required": ["customer", "items"],
        "additionalProperties": False,
        "properties": {
            "customer": {"type": "string", "minLength": 1},
            "items": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "required": ["sku", "quantity"],
                    "additionalProperties": False,
                    "properties": {
                        "sku": {"type": "string", "minLength": 1},
                        "quantity": {"type": "integer", "minimum": 1},
                    },
                },
            },
        },
    },
    output_schema={
        "type": "object",
        "required": ["orderId", "status", "customer", "lines"],
        "properties": {
            "orderId": {"type": "string"},
            "status": {"type": "string", "enum": ["confirmed", "backorder"]},
            "customer": {"type": "string"},
            "createdAt": {"type": "string"},
            "lines": {"type": "array", "items": {"type": "object"}},
        },
    },
    input_type="uli.order.create.request@1",
    output_type="uli.order.create.response@1",
)

service.provide(
    "order.list",
    "1.0.0",
    list_orders,
    input_schema={"type": "object", "additionalProperties": False, "properties": {}},
    output_schema={"type": "object", "required": ["orders"]},
    input_type="uli.order.list.request@1",
    output_type="uli.order.list.response@1",
)

app = service.create_app()

if __name__ == "__main__":
    service.run()
