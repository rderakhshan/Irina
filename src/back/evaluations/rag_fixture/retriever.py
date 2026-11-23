"""Disposable, test-only retrieval fixture.

This module exists only to exercise the retrieval evaluation pipeline. It is
not part of Irina's production tool catalog and can be deleted without touching
the harness or providers.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime

from ..worlds.factory import Chunk, World

TOKEN = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> list[str]:
    return TOKEN.findall(text.casefold())


@dataclass(frozen=True, slots=True)
class RetrievalHit:
    chunk_id: str
    document_id: str
    text: str
    score: float


class FixtureRetriever:
    """In-memory BM25-style retriever over synthetic chunks."""

    k1 = 1.5
    b = 0.75

    def __init__(self, world: World) -> None:
        self.world = world
        self._chunks = world.chunks
        self._tokens = {chunk.chunk_id: _tokens(chunk.text) for chunk in self._chunks}
        self._lengths = {chunk_id: len(tokens) for chunk_id, tokens in self._tokens.items()}
        self._avg_length = (
            sum(self._lengths.values()) / len(self._lengths) if self._lengths else 0.0
        )
        self._doc_freq: Counter[str] = Counter()
        for tokens in self._tokens.values():
            for token in set(tokens):
                self._doc_freq[token] += 1
        self._total = len(self._chunks)

    def _idf(self, token: str) -> float:
        freq = self._doc_freq.get(token, 0)
        return math.log(1 + (self._total - freq + 0.5) / (freq + 0.5))

    def _score(self, query_tokens: list[str], chunk: Chunk) -> float:
        tokens = self._tokens[chunk.chunk_id]
        counts = Counter(tokens)
        length = self._lengths[chunk.chunk_id] or 1
        score = 0.0
        for token in query_tokens:
            frequency = counts.get(token, 0)
            if not frequency:
                continue
            numerator = frequency * (self.k1 + 1)
            denominator = frequency + self.k1 * (
                1 - self.b + self.b * length / (self._avg_length or 1)
            )
            score += self._idf(token) * numerator / denominator
        return score

    def search(
        self,
        query: str,
        *,
        as_of: datetime | None = None,
        access_scope: frozenset[str] = frozenset({"analyst"}),
        k: int = 5,
    ) -> list[RetrievalHit]:
        if k <= 0:
            raise ValueError("k must be positive")
        decision_time = as_of or self.world.as_of
        allowed = {
            chunk.chunk_id
            for chunk in self.world.visible_chunks(
                decision_time, access_scope=access_scope
            )
        }
        query_tokens = _tokens(query)
        ranked: list[tuple[float, Chunk]] = []
        for chunk in self._chunks:
            if chunk.chunk_id not in allowed:
                continue
            score = self._score(query_tokens, chunk)
            if score > 0:
                ranked.append((score, chunk))
        ranked.sort(key=lambda item: (-item[0], item[1].chunk_id))
        return [
            RetrievalHit(
                chunk_id=chunk.chunk_id,
                document_id=chunk.document_id,
                text=chunk.text,
                score=round(score, 6),
            )
            for score, chunk in ranked[:k]
        ]


__all__ = ["FixtureRetriever", "RetrievalHit"]
