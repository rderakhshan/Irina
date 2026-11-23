"""
main.py
-------
CLI entry point for the Chapter 2 Exercises ecosystem.

The registry drives everything: new agents register themselves, and this
little CLI discovers them automatically — no wiring changes needed here.

Usage (from inside the Exercises/ folder):
    python main.py list                 # show all registered agents
    python main.py chat basic_chatbot   # chat with an agent interactively
    python main.py run   <pattern> ...  # run a multi-agent pattern (later steps)

    python main.py chat basic_chatbot --no-stream
"""

from __future__ import annotations

import argparse
import importlib
import sys


# ---------------------------------------------------------------------------
# Import-time registration
# ---------------------------------------------------------------------------
# Each module registers its agent(s) on import. Import them all up front so
# `list` and `chat` see the full ecosystem. As new agent files are added they
# only need to be added to this import list (or auto-discovered later).
#
# The folder is called `specialist_agents` (not `agents`) on purpose: the
# OpenAI Agents SDK exposes a top-level package also named `agents`, and a
# local `agents/` folder would shadow it (Chapter 4 ran into this exact trap).
_AGENT_MODULES = [
    "specialist_agents.basic_chatbot",
    "specialist_agents.fundamental_retrieval_agent",
]

_PATTERN_MODULES = [
    # "patterns.episodic_memory",   # step 5
    # "patterns.semantic_memory",   # step 6
    # "patterns.evaluator_optimizer",  # step 8a
    # "patterns.sequential_chain",  # step 8b
]


def _load_agent_modules() -> None:
    import specialist_agents  # noqa: F401  (ensure package importable)
    for mod in _AGENT_MODULES:
        importlib.import_module(mod)

def _load_pattern_modules() -> None:
    for mod in _PATTERN_MODULES:
        importlib.import_module(mod)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="chapter2-exercises",
        description="Chapter 2 Exercises — the growing agent ecosystem.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="List all registered agents and patterns.")
    p_list.set_defaults(func=cmd_list)

    p_chat = sub.add_parser("chat", help="Chat with an agent interactively.")
    p_chat.add_argument("agent", help="Registered agent name, e.g. basic_chatbot")
    p_chat.add_argument("--no-stream", action="store_true", help="Disable streaming output.")
    p_chat.add_argument("--max-turns", type=int, default=10, help="Max agent turns per exchange.")
    p_chat.set_defaults(func=cmd_chat)

    return parser


def cmd_list(args) -> None:
    from core import registry
    _load_agent_modules()
    _load_pattern_modules()
    print("Agents:")
    for name in registry.list_agents():
        print(f"  - {name}")
    print("\nPatterns:")
    pats = registry.list_patterns()
    if pats:
        for name in pats:
            print(f"  - {name}")
    else:
        print("  (none yet — coming in steps 4–8)")


def cmd_chat(args) -> None:
    import asyncio

    from core import registry
    from core.repl import run_repl
    _load_agent_modules()
    agent = registry.get_agent(args.agent)
    asyncio.run(run_repl(agent, stream=not args.no_stream, max_turns=args.max_turns))


def main() -> None:
    # Ensure running from the Exercises directory so relative imports resolve
    # whether invoked as `python main.py` or `python -m`.
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))

    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()