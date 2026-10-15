"""External URL runtime.

Registers an already-hosted web application by URL. ULI records it and can
*check* whether the browser is likely to allow embedding, but it cannot force
it: the remote server's ``X-Frame-Options`` / ``Content-Security-Policy:
frame-ancestors`` and cookie policies always win. We report the truth instead
of pretending embedding always works.
"""
from __future__ import annotations

import re

import httpx

from core.models import ApplicationRecord, AppState
from runtime_adapters.base import RuntimeAdapter, RuntimeStatus

_FRAME_ANCESTORS_RE = re.compile(r"frame-ancestors([^;]+)", re.IGNORECASE)


def evaluate_embedding_headers(headers: dict[str, str]) -> dict[str, object]:
    """Pure function: decide embeddability from response headers."""
    lowered = {k.lower(): v for k, v in headers.items()}
    xfo = lowered.get("x-frame-options", "").strip().lower()
    csp = lowered.get("content-security-policy", "")

    blockers: list[str] = []
    if xfo:
        if xfo in ("deny", "sameorigin"):
            blockers.append(f"X-Frame-Options: {xfo}")
    if csp:
        m = _FRAME_ANCESTORS_RE.search(csp)
        if m:
            value = m.group(1).strip()
            if value and "'none'" not in value and "*" not in value:
                blockers.append(f"CSP frame-ancestors {value}")

    return {
        "embeddable": not blockers,
        "blockers": blockers,
        "x_frame_options": xfo or None,
        "has_csp": bool(csp),
        "note": (
            "Header check only. Browser cookie policies (SameSite) and the remote "
            "site's own JS may still prevent embedding."
        ),
    }


class ExternalUrlRuntime(RuntimeAdapter):
    type = "external-url"
    executes_process = False
    supports_capabilities = False

    def _url(self, record: ApplicationRecord) -> str:
        return record.manifest.get("runtime", {}).get("url", "")

    async def start(self, record: ApplicationRecord) -> RuntimeStatus:
        url = self._url(record)
        if not url:
            return RuntimeStatus(state=AppState.ERROR, detail="no runtime.url configured")
        return RuntimeStatus(state=AppState.RUNNING, detail=f"registered external URL {url}")

    async def stop(self, record: ApplicationRecord) -> RuntimeStatus:
        return RuntimeStatus(state=AppState.STOPPED, detail="external URL unregistered")

    async def status(self, record: ApplicationRecord) -> RuntimeStatus:
        return RuntimeStatus(state=record.state, detail=self._url(record))

    async def embed_check(self, record: ApplicationRecord, timeout: float = 8.0) -> dict[str, object]:
        url = self._url(record)
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
                resp = await client.get(url, headers={"User-Agent": "ULI-EmbedCheck/1.0"})
            info = evaluate_embedding_headers(dict(resp.headers))
            info["status_code"] = resp.status_code
            info["final_url"] = str(resp.url)
            info["reachable"] = True
            if resp.status_code >= 400 and info["embeddable"]:
                info["embeddable"] = False
                info["blockers"].append(f"HTTP {resp.status_code}")  # type: ignore[union-attr]
            return info
        except httpx.HTTPError as exc:
            return {
                "embeddable": False,
                "reachable": False,
                "blockers": [f"request failed: {exc.__class__.__name__}: {exc}"],
                "note": "Could not reach the URL from the platform.",
            }
