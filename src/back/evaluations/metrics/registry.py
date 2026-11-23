"""Load and validate the metric dictionary."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

FORMULAS = {
    "RATIO",
    "RATE",
    "COUNT",
    "LATENCY",
    "COST",
    "JUDGE",
    "BINARY",
    "LABEL",
    "ACCURACY",
    "PRECISION",
    "RECALL",
    "FNR",
    "F1",
    "P_AT_K",
    "R_AT_K",
    "MRR",
    "NDCG",
    "PAIR",
    "PERCENT_CHANGE",
    "COMP_RATIO",
    "TOKEN_REDUCTION",
    "HASH",
    "BENCH",
}
DEPENDENCIES = {"D", "C", "N", "B"}
MODES = {"OFF", "ON-S", "ON-A", "ON-T"}
REQUIRED = {
    "metric_id",
    "pillar",
    "subpillar",
    "concerns",
    "dataset_dependency",
    "datasets",
    "formula",
    "value_type",
    "unit",
    "bounds",
    "modes",
    "engine",
    "oracle",
    "undefined",
    "severity",
    "owner",
    "status",
}
DEFAULT_PATH = Path(__file__).resolve().parents[1] / "configs" / "metric_dictionary.yaml"


class MetricDictionaryError(ValueError):
    """The metric dictionary is invalid."""


def _mode(value: Any) -> str:
    if value is False:
        return "OFF"
    if value is True:
        return "ON"
    return str(value)


@dataclass(frozen=True, slots=True)
class MetricDefinition:
    metric_id: str
    pillar: str
    subpillar: str
    concerns: tuple[str, ...]
    dataset_dependency: str
    datasets: tuple[str, ...]
    formula: str
    value_type: str
    unit: str
    bounds: tuple[float | None, float | None]
    modes: tuple[str, ...]
    engine: str
    oracle: str
    undefined: str
    severity: str
    owner: str
    status: str

    @classmethod
    def from_mapping(cls, raw: dict[str, Any], index: int) -> "MetricDefinition":
        missing = REQUIRED - set(raw)
        if missing:
            raise MetricDictionaryError(
                f"metric {index} missing fields: {sorted(missing)}"
            )
        formula = str(raw["formula"])
        if formula not in FORMULAS:
            raise MetricDictionaryError(
                f"{raw['metric_id']}: unknown formula {formula!r}"
            )
        dependency = str(raw["dataset_dependency"])
        if dependency not in DEPENDENCIES:
            raise MetricDictionaryError(
                f"{raw['metric_id']}: unknown dataset dependency {dependency!r}"
            )
        modes = tuple(_mode(value) for value in raw["modes"])
        if not modes or any(mode not in MODES for mode in modes):
            raise MetricDictionaryError(
                f"{raw['metric_id']}: invalid modes {modes!r}"
            )
        bounds = raw["bounds"]
        if not isinstance(bounds, list) or len(bounds) != 2:
            raise MetricDictionaryError(
                f"{raw['metric_id']}: bounds must be [min, max]"
            )
        return cls(
            metric_id=str(raw["metric_id"]),
            pillar=str(raw["pillar"]),
            subpillar=str(raw["subpillar"]),
            concerns=tuple(str(value) for value in raw["concerns"]),
            dataset_dependency=dependency,
            datasets=tuple(str(value) for value in raw["datasets"]),
            formula=formula,
            value_type=str(raw["value_type"]),
            unit=str(raw["unit"]),
            bounds=(bounds[0], bounds[1]),
            modes=modes,
            engine=str(raw["engine"]),
            oracle=str(raw["oracle"]),
            undefined=str(raw["undefined"]),
            severity=str(raw["severity"]),
            owner=str(raw["owner"]),
            status=str(raw["status"]),
        )


def load_dictionary(path: str | Path | None = None) -> dict[str, MetricDefinition]:
    source = Path(path) if path is not None else DEFAULT_PATH
    try:
        raw = yaml.safe_load(source.read_text(encoding="utf-8"))
    except OSError as exc:
        raise MetricDictionaryError(f"cannot read {source}: {exc}") from exc
    if not isinstance(raw, dict) or "metrics" not in raw:
        raise MetricDictionaryError("dictionary must contain a 'metrics' list")
    definitions: dict[str, MetricDefinition] = {}
    for index, item in enumerate(raw["metrics"]):
        if not isinstance(item, dict):
            raise MetricDictionaryError(f"metric {index} must be a mapping")
        definition = MetricDefinition.from_mapping(item, index)
        if definition.metric_id in definitions:
            raise MetricDictionaryError(
                f"duplicate metric_id {definition.metric_id!r}"
            )
        definitions[definition.metric_id] = definition
    if not definitions:
        raise MetricDictionaryError("dictionary is empty")
    return definitions


def validate_dictionary(path: str | Path | None = None) -> list[str]:
    definitions = load_dictionary(path)
    problems: list[str] = []
    for metric in definitions.values():
        low, high = metric.bounds
        if low is not None and high is not None and low > high:
            problems.append(f"{metric.metric_id}: lower bound exceeds upper bound")
        if metric.dataset_dependency in {"D", "C", "B"} and not metric.datasets:
            problems.append(f"{metric.metric_id}: labeled metric has no dataset")
    return problems


__all__ = [
    "DEFAULT_PATH",
    "MetricDefinition",
    "MetricDictionaryError",
    "load_dictionary",
    "validate_dictionary",
]
