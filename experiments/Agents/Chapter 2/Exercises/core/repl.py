"""
repl.py
-------
The generic interactive-loop host — the "serving counter."

Every conversational agent in the ecosystem is launched through the same
`run_repl()` entry point, so the UX is identical no matter which memory / tool
layers an agent has been grown with. Backed by the Agents SDK's
`run_demo_loop`, which handles the input() -> run -> print cycle for us.

Why this file is separate from the agents: this is the *machine that runs any
conversation*. The agent modules (specialist_agents/*.py) only describe one
specific agent's identity. The two are written once here and reused by every
future agent instead of duplicating the loop.

One limitation of the plain loop: it does not surface tool calls or memory
state. Agents that want to *show* what is happening (e.g. the ReAct trace, or
the working-memory printout) should use `run_demo_loop(..., stream=True)` or
call `run_repl` with a custom per-run hook instead.
"""

from __future__ import annotations

from agents import Agent
from agents.repl import run_demo_loop

from core.config import MODEL


async def run_repl(
    agent: Agent,
    *,
    stream: bool = True,
    max_turns: int | None = 10,
) -> None:
    """
    Run an interactive REPL around `agent`.

    Type 'exit' or Ctrl-C to leave. Any registered ecosystem agent can be
    dropped in here interchangeably.
    """
    await run_demo_loop(
        agent,
        stream=stream,
        max_turns=max_turns,
    )


def make_default_agent() -> Agent:
    """Fallback agent used when the CLI has nothing registered yet."""
    from agents import Agent as _Agent

    return _Agent(name="empty", instructions="You exist.", model=MODEL)