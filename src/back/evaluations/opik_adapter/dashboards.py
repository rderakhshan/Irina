"""Code-defined Opik dashboards for Irina governance and runtime behavior.

No Ollie widgets. Only supported widgets:
text_markdown, experiments_feedback_scores, experiment_leaderboard,
project_metrics, project_stats_card.
"""

from __future__ import annotations

import os
from typing import Any

from ...harness.providers.tracing import _get_client

GOVERNANCE_NAME = "Irina Governance"
RUNTIME_NAME = "Irina Runtime"

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

RISK_METRICS = [
    "llm.unsupported_material_claim_rate",
    "llm.contradicted_claim_rate",
    "llm.prompt_injection_success_rate",
    "tools.unauthorized_execution_count",
    "environment.runtime_timeout_error_rate",
    "environment.safe_degradation_correctness",
]

RETRIEVAL_METRICS = [
    "memory.retrieval_precision_at_k",
    "memory.retrieval_recall_at_k",
    "memory.retrieval_mrr",
    "memory.retrieval_ndcg",
    "tools.retrieval_precision_at_k",
    "tools.retrieval_recall_at_k",
    "tools.retrieval_mrr",
    "tools.retrieval_ndcg",
]


def _widget(widget_id: str, title: str, widget_type: str, config: dict[str, Any]) -> dict[str, Any]:
    return {"id": widget_id, "title": title, "type": widget_type, "config": config}


def _layout(widget_id: str, x: int, y: int, w: int, h: int) -> dict[str, Any]:
    return {"i": widget_id, "x": x, "y": y, "w": w, "h": h}


def _feedback_widget(
    widget_id: str,
    title: str,
    scores: list[str],
    chart_type: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    return (
        _widget(
            widget_id,
            title,
            "experiments_feedback_scores",
            {
                "chartType": chart_type,
                "filters": [],
                "groups": [],
                "feedbackScores": scores,
            },
        ),
        _layout(widget_id, 0, 0, 3, 4),
    )


def _markdown(widget_id: str, title: str, content: str) -> tuple[dict[str, Any], dict[str, Any]]:
    return (
        _widget(widget_id, title, "text_markdown", {"content": content}),
        _layout(widget_id, 0, 0, 4, 3),
    )


def _section(section_id: str, title: str, widgets: list[tuple[dict[str, Any], dict[str, Any]]]) -> dict[str, Any]:
    layouts = []
    for index, (_, layout) in enumerate(widgets):
        placed = dict(layout)
        placed["x"] = (index % 2) * 3
        placed["y"] = (index // 2) * 4
        layouts.append(placed)
    return {
        "id": section_id,
        "title": title,
        "widgets": [widget for widget, _ in widgets],
        "layout": layouts,
    }


def _inject_project_id(sections: list[dict[str, Any]], project_id: str) -> None:
    if not project_id:
        return
    for section in sections:
        for widget in section.get("widgets", []):
            if widget.get("type") in {"project_metrics", "project_stats_card"}:
                widget.setdefault("config", {})["projectId"] = project_id


def build_governance_sections() -> list[dict[str, Any]]:
    return [
        _section(
            "section-overview",
            "Overview",
            [
                _markdown(
                    "widget-overview",
                    "Evidence and limits",
                    "## Irina governance\n\n"
                    "- Per-pillar composites, **not a single governance score**.\n"
                    "- Weights are provisional until an owner approves them.\n"
                    "- Gates are logged as `gate.<composite>` scores (1 = triggered).\n"
                    "- Synthetic and fixture-only evidence is not production compliance.\n"
                    "- Use the local report for pooled rates and full limitations.",
                )
            ],
        ),
        _section(
            "section-trends",
            "Trends over experiments (line)",
            [
                _feedback_widget(
                    "widget-trend-composites",
                    "Composite trend",
                    COMPOSITES,
                    "line",
                )
            ],
        ),
        _section(
            "section-llm",
            "LLM",
            [
                _feedback_widget(
                    "widget-llm-bar",
                    "LLM indices (bar)",
                    ["llm.answer_quality_index", "llm.grounding_index", "llm.safety_index"],
                    "bar",
                ),
                _feedback_widget(
                    "widget-llm-radar",
                    "LLM indices (radar)",
                    ["llm.answer_quality_index", "llm.grounding_index", "llm.safety_index"],
                    "radar",
                ),
            ],
        ),
        _section(
            "section-memory",
            "Memory",
            [
                _feedback_widget(
                    "widget-memory-bar",
                    "Memory indices (bar)",
                    ["memory.retrieval_index", "memory.lifecycle_index"],
                    "bar",
                ),
                _feedback_widget(
                    "widget-memory-retrieval",
                    "Memory retrieval components",
                    RETRIEVAL_METRICS[:4],
                    "bar",
                ),
            ],
        ),
        _section(
            "section-tools",
            "Tools",
            [
                _feedback_widget(
                    "widget-tools-bar",
                    "Tool indices (bar)",
                    ["tools.execution_index", "tools.authorization_index"],
                    "bar",
                ),
                _feedback_widget(
                    "widget-tools-risk",
                    "Authorization and injection",
                    [
                        "llm.prompt_injection_success_rate",
                        "tools.unauthorized_execution_count",
                        "tools.approval_compliance_rate",
                    ],
                    "bar",
                ),
            ],
        ),
        _section(
            "section-environment",
            "Environment",
            [
                _feedback_widget(
                    "widget-environment-bar",
                    "Environment indices (bar)",
                    [
                        "environment.ingestion_index",
                        "environment.temporal_index",
                        "environment.resilience_index",
                        "environment.audit_index",
                    ],
                    "bar",
                ),
                _feedback_widget(
                    "widget-environment-radar",
                    "Environment indices (radar)",
                    [
                        "environment.ingestion_index",
                        "environment.temporal_index",
                        "environment.resilience_index",
                        "environment.audit_index",
                    ],
                    "radar",
                ),
            ],
        ),
        _section(
            "section-failure-anatomy",
            "Failure anatomy",
            [
                _feedback_widget(
                    "widget-risk-bar",
                    "Risk indicators (lower is better)",
                    RISK_METRICS,
                    "bar",
                ),
                _feedback_widget(
                    "widget-gates-bar",
                    "Triggered gates",
                    [f"gate.{name}" for name in COMPOSITES],
                    "bar",
                ),
            ],
        ),
        _section(
            "section-retrieval",
            "Retrieval quality",
            [
                _feedback_widget(
                    "widget-retrieval-bar",
                    "Memory vs tools retrieval",
                    RETRIEVAL_METRICS,
                    "bar",
                )
            ],
        ),
        _section(
            "section-calibration",
            "Calibration",
            [
                _feedback_widget(
                    "widget-calibration-bar",
                    "Judge health",
                    [
                        "calibration.judge_health",
                        "calibration.judge_precision",
                        "calibration.judge_recall",
                        "calibration.judge_fnr",
                    ],
                    "bar",
                )
            ],
        ),
        _section(
            "section-leaderboard",
            "Ranking",
            [
                (
                    _widget(
                        "widget-leaderboard",
                        "Experiment leaderboard",
                        "experiment_leaderboard",
                        {
                            "filters": [],
                            "selectedColumns": COMPOSITES
                            + [
                                "llm.prompt_injection_success_rate",
                                "tools.unauthorized_execution_count",
                                "environment.runtime_timeout_error_rate",
                            ],
                            "enableRanking": True,
                            "rankingMetric": "llm.grounding_index",
                            "maxRows": 50,
                        },
                    ),
                    _layout("widget-leaderboard", 0, 0, 4, 6),
                )
            ],
        ),
    ]


def build_runtime_sections(project_id: str = "") -> list[dict[str, Any]]:
    def metric_widget(
        widget_id: str,
        title: str,
        metric_type: str,
        chart_type: str,
        **extra: Any,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        config = {
            "metricType": metric_type,
            "chartType": chart_type,
            "traceFilters": [],
            **extra,
        }
        if project_id:
            config["projectId"] = project_id
        return (
            _widget(widget_id, title, "project_metrics", config),
            _layout(widget_id, 0, 0, 2, 4),
        )

    def stat_widget(
        widget_id: str,
        title: str,
        metric: str,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        config = {
            "source": "traces",
            "projectId": project_id,
            "metric": metric,
            "traceFilters": [],
        }
        return (
            _widget(widget_id, title, "project_stats_card", config),
            _layout(widget_id, 0, 0, 1, 2),
        )

    sections = [
        _section(
            "runtime-overview",
            "Overview",
            [
                _markdown(
                    "runtime-overview-md",
                    "Runtime behavior",
                    "## Irina runtime\n\n"
                    "- Volume, latency, errors, tokens, and cost from real runs.\n"
                    "- Breakdowns by model/provider where available.\n"
                    "- Runtime traces are observability; control evidence stays in the\n"
                    "  local event/session records.",
                )
            ],
        ),
        _section(
            "runtime-cards",
            "Health cards",
            [
                stat_widget("runtime-trace-count", "Traces", "trace_count"),
                stat_widget("runtime-errors", "Errors", "error_count"),
                stat_widget("runtime-p50", "Latency p50", "duration.p50"),
                stat_widget("runtime-p99", "Latency p99", "duration.p99"),
                stat_widget("runtime-cost", "Estimated cost", "total_estimated_cost_sum"),
            ],
        ),
        _section(
            "runtime-volume",
            "Volume, latency, cost",
            [
                metric_widget(
                    "runtime-trace-volume",
                    "Trace volume",
                    "TRACE_COUNT",
                    "bar",
                    breakdown={"field": "name"},
                ),
                metric_widget(
                    "runtime-duration-line",
                    "Trace duration",
                    "DURATION",
                    "line",
                    breakdown={"field": "name"},
                ),
                metric_widget("runtime-cost-line", "Cost trend", "COST", "line"),
                metric_widget(
                    "runtime-token-line",
                    "Token usage",
                    "TOKEN_USAGE",
                    "line",
                ),
                metric_widget(
                    "runtime-error-line",
                    "Error rate",
                    "TRACE_ERROR_RATE",
                    "line",
                ),
            ],
        ),
        _section(
            "runtime-breakdown",
            "Model and provider breakdown",
            [
                metric_widget(
                    "runtime-model-count",
                    "Traces by model",
                    "TRACE_COUNT",
                    "bar",
                    breakdown={"field": "model"},
                ),
                metric_widget(
                    "runtime-model-latency",
                    "Latency by model",
                    "DURATION",
                    "line",
                    breakdown={"field": "model"},
                ),
                metric_widget(
                    "runtime-provider-count",
                    "Traces by provider",
                    "TRACE_COUNT",
                    "bar",
                    breakdown={"field": "provider"},
                ),
            ],
        ),
        _section(
            "runtime-spans",
            "Spans",
            [
                metric_widget("runtime-span-count", "Span volume", "SPAN_COUNT", "bar"),
                metric_widget("runtime-span-duration", "Span duration", "SPAN_DURATION", "line"),
                metric_widget("runtime-span-errors", "Span error rate", "SPAN_ERROR_RATE", "line"),
                metric_widget("runtime-span-tokens", "Span tokens", "SPAN_TOKEN_USAGE", "line"),
            ],
        ),
    ]
    return sections


def _project_id(client: Any, name: str) -> str:
    try:
        result = client.rest_client.projects.find_projects(size=100)
        for project in result.content:
            if project.name == name:
                return str(project.id)
    except Exception:
        pass
    return ""


def _ensure_one(
    client: Any,
    *,
    name: str,
    dashboard_type: str,
    description: str,
    sections: list[dict[str, Any]],
    project_name: str,
    recreate: bool,
) -> Any:
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
            type=dashboard_type,
            description=description,
            project_name=project_name,
            sections=sections,
        )
    except Exception:
        return None


def ensure_dashboards(*, recreate: bool = False) -> list[Any]:
    client = _get_client()
    if client is None:
        return []
    project_name = os.environ.get("OPIK_PROJECT_NAME", "Irina")
    project_id = _project_id(client, project_name)
    results = [
        _ensure_one(
            client,
            name=GOVERNANCE_NAME,
            dashboard_type="experiments",
            description="Irina governance composites, failure anatomy, and ranking.",
            sections=build_governance_sections(),
            project_name=project_name,
            recreate=recreate,
        ),
        _ensure_one(
            client,
            name=RUNTIME_NAME,
            dashboard_type="multi_project",
            description="Irina runtime volume, latency, errors, tokens, cost, and breakdowns.",
            sections=build_runtime_sections(project_id),
            project_name=project_name,
            recreate=recreate,
        ),
    ]
    return [item for item in results if item is not None]


def ensure_dashboard(*, name: str = GOVERNANCE_NAME, project_name: str | None = None, recreate: bool = False) -> Any:
    client = _get_client()
    if client is None:
        return None
    project_name = project_name or os.environ.get("OPIK_PROJECT_NAME", "Irina")
    project_id = _project_id(client, project_name)
    if name == GOVERNANCE_NAME:
        sections = build_governance_sections()
        dashboard_type = "experiments"
    else:
        sections = build_runtime_sections(project_id)
        dashboard_type = "multi_project"
    return _ensure_one(
        client,
        name=name,
        dashboard_type=dashboard_type,
        description="Irina dashboard",
        sections=sections,
        project_name=project_name,
        recreate=recreate,
    )


__all__ = [
    "COMPOSITES",
    "GOVERNANCE_NAME",
    "RUNTIME_NAME",
    "build_governance_sections",
    "build_runtime_sections",
    "ensure_dashboard",
    "ensure_dashboards",
]
