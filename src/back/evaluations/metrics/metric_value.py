"""Typed metric values and calculation primitives."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum
from typing import Any, Literal

ValueType = Literal["int64", "float64", "decimal", "bool", "enum"]
Direction = Literal["higher_better", "lower_better", "target", "informational"]


class UndefinedReason(StrEnum):
    EMPTY_DENOMINATOR = "empty_denominator"
    MISSING_GOLD = "missing_gold"
    MISSING_TELEMETRY = "missing_telemetry"
    NOT_APPLICABLE = "not_applicable"
    UNVERIFIED_JUDGE = "unverified_judge"
    UNSUPPORTED_API = "unsupported_api"


@dataclass(frozen=True, slots=True)
class MetricValue:
    metric_id: str
    value: int | float | Decimal | bool | str | None
    value_type: ValueType
    unit: str = "proportion"
    numerator: int | None = None
    denominator: int | None = None
    sample_size: int | None = None
    aggregation: str = "micro"
    direction: Direction = "higher_better"
    undefined_reason: UndefinedReason | None = None
    dataset_version: str = ""
    oracle_version: str = ""
    evaluator_version: str = ""
    integration_level: str = "L0_oracle_unit"
    evidence_refs: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if (self.value is None) == (self.undefined_reason is None):
            raise ValueError("exactly one of value or undefined_reason is required")
        if self.value is not None and self.value_type == "float64":
            if not isinstance(self.value, (int, float)):
                raise TypeError("float64 value must be numeric")
            if self.value != self.value or self.value in (float("inf"), float("-inf")):
                raise ValueError("float64 value must be finite")
        if self.numerator is not None and self.numerator < 0:
            raise ValueError("numerator must be non-negative")
        if self.denominator is not None and self.denominator < 0:
            raise ValueError("denominator must be non-negative")
        if (
            self.numerator is not None
            and self.denominator is not None
            and self.unit == "proportion"
            and self.numerator > self.denominator
        ):
            raise ValueError("numerator cannot exceed denominator")

    @property
    def defined(self) -> bool:
        return self.value is not None

    def as_dict(self) -> dict[str, Any]:
        return {
            "metric_id": self.metric_id,
            "value": (
                str(self.value) if isinstance(self.value, Decimal) else self.value
            ),
            "value_type": self.value_type,
            "unit": self.unit,
            "numerator": self.numerator,
            "denominator": self.denominator,
            "sample_size": self.sample_size,
            "aggregation": self.aggregation,
            "direction": self.direction,
            "undefined_reason": (
                self.undefined_reason.value if self.undefined_reason else None
            ),
            "dataset_version": self.dataset_version,
            "oracle_version": self.oracle_version,
            "evaluator_version": self.evaluator_version,
            "integration_level": self.integration_level,
            "evidence_refs": list(self.evidence_refs),
        }


def undefined(
    metric_id: str,
    reason: UndefinedReason,
    *,
    value_type: ValueType = "float64",
    unit: str = "proportion",
    integration_level: str = "L0_oracle_unit",
) -> MetricValue:
    return MetricValue(
        metric_id=metric_id,
        value=None,
        value_type=value_type,
        unit=unit,
        undefined_reason=reason,
        integration_level=integration_level,
    )


__all__ = [
    "Direction",
    "MetricValue",
    "UndefinedReason",
    "ValueType",
    "undefined",
]
