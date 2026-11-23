"""Opik adapter for traces, datasets, and experiments (best-effort)."""

from .client import OpikCapability, capability, ensure_dataset, flush, log_trace

__all__ = [
    "OpikCapability",
    "capability",
    "ensure_dataset",
    "flush",
    "log_trace",
]
