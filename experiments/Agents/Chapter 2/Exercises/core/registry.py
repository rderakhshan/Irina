"""
registry.py
-----------
The ecosystem index.

Every agent in the Exercises package registers itself here under a short
namespaced key (e.g. "basic_chatbot"). The CLI, `main.py`, discovers what is
available by asking the registry, so adding a new agent to the ecosystem is
*only* two things:

    1. write an agent module under agents/ (or a pattern under patterns/)
    2. decorate its builder with @register(...)

No other file needs to change.
"""

from __future__ import annotations

from typing import Callable

from agents import Agent

# name -> constructor that returns a configured Agent
_AGENTS: dict[str, Callable[[], Agent]] = {}

# name -> constructor for a multi-agent pattern that returns a string result
_PATTERNS: dict[str, Callable[..., object]] = {}


def register_agent(name: str) -> Callable[[Callable[[], Agent]], Callable[[], Agent]]:
    """Decorator: mark a zero-arg builder as an ecosystem agent."""

    def decorator(builder: Callable[[], Agent]) -> Callable[[], Agent]:
        if name in _AGENTS:
            raise ValueError(f"Duplicate agent registration: {name!r}")
        _AGENTS[name] = builder
        return builder

    return decorator


def register_pattern(name: str):
    """Decorator: mark a pattern builder (takes args, returns a result)."""

    def decorator(builder):
        if name in _PATTERNS:
            raise ValueError(f"Duplicate pattern registration: {name!r}")
        _PATTERNS[name] = builder
        return builder

    return decorator


def get_agent(name: str) -> Agent:
    """Construct the agent registered under `name`."""
    if name not in _AGENTS:
        available = ", ".join(sorted(_AGENTS))
        raise KeyError(f"Unknown agent {name!r}. Registered: {available or '(none)'}")
    return _AGENTS[name]()


def list_agents() -> list[str]:
    return sorted(_AGENTS)


def list_patterns() -> list[str]:
    return sorted(_PATTERNS)


def build_pattern(name: str, *args, **kwargs):
    if name not in _PATTERNS:
        available = ", ".join(sorted(_PATTERNS))
        raise KeyError(f"Unknown pattern {name!r}. Registered: {available or '(none)'}")
    return _PATTERNS[name](*args, **kwargs)