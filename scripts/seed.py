"""Register the bundled example applications and import the example static site.

Idempotent. Safe to run repeatedly. Does not start any application.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def main() -> None:
    from core.bootstrap import ensure_builtin_apps, import_example_static_site
    from core.services import Services

    svc = Services()
    added = ensure_builtin_apps(svc.registry)
    static = import_example_static_site(svc.registry)

    print("Registered built-in apps:", ", ".join(added) if added else "(already present)")
    print("Static example site:", static or "(not found)")
    print("\nKnown applications:")
    for rec in svc.registry.list():
        print(f"  - {rec.app_id:32s} {rec.runtime_type:12s} {rec.state:10s} trust={rec.trust}")


if __name__ == "__main__":
    main()
