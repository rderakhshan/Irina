import asyncio, sys
sys.path.insert(0, r"D:\AI Engineering LAB\Financial-AI-Agents\Building-AI-Agents-for-Finance-main\Chapter 2\Exercises")
from specialist_agents import fundamental_retrieval_agent
from core.registry import get_agent
agent = get_agent("fundamental_retrieval_agent")
print("NAME:", agent.name)
print("TOOL:", [t.name for t in agent.tools])
