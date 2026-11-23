"""Versioned, vendor-neutral evaluation contracts."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

SCHEMA_VERSION = "1"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class RunRecord:
    run_id: str
    request_id: str
    session_id: str | None = None
    trace_id: str | None = None
    started_at: datetime = field(default_factory=utc_now)
    ended_at: datetime | None = None
    status: str = "running"
    provider: str = ""
    model: str = ""
    routing_mode: str = ""
    prompt_version: str = ""
    tool_schema_version: str = ""
    retrieval_index_version: str = ""
    corpus_version: str = ""
    policy_version: str = ""
    policy_hash: str = ""
    dataset_version: str = ""
    code_commit: str = ""
    environment: str = "offline"
    autonomy_mode: str = "advisory"
    reviewer: str = ""
    schema_version: str = SCHEMA_VERSION

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class GovernanceEvent:
    event_id: str
    run_id: str
    event_type: str
    timestamp: datetime = field(default_factory=utc_now)
    trace_id: str | None = None
    span_id: str | None = None
    actor: str = ""
    action_id: str | None = None
    policy_id: str | None = None
    control_id: str | None = None
    decision: str = ""
    reason: str = ""
    payload_redacted: dict[str, Any] = field(default_factory=dict)
    provenance: str = ""
    schema_version: str = SCHEMA_VERSION

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ToolAction:
    action_id: str
    run_id: str
    tool_name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    purpose: str = ""
    proposed: bool = True
    executed: bool = False
    gate_decision: str = ""
    approval_id: str | None = None
    effect: str = ""
    idempotency_key: str = ""
    error: str | None = None
    schema_version: str = SCHEMA_VERSION

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ApprovalRecord:
    approval_id: str
    run_id: str
    action_id: str
    decision: str
    approved_payload_hash: str = ""
    approver: str = ""
    approver_role: str = ""
    policy_id: str = ""
    decided_at: datetime = field(default_factory=utc_now)
    expires_at: datetime | None = None
    revoked: bool = False
    simulated: bool = False
    execution_linked: bool = False
    schema_version: str = SCHEMA_VERSION

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class EvidenceRecord:
    evidence_id: str
    document_id: str
    chunk_id: str = ""
    source: str = ""
    source_hash: str = ""
    available_at: datetime | None = None
    effective_at: datetime | None = None
    filed_at: datetime | None = None
    ingested_at: datetime | None = None
    classification: str = "internal"
    snapshot_version: str = ""
    claim_ids: list[str] = field(default_factory=list)
    stale: bool = False
    schema_version: str = SCHEMA_VERSION

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class EvaluationResult:
    result_id: str
    check_id: str
    case_id: str
    run_id: str
    engine: str
    metric_name: str
    integration_level: str
    value: Any = None
    undefined_reason: str | None = None
    expected: Any = None
    passed: bool | None = None
    rationale: str = ""
    evaluator_model: str = ""
    rubric_version: str = ""
    dataset_version: str = ""
    oracle_version: str = ""
    evidence_refs: list[str] = field(default_factory=list)
    cost: float | None = None
    latency_ms: float | None = None
    schema_version: str = SCHEMA_VERSION

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class CoverageStatus:
    concern_id: str
    pillar: str
    check_id: str
    applicability: str
    implementation_status: str
    owner: str = ""
    blocker: str = ""
    review_trigger: str = ""
    evidence_refs: list[str] = field(default_factory=list)
    schema_version: str = SCHEMA_VERSION

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


__all__ = [
    "ApprovalRecord",
    "CoverageStatus",
    "EvaluationResult",
    "EvidenceRecord",
    "GovernanceEvent",
    "RunRecord",
    "SCHEMA_VERSION",
    "ToolAction",
    "utc_now",
]
