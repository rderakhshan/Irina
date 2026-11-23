"""Memory retrieval and state-transition oracles."""

from __future__ import annotations

from datetime import datetime
from typing import Iterable

from ..worlds.factory import MemoryItem


def relevant_memory_ids(
    memories: Iterable[MemoryItem],
    *,
    as_of: datetime,
    query_terms: set[str],
) -> list[str]:
    matches: list[str] = []
    for item in memories:
        if item.valid_from > as_of:
            continue
        if item.valid_to is not None and item.valid_to <= as_of:
            continue
        text = item.text.casefold()
        if any(term.casefold() in text for term in query_terms):
            matches.append(item.memory_id)
    return matches


def apply_transitions(
    state: dict[str, str],
    transitions: list[dict[str, str]],
) -> dict[str, str]:
    updated = dict(state)
    for transition in transitions:
        operation = transition["op"]
        memory_id = transition["memory_id"]
        if operation == "write":
            updated[memory_id] = transition["text"]
        elif operation == "delete":
            updated.pop(memory_id, None)
        elif operation == "update":
            if memory_id not in updated:
                raise KeyError(f"cannot update missing memory {memory_id}")
            updated[memory_id] = transition["text"]
        else:
            raise ValueError(f"unknown transition {operation!r}")
    return updated


def preservation_recall(
    required_facts: Iterable[str],
    preserved_facts: Iterable[str],
) -> float | None:
    required = set(required_facts)
    if not required:
        return None
    preserved = set(preserved_facts)
    return len(required & preserved) / len(required)


__all__ = ["apply_transitions", "preservation_recall", "relevant_memory_ids"]
