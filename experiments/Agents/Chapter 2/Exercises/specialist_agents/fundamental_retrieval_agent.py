"""
fundamental_retrieval_agent.py
------------------------------
Step 2 (Lab 1): the tool-use pattern.

One agent with exactly one tool. The book's point: the LLM is asked a
question about a company's fundamentals and answers it by *calling the tool*
for live numbers instead of relying on its frozen training knowledge.

The `CURRENT_YEAR` in the instructions is deliberate. Lab 1 shows the
knowledge-cutoff trap: asked for the "most recent fiscal year", gpt-4o-mini
reports the year from its training cutoff (2023) unless told the current year.
We bake the current year in so the agent always asks the tool for the right
period.
"""

from __future__ import annotations

from agents import Agent

from core.config import CURRENT_YEAR, MODEL
from core.registry import register_agent
from tools.fundamentals import get_company_fundamentals


@register_agent("fundamental_retrieval_agent")
def build_fundamental_retrieval_agent() -> Agent:
    return Agent(
        name="Fundamental Retrieval Agent",
        model=MODEL,
        instructions=f"""
You are a Fundamental Retrieval Agent.

Tasks:
1) Call the fundamentals tool for the specified ticker.
2) Output the desired set of ratios.

Important: the current year is {CURRENT_YEAR}. When asked for the "most
recent fiscal year", use the latest year present in the tool's output.
""",
        tools=[get_company_fundamentals],
    )