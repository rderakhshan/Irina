"""L2 execution through Irina's real harness with a scripted model."""

from __future__ import annotations

import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ...harness.loop.runner import RunEvent
from ...harness.orchestration.harness import Harness
from ...harness.providers.base import ProviderResponse, TokenUsage
from ...harness.tools_and_guardrails.security import Policy
from ...harness.tools_and_guardrails.tools import LocalWorkspace


class ScriptedProvider:
    """Returns one fixed answer; exercises the harness without a real model."""

    provider_name = "scripted"
    default_model = "scripted-model"

    def __init__(self, answer: str) -> None:
        self.answer = answer

    def complete(self, model, system, messages, tools) -> ProviderResponse:
        return ProviderResponse(
            text=self.answer,
            tool_calls=[],
            finish_reason="stop",
            usage=TokenUsage(input_tokens=0, output_tokens=0),
        )


@dataclass(slots=True)
class HarnessRun:
    answer: str
    status: str
    turns: int
    tool_calls: int
    events: list[RunEvent] = field(default_factory=list)
    session_path: str | None = None
    integration_level: str = "L2_irina_integrated"


def run_scripted(
    prompt: str,
    answer: str,
    *,
    workdir: str | Path | None = None,
    persist: bool = False,
) -> HarnessRun:
    workspace = Path(workdir) if workdir is not None else Path(tempfile.mkdtemp())
    workspace.mkdir(parents=True, exist_ok=True)
    events: list[RunEvent] = []
    harness = Harness(
        workdir=workspace,
        provider=ScriptedProvider(answer),
        persist=persist,
        workspace_backend=LocalWorkspace(workspace),
        policy=Policy("yolo"),
        on_event=events.append,
        max_turns=1,
        max_seconds=30,
        max_total_tokens=2_000,
    )
    try:
        result = harness.run(prompt)
        return HarnessRun(
            answer=result.text,
            status=result.status.value,
            turns=result.turns,
            tool_calls=result.tool_calls,
            events=events,
            session_path=str(harness.session_path) if harness.session_path else None,
        )
    finally:
        harness.close()


__all__ = ["HarnessRun", "ScriptedProvider", "run_scripted"]
