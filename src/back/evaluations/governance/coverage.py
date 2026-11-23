"""Coverage matrix built from the metric dictionary."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from ..contracts.records import CoverageStatus
from ..metrics.registry import load_dictionary

CONCERNS = (
    "trustworthiness",
    "accountability",
    "explainability",
    "fairness",
    "privacy",
    "safety",
    "security_resilience",
    "organizational_values",
    "lifecycle",
    "risk_management",
    "auditing",
    "compliance",
)


def coverage_statuses() -> list[CoverageStatus]:
    definitions = load_dictionary()
    statuses: list[CoverageStatus] = []
    for metric in definitions.values():
        for concern in metric.concerns:
            applicability = "not_applicable" if metric.status == "blocked" else "applicable"
            statuses.append(
                CoverageStatus(
                    concern_id=concern,
                    pillar=metric.pillar,
                    check_id=metric.metric_id,
                    applicability=applicability,
                    implementation_status=metric.status,
                    owner=metric.owner,
                    blocker="" if metric.status != "blocked" else "requires runtime control",
                )
            )
    return statuses


def summary() -> dict[str, Any]:
    statuses = coverage_statuses()
    by_concern: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    by_pillar: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for status in statuses:
        by_concern[status.concern_id][status.implementation_status] += 1
        by_pillar[status.pillar][status.implementation_status] += 1
    return {
        "schema_version": "1",
        "concerns": {
            concern: dict(counts) for concern, counts in sorted(by_concern.items())
        },
        "pillars": {pillar: dict(counts) for pillar, counts in sorted(by_pillar.items())},
        "unmapped_concerns": [
            concern for concern in CONCERNS if concern not in by_concern
        ],
        "checks": [status.as_dict() for status in statuses],
        "limitations": [
            "planned checks are not implemented checks",
            "blocked checks cannot be reported as passes",
            "synthetic fixtures are not production evidence",
        ],
    }


def write_coverage(output_dir: str | Path) -> Path:
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "coverage.json"
    path.write_text(
        json.dumps(summary(), indent=2, default=str), encoding="utf-8"
    )
    return path


__all__ = ["CONCERNS", "coverage_statuses", "summary", "write_coverage"]
