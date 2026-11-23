"""Push dataset cases as Opik Test Suites and optionally run them."""

from __future__ import annotations

import os
from typing import Any

from ...harness.providers.tracing import _load_opik, _get_client


def ensure_suite(
    *,
    name: str,
    description: str,
    assertions: list[str],
    cases: list[dict[str, Any]],
) -> Any:
    client = _get_client()
    module = _load_opik()
    if client is None or module is None:
        return None
    try:
        suite = client.get_or_create_test_suite(
            name=name,
            description=description,
            global_assertions=assertions,
            tags=["irina", "governance-eval"],
            project_name=os.environ.get("OPIK_PROJECT_NAME", "Irina"),
        )
        items = [
            {
                "data": {
                    "case_id": case["case_id"],
                    "inputs": case["inputs"],
                    "expected": case["expected"],
                    "expected_behavior": case["expected_behavior"],
                    "severity": case["severity"],
                },
                "assertions": [case["expected_behavior"]],
                "description": case["expected_behavior"],
            }
            for case in cases
        ]
        if items:
            suite.insert(items)
        return suite
    except Exception:
        return None


def run_suite(suite: Any, task: Any, *, experiment_name: str) -> Any:
    module = _load_opik()
    if suite is None or module is None:
        return None
    try:
        return module.run_tests(
            test_suite=suite,
            task=task,
            experiment_name=experiment_name,
            experiment_config={"suite": suite.name},
        )
    except Exception:
        return None


__all__ = ["ensure_suite", "run_suite"]
