"""Create or refresh the predefined Opik dashboards.

Usage:
    python -m src.back.evaluations.run_dashboards
    python -m src.back.evaluations.run_dashboards --recreate
"""

from __future__ import annotations

import argparse
import sys

from ..harness.observability import ensure_opik
from .opik_adapter.dashboards import ensure_dashboards


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create Irina Opik dashboards")
    parser.add_argument("--recreate", action="store_true")
    args = parser.parse_args(argv)

    status = ensure_opik()
    if status.state not in {"reused", "started"}:
        print(f"[opik] {status.detail}; cannot create dashboards", file=sys.stderr)
        return 1
    dashboards = ensure_dashboards(recreate=args.recreate)
    if not dashboards:
        print("[opik] dashboard creation blocked", file=sys.stderr)
        return 1
    for dashboard in dashboards:
        print(
            f"[opik] dashboard={getattr(dashboard, 'id', '')} "
            f"name={getattr(dashboard, 'name', '')}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
