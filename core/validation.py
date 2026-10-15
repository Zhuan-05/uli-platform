"""JSON Schema payload validation helpers (shared by Core and the broker)."""
from __future__ import annotations

from typing import Any

from jsonschema import Draft202012Validator


class PayloadValidationError(ValueError):
    def __init__(self, label: str, errors: list[str]):
        self.label = label
        self.errors = errors
        super().__init__(f"{label} failed schema validation: " + "; ".join(errors))


def validate_payload(schema: dict[str, Any] | None, payload: Any, label: str) -> None:
    """Validate *payload* against *schema*.

    An empty/None schema means "no constraint" (accepts anything), which is the
    documented meaning of the ``*`` contract.
    """
    if not schema:
        return
    validator = Draft202012Validator(schema)
    errors = [
        f"{'/'.join(str(p) for p in e.absolute_path) or '<root>'}: {e.message}"
        for e in sorted(validator.iter_errors(payload), key=lambda e: list(e.absolute_path))
    ]
    if errors:
        raise PayloadValidationError(label, errors)
