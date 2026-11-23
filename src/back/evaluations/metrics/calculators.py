"""Deterministic metric calculators.

Every function returns ``None`` for an undefined metric rather than inventing a
value. Callers convert ``None`` into an explicit :class:`MetricValue` reason.
"""

from __future__ import annotations

import hashlib
import math
from decimal import Decimal
from typing import Any, Iterable, Sequence


def safe_ratio(numerator: int, denominator: int) -> float | None:
    if numerator < 0 or denominator < 0 or numerator > denominator:
        raise ValueError("invalid proportion counts")
    return numerator / denominator if denominator else None


def rate(matches: int, eligible: int) -> float | None:
    return safe_ratio(matches, eligible)


def precision(true_positives: int, false_positives: int) -> float | None:
    if true_positives < 0 or false_positives < 0:
        raise ValueError("counts must be non-negative")
    total = true_positives + false_positives
    return true_positives / total if total else None


def recall(true_positives: int, false_negatives: int) -> float | None:
    if true_positives < 0 or false_negatives < 0:
        raise ValueError("counts must be non-negative")
    total = true_positives + false_negatives
    return true_positives / total if total else None


def false_negative_rate(true_positives: int, false_negatives: int) -> float | None:
    denominator = true_positives + false_negatives
    return false_negatives / denominator if denominator else None


def f1(precision_value: float | None, recall_value: float | None) -> float | None:
    if precision_value is None or recall_value is None:
        return None
    total = precision_value + recall_value
    return 2 * precision_value * recall_value / total if total else None


def precision_at_k(retrieved: Sequence[str], relevant: Iterable[str], k: int) -> float | None:
    if k <= 0:
        raise ValueError("k must be positive")
    relevant_set = set(relevant)
    top = list(dict.fromkeys(retrieved))[:k]
    hits = sum(1 for item in top if item in relevant_set)
    return hits / k


def recall_at_k(retrieved: Sequence[str], relevant: Iterable[str], k: int) -> float | None:
    if k <= 0:
        raise ValueError("k must be positive")
    relevant_set = set(relevant)
    if not relevant_set:
        return None
    top = list(dict.fromkeys(retrieved))[:k]
    hits = sum(1 for item in top if item in relevant_set)
    return hits / len(relevant_set)


def reciprocal_rank(retrieved: Sequence[str], relevant: Iterable[str]) -> float | None:
    relevant_set = set(relevant)
    if not relevant_set:
        return None
    for position, item in enumerate(dict.fromkeys(retrieved), start=1):
        if item in relevant_set:
            return 1 / position
    return 0.0


def mean_reciprocal_rank(
    rankings: Sequence[tuple[Sequence[str], Iterable[str]]],
) -> float | None:
    values = [reciprocal_rank(retrieved, relevant) for retrieved, relevant in rankings]
    defined = [value for value in values if value is not None]
    if not defined:
        return None
    return sum(defined) / len(defined)


def ndcg_at_k(
    retrieved: Sequence[str],
    relevance: dict[str, float],
    k: int,
) -> float | None:
    if k <= 0:
        raise ValueError("k must be positive")
    top = list(dict.fromkeys(retrieved))[:k]
    dcg = 0.0
    for position, item in enumerate(top, start=1):
        gain = (2 ** relevance.get(item, 0.0)) - 1
        dcg += gain / math.log2(position + 1)
    ideal = sorted(relevance.values(), reverse=True)[:k]
    idcg = 0.0
    for position, gain_value in enumerate(ideal, start=1):
        gain = (2 ** gain_value) - 1
        idcg += gain / math.log2(position + 1)
    return dcg / idcg if idcg else None


def pair_disparity(pairs: Sequence[tuple[bool, bool]]) -> float | None:
    if not pairs:
        return None
    unjustified = sum(1 for left, right in pairs if left != right)
    return unjustified / len(pairs)


def percent_change(current: float, baseline: float) -> float | None:
    return 100 * (current - baseline) / baseline if baseline else None


def compaction_ratio(tokens_before: int, tokens_after: int) -> float | None:
    if tokens_before < 0 or tokens_after < 0:
        raise ValueError("token counts must be non-negative")
    return tokens_after / tokens_before if tokens_before else None


def token_reduction(tokens_before: int, tokens_after: int) -> float | None:
    ratio = compaction_ratio(tokens_before, tokens_after)
    return 1 - ratio if ratio is not None else None


def canonical_bytes(value: Any) -> bytes:
    import json

    return json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")


def sha256_hex(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def hash_matches(value: Any, expected_digest: str) -> bool:
    return sha256_hex(value) == expected_digest.lower()


def numeric_correct(
    predicted: Decimal | str | int | float,
    reference: Decimal | str | int | float,
    *,
    atol: Decimal = Decimal("0"),
    rtol: Decimal = Decimal("0"),
) -> bool:
    left = Decimal(str(predicted))
    right = Decimal(str(reference))
    tolerance = atol + rtol * abs(right)
    return abs(left - right) <= tolerance


def accuracy(correct: int, total: int) -> float | None:
    return safe_ratio(correct, total)


__all__ = [
    "accuracy",
    "canonical_bytes",
    "compaction_ratio",
    "false_negative_rate",
    "f1",
    "hash_matches",
    "mean_reciprocal_rank",
    "ndcg_at_k",
    "numeric_correct",
    "pair_disparity",
    "percent_change",
    "precision",
    "precision_at_k",
    "rate",
    "recall",
    "recall_at_k",
    "reciprocal_rank",
    "safe_ratio",
    "sha256_hex",
    "token_reduction",
]
