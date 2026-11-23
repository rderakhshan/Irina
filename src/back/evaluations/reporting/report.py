"""Human- and machine-readable evaluation reports."""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from ..metrics.metric_value import MetricValue
from ..runners.reference import SuiteResult


@dataclass(slots=True)
class MetricSummary:
    metric_id: str
    value: float | int | bool | None
    defined: bool
    numerator: int | None
    denominator: int | None
    samples: int
    undefined_reasons: list[str] = field(default_factory=list)


def summarise_metrics(outcomes: list[Any]) -> list[MetricSummary]:
    grouped: dict[str, list[MetricValue]] = defaultdict(list)
    for outcome in outcomes:
        for metric in outcome.metrics:
            grouped[metric.metric_id].append(metric)
    summaries: list[MetricSummary] = []
    for metric_id, values in sorted(grouped.items()):
        defined = [value for value in values if value.defined]
        reasons = sorted(
            {
                value.undefined_reason.value
                for value in values
                if value.undefined_reason is not None
            }
        )
        if not defined:
            summaries.append(
                MetricSummary(
                    metric_id=metric_id,
                    value=None,
                    defined=False,
                    numerator=None,
                    denominator=None,
                    samples=len(values),
                    undefined_reasons=reasons,
                )
            )
            continue
        numerator = sum(value.numerator or 0 for value in defined)
        denominator = sum(value.denominator or 0 for value in defined)
        if denominator:
            aggregate: float = numerator / denominator
        else:
            numeric = [
                float(value.value)
                for value in defined
                if isinstance(value.value, (int, float))
            ]
            aggregate = sum(numeric) / len(numeric) if numeric else float("nan")
        summaries.append(
            MetricSummary(
                metric_id=metric_id,
                value=round(aggregate, 6),
                defined=True,
                numerator=numerator if denominator else None,
                denominator=denominator or None,
                samples=len(values),
                undefined_reasons=reasons,
            )
        )
    return summaries


def build_report(result: SuiteResult, *, world_manifest: dict[str, Any]) -> dict[str, Any]:
    summaries = summarise_metrics(result.outcomes)
    cases = []
    for outcome in result.outcomes:
        cases.append(
            {
                "case_id": outcome.case_id,
                "family_id": outcome.family_id,
                "passed": outcome.passed,
                "metrics": [metric.as_dict() for metric in outcome.metrics],
                "details": outcome.details,
            }
        )
    return {
        "schema_version": "1",
        "dataset_version": result.dataset_version,
        "world_id": result.world_id,
        "world_manifest": world_manifest,
        "integration_level": result.integration_level,
        "totals": {
            "cases": len(result.outcomes),
            "passed": result.passed,
            "failed": result.failed,
            "undefined": result.undefined,
        },
        "metrics": [asdict(summary) for summary in summaries],
        "cases": cases,
        "limitations": [
            "Synthetic fixtures are fictional.",
            "Reference responder results are L1 evidence, not LLM behavior.",
            "Fixture RAG is not production retrieval.",
        ],
    }


def to_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Governance Evaluation Report",
        "",
        f"- World: `{report.get('world_id', '')}`",
        f"- Dataset: `{report.get('dataset_version', '')}`",
        f"- Evidence level: `{report.get('integration_level', '')}`",
        f"- Cases: {report['totals']['cases']} "
        f"(passed {report['totals']['passed']}, failed {report['totals']['failed']}, "
        f"undefined {report['totals']['undefined']})",
        "",
        "| Metric | Value | N | Denominator | Undefined |",
        "|---|---|---|---|---|",
    ]
    for metric in report.get("metrics", []):
        undefined = ", ".join(metric.get("undefined_reasons", [])) or "-"
        value = metric["value"] if metric["value"] is not None else "undefined"
        lines.append(
            f"| `{metric['metric_id']}` | {value} | {metric['samples']} | "
            f"{metric['denominator'] or '-'} | {undefined} |"
        )
    lines.extend(["", "## Failures", ""])
    failures = [case for case in report.get("cases", []) if case["passed"] is False]
    if not failures:
        lines.append("None.")
    else:
        for case in failures:
            lines.append(f"- `{case['case_id']}` ({case['family_id']})")
    lines.extend(["", "## Limitations", ""])
    for limitation in report.get("limitations", []):
        lines.append(f"- {limitation}")
    return "\n".join(lines) + "\n"


def write_report(
    result: SuiteResult,
    *,
    world_manifest: dict[str, Any],
    output_dir: str | Path,
) -> tuple[Path, Path]:
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    report = build_report(result, world_manifest=world_manifest)
    json_path = directory / "evaluation_report.json"
    md_path = directory / "evaluation_report.md"
    json_path.write_text(
        json.dumps(report, indent=2, default=str), encoding="utf-8"
    )
    md_path.write_text(to_markdown(report), encoding="utf-8")
    return json_path, md_path


__all__ = [
    "MetricSummary",
    "build_report",
    "summarise_metrics",
    "to_markdown",
    "write_report",
]
