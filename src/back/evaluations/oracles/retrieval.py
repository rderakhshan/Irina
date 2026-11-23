"""Retrieval oracles over the synthetic corpus."""

from __future__ import annotations

from ..metrics.calculators import (
    mean_reciprocal_rank,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
)
from ..worlds.factory import Chunk


def evaluate_ranking(
    retrieved_ids: list[str],
    relevant_ids: list[str],
    *,
    k: int,
    graded_relevance: dict[str, float] | None = None,
) -> dict[str, float | None]:
    return {
        "precision_at_k": precision_at_k(retrieved_ids, relevant_ids, k),
        "recall_at_k": recall_at_k(retrieved_ids, relevant_ids, k),
        "mrr": mean_reciprocal_rank([(retrieved_ids, relevant_ids)]),
        "ndcg": ndcg_at_k(retrieved_ids, graded_relevance or {}, k),
    }


def graded_relevance(chunks: tuple[Chunk, ...], relevant_ids: set[str]) -> dict[str, float]:
    return {
        chunk.chunk_id: (1.0 if chunk.chunk_id in relevant_ids else 0.0)
        for chunk in chunks
    }


__all__ = ["evaluate_ranking", "graded_relevance"]
