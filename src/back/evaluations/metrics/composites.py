"""Weighted composite indices over atomic metrics."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .metric_value import MetricValue, UndefinedReason

DEFAULT_PATH = (
    Path(__file__).resolve().parents[1] / "configs" / "composite_metrics.yaml"
)


@dataclass(frozen=True, slots=True)
class Component:
    metric: str
    weight: float = 1.0
    invert: bool = False
    kind: str = "rate"
    clamp: bool = False


@dataclass(frozen=True, slots=True)
class Gate:
    metric: str
    op: str
    threshold: Any


@dataclass(frozen=True, slots=True)
class CompositeDefinition:
    id: str
    pillar: str
    concerns: tuple[str, ...]
    components: tuple[Component, ...]
    min_coverage: float
    gate: Gate | None


@dataclass(slots=True)
class CompositeResult:
    id: str
    value: float | None
    coverage: float
    defined_components: int
    total_components: int
    missing: list[str] = field(default_factory=list)
    gate_triggered: bool = False
    gate_detail: str = ""
    definition: CompositeDefinition | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "value": self.value,
            "coverage": self.coverage,
            "defined_components": self.defined_components,
            "total_components": self.total_components,
            "missing": self.missing,
            "gate_triggered": self.gate_triggered,
            "gate_detail": self.gate_detail,
        }


def load_composites(path: str | Path | None = None) -> list[CompositeDefinition]:
    source = Path(path) if path is not None else DEFAULT_PATH
    raw = yaml.safe_load(source.read_text(encoding="utf-8"))
    definitions = []
    for item in raw.get("composites", []):
        components = tuple(
            Component(
                metric=str(component["metric"]),
                weight=float(component.get("weight", 1.0)),
                invert=bool(component.get("invert", False)),
                kind=str(component.get("kind", "rate")),
                clamp=bool(component.get("clamp", False)),
            )
            for component in item.get("components", [])
        )
        gate_raw = item.get("gate")
        gate = (
            Gate(
                metric=str(gate_raw["metric"]),
                op=str(gate_raw["op"]),
                threshold=gate_raw.get("threshold"),
            )
            if gate_raw
            else None
        )
        definitions.append(
            CompositeDefinition(
                id=str(item["id"]),
                pillar=str(item["pillar"]),
                concerns=tuple(str(value) for value in item.get("concerns", [])),
                components=components,
                min_coverage=float(item.get("min_coverage", 0.8)),
                gate=gate,
            )
        )
    return definitions


def _normalise(metric: MetricValue, component: Component) -> float | None:
    if not metric.defined or metric.value is None:
        return None
    if component.kind == "bool":
        score = 1.0 if bool(metric.value) else 0.0
    elif component.kind == "zero_count":
        score = 1.0 if float(metric.value) == 0 else 0.0
    else:
        score = float(metric.value)
    if component.invert:
        score = 1.0 - score
    if component.clamp:
        score = min(1.0, max(0.0, score))
    return score


def _gate_triggered(gate: Gate | None, metrics: dict[str, MetricValue]) -> tuple[bool, str]:
    if gate is None:
        return False, ""
    metric = metrics.get(gate.metric)
    if metric is None or not metric.defined:
        return False, f"gate metric {gate.metric} undefined"
    value = metric.value
    if gate.op == ">":
        triggered = value > gate.threshold
    elif gate.op == ">=":
        triggered = value >= gate.threshold
    elif gate.op == "<":
        triggered = value < gate.threshold
    elif gate.op == "<=":
        triggered = value <= gate.threshold
    elif gate.op == "==":
        triggered = value == gate.threshold
    else:
        triggered = False
    return triggered, f"{gate.metric} {gate.op} {gate.threshold} (observed {value})"


def compute_composites(
    metrics: dict[str, MetricValue],
    definitions: list[CompositeDefinition] | None = None,
) -> list[CompositeResult]:
    results: list[CompositeResult] = []
    for definition in definitions or load_composites():
        total_weight = sum(component.weight for component in definition.components)
        weighted = 0.0
        defined_weight = 0.0
        missing: list[str] = []
        for component in definition.components:
            metric = metrics.get(component.metric)
            score = _normalise(metric, component) if metric is not None else None
            if score is None:
                missing.append(component.metric)
                continue
            weighted += score * component.weight
            defined_weight += component.weight
        coverage = defined_weight / total_weight if total_weight else 0.0
        value = weighted / defined_weight if defined_weight else None
        gate_triggered, gate_detail = _gate_triggered(definition.gate, metrics)
        results.append(
            CompositeResult(
                id=definition.id,
                value=value if coverage >= definition.min_coverage else None,
                coverage=coverage,
                defined_components=len(definition.components) - len(missing),
                total_components=len(definition.components),
                missing=missing,
                gate_triggered=gate_triggered,
                gate_detail=gate_detail,
                definition=definition,
            )
        )
    return results


__all__ = [
    "Component",
    "CompositeDefinition",
    "CompositeResult",
    "DEFAULT_PATH",
    "Gate",
    "compute_composites",
    "load_composites",
]
