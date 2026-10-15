"""System Blueprint schema (versioned) and structural validation.

A Blueprint is a *design-time* artifact, deliberately separated from execution
logic. It stores which capability nodes exist and how their typed ports connect.
"""
from __future__ import annotations

from typing import Any

from jsonschema import Draft202012Validator

NODE_KINDS = ("input", "capability", "output")

BLUEPRINT_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://uli.local/schemas/blueprint.v1.json",
    "title": "ULI System Blueprint v1",
    "type": "object",
    "additionalProperties": False,
    "required": ["blueprintVersion", "id", "name", "version", "nodes", "edges"],
    "properties": {
        "blueprintVersion": {"type": "string", "const": "1.0"},
        "id": {"type": "string", "pattern": r"^[a-zA-Z0-9._\-]{3,128}$"},
        "name": {"type": "string", "minLength": 1, "maxLength": 120},
        "description": {"type": "string", "maxLength": 2000},
        "version": {"type": "string", "pattern": r"^\d+\.\d+\.\d+$"},
        "nodes": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["id", "kind"],
                "properties": {
                    "id": {"type": "string", "minLength": 1, "maxLength": 64},
                    "kind": {"type": "string", "enum": list(NODE_KINDS)},
                    "label": {"type": "string", "maxLength": 120},
                    "position": {
                        "type": "object",
                        "required": ["x", "y"],
                        "properties": {"x": {"type": "number"}, "y": {"type": "number"}},
                    },
                    "capability": {"type": "string"},
                    "appId": {"type": "string"},
                    "inputType": {"type": "string"},
                    "outputType": {"type": "string"},
                    "sample": {"type": "object"},
                    "config": {"type": "object"},
                },
            },
        },
        "edges": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["id", "source", "target"],
                "properties": {
                    "id": {"type": "string", "minLength": 1},
                    "source": {"type": "string"},
                    "target": {"type": "string"},
                    "sourcePort": {"type": "string", "default": "out"},
                    "targetPort": {"type": "string", "default": "in"},
                },
            },
        },
    },
}


class BlueprintValidationError(ValueError):
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


def validate_blueprint_structure(raw: dict[str, Any]) -> None:
    if not isinstance(raw, dict):
        raise BlueprintValidationError(["blueprint must be a JSON object"])
    validator = Draft202012Validator(BLUEPRINT_SCHEMA)
    errors = [
        f"{'/'.join(str(p) for p in e.absolute_path) or '<root>'}: {e.message}"
        for e in sorted(validator.iter_errors(raw), key=lambda e: list(e.absolute_path))
    ]

    nodes = raw.get("nodes", [])
    ids = [n.get("id") for n in nodes]
    duplicates = {i for i in ids if ids.count(i) > 1}
    if duplicates:
        errors.append(f"duplicate node ids: {sorted(duplicates)}")

    id_set = set(ids)
    for edge in raw.get("edges", []):
        if edge.get("source") not in id_set:
            errors.append(f"edge {edge.get('id')}: unknown source node {edge.get('source')!r}")
        if edge.get("target") not in id_set:
            errors.append(f"edge {edge.get('id')}: unknown target node {edge.get('target')!r}")

    for node in nodes:
        if node.get("kind") == "capability" and not node.get("capability"):
            errors.append(f"capability node {node.get('id')!r} is missing 'capability'")

    if errors:
        raise BlueprintValidationError(errors)


def empty_blueprint(blueprint_id: str, name: str) -> dict[str, Any]:
    return {
        "blueprintVersion": "1.0",
        "id": blueprint_id,
        "name": name,
        "version": "1.0.0",
        "nodes": [],
        "edges": [],
    }
