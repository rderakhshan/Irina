"""Tests for the deterministic synthetic world and oracles."""

from __future__ import annotations

import unittest
from datetime import datetime, timezone
from decimal import Decimal

from src.back.evaluations.oracles import (
    apply_transitions,
    approval_precedes_execution,
    assets_identity_residual,
    decide,
    leverage,
    lookahead_ids,
    net_margin,
    preservation_recall,
    unauthorized_ids,
)
from src.back.evaluations.worlds import WorldFactory


class WorldTests(unittest.TestCase):
    def setUp(self) -> None:
        self.world = WorldFactory().build(seed=7)
        self.company = self.world.company("AAA")

    def test_same_seed_is_reproducible(self) -> None:
        other = WorldFactory().build(seed=7)
        self.assertEqual(self.world.manifest, other.manifest)

    def test_different_seed_changes_world(self) -> None:
        other = WorldFactory().build(seed=8)
        self.assertNotEqual(self.world.manifest["world_hash"], other.manifest["world_hash"])

    def test_future_document_excluded(self) -> None:
        visible = {doc.document_id for doc in self.world.visible_documents(self.world.as_of)}
        self.assertNotIn("AAA-PRELIM-2025", visible)
        self.assertNotIn("AAA-10K-A-2025", visible)
        self.assertIn("AAA-10K-2024", visible)

    def test_confidential_document_excluded(self) -> None:
        visible = {doc.document_id for doc in self.world.visible_documents(self.world.as_of)}
        self.assertNotIn("AAA-CREDIT-INTERNAL", visible)
        privileged = {
            doc.document_id
            for doc in self.world.visible_documents(
                self.world.as_of, access_scope=frozenset({"analyst", "credit_committee"})
            )
        }
        self.assertIn("AAA-CREDIT-INTERNAL", privileged)

    def test_chunks_respect_time_and_access(self) -> None:
        chunks = self.world.visible_chunks(self.world.as_of)
        self.assertTrue(all(not chunk.document_id.endswith("PRELIM-2025") for chunk in chunks))
        self.assertTrue(all(not chunk.document_id.endswith("CREDIT-INTERNAL") for chunk in chunks))

    def test_lookahead_and_unauthorized_detection(self) -> None:
        leaked = lookahead_ids(
            self.world, ["AAA-PRELIM-2025", "AAA-10K-2024"], self.world.as_of
        )
        self.assertEqual(leaked, ["AAA-PRELIM-2025"])
        denied = unauthorized_ids(self.world, ["AAA-CREDIT-INTERNAL"], frozenset({"analyst"}))
        self.assertEqual(denied, ["AAA-CREDIT-INTERNAL"])


class OracleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.world = WorldFactory().build(seed=7)
        self.company = self.world.company("AAA")

    def test_financial_calculations_are_decimal_and_consistent(self) -> None:
        self.assertEqual(assets_identity_residual(self.company), Decimal("0.0000"))
        self.assertEqual(leverage(self.company), (self.company.total_debt / self.company.equity).quantize(Decimal("0.0001")))
        self.assertEqual(net_margin(self.company), (self.company.net_income / self.company.revenue).quantize(Decimal("0.0001")))

    def test_policy_fails_closed_and_escalates(self) -> None:
        self.assertEqual(
            decide(self.world.policy_rules, principal="analyst", action="submit_order").decision,
            "reject",
        )
        decision = decide(
            self.world.policy_rules, principal="analyst", action="send_client_memo"
        )
        self.assertEqual(decision.decision, "escalate")
        self.assertTrue(decision.requires_approval)

    def test_approval_must_precede_and_bind_payload(self) -> None:
        now = datetime(2025, 1, 1, tzinfo=timezone.utc)
        later = datetime(2025, 1, 2, tzinfo=timezone.utc)
        self.assertTrue(
            approval_precedes_execution(
                approval_at=now,
                execution_at=later,
                approved_payload_hash="a",
                executed_payload_hash="a",
            )
        )
        self.assertFalse(
            approval_precedes_execution(
                approval_at=now,
                execution_at=later,
                approved_payload_hash="a",
                executed_payload_hash="b",
            )
        )
        self.assertFalse(
            approval_precedes_execution(
                approval_at=later,
                execution_at=now,
                approved_payload_hash="a",
                executed_payload_hash="a",
            )
        )

    def test_memory_transitions_and_preservation(self) -> None:
        state = {"m1": "old", "m2": "keep"}
        updated = apply_transitions(
            state,
            [
                {"op": "update", "memory_id": "m1", "text": "new"},
                {"op": "delete", "memory_id": "m2"},
            ],
        )
        self.assertEqual(updated, {"m1": "new"})
        self.assertAlmostEqual(preservation_recall(["a", "b"], ["a"]), 0.5)
        self.assertIsNone(preservation_recall([], []))


if __name__ == "__main__":
    unittest.main()
