"""Shared enums for evaluation evidence."""

from __future__ import annotations

from enum import StrEnum


class IntegrationLevel(StrEnum):
    L0_ORACLE_UNIT = "L0_oracle_unit"
    L1_SIMULATED_WORKFLOW = "L1_simulated_workflow"
    L2_IRINA_INTEGRATED = "L2_irina_integrated"
    L3_PRODUCTION_OBSERVED = "L3_production_observed"


class EvaluationStatus(StrEnum):
    IMPLEMENTED = "implemented"
    PARTIAL = "partial"
    BLOCKED = "blocked"
    NOT_APPLICABLE = "not_applicable"
    PLANNED = "planned"
    VERIFIED = "verified"


class Decision(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    CONDITIONAL_PASS = "conditional_pass"
    NEEDS_HUMAN_REVIEW = "needs_human_review"


class Timing(StrEnum):
    OFF = "OFF"
    ON_S = "ON-S"
    ON_A = "ON-A"
    ON_T = "ON-T"


class DatasetDependency(StrEnum):
    D = "D"
    C = "C"
    N = "N"
    B = "B"


__all__ = [
    "DatasetDependency",
    "Decision",
    "EvaluationStatus",
    "IntegrationLevel",
    "Timing",
]
