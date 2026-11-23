"""Code-defined Opik dashboards for Irina governance metrics.

No Ollie charts are used. Only supported widgets:
text_markdown, experiments_feedback_scores, experiment_leaderboard.
"""

from __future__ import annotations

import os
from typing import Any

from ...harness.providers.tracing import _get_client

DASHBOARD_NAME = "Irina Governance"
COMPOSITES = [
    "llm.answer_quality_index",
    "llm.grounding_index",
    "llm.safety_index",
    "memory.retrieval_index",
    "memory.lifecycle_index",
    "tools.execution_index",
    "tools.authorization_index",
    "environment.ingestion_index",
    "environment.temporal_index",
    "environment.resilience_index",
    "environment.audit_index",
    "calibration.judge_health",
]


def _widget(widget_id: str, title: str, widget_type: str, config: dict[str, Any]) -> dict[str, Any]:
    return {"id": widget_id, "title": title, "type": widget_type, "config": config}


def _layout(widget_id: str, x: int, y: int, w: int, h: int) -> dict[str, Any]:
    return {"i": widget_id, "x": x, "y": y, "w": w, "h": h}


def _chart(
    widget_id: str,
    title: str,
    scores: list[str],
    chart_type: str = "radar",
) -> tuple[dict[str, Any], dict[str, Any]]:
    widget = _widget(
        widget_id,
        title,
        "experiments_feedback_scores",
        {
            "chartType": chart_type,
            "filters": [],
            "groups": [],
            "feedbackScores": scores,
        },
    )
    return widget, _layout(widget_id, 0, 0, 2, 4)


def build_sections() -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    overview_id = "section-overview"
    overview_widget = _widget(
        "widget-overview",
        "Evidence and limits",
        "text_markdown",
        {
            "content": (
                "## Irina governance evidence\n\n"
                "- Composites are per-pillar indices, **not a single governance score**.\n"
                "- Weights are provisional until a governance owner approves them.\n"
                "- Critical gate failures are shown in trace metadata and the local report.\n"
                "- Synthetic and fixture-only results are not production compliance evidence.\n"
                "- Use the local JSON/Markdown report for pooled rates and full limitations."
            )
        },
    )
    sections.append(
        {
            "id": overview_id,
            "title": "Overview",
            "widgets": [overview_widget],
            "layout": [_layout("widget-overview", 0, 0, 4, 3)],
        }
    )

    groups = [
        ("LLM", "section-llm", ["llm.answer_quality_index", "llm.grounding_index", "llm.safety_index"]),
        ("Memory", "section-memory", ["memory.retrieval_index", "memory.lifecycle_index"]),
        ("Tools", "section-tools", ["tools.execution_index", "tools.authorization_index"]),
        (
            "Environment",
            "section-environment",
            [
                "environment.ingestion_index",
                "environment.temporal_index",
                "environment.resilience_index",
                "environment.audit_index",
            ],
        ),
        ("Calibration", "section-calibration", ["calibration.judge_health"]),
    ]
    for title, section_id, scores in groups:
        widget_id = f"widget-{section_id}"
        widget, layout = _chart(widget_id, f"{title} indices", scores)
        sections.append(
            {
                "id": section_id,
                "title": title,
                "widgets": [widget],
                "layout": [layout],
            }
        )

    leaderboard = _widget(
        "widget-leaderboard",
        "Experiment leaderboard",
        "experiment_leaderboard",
        {
            "filters": [],
            "selectedColumns": [
                "llm.grounding_index",
                "llm.answer_quality_index",
                "memory.retrieval_index",
                "tools.authorization_index",
                "environment.resilience_index",
            ],
            "enableRanking": True,
            "rankingMetric": "llm.grounding_index",
            "maxRows": 20,
        },
    )
    sections.append(
        {
            "id": "section-leaderboard",
            "title": "Ranking",
            "widgets": [leaderboard],
            "layout": [_layout("widget-leaderboard", 0, 0, 4, 4)],
        }
    )
    return sections


def ensure_dashboard(
    *,
    name: str = DASHBOARD_NAME,
    project_name: str | None = None,
    recreate: bool = False,
) -> Any:
    client = _get_client()
    if client is None:
        return None
    project = project_name or os.environ.get("OPIK_PROJECT_NAME", "Irina")
    try:
        existing = client.get_dashboards(name=name, max_results=10)
    except Exception:
        existing = []
    if existing and not recreate:
        return existing[0]
    if existing and recreate:
        try:
            client.delete_dashboard(existing[0].id)
        except Exception:
            pass
    try:
        return client.create_dashboard(
            name=name,
            type="experiments",
            description=(
                "Irina governance composites and experiment ranking. "
                "No Ollie widgets."
            ),
            project_name=project,
            sections=build_sections(),
        )
    except Exception:
        return None


__all__ = ["COMPOSITES", "DASHBOARD_NAME", "build_sections", "ensure_dashboard"]
