"""Run the offline core suite and write reports.

Usage:
    python -m src.back.evaluations.run_core --out reports/core
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from .contracts import IntegrationLevel
from .datasets import build_core_datasets, flatten_datasets
from .governance import write_coverage
from .metrics import MetricValue, UndefinedReason, compute_composites
from .reporting import summarise_metrics, write_report
from .runners import run_core_suite
from .worlds import WorldFactory


def _suite_metrics(outcomes):
    values: dict[str, MetricValue] = {}
    for summary in summarise_metrics(outcomes):
        if summary.defined:
            values[summary.metric_id] = MetricValue(
                metric_id=summary.metric_id,
                value=summary.value,
                value_type="float64",
                numerator=summary.numerator,
                denominator=summary.denominator,
                sample_size=summary.samples,
            )
        else:
            reason = UndefinedReason.MISSING_TELEMETRY
            if summary.undefined_reasons:
                try:
                    reason = UndefinedReason(summary.undefined_reasons[0])
                except ValueError:
                    pass
            values[summary.metric_id] = MetricValue(
                metric_id=summary.metric_id,
                value=None,
                value_type="float64",
                undefined_reason=reason,
            )
    return values


def _run_l2(cases):
    from .checks import check_ds01
    from .runners.harness_runner import run_scripted
    from .runners.reference import SuiteResult

    outcomes = []
    for case in cases:
        answer = str(case.expected.get("answer") or "")
        run = run_scripted(case.inputs["question"], answer)
        abstained = not answer.strip() and not run.answer.strip()
        outcomes.append(
            check_ds01(case, run.answer, abstained=abstained)
        )
    return SuiteResult(
        outcomes=outcomes,
        integration_level="L2_irina_integrated",
        world_id=cases[0].world_id if cases else "",
        dataset_version=cases[0].dataset_version if cases else "",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Irina's offline core evaluation")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--out", default="reports/core")
    parser.add_argument("--opik", action="store_true", help="mirror results to local Opik")
    parser.add_argument(
        "--dashboard",
        action="store_true",
        help="create/update the predefined Opik governance dashboard",
    )
    parser.add_argument(
        "--l2",
        action="store_true",
        help="run DS01 through the real Harness with a scripted model",
    )
    args = parser.parse_args(argv)

    world = WorldFactory().build(seed=args.seed)
    grouped = build_core_datasets(world)
    cases = flatten_datasets(grouped)
    if args.l2:
        cases = [case for case in cases if case.family_id == "DS01"]
        result = _run_l2(cases)
    else:
        result = run_core_suite(world, cases)

    composites = compute_composites(_suite_metrics(result.outcomes))

    json_path, md_path = write_report(
        result,
        world_manifest=world.manifest,
        output_dir=args.out,
        composites=composites,
    )
    coverage_path = write_coverage(args.out)

    if args.opik:
        from ..harness.observability import ensure_opik
        from .opik_adapter import (
            create_experiment,
            dataset_items,
            ensure_dataset,
            flush,
            link_experiment_items,
            log_feedback_scores,
            log_trace,
        )

        status = ensure_opik()
        if status.state not in {"reused", "started"}:
            print(f"[opik] {status.detail}; skipping mirror", file=sys.stderr)
        else:
            dataset_name = f"irina-core-{result.dataset_version}-s{args.seed}"
            summary_item = {
                "case_id": "run-summary",
                "family_id": "SUMMARY",
                "inputs": {"seed": args.seed, "suite": "core"},
                "expected": {"composites": [item.id for item in composites]},
                "expected_behavior": "suite_summary",
                "severity": "high",
            }
            ensure_dataset(
                dataset_name,
                [case.as_dict() for case in cases] + [summary_item],
            )
            item_ids = dataset_items(dataset_name)
            experiment = create_experiment(
                name=(
                    f"irina-core-{result.dataset_version}-s{args.seed}-"
                    f"{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
                ),
                dataset_name=dataset_name,
                config={
                    "dataset_version": result.dataset_version,
                    "seed": args.seed,
                    "integration_level": IntegrationLevel.L1_SIMULATED_WORKFLOW.value,
                },
            )
            references: list[tuple[str, str]] = []
            for outcome in result.outcomes:
                trace_id = log_trace(
                    f"eval:{outcome.case_id}",
                    input={"case_id": outcome.case_id, "family_id": outcome.family_id},
                    output={
                        "passed": outcome.passed,
                        "metrics": [metric.as_dict() for metric in outcome.metrics],
                    },
                    metadata={
                        "integration_level": IntegrationLevel.L1_SIMULATED_WORKFLOW.value
                    },
                )
                if trace_id:
                    scores = [
                        {
                            "name": metric.metric_id,
                            "value": float(metric.value),
                        }
                        for metric in outcome.metrics
                        if metric.defined
                        and isinstance(metric.value, (int, float, bool))
                    ]
                    log_feedback_scores(trace_id, scores)
                    item_id = item_ids.get(outcome.case_id)
                    if item_id:
                        references.append((item_id, trace_id))
            summary_trace = log_trace(
                "eval:run-summary",
                input={"seed": args.seed, "suite": "core"},
                output={
                    "composites": [item.as_dict() for item in composites],
                },
                metadata={
                    "integration_level": result.integration_level,
                    "gates": {
                        item.id: item.gate_triggered for item in composites
                    },
                },
            )
            if summary_trace:
                log_feedback_scores(
                    summary_trace,
                    [
                        {"name": item.id, "value": float(item.value)}
                        for item in composites
                        if item.value is not None
                    ],
                )
                summary_item_id = item_ids.get("run-summary")
                if summary_item_id:
                    references.append((summary_item_id, summary_trace))
            linked = link_experiment_items(experiment, references)
            if experiment is None:
                print("[opik] experiment creation blocked", file=sys.stderr)
            else:
                print(
                    f"[opik] experiment={getattr(experiment, 'id', '')} "
                    f"items={linked}",
                    file=sys.stderr,
                )
            flush()
            if args.dashboard:
                from .opik_adapter.dashboards import ensure_dashboard

                dashboard = ensure_dashboard()
                if dashboard is None:
                    print("[opik] dashboard creation blocked", file=sys.stderr)
                else:
                    print(
                        f"[opik] dashboard={getattr(dashboard, 'id', '')}",
                        file=sys.stderr,
                    )

    print(
        json.dumps(
            {
                "cases": len(result.outcomes),
                "passed": result.passed,
                "failed": result.failed,
                "undefined": result.undefined,
                "report": str(json_path),
                "markdown": str(md_path),
                "coverage": str(coverage_path),
            },
            indent=2,
        )
    )
    return 0 if result.failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
