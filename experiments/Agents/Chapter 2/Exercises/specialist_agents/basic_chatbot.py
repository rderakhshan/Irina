"""
basic_chatbot.py
----------------
Step 1 — the starting point of the ecosystem ladder.

A minimal OpenAI Agents SDK chatbot with:
  - NO tools          (it cannot fetch live data)
  - NO memory         (every turn is stateless)
  - NO output schema

It exists to be the *host* every later step grows capability onto:
   Step 2 adds tools, Step 3 adds working memory, Step 5 adds episodic memory,
   Step 6 adds semantic memory, ... so this file gets richer but the
   run_repl() entry point (core.repl) stays identical.

Run it standalone:
   python -m specialist_agents.basic_chatbot
"""

from __future__ import annotations

from agents import Agent

from core.config import MODEL
from core.registry import register_agent


@register_agent("basic_chatbot")
def build_basic_chatbot() -> Agent:
    return Agent(
        name="Basic Chatbot",
        instructions=(
            "You are a friendly, curious assistant who happens to work in "
            "finance. Answer in plain, conversational language. You have no "
            "tools and no memory: if the user asks for live data, explain "
            "that you cannot fetch it yet, and suggest what you could look "
            "up once tools are attached."
        ),
        model=MODEL,
    )


def main() -> None:
    import asyncio

    from core.repl import run_repl

    asyncio.run(run_repl(build_basic_chatbot()))


if __name__ == "__main__":
    main()