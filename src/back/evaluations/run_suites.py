"""Create Opik Test Suites from the synthetic core datasets.

Usage:
    python -m src.back.evaluations.run_suites
    python -m src.back.evaluations.run_suites --family DS01 --run
"""

from __future__ import annotations

import argparse
import sys

from ..harness.observability import ensure_opik
from .datasets import build_core_datasets
from .opik_adapter.suites import ensure_suite, run_suite
from .runners.reference import ReferenceResponder
from .worlds import WorldFactory


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create Opik test suites")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--family", default="", help="run this family after creation")
    parser.add_argument("--run", action="store_true", help="run the selected family")
    args = parser.parse_args(argv)

    status = ensure_opik()
    if status.state not in {"reused", "started"}:
        print(f"[opik] {status.detail}; cannot create suites", file=sys.stderr)
        return 1

    world = WorldFactory().build(seed=args.seed)
    grouped = build_core_datasets(world)
    responder = ReferenceResponder(world)
    case_by_id = {
        case.case_id: case for cases in grouped.values() for case in cases
    }
    created = 0
    for family, cases in sorted(grouped.items()):
        assertions = sorted(
            {case.expected_behavior for case in cases if case.expected_behavior}
        ) or ["Response satisfies the expected behavior described in the case"]
        suite = ensure_suite(
            name=f"irina-{family}",
            description=f"Irina {family} governance suite",
            assertions=assertions,
            cases=[case.as_dict() for case in cases],
        )
        if suite is None:
            print(f"[opik] suite {family} blocked", file=sys.stderr)
            continue
        created += 1
        print(f"[opik] suite={family} items={len(cases)}")
        if args.run and args.family == family:
            def task(data, _cases=case_by_id):
                case = _cases[data["case_id"]]
                outcome = responder.run(case)
                return {
                    "input": data.get("inputs", {}),
                    "output": {
                        "passed": outcome.passed,
                        "metrics": [metric.as_dict() for metric in outcome.metrics],
                    },
                }

            result = run_suite(
                suite,
                task,
                experiment_name=f"irina-suite-{family}-seed{args.seed}",
            )
            print(f"[opik] suite-run={family} result={'ok' if result else 'blocked'}")
    print(f"[opik] suites created: {created}")
    return 0 if created else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
