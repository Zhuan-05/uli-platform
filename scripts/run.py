"""Development / production entrypoint for ULI Core.

Usage:
    python scripts/run.py [--host 127.0.0.1] [--port 8787] [--seed] [--start-all]
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def main() -> None:
    parser = argparse.ArgumentParser(prog="uli-core")
    parser.add_argument("--host", default=os.environ.get("ULI_CORE_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("ULI_CORE_PORT", "8787")))
    parser.add_argument("--seed", action="store_true", help="register bundled example apps")
    parser.add_argument("--seed-static", action="store_true", help="also import the example static site")
    parser.add_argument("--start-all", action="store_true", help="start every registered app on boot")
    parser.add_argument("--reload", action="store_true", help="dev auto-reload")
    args = parser.parse_args()

    os.environ["ULI_CORE_HOST"] = args.host
    os.environ["ULI_CORE_PORT"] = str(args.port)
    os.environ["ULI_CORE_URL"] = os.environ.get("ULI_CORE_URL", f"http://127.0.0.1:{args.port}")

    from core.bootstrap import ensure_builtin_apps, import_example_static_site
    from core.server import create_app
    from core.services import Services

    services = Services()
    if args.seed:
        added = ensure_builtin_apps(services.registry)
        if added:
            print("[uli] registered built-in apps:", ", ".join(added))
        if args.seed_static:
            import_example_static_site(services.registry)

    if args.start_all:
        async def _start_all() -> None:
            for rec in services.registry.list():
                try:
                    _, status = await services.manager.start(rec.app_id)
                    print(f"[uli] started {rec.app_id}: {status.get('detail')}")
                except Exception as exc:  # noqa: BLE001
                    print(f"[uli] could not start {rec.app_id}: {exc}")

        asyncio.run(_start_all())

    app = create_app(services)

    import uvicorn

    print(f"[uli] ULI Core v1.0 listening on http://{args.host}:{args.port}")
    print(f"[uli] API docs: http://{args.host}:{args.port}/docs")
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level="info",
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
