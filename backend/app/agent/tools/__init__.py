"""Tool registry exposed to the agent orchestrator.

Each tool exposes a JSON-schema-style spec (compatible with Anthropic and OpenAI tool calling)
plus a `run` callable. The orchestrator picks tools by name and forwards the arguments.
"""
from app.agent.tools.policy_retriever import policy_retriever_tool
from app.agent.tools.medicines_checker import medicines_checker_tool
from app.agent.tools.facility_checker import facility_checker_tool


TOOL_REGISTRY = {
    policy_retriever_tool.name: policy_retriever_tool,
    medicines_checker_tool.name: medicines_checker_tool,
    facility_checker_tool.name: facility_checker_tool,
}


def get_tool_specs() -> list[dict]:
    return [t.spec for t in TOOL_REGISTRY.values()]


def run_tool(name: str, arguments: dict) -> dict:
    if name not in TOOL_REGISTRY:
        return {"error": f"Unknown tool: {name}"}
    tool = TOOL_REGISTRY[name]
    return tool.run(arguments)


__all__ = [
    "TOOL_REGISTRY",
    "get_tool_specs",
    "run_tool",
    "policy_retriever_tool",
    "medicines_checker_tool",
    "facility_checker_tool",
]
