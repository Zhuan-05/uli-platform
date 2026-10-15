"""Compatibility subsystem: manifest validation + version/protocol checks."""
from compatibility.manifest_schema import JSON_SCHEMA
from compatibility.validator import (
    ManifestValidationError,
    load_manifest_file,
    validate_manifest_dict,
)

__all__ = [
    "JSON_SCHEMA",
    "ManifestValidationError",
    "load_manifest_file",
    "validate_manifest_dict",
]
