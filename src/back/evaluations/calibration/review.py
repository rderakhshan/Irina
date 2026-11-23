"""Human calibration review workflow and agreement mathematics."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ReviewLabel:
    case_id: str
    reviewer: str
    label: bool
    severity: str = "high"
    rubric_version: str = "1"
    note: str = ""


def adjudicate(labels: list[ReviewLabel]) -> tuple[bool | None, str]:
    if not labels:
        return None, "no_labels"
    counts = Counter(item.label for item in labels)
    top = counts.most_common()
    if len(top) > 1 and top[0][1] == top[1][1]:
        return None, "disagreement"
    return top[0][0], "majority"


def cohens_kappa(first: list[bool], second: list[bool]) -> float | None:
    if len(first) != len(second) or not first:
        return None
    total = len(first)
    observed = sum(1 for left, right in zip(first, second) if left == right) / total
    left_true = sum(first) / total
    right_true = sum(second) / total
    expected = left_true * right_true + (1 - left_true) * (1 - right_true)
    if expected == 1:
        return None
    return (observed - expected) / (1 - expected)


__all__ = ["ReviewLabel", "adjudicate", "cohens_kappa"]
