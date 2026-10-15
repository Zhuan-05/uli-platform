"""Independent Theme Design Layer.

Themes are pure design tokens (colors, typography, borders, radius, shadows,
layout). They are completely decoupled from backend logic: switching a theme
never touches application code. Only *native* ULI apps that opt into the theme
SDK inherit these tokens; imported third-party websites do not.
"""
from __future__ import annotations

import json
from typing import Any

from core import config

DARK_GLASS: dict[str, Any] = {
    "id": "uli.glass.dark",
    "name": "ULI Glass (Dark)",
    "mode": "dark",
    "tokens": {
        "color": {
            "bg": "#070a11",
            "bgGradient": "radial-gradient(1200px 700px at 15% -10%, #16233c 0%, #070a11 60%)",
            "surface": "rgba(20, 27, 42, 0.62)",
            "surfaceSolid": "#141b2a",
            "surfaceHover": "rgba(38, 50, 74, 0.72)",
            "text": "#e8eefc",
            "muted": "#8ea0c0",
            "accent": "#4f8cff",
            "accentSoft": "rgba(79, 140, 255, 0.16)",
            "border": "rgba(255, 255, 255, 0.10)",
            "danger": "#ff6b6b",
            "success": "#7ee0a3",
            "warning": "#ffb86b",
        },
        "typography": {
            "fontFamily": "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
            "fontFamilyMono": "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace",
            "fontSizeBase": "14px",
            "fontSizeSmall": "12px",
            "fontSizeHeading": "20px",
            "lineHeight": "1.5",
        },
        "border": {"width": "1px", "style": "solid"},
        "radius": {"sm": "8px", "md": "12px", "lg": "18px", "pill": "999px"},
        "shadow": {
            "sm": "0 1px 2px rgba(0,0,0,0.35)",
            "md": "0 12px 32px rgba(0,0,0,0.45)",
            "glow": "0 0 0 1px rgba(79,140,255,0.25), 0 8px 30px rgba(79,140,255,0.18)",
        },
        "blur": {"glass": "18px"},
        "layout": {"sidebarWidth": "280px", "density": "comfortable", "canvasGrid": "24px"},
    },
}

LIGHT: dict[str, Any] = {
    "id": "uli.glass.light",
    "name": "ULI Glass (Light)",
    "mode": "light",
    "tokens": {
        "color": {
            "bg": "#eef2f9",
            "bgGradient": "radial-gradient(1200px 700px at 15% -10%, #ffffff 0%, #e8eef9 60%)",
            "surface": "rgba(255, 255, 255, 0.72)",
            "surfaceSolid": "#ffffff",
            "surfaceHover": "rgba(240, 245, 255, 0.9)",
            "text": "#101828",
            "muted": "#5b6b86",
            "accent": "#2563eb",
            "accentSoft": "rgba(37, 99, 235, 0.12)",
            "border": "rgba(16, 24, 40, 0.12)",
            "danger": "#d92d20",
            "success": "#15803d",
            "warning": "#b45309",
        },
        "typography": {
            "fontFamily": "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
            "fontFamilyMono": "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace",
            "fontSizeBase": "14px",
            "fontSizeSmall": "12px",
            "fontSizeHeading": "20px",
            "lineHeight": "1.5",
        },
        "border": {"width": "1px", "style": "solid"},
        "radius": {"sm": "8px", "md": "12px", "lg": "18px", "pill": "999px"},
        "shadow": {
            "sm": "0 1px 2px rgba(16,24,40,0.06)",
            "md": "0 12px 32px rgba(16,24,40,0.12)",
            "glow": "0 0 0 1px rgba(37,99,235,0.20), 0 8px 30px rgba(37,99,235,0.14)",
        },
        "blur": {"glass": "18px"},
        "layout": {"sidebarWidth": "280px", "density": "comfortable", "canvasGrid": "24px"},
    },
}

BUILTIN_THEMES: dict[str, dict[str, Any]] = {t["id"]: t for t in (DARK_GLASS, LIGHT)}
DEFAULT_THEME_ID = DARK_GLASS["id"]


class ThemeNotFound(KeyError):
    pass


class ThemeManager:
    def __init__(self) -> None:
        self._themes = dict(BUILTIN_THEMES)

    def list(self) -> list[dict[str, Any]]:
        return [
            {"id": t["id"], "name": t["name"], "mode": t["mode"], "builtin": t["id"] in BUILTIN_THEMES}
            for t in self._themes.values()
        ]

    def get(self, theme_id: str) -> dict[str, Any]:
        if theme_id not in self._themes:
            raise ThemeNotFound(theme_id)
        return self._themes[theme_id]

    def active_id(self) -> str:
        if config.themes_active_file().exists():
            try:
                return json.loads(config.themes_active_file().read_text(encoding="utf-8"))["id"]
            except Exception:  # noqa: BLE001
                pass
        return DEFAULT_THEME_ID

    def activate(self, theme_id: str) -> dict[str, Any]:
        theme = self.get(theme_id)
        config.themes_active_file().write_text(
            json.dumps({"id": theme_id}), encoding="utf-8"
        )
        return theme

    def import_theme(self, payload: dict[str, Any]) -> dict[str, Any]:
        required = {"id", "name", "mode", "tokens"}
        missing = required - set(payload)
        if missing:
            raise ValueError(f"theme missing required keys: {sorted(missing)}")
        if not isinstance(payload["tokens"], dict):
            raise ValueError("theme.tokens must be an object")
        payload = {**payload, "builtin": False}
        self._themes[payload["id"]] = payload
        return payload

    def export_theme(self, theme_id: str) -> dict[str, Any]:
        return dict(self.get(theme_id))
