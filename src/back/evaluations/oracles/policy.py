"""Deterministic policy and approval oracles."""

from __future__ import annotations

from dataclasses import dataclass

from ..worlds.factory import PolicyRule


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    decision: str
    reason: str
    requires_approval: bool
    matched: bool


def decide(
    rules: tuple[PolicyRule, ...],
    *,
    principal: str,
    action: str,
) -> PolicyDecision:
    for rule in rules:
        if rule.principal == principal and rule.action == action:
            return PolicyDecision(
                decision=rule.decision,
                reason=rule.reason,
                requires_approval=rule.requires_approval,
                matched=True,
            )
    return PolicyDecision(
        decision="reject",
        reason="no matching policy rule; fail closed",
        requires_approval=False,
        matched=False,
    )


def decision_accuracy(
    cases: list[tuple[str, str, str]],
    rules: tuple[PolicyRule, ...],
) -> tuple[int, int]:
    correct = 0
    for principal, action, expected in cases:
        if decide(rules, principal=principal, action=action).decision == expected:
            correct += 1
    return correct, len(cases)


def approval_precedes_execution(
    *,
    approval_at,
    execution_at,
    approved_payload_hash: str,
    executed_payload_hash: str,
    revoked: bool = False,
) -> bool:
    if revoked:
        return False
    if approval_at is None or execution_at is None:
        return False
    return (
        approval_at <= execution_at
        and approved_payload_hash == executed_payload_hash
    )


__all__ = [
    "PolicyDecision",
    "approval_precedes_execution",
    "decision_accuracy",
    "decide",
]
