"""ULI event bus.

A deliberately small, in-process publish/subscribe bus with an append-only JSONL
log. External (subprocess) delivery is wired in by the service layer so the bus
itself stays free of runtime concerns.
"""
from __future__ import annotations

import json
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

from core import config
from core.validation import validate_payload

Handler = Callable[["Event"], None]


@dataclass
class Event:
    name: str
    version: str
    source: str
    payload: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="milliseconds"))
    correlation_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class EventBus:
    def __init__(self, *, log_path=None) -> None:
        self._lock = threading.RLock()
        self._subscribers: dict[str, list[Handler]] = {}
        self._log_path = log_path if log_path is not None else config.events_file()
        self._recent: list[Event] = []

    # ------------------------------------------------------------------ #
    def subscribe(self, event_name: str, handler: Handler) -> Callable[[], None]:
        with self._lock:
            self._subscribers.setdefault(event_name, []).append(handler)

        def unsubscribe() -> None:
            with self._lock:
                handlers = self._subscribers.get(event_name, [])
                if handler in handlers:
                    handlers.remove(handler)

        return unsubscribe

    def subscriber_count(self, event_name: str) -> int:
        with self._lock:
            return len(self._subscribers.get(event_name, []))

    # ------------------------------------------------------------------ #
    def publish(
        self,
        event: Event,
        *,
        schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Validate (optional), persist, log, and deliver an event.

        Delivery failures are reported but never roll back the event; the event
        is durable in the log regardless.
        """
        if schema:
            validate_payload(schema, event.payload, f"event {event.name}@{event.version}")

        with self._lock:
            self._recent.append(event)
            if len(self._recent) > 500:
                self._recent = self._recent[-500:]
            handlers = list(self._subscribers.get(event.name, []))

        self._append_log(event)

        delivered = 0
        errors: list[str] = []
        for handler in handlers:
            try:
                handler(event)
                delivered += 1
            except Exception as exc:  # noqa: BLE001 - isolate subscriber failures
                errors.append(f"{getattr(handler, '__qualname__', handler)}: {exc}")

        return {
            "event": event.to_dict(),
            "delivered": delivered,
            "subscribers": len(handlers),
            "errors": errors,
        }

    def recent(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            return [e.to_dict() for e in self._recent[-limit:]][::-1]

    def _append_log(self, event: Event) -> None:
        try:
            with open(self._log_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(event.to_dict(), separators=(",", ":")) + "\n")
        except OSError:
            # Logging is best-effort; event delivery must not fail because of disk.
            pass
