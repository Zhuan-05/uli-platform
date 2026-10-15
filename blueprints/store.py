"""JSON-file backed blueprint store (design-time artifacts)."""
from __future__ import annotations

import json
from threading import RLock

from blueprints.schema import validate_blueprint_structure
from core import config


class BlueprintNotFound(KeyError):
    pass


class BlueprintStore:
    def __init__(self, path=None) -> None:
        self._path = path or config.blueprints_file()
        self._lock = RLock()
        if not self._path.exists():
            self._write({})

    def _read(self) -> dict:
        try:
            data = json.loads(self._path.read_text(encoding="utf-8") or "{}")
        except (OSError, json.JSONDecodeError):
            data = {}
        return data.get("blueprints", {}) if isinstance(data, dict) else {}

    def _write(self, blueprints: dict) -> None:
        self._path.write_text(
            json.dumps({"blueprints": blueprints}, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def list(self) -> list[dict]:
        with self._lock:
            return list(self._read().values())

    def get(self, blueprint_id: str) -> dict:
        with self._lock:
            data = self._read()
        if blueprint_id not in data:
            raise BlueprintNotFound(blueprint_id)
        return data[blueprint_id]

    def save(self, blueprint: dict) -> dict:
        validate_blueprint_structure(blueprint)
        with self._lock:
            data = self._read()
            data[blueprint["id"]] = blueprint
            self._write(data)
        return blueprint

    def delete(self, blueprint_id: str) -> bool:
        with self._lock:
            data = self._read()
            if blueprint_id not in data:
                return False
            del data[blueprint_id]
            self._write(data)
        return True
