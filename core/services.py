"""Composition root: builds the ULI Core service graph.

Everything is constructed here and injected downward, so components never reach
for global state and can be replaced in tests.
"""
from __future__ import annotations

from blueprints import BlueprintEngine, BlueprintStore
from core.capabilities import CapabilityRegistry
from core.registry import ApplicationRegistry
from event_bus import EventBus
from module_manager import ModuleManager
from runtime_adapters import RuntimeAdapterRegistry
from theme_design import ThemeManager


class Services:
    def __init__(self) -> None:
        self.registry = ApplicationRegistry()
        self.capabilities = CapabilityRegistry(self.registry)
        self.runtimes = RuntimeAdapterRegistry()
        self.bus = EventBus()
        self.manager = ModuleManager(self.registry, self.capabilities, self.runtimes, self.bus)
        self.blueprints = BlueprintStore()
        self.engine = BlueprintEngine(self.capabilities, self.manager)
        self.themes = ThemeManager()


_services: Services | None = None


def get_services() -> Services:
    global _services
    if _services is None:
        _services = Services()
    return _services


def reset_services() -> None:
    """Test helper: drop the singleton so the next call rebuilds it."""
    global _services
    _services = None
