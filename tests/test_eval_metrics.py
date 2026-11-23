"""Tests for metric definitions and calculators."""

from __future__ import annotations

import unittest
from decimal import Decimal

from src.back.evaluations.metrics import (
    MetricValue,
    UndefinedReason,
    compaction_ratio,
    f1,
    load_dictionary,
    mean_reciprocal_rank,
    ndcg_at_k,
    numeric_correct,
    precision,
    precision_at_k,
    recall,
    recall_at_k,
    safe_ratio,
    validate_dictionary,
)


class DictionaryTests(unittest.TestCase):
    def test_dictionary_loads_and_validates(self) -> None:
        definitions = load_dictionary()
        self.assertGreater(len(definitions), 20)
        self.assertEqual(validate_dictionary(), [])
        self.assertTrue(all(metric.dataset_dependency in {"D", "C", "N", "B"} for metric in definitions.values()))


class CalculatorTests(unittest.TestCase):
    def test_safe_ratio_undefined_for_empty_denominator(self) -> None:
        self.assertIsNone(safe_ratio(0, 0))
        self.assertEqual(safe_ratio(1, 4), 0.25)
        with self.assertRaises(ValueError):
            safe_ratio(5, 2)
        with self.assertRaises(ValueError):
            safe_ratio(-1, 2)

    def test_precision_recall_f1_undefined(self) -> None:
        self.assertIsNone(precision(0, 0))
        self.assertIsNone(recall(0, 0))
        self.assertIsNone(f1(None, 0.5))
        self.assertAlmostEqual(f1(0.5, 0.5), 0.5)

    def test_retrieval_metrics(self) -> None:
        retrieved = ["a", "b", "c"]
        relevant = ["b", "c"]
        self.assertAlmostEqual(precision_at_k(retrieved, relevant, 3), 2 / 3)
        self.assertAlmostEqual(recall_at_k(retrieved, relevant, 3), 1.0)
        self.assertAlmostEqual(precision_at_k(["a"], relevant, 3), 0.0)
        self.assertIsNone(recall_at_k(["a"], [], 3))
        self.assertAlmostEqual(mean_reciprocal_rank([(["x", "b"], ["b"])]), 0.5)
        self.assertIsNone(mean_reciprocal_rank([(["x"], [])]))
        self.assertAlmostEqual(
            ndcg_at_k(["b", "a"], {"b": 1.0, "a": 0.0}, 2),
            1.0,
        )
        self.assertIsNone(ndcg_at_k([], {}, 2))

    def test_numeric_tolerance(self) -> None:
        self.assertTrue(numeric_correct(Decimal("1.00001"), Decimal("1.0"), atol=Decimal("0.0001")))
        self.assertFalse(numeric_correct(Decimal("1.1"), Decimal("1.0"), atol=Decimal("0.0001")))
        self.assertTrue(numeric_correct(Decimal("100.5"), Decimal("100"), rtol=Decimal("0.01")))

    def test_compaction_ratio(self) -> None:
        self.assertAlmostEqual(compaction_ratio(100, 25), 0.25)
        self.assertIsNone(compaction_ratio(0, 10))


class MetricValueTests(unittest.TestCase):
    def test_requires_exactly_one_of_value_or_reason(self) -> None:
        with self.assertRaises(ValueError):
            MetricValue(metric_id="x", value=None, value_type="float64")
        with self.assertRaises(ValueError):
            MetricValue(
                metric_id="x",
                value=1.0,
                value_type="float64",
                undefined_reason=UndefinedReason.EMPTY_DENOMINATOR,
            )

    def test_rejects_nan_and_bad_counts(self) -> None:
        with self.assertRaises(ValueError):
            MetricValue(metric_id="x", value=float("nan"), value_type="float64")
        with self.assertRaises(ValueError):
            MetricValue(
                metric_id="x",
                value=1.0,
                value_type="float64",
                numerator=3,
                denominator=2,
                unit="proportion",
            )

    def test_undefined_metric_is_not_zero(self) -> None:
        metric = MetricValue(
            metric_id="x",
            value=None,
            value_type="float64",
            undefined_reason=UndefinedReason.EMPTY_DENOMINATOR,
        )
        self.assertFalse(metric.defined)
        self.assertIsNone(metric.value)


if __name__ == "__main__":
    unittest.main()


class ClaimMetricTests(unittest.TestCase):
    def test_zero_claims_is_undefined_not_success(self) -> None:
        from src.back.evaluations.checks.claims import claim_citation_coverage

        metric = claim_citation_coverage([])
        self.assertFalse(metric.defined)
        self.assertEqual(metric.undefined_reason.value, "empty_denominator")

    def test_claim_support_and_citation_rates(self) -> None:
        from src.back.evaluations.checks.claims import (
            Claim,
            claim_citation_coverage,
            claim_support_rate,
            citation_resolution_rate,
            contradicted_claim_rate,
        )

        claims = [
            Claim("c1", "assets were 10", ("doc#1",), "supported"),
            Claim("c2", "debt was 5", ("doc#2",), "contradicted"),
            Claim("c3", "margin was 2", (), "insufficient"),
        ]
        self.assertAlmostEqual(claim_citation_coverage(claims).value, 2 / 3)
        self.assertAlmostEqual(claim_support_rate(claims).value, 1 / 3)
        self.assertAlmostEqual(contradicted_claim_rate(claims).value, 1 / 3)
        self.assertAlmostEqual(
            citation_resolution_rate(claims, {"doc#1"}).value, 0.5
        )
        self.assertFalse(citation_resolution_rate([], set()).defined)


class AuditMetricTests(unittest.TestCase):
    def test_event_completeness_and_undefined(self) -> None:
        from src.back.evaluations.checks.audit import event_completeness

        metric = event_completeness(["run_started", "run_ended"], ["run_started", "run_ended", "tool_started"])
        self.assertAlmostEqual(metric.value, 2 / 3)
        self.assertFalse(event_completeness([], []).defined)

    def test_trace_correlation(self) -> None:
        from src.back.evaluations.checks.audit import trace_correlation

        metric = trace_correlation([{"run_id": "r", "trace_id": "t"}, {"run_id": "r"}])
        self.assertAlmostEqual(metric.value, 0.5)
        self.assertFalse(trace_correlation([]).defined)

    def test_evidence_integrity_hash(self) -> None:
        from src.back.evaluations.checks.audit import evidence_integrity
        from src.back.evaluations.metrics.calculators import sha256_hex

        value = {"doc": "x"}
        self.assertTrue(evidence_integrity(value, sha256_hex(value)).value)
        self.assertFalse(evidence_integrity(value, "deadbeef").value)
        self.assertFalse(evidence_integrity(value, "").defined)
