"""Inventory App backend - a native ULI application.

Runs as its own process. Exposes three capabilities over the ULI SDK and
publishes ``inventory.low_stock`` events. It has no knowledge of any other
application; the only cross-app channel is the ULI Core broker.
"""
from __future__ import annotations

import os

from uli_sdk import ULIService

APP_ID = "uli.examples.inventory"
VERSION = "1.0.0"

service = ULIService(APP_ID, VERSION, name="Inventory App")

# Simple in-memory stock ledger (MVP; a real app would own a database).
_STOCK: dict[str, dict] = {
    "SKU-001": {"sku": "SKU-001", "name": "Widget", "quantity": 5, "reorderLevel": 10},
    "SKU-002": {"sku": "SKU-002", "name": "Gadget", "quantity": 50, "reorderLevel": 20},
    "SKU-003": {"sku": "SKU-003", "name": "Gizmo", "quantity": 0, "reorderLevel": 5},
}

_DEFAULT_REORDER = int(os.environ.get("INVENTORY_DEFAULT_REORDER", "10"))


async def check_stock(payload: dict) -> dict:
    sku = payload["sku"]
    requested = int(payload.get("quantity", 1))
    record = _STOCK.get(sku)
    if record is None:
        return {
            "sku": sku,
            "known": False,
            "available": 0,
            "requested": requested,
            "inStock": False,
        }
    available = record["quantity"]
    result = {
        "sku": sku,
        "name": record["name"],
        "known": True,
        "available": available,
        "requested": requested,
        "inStock": available >= requested and available > 0,
        "reorderLevel": record["reorderLevel"],
    }
    if available <= record["reorderLevel"]:
        # Best-effort event; a broker outage must not fail the capability.
        try:
            await service.publish(
                "inventory.low_stock",
                {"sku": sku, "quantity": available, "reorderLevel": record["reorderLevel"]},
            )
        except Exception:  # noqa: BLE001
            pass
    return result


async def list_inventory(payload: dict) -> dict:
    low_only = bool(payload.get("lowOnly", False))
    items = [
        {
            "sku": r["sku"],
            "name": r["name"],
            "quantity": r["quantity"],
            "reorderLevel": r["reorderLevel"],
        }
        for r in _STOCK.values()
        if not low_only or r["quantity"] <= r["reorderLevel"]
    ]
    return {"items": sorted(items, key=lambda i: i["sku"])}


async def record_inventory(payload: dict) -> dict:
    sku = payload["sku"]
    existing = _STOCK.get(sku)
    record = {
        "sku": sku,
        "name": payload.get("name") or (existing or {}).get("name", sku),
        "quantity": int(payload["quantity"]),
        "reorderLevel": int(
            payload.get("reorderLevel",
                       (existing or {}).get("reorderLevel", _DEFAULT_REORDER))
        ),
    }
    _STOCK[sku] = record
    return {"sku": sku, "quantity": record["quantity"], "updated": True}


service.provide(
    "inventory.check",
    "1.0.0",
    check_stock,
    input_schema={
        "type": "object",
        "required": ["sku"],
        "additionalProperties": False,
        "properties": {
            "sku": {"type": "string", "minLength": 1},
            "quantity": {"type": "integer", "minimum": 0},
        },
    },
    output_schema={
        "type": "object",
        "required": ["sku", "known", "available", "inStock"],
        "properties": {
            "sku": {"type": "string"},
            "name": {"type": "string"},
            "known": {"type": "boolean"},
            "available": {"type": "integer", "minimum": 0},
            "requested": {"type": "integer", "minimum": 0},
            "inStock": {"type": "boolean"},
            "reorderLevel": {"type": "integer", "minimum": 0},
        },
    },
    input_type="uli.inventory.check.request@1",
    output_type="uli.inventory.check.response@1",
)

service.provide(
    "inventory.list",
    "1.0.0",
    list_inventory,
    input_schema={
        "type": "object",
        "additionalProperties": False,
        "properties": {"lowOnly": {"type": "boolean"}},
    },
    output_schema={"type": "object", "required": ["items"]},
    input_type="uli.inventory.list.request@1",
    output_type="uli.inventory.list.response@1",
)

service.provide(
    "inventory.record",
    "1.0.0",
    record_inventory,
    input_schema={
        "type": "object",
        "required": ["sku", "quantity"],
        "additionalProperties": False,
        "properties": {
            "sku": {"type": "string", "minLength": 1},
            "name": {"type": "string"},
            "quantity": {"type": "integer", "minimum": 0},
            "reorderLevel": {"type": "integer", "minimum": 0},
        },
    },
    output_schema={"type": "object", "required": ["sku", "quantity", "updated"]},
    input_type="uli.inventory.record.request@1",
    output_type="uli.inventory.record.response@1",
)

app = service.create_app()

if __name__ == "__main__":
    service.run()
