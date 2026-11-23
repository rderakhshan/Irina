"""Audit-trail checks over recorded events and artifacts."""

from __future__ import annotations

from typing import Any, Iterable

from ..metrics.calculators import hash_matches
from ..metrics.metric_value import MetricValue, UndefinedReason


def _metric(metric_id: str, numerator: int, denominator: int) -> MetricValue:
    if denominator == 0:
        return MetricValue(
            metric_id=metric_id,
            value=None,
            value_type="float64",
            undefined_reason=UndefinedReason.MISSING_TELEMETRY,
        )
    return MetricValue(
        metric_id=metric_id,
        value=numerator / denominator,
        value_type="float64",
        numerator=numerator,
        denominator=denominator,
    )


def event_completeness(observed: Iterable[str], required: Iterable[str]) -> MetricValue:
    expected = list(dict.fromkeys(required))
    seen = set(observed)
    matched = sum(1 for event in expected if event in seen)
    return _metric("environment.governance_event_completeness", matched, len(expected))


def trace_correlation(records: Iterable[dict[str, Any]]) -> MetricValue:
    rows = list(records)
    linked = sum(
        1
        for row in rows
        if row.get("run_id") and row.get("trace_id")
    )
    return _metric("environment.trace_correlation_rate", linked, len(rows))


def evidence_integrity(value: Any, expected_hash: str) -> MetricValue:
    if not expected_hash:
        return MetricValue(
            metric_id="environment.evidence_integrity_version_binding",
            value=None,
            value_type="bool",
            unit="boolean",
            undefined_reason=UndefinedReason.MISSING_GOLD,
        )
    return MetricValue(
        metric_id="environment.evidence_integrity_version_binding",
        value=hash_matches(value, expected_hash),
        value_type="bool",
        unit="boolean",
    )


__all__ = ["event_completeness", "evidence_integrity", "trace_correlation"]
