"""Optional benchmark lane. Never mixed into governance pass/fail."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class BenchmarkSpec:
    name: str
    version: str
    license: str
    cache_dir: str


@dataclass(frozen=True, slots=True)
class BenchmarkStatus:
    name: str
    status: str
    detail: str


BENCHMARKS = (
    BenchmarkSpec("GSM8K", "pinned", "MIT", "benchmarks/gsm8k"),
    BenchmarkSpec("DROP", "pinned", "CC-BY-SA", "benchmarks/drop"),
    BenchmarkSpec("TruthfulQA", "pinned", "Apache-2.0", "benchmarks/truthfulqa"),
    BenchmarkSpec("BIG-Bench Hard", "pinned", "Apache-2.0", "benchmarks/bbh"),
    BenchmarkSpec("MMLU", "pinned", "MIT", "benchmarks/mmlu"),
    BenchmarkSpec("HumanEval", "pinned", "MIT", "benchmarks/humaneval"),
)


def check_benchmarks(root: str | Path = ".") -> list[BenchmarkStatus]:
    base = Path(root)
    statuses = []
    for spec in BENCHMARKS:
        directory = base / spec.cache_dir
        if directory.is_dir() and any(directory.iterdir()):
            statuses.append(
                BenchmarkStatus(spec.name, "available", str(directory))
            )
        else:
            statuses.append(
                BenchmarkStatus(
                    spec.name,
                    "blocked",
                    f"missing local cache: {directory}",
                )
            )
    return statuses


__all__ = ["BENCHMARKS", "BenchmarkSpec", "BenchmarkStatus", "check_benchmarks"]
