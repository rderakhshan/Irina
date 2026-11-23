"""Tests for the disposable retrieval fixture."""

from __future__ import annotations

import unittest
from datetime import datetime, timezone

from src.back.evaluations.rag_fixture import FixtureRetriever
from src.back.evaluations.worlds import WorldFactory


class RetrieverTests(unittest.TestCase):
    def setUp(self) -> None:
        self.world = WorldFactory().build(seed=7)
        self.retriever = FixtureRetriever(self.world)

    def test_retrieves_relevant_chunks(self) -> None:
        hits = self.retriever.search("total debt equity leverage", k=5)
        self.assertTrue(hits)
        self.assertTrue(any("10K-2024" in hit.document_id for hit in hits))

    def test_excludes_future_documents(self) -> None:
        hits = self.retriever.search("preliminary 2025 results", k=5)
        self.assertTrue(all("PRELIM-2025" not in hit.document_id for hit in hits))

    def test_excludes_confidential_documents_for_analyst(self) -> None:
        hits = self.retriever.search("confidential credit review", k=5)
        self.assertTrue(all("CREDIT-INTERNAL" not in hit.document_id for hit in hits))

    def test_privileged_scope_can_see_confidential(self) -> None:
        hits = self.retriever.search(
            "confidential credit review",
            access_scope=frozenset({"analyst", "credit_committee"}),
            k=5,
        )
        self.assertTrue(any("CREDIT-INTERNAL" in hit.document_id for hit in hits))

    def test_k_must_be_positive(self) -> None:
        with self.assertRaises(ValueError):
            self.retriever.search("debt", k=0)

    def test_deterministic(self) -> None:
        first = [hit.chunk_id for hit in self.retriever.search("debt", k=5)]
        second = [hit.chunk_id for hit in self.retriever.search("debt", k=5)]
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
