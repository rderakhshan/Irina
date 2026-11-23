"""Opik adapter for traces, datasets, experiments, and feedback."""

from .client import (
    OpikCapability,
    capability,
    create_experiment,
    dataset_items,
    ensure_dataset,
    flush,
    link_experiment_items,
    log_feedback_scores,
    log_trace,
)

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
