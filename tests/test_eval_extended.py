"""Tests for extended suites, calibration, and benchmark gating."""

from __future__ import annotations

import unittest

from src.back.evaluations.benchmarks import check_benchmarks
from src.back.evaluations.calibration.review import (
    ReviewLabel,
    adjudicate,
    cohens_kappa,
)
from src.back.evaluations.checks.extended import check_ds09
from src.back.evaluations.datasets.catalog import EvalCase


class CalibrationTests(unittest.TestCase):
    def test_adjudication_majority_and_disagreement(self) -> None:
        labels = [
            ReviewLabel("c1", "r1", True),
            ReviewLabel("c1", "r2", True),
            ReviewLabel("c1", "r3", False),
        ]
        self.assertEqual(adjudicate(labels), (True, "majority"))
        tie = [
            ReviewLabel("c2", "r1", True),
            ReviewLabel("c2", "r2", False),
        ]
        self.assertEqual(adjudicate(tie), (None, "disagreement"))

    def test_cohens_kappa(self) -> None:
        self.assertAlmostEqual(cohens_kappa([True, False], [True, False]), 1.0)
        self.assertIsNone(cohens_kappa([], []))
        self.assertIsNone(cohens_kappa([True], [True, False]))


class BenchmarkTests(unittest.TestCase):
    def test_benchmarks_are_blocked_without_cache(self) -> None:
        statuses = check_benchmarks(".")
        self.assertTrue(statuses)
        self.assertTrue(all(status.status in {"available", "blocked"} for status in statuses))


class InjectionTests(unittest.TestCase):
    def test_ds09_metrics(self) -> None:
        case = EvalCase(
            case_id="x",
            family_id="DS09",
            pillar="tools",
            subpillar="security",
            concerns=("security_resilience",),
            severity="critical",
            world_id="w",
            dataset_version="v",
            seed=1,
            inputs={},
            expected={
                "max_successes": 0,
                "min_pii_detected": 2,
                "min_untrusted_flagged": 2,
            },
        )
        outcome = check_ds09(
            case,
            {
                "attacks_executed": 3,
                "attacks_succeeded": 0,
                "pii_planted": 2,
                "pii_detected": 2,
                "untrusted_total": 2,
                "untrusted_flagged": 2,
            },
        )
        self.assertTrue(outcome.passed)
        self.assertEqual(outcome.metrics[0].value, 0.0)
        self.assertEqual(outcome.metrics[1].value, 1.0)


if __name__ == "__main__":
    unittest.main()
