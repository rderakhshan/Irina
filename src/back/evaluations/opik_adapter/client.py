"""Best-effort local Opik integration; every call degrades to blocked."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from ...harness.providers.tracing import _get_client, flush_tracing


@dataclass(slots=True)
class OpikCapability:
    available: bool
    detail: str = ""


def capability() -> OpikCapability:
    client = _get_client()
    return OpikCapability(
        available=client is not None,
        detail="local Opik client" if client else "Opik unavailable",
    )


def log_trace(
    name: str,
    *,
    input: dict[str, Any],
    output: dict[str, Any],
    metadata: dict[str, Any] | None = None,
) -> str | None:
    """Write one complete trace.

    The payload is supplied at creation and ``end()`` is deliberately not
    called: with batching enabled an immediate end/update can race the create
    message and leave an empty placeholder trace.
    """
    client = _get_client()
    if client is None:
        return None
    now = datetime.now(timezone.utc)
    try:
        trace = client.trace(
            name=name,
            input=input,
            output=output,
            metadata=metadata or {},
            start_time=now,
            end_time=now,
        )
        return str(getattr(trace, "id", "")) or None
    except Exception:
        return None


def ensure_dataset(name: str, items: list[dict[str, Any]]) -> str | None:
    client = _get_client()
    if client is None:
        return None
    try:
        dataset = client.get_or_create_dataset(
            name=name, project_name=os.environ.get("OPIK_PROJECT_NAME", "Irina")
        )
        if items and hasattr(dataset, "insert"):
            dataset.insert(items)
        return name
    except Exception:
        return None


def dataset_items(name: str) -> dict[str, str]:
    """Return case_id -> dataset item id for an existing dataset."""
    client = _get_client()
    if client is None:
        return {}
    try:
        dataset = client.get_dataset(
            name=name, project_name=os.environ.get("OPIK_PROJECT_NAME", "Irina")
        )
        mapping: dict[str, str] = {}
        for item in dataset.get_items():
            case_id = str(item.get("case_id", ""))
            item_id = str(item.get("id", ""))
            if case_id and item_id:
                mapping[case_id] = item_id
        return mapping
    except Exception:
        return {}


def create_experiment(
    *,
    name: str,
    dataset_name: str,
    config: dict[str, Any] | None = None,
) -> Any:
    client = _get_client()
    if client is None:
        return None
    try:
        return client.create_experiment(
            dataset_name=dataset_name,
            name=name,
            experiment_config=config or {},
            tags=["irina", "governance-eval"],
            project_name=os.environ.get("OPIK_PROJECT_NAME", "Irina"),
        )
    except Exception:
        return None


def link_experiment_items(experiment: Any, references: list[tuple[str, str]]) -> int:
    """Link (dataset_item_id, trace_id) pairs to an experiment."""
    if experiment is None or not references:
        return 0
    try:
        from opik.api_objects.experiment.experiment_item import (
            ExperimentItemReferences,
        )

        experiment.insert(
            [
                ExperimentItemReferences(
                    dataset_item_id=item_id,
                    trace_id=trace_id,
                    project_name=os.environ.get("OPIK_PROJECT_NAME", "Irina"),
                )
                for item_id, trace_id in references
                if item_id and trace_id
            ]
        )
        return len(references)
    except Exception:
        return 0


def log_feedback_scores(
    trace_id: str,
    scores: list[dict[str, Any]],
) -> int:
    client = _get_client()
    if client is None or not trace_id or not scores:
        return 0
    try:
        client.log_traces_feedback_scores(
            scores=[
                {
                    "id": trace_id,
                    "name": str(score["name"]),
                    "value": float(score["value"]),
                    **(
                        {"reason": str(score["reason"])}
                        if score.get("reason")
                        else {}
                    ),
                }
                for score in scores
            ],
            project_name=os.environ.get("OPIK_PROJECT_NAME", "Irina"),
        )
        return len(scores)
    except Exception:
        return 0


def flush() -> None:
    flush_tracing()


__all__ = [
    "OpikCapability",
    "capability",
    "create_experiment",
    "dataset_items",
    "ensure_dataset",
    "flush",
    "link_experiment_items",
    "log_feedback_scores",
    "log_trace",
]
