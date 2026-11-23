"""Create or refresh the predefined Opik governance dashboard.

Usage:
    python -m src.back.evaluations.run_dashboards
    python -m src.back.evaluations.run_dashboards --recreate
"""

from __future__ import annotations

import argparse
import sys

from ..harness.observability import ensure_opik
from .opik_adapter.dashboards import ensure_dashboard


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create Irina Opik dashboard")
    parser.add_argument("--recreate", action="store_true")
    args = parser.parse_args(argv)

    status = ensure_opik()
    if status.state not in {"reused", "started"}:
        print(f"[opik] {status.detail}; cannot create dashboard", file=sys.stderr)
        return 1
    dashboard = ensure_dashboard(recreate=args.recreate)
    if dashboard is None:
        print("[opik] dashboard creation blocked", file=sys.stderr)
        return 1
    print(f"[opik] dashboard={getattr(dashboard, 'id', '')} name={dashboard.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
