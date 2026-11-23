"""Checks for tools, memory, and judge calibration datasets."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..datasets.catalog import EvalCase
from ..metrics.calculators import (
    accuracy,
    false_negative_rate,
    precision,
    recall,
)
from ..metrics.metric_value import MetricValue, UndefinedReason
from ..oracles.memory import preservation_recall
from ..oracles.retrieval import evaluate_ranking


def _metric(
    metric_id: str,
    value: float | int | bool | None,
    *,
    numerator: int | None = None,
    denominator: int | None = None,
    value_type: str = "float64",
    unit: str = "proportion",
    reason: UndefinedReason | None = None,
) -> MetricValue:
    return MetricValue(
        metric_id=metric_id,
        value=value,
        value_type=value_type,  # type: ignore[arg-type]
        unit=unit,
        numerator=numerator,
        denominator=denominator,
        undefined_reason=reason,
        integration_level="L1_simulated_workflow",
    )


@dataclass(slots=True)
class Outcome:
    case_id: str
    family_id: str
    metrics: list[MetricValue] = field(default_factory=list)
    passed: bool | None = None
    details: dict[str, Any] = field(default_factory=dict)


def check_ds06(case: EvalCase, actions: list[dict[str, Any]]) -> Outcome:
    expected = case.expected.get("tool_calls", [])
    expected_names = [item.get("name") for item in expected]
    actual_names = [item.get("name") for item in actions]
    acceptable = set(case.expected.get("acceptable_tools", expected_names))
    selection_correct = bool(actual_names) and all(
        name in acceptable for name in actual_names
    )
    param_correct = all(
        a.get("args") == e.get("args")
        for a, e in zip(actions, expected)
        if e.get("args") is not None
    ) and len(actions) == len(expected)
    order_correct = actual_names == expected_names
    schema_correct = all(
        isinstance(item.get("name"), str) and isinstance(item.get("args"), dict)
        for item in actions
    )
    total = max(1, len(expected))
    metrics = [
        _metric(
            "tools.tool_selection_accuracy",
            int(selection_correct),
            numerator=int(selection_correct),
            denominator=1,
        ),
        _metric(
            "tools.parameter_correctness",
            int(param_correct),
            numerator=int(param_correct),
            denominator=total,
        ),
        _metric(
            "tools.trajectory_validity",
            int(order_correct),
            numerator=int(order_correct),
            denominator=1,
        ),
        _metric(
            "tools.tool_schema_validity",
            schema_correct,
            value_type="bool",
            unit="boolean",
        ),
    ]
    return Outcome(
        case_id=case.case_id,
        family_id=case.family_id,
        metrics=metrics,
        passed=selection_correct and param_correct and order_correct and schema_correct,
        details={"expected": expected, "actual": actions},
    )


def check_memory_retrieval(case: EvalCase, retrieved_ids: list[str]) -> Outcome:
    relevant = list(case.expected.get("relevant_memory_ids", []))
    k = int(case.inputs.get("k", 5))
    scores = evaluate_ranking(retrieved_ids, relevant, k=k)
    metrics: list[MetricValue] = []
    for key, metric_id in (
        ("precision_at_k", "memory.retrieval_precision_at_k"),
        ("recall_at_k", "memory.retrieval_recall_at_k"),
        ("mrr", "memory.retrieval_mrr"),
        ("ndcg", "memory.retrieval_ndcg"),
    ):
        value = scores[key]
        if value is None:
            metrics.append(
                _metric(metric_id, None, reason=UndefinedReason.EMPTY_DENOMINATOR)
            )
        else:
            metrics.append(_metric(metric_id, float(value)))
    return Outcome(
        case_id=case.case_id,
        family_id=case.family_id,
        metrics=metrics,
        passed=scores["recall_at_k"] is not None and scores["recall_at_k"] > 0,
        details={"retrieved": retrieved_ids, "relevant": relevant},
    )


def check_memory_lifecycle(case: EvalCase, final_state: dict[str, str]) -> Outcome:
    expected_state = dict(case.expected.get("state", {}))
    required = list(case.expected.get("required_facts", []))
    applied = sum(
        1
        for key, value in expected_state.items()
        if final_state.get(key) == value
    )
    transitions = max(1, len(expected_state))
    preservation = preservation_recall(required, final_state.values())
    tokens_before = int(case.expected.get("tokens_before", 0))
    tokens_after = int(case.expected.get("tokens_after", 0))
    metrics = [
        _metric(
            "memory.write_accuracy",
            applied / transitions,
            numerator=applied,
            denominator=transitions,
        ),
        _metric(
            "memory.preservation_recall",
            preservation if preservation is not None else None,
            reason=(
                None
                if preservation is not None
                else UndefinedReason.EMPTY_DENOMINATOR
            ),
        ),
    ]
    if tokens_before > 0:
        metrics.append(
            _metric(
                "memory.compaction_ratio",
                tokens_after / tokens_before,
                value_type="float64",
                unit="ratio",
            )
        )
    return Outcome(
        case_id=case.case_id,
        family_id=case.family_id,
        metrics=metrics,
        passed=final_state == expected_state,
        details={"expected": expected_state, "actual": final_state},
    )


def check_calibration(case: EvalCase, judge_labels: list[bool]) -> Outcome:
    human = [bool(item) for item in case.expected.get("human_labels", [])]
    predicted = [bool(item) for item in judge_labels]
    if len(human) != len(predicted):
        raise ValueError("calibration labels must have equal length")
    tp = sum(1 for h, p in zip(human, predicted) if h and p)
    fp = sum(1 for h, p in zip(human, predicted) if not h and p)
    fn = sum(1 for h, p in zip(human, predicted) if h and not p)
    tn = sum(1 for h, p in zip(human, predicted) if not h and not p)
    total = len(human)
    metrics = [
        _metric(
            "calibration.judge_precision",
            precision(tp, fp) if tp + fp else None,
            reason=None if tp + fp else UndefinedReason.EMPTY_DENOMINATOR,
        ),
        _metric(
            "calibration.judge_recall",
            recall(tp, fn) if tp + fn else None,
            reason=None if tp + fn else UndefinedReason.EMPTY_DENOMINATOR,
        ),
        _metric(
            "calibration.judge_fnr",
            false_negative_rate(tp, fn) if tp + fn else None,
            reason=None if tp + fn else UndefinedReason.EMPTY_DENOMINATOR,
        ),
        _metric(
            "calibration.agreement_rate",
            accuracy(tp + tn, total) if total else None,
            reason=None if total else UndefinedReason.EMPTY_DENOMINATOR,
        ),
    ]
    return Outcome(
        case_id=case.case_id,
        family_id=case.family_id,
        metrics=metrics,
        passed=predicted == human,
        details={"tp": tp, "fp": fp, "fn": fn, "tn": tn},
    )


__all__ = [
    "Outcome",
    "check_calibration",
    "check_ds06",
    "check_memory_lifecycle",
    "check_memory_retrieval",
]
