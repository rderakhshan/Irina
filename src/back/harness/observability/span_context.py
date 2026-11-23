"""Context variable holding the active run tracer."""

from __future__ import annotations

from contextvars import ContextVar, Token
from typing import Any

_CURRENT: ContextVar[Any] = ContextVar("irina_run_tracer", default=None)


def current_tracer() -> Any:
    return _CURRENT.get()


def set_current_tracer(tracer: Any) -> Token:
    return _CURRENT.set(tracer)


def reset_current_tracer(token: Token) -> None:
    _CURRENT.reset(token)


__all__ = [
    "current_tracer",
    "reset_current_tracer",
    "set_current_tracer",
]
