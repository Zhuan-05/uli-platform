"""Public JSON Schema for ``app.manifest.json`` (ULI v1.0).

The schema is the single source of truth for manifest shape. Runtime-specific
requirements (e.g. local-python needs an entry point) are expressed with
if/then blocks so they cannot be accidentally skipped.
"""
from __future__ import annotations

SEMVER_PATTERN = r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.\-]+)?(?:\+[0-9A-Za-z.\-]+)?$"
RANGE_PATTERN = r"^[<>=~^*vV0-9xX\s.,|\-]+$"
ID_PATTERN = r"^[a-z0-9](?:[a-z0-9._\-]{1,126}[a-z0-9])?$"
CAPABILITY_PATTERN = r"^[a-z][a-z0-9]*(?:\.[a-z0-9][a-z0-9\-_]*)+@[0-9]+$"
# Capabilities are addressed as ``namespace.action`` and versioned separately;
# the @N suffix is optional sugar used in blueprint port labels.

JSON_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://uli.local/schemas/app.manifest.v1.json",
    "title": "ULI Application Manifest v1",
    "type": "object",
    "additionalProperties": False,
    "required": ["manifestVersion", "id", "name", "version", "uli", "runtime"],
    "properties": {
        "manifestVersion": {"type": "string", "const": "1.0"},
        "id": {"type": "string", "pattern": ID_PATTERN, "minLength": 3},
        "name": {"type": "string", "minLength": 1, "maxLength": 120},
        "description": {"type": "string", "maxLength": 2000},
        "version": {"type": "string", "pattern": SEMVER_PATTERN},
        "dataOwner": {"type": "string", "maxLength": 200},
        "uli": {
            "type": "object",
            "additionalProperties": False,
            "required": ["protocol"],
            "properties": {
                "protocol": {"type": "string", "pattern": RANGE_PATTERN, "minLength": 1},
            },
        },
        "runtime": {
            "type": "object",
            "additionalProperties": False,
            "required": ["type"],
            "properties": {
                "type": {
                    "type": "string",
                    "enum": [
                        "static-site",
                        "external-url",
                        "local-python",
                        "local-node",
                        "in-process",
                    ],
                },
                "entry": {"type": "string"},
                "url": {"type": "string", "pattern": r"^https?://"},
                "staticDir": {"type": "string"},
                "port": {"type": "integer", "minimum": 0, "maximum": 65535},
                "healthPath": {"type": "string", "pattern": r"^/"},
                "workingDir": {"type": "string"},
                "env": {
                    "type": "object",
                    "additionalProperties": {"type": "string"},
                },
            },
            "allOf": [
                {
                    "if": {"properties": {"type": {"const": "local-python"}}},
                    "then": {"required": ["entry"]},
                },
                {
                    "if": {"properties": {"type": {"const": "local-node"}}},
                    "then": {"required": ["entry"]},
                },
                {
                    "if": {"properties": {"type": {"const": "external-url"}}},
                    "then": {"required": ["url"]},
                },
                {
                    "if": {"properties": {"type": {"const": "static-site"}}},
                    "then": {"required": ["staticDir"]},
                },
            ],
        },
        "frontend": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "entry": {"type": "string"},
                "embed": {"type": "boolean", "default": True},
                "extensionPoints": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["id", "slot"],
                        "properties": {
                            "id": {"type": "string", "pattern": ID_PATTERN},
                            "slot": {"type": "string"},
                            "title": {"type": "string"},
                            "description": {"type": "string"},
                        },
                    },
                },
            },
        },
        "capabilities": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "provides": {
                    "type": "array",
                    "items": {"$ref": "#/$defs/provides"},
                },
                "requires": {
                    "type": "array",
                    "items": {"$ref": "#/$defs/requires"},
                },
            },
        },
        "events": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "publishes": {
                    "type": "array",
                    "items": {"$ref": "#/$defs/eventDecl"},
                },
                "subscribes": {
                    "type": "array",
                    "items": {"$ref": "#/$defs/eventDecl"},
                },
            },
        },
        "permissions": {
            "type": "array",
            "items": {
                "type": "string",
                "pattern": r"^[a-z][a-z0-9]*(\.[a-z0-9*][a-z0-9._\-*]*)+$",
            },
            "uniqueItems": True,
        },
        "ui": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "extensionPoints": {"type": "array", "items": {"type": "object"}},
            },
        },
        "config": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "fields": {
                    "type": "array",
                    "items": {"$ref": "#/$defs/configField"},
                }
            },
        },
    },
    "$defs": {
        "jsonSchemaObject": {
            "type": "object",
            "description": "A JSON Schema (draft 2020-12) describing a payload.",
        },
        "provides": {
            "type": "object",
            "additionalProperties": False,
            "required": ["id", "version", "inputSchema", "outputSchema"],
            "properties": {
                "id": {"type": "string", "pattern": ID_PATTERN},
                "version": {"type": "string", "pattern": SEMVER_PATTERN},
                "description": {"type": "string", "maxLength": 2000},
                "inputType": {"type": "string", "minLength": 1},
                "outputType": {"type": "string", "minLength": 1},
                "inputSchema": {"$ref": "#/$defs/jsonSchemaObject"},
                "outputSchema": {"$ref": "#/$defs/jsonSchemaObject"},
                "timeoutMs": {"type": "integer", "minimum": 100, "maximum": 600000},
            },
        },
        "requires": {
            "type": "object",
            "additionalProperties": False,
            "required": ["id"],
            "properties": {
                "id": {"type": "string", "pattern": ID_PATTERN},
                "version": {"type": "string", "pattern": RANGE_PATTERN, "default": "*"},
                "optional": {"type": "boolean", "default": False},
            },
        },
        "eventDecl": {
            "type": "object",
            "additionalProperties": False,
            "required": ["name", "version"],
            "properties": {
                "name": {"type": "string", "pattern": ID_PATTERN},
                "version": {"type": "string", "pattern": SEMVER_PATTERN},
                "description": {"type": "string", "maxLength": 2000},
                "schema": {"$ref": "#/$defs/jsonSchemaObject"},
            },
        },
        "configField": {
            "type": "object",
            "additionalProperties": False,
            "required": ["key", "type"],
            "properties": {
                "key": {"type": "string", "pattern": ID_PATTERN},
                "label": {"type": "string"},
                "type": {"type": "string", "enum": ["string", "number", "boolean", "secret"]},
                "required": {"type": "boolean", "default": False},
                "default": {},
                "description": {"type": "string", "maxLength": 1000},
            },
        },
    },
}
