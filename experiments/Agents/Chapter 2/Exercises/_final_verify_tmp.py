import sys, asyncio, os
BASE = r"D:\AI Engineering LAB\Financial-AI-Agents\Building-AI-Agents-for-Finance-main\Chapter 2\Exercises"
sys.path.insert(0, BASE)
os.chdir(BASE)

from agents import Runner
from core.registry import get_agent

agent = get_agent("fundamental_retrieval_agent")
print("REGISTERED AGENT:", agent.name)
print("TOOLS:", [(t.name, type(t).__name__) for t in agent.tools])

async def main():
    result = await Runner.run(agent, "Get the current liquidity ratios (current ratio, quick ratio, cash ratio) for MSFT for fiscal year 2026. Return the actual numbers to me directly.")
    print("\n=== FINAL OUTPUT ===")
    print(result.final_output)

    for item in result.raw_responses[-1].output:
        if item.type == "function_call":
            print("\nCALL:", item.name)
        elif item.type == "function_call_output":
            print("OUTPUT (first 600 chars):")
            print(item.output[:1600])

asyncio.run(main())
