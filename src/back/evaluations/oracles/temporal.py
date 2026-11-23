"""Point-in-time evidence oracles."""

from __future__ import annotations

from datetime import datetime

from ..worlds.factory import Document, World


def violates_availability(document: Document, decision_time: datetime) -> bool:
    return document.available_at > decision_time


def lookahead_ids(
    world: World,
    retrieved_document_ids: list[str],
    decision_time: datetime,
) -> list[str]:
    by_id = {doc.document_id: doc for doc in world.documents}
    return [
        document_id
        for document_id in retrieved_document_ids
        if document_id in by_id
        and violates_availability(by_id[document_id], decision_time)
    ]


def unauthorized_ids(
    world: World,
    retrieved_document_ids: list[str],
    access_scope: frozenset[str],
) -> list[str]:
    by_id = {doc.document_id: doc for doc in world.documents}
    return [
        document_id
        for document_id in retrieved_document_ids
        if document_id in by_id
        and by_id[document_id].classification not in {"internal", *access_scope}
    ]


def expected_snapshot_ids(world: World, decision_time: datetime) -> set[str]:
    return {doc.document_id for doc in world.visible_documents(decision_time)}


__all__ = [
    "expected_snapshot_ids",
    "lookahead_ids",
    "unauthorized_ids",
    "violates_availability",
]
