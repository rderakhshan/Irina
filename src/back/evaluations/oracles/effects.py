"""Side-effect ledger for synthetic tool execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True, slots=True)
class Effect:
    action_id: str
    tool_name: str
    executed: bool
    allowed: bool
    payload_hash: str = ""
    external: bool = True
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class EffectLedger:
    """Records synthetic effects; never reaches a real financial system."""

    def __init__(self) -> None:
        self._effects: list[Effect] = []

    def record(self, effect: Effect) -> None:
        self._effects.append(effect)

    def all(self) -> tuple[Effect, ...]:
        return tuple(self._effects)

    def unauthorized(self) -> tuple[Effect, ...]:
        return tuple(
            effect
            for effect in self._effects
            if effect.executed and not effect.allowed
        )

    def forbidden(self, forbidden_tools: set[str]) -> tuple[Effect, ...]:
        return tuple(
            effect
            for effect in self._effects
            if effect.executed and effect.tool_name in forbidden_tools
        )

    def external_effects(self) -> tuple[Effect, ...]:
        return tuple(
            effect
            for effect in self._effects
            if effect.executed and effect.external
        )


__all__ = ["Effect", "EffectLedger"]
