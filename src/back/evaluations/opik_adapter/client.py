"""Best-effort local Opik integration; every call degrades to blocked."""

from __future__ import annotations

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
        dataset = client.get_or_create_dataset(name=name)
        if items and hasattr(dataset, "insert"):
            dataset.insert(items)
        return name
    except Exception:
        return None


def flush() -> None:
    flush_tracing()


__all__ = ["OpikCapability", "capability", "ensure_dataset", "flush", "log_trace"]
