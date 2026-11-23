"""Claim-level verification helpers with explicit undefined semantics."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..metrics.metric_value import MetricValue, UndefinedReason

SUPPORT_LABELS = {"supported", "contradicted", "insufficient", "unverified"}


@dataclass(frozen=True, slots=True)
class Claim:
    claim_id: str
    text: str
    citations: tuple[str, ...] = ()
    support: str = "unverified"

    def __post_init__(self) -> None:
        if self.support not in SUPPORT_LABELS:
            raise ValueError(f"unknown support label {self.support!r}")


def _metric(
    metric_id: str,
    numerator: int,
    denominator: int,
) -> MetricValue:
    if denominator == 0:
        return MetricValue(
            metric_id=metric_id,
            value=None,
            value_type="float64",
            undefined_reason=UndefinedReason.EMPTY_DENOMINATOR,
            integration_level="L0_oracle_unit",
        )
    return MetricValue(
        metric_id=metric_id,
        value=numerator / denominator,
        value_type="float64",
        numerator=numerator,
        denominator=denominator,
        integration_level="L0_oracle_unit",
    )


def claim_citation_coverage(claims: list[Claim]) -> MetricValue:
    material = [claim for claim in claims if claim.text.strip()]
    cited = [claim for claim in material if claim.citations]
    return _metric("llm.claim_citation_coverage", len(cited), len(material))


def citation_resolution_rate(
    claims: list[Claim],
    resolvable: set[str],
) -> MetricValue:
    cited_refs = [ref for claim in claims for ref in claim.citations]
    resolved = [ref for ref in cited_refs if ref in resolvable]
    return _metric(
        "llm.citation_resolution_rate", len(resolved), len(cited_refs)
    )


def claim_support_rate(claims: list[Claim]) -> MetricValue:
    material = [claim for claim in claims if claim.text.strip()]
    supported = [claim for claim in material if claim.support == "supported"]
    return _metric("llm.claim_support_rate", len(supported), len(material))


def contradicted_claim_rate(claims: list[Claim]) -> MetricValue:
    material = [claim for claim in claims if claim.text.strip()]
    contradicted = [claim for claim in material if claim.support == "contradicted"]
    return _metric(
        "llm.contradicted_claim_rate", len(contradicted), len(material)
    )


def unsupported_material_claim_rate(
    claims: list[Claim],
    *,
    unverified_is_unsupported: bool = False,
) -> MetricValue:
    material = [claim for claim in claims if claim.text.strip()]
    unsupported_labels = {"contradicted", "insufficient"}
    if unverified_is_unsupported:
        unsupported_labels.add("unverified")
    unsupported = [claim for claim in material if claim.support in unsupported_labels]
    return _metric(
        "llm.unsupported_material_claim_rate", len(unsupported), len(material)
    )


__all__ = [
    "Claim",
    "SUPPORT_LABELS",
    "claim_citation_coverage",
    "claim_support_rate",
    "citation_resolution_rate",
    "contradicted_claim_rate",
    "unsupported_material_claim_rate",
]
