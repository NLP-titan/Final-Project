"""ReAct-style orchestrator with multi-turn history, retries, and a heuristic fallback.

Two execution paths:
  - LLM path (Anthropic or OpenAI). The LLM picks tools via native tool-calling, the
    orchestrator runs them, feeds the results back, and iterates until the model produces a
    final natural-language answer.
  - Heuristic fallback (no API key configured, or LLM failure). A keyword router calls the
    most appropriate tool and renders a deterministic answer.

Multi-turn:
  - `history` is a list of `{"role": "user"|"assistant", "content": str}` from earlier turns.
  - The LLM path replays history before the current question; the heuristic path uses only the
    current question (history doesn't help keyword routing).

Retries:
  - LLM API calls are wrapped with exponential backoff.
  - Tool execution failures are surfaced back to the model so it can recover within the same
    turn (no retry needed at the orchestrator level).
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Sequence

from app.agent.prompts import SYSTEM_PROMPT
from app.agent.tools import TOOL_REGISTRY, get_tool_specs, run_tool
from app.config import settings
from app.utils.retry import retry_call


log = logging.getLogger(__name__)
MAX_TOOL_ITERATIONS = settings.agent_max_tool_iterations
MAX_HISTORY_TURNS = settings.agent_max_history_turns  # cap to keep prompts bounded


@dataclass
class AgentResponse:
    answer: str
    tool_calls: list[dict] = field(default_factory=list)
    provider: str = "heuristic"
    fallback_reason: str | None = None

    def to_dict(self) -> dict:
        return {
            "answer": self.answer,
            "tool_calls": self.tool_calls,
            "provider": self.provider,
            "fallback_reason": self.fallback_reason,
        }


def answer(question: str, history: Sequence[dict] | None = None) -> AgentResponse:
    question = (question or "").strip()
    if not question:
        return AgentResponse(answer="Please ask a question about NHIS.")

    history = list(history or [])[-MAX_HISTORY_TURNS * 2 :]

    provider = settings.llm_provider.lower()
    if provider == "anthropic" and settings.anthropic_api_key:
        try:
            return _run_anthropic(question, history)
        except Exception as exc:
            log.exception("Anthropic agent failed; falling back to heuristic")
            return _heuristic(question, fallback_reason=f"anthropic_error: {exc}")
    if provider == "openai" and settings.openai_api_key:
        try:
            return _run_openai(question, history)
        except Exception as exc:
            log.exception("OpenAI agent failed; falling back to heuristic")
            return _heuristic(question, fallback_reason=f"openai_error: {exc}")
    return _heuristic(question)


# ---------------------------------------------------------------------------
# Anthropic path
# ---------------------------------------------------------------------------
def _run_anthropic(question: str, history: list[dict]) -> AgentResponse:
    from anthropic import Anthropic

    client = Anthropic(api_key=settings.anthropic_api_key)
    messages: list[dict] = [
        {"role": h["role"], "content": h["content"]}
        for h in history
        if h.get("role") in {"user", "assistant"} and h.get("content")
    ]
    messages.append({"role": "user", "content": question})

    tool_calls: list[dict] = []

    for _ in range(MAX_TOOL_ITERATIONS):
        resp = retry_call(
            lambda: client.messages.create(
                model=settings.anthropic_model,
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                tools=get_tool_specs(),
                messages=messages,
            ),
            attempts=3,
            description="anthropic.messages.create",
        )

        if resp.stop_reason == "tool_use":
            assistant_blocks = [b.model_dump() for b in resp.content]
            messages.append({"role": "assistant", "content": assistant_blocks})

            tool_results = []
            for block in resp.content:
                if block.type == "tool_use":
                    tool_input = dict(block.input or {})
                    output = run_tool(block.name, tool_input)
                    tool_calls.append(
                        {"name": block.name, "input": tool_input, "output": output}
                    )
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(output)[:8000],
                        }
                    )
            messages.append({"role": "user", "content": tool_results})
            continue

        text_parts = [b.text for b in resp.content if getattr(b, "type", None) == "text"]
        return AgentResponse(
            answer="\n".join(text_parts).strip() or "(no answer)",
            tool_calls=tool_calls,
            provider="anthropic",
        )

    return AgentResponse(
        answer="The agent could not converge on an answer within the iteration budget.",
        tool_calls=tool_calls,
        provider="anthropic",
    )


# ---------------------------------------------------------------------------
# OpenAI path
# ---------------------------------------------------------------------------
def _openai_tool_specs() -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": spec["name"],
                "description": spec["description"],
                "parameters": spec["input_schema"],
            },
        }
        for spec in get_tool_specs()
    ]


def _run_openai(question: str, history: list[dict]) -> AgentResponse:
    from openai import OpenAI

    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=settings.openai_api_key)
    messages: list[dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    for h in history:
        if h.get("role") in {"user", "assistant"} and h.get("content"):
            messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": question})

    tool_calls_log: list[dict] = []

    for _ in range(MAX_TOOL_ITERATIONS):
        resp = retry_call(
            lambda: client.chat.completions.create(
                model=settings.openai_model,
                messages=messages,
                tools=_openai_tool_specs(),
            ),
            attempts=3,
            description="openai.chat.completions.create",
        )
        msg = resp.choices[0].message
        if msg.tool_calls:
            messages.append(
                {
                    "role": "assistant",
                    "content": msg.content or "",
                    "tool_calls": [tc.model_dump() for tc in msg.tool_calls],
                }
            )
            for tc in msg.tool_calls:
                args = json.loads(tc.function.arguments or "{}")
                output = run_tool(tc.function.name, args)
                tool_calls_log.append(
                    {"name": tc.function.name, "input": args, "output": output}
                )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "name": tc.function.name,
                        "content": json.dumps(output)[:8000],
                    }
                )
            continue
        return AgentResponse(
            answer=(msg.content or "").strip() or "(no answer)",
            tool_calls=tool_calls_log,
            provider="openai",
        )

    return AgentResponse(
        answer="The agent could not converge on an answer within the iteration budget.",
        tool_calls=tool_calls_log,
        provider="openai",
    )


# ---------------------------------------------------------------------------
# Heuristic fallback (no LLM)
# ---------------------------------------------------------------------------
MEDICINE_HINTS = (
    "medicine",
    "medication",
    "drug",
    "tablet",
    "capsule",
    "injection",
    "prescription",
    "pay for",
    "covered drug",
)
FACILITY_HINTS = (
    "hospital",
    "clinic",
    "health centre",
    "polyclinic",
    "facility",
    "accredited",
)
ENROLLMENT_HINTS = (
    "renew",
    "register",
    "enrol",
    "enroll",
    "card expired",
    "premium",
    "ghana card",
)
DISPUTE_HINTS = (
    "turned away",
    "denied",
    "complaint",
    "refused",
    "charged me",
    "rights",
)


def _heuristic(question: str, fallback_reason: str | None = None) -> AgentResponse:
    q = question.lower()
    tool_calls: list[dict] = []

    if any(h in q for h in MEDICINE_HINTS):
        candidate = _extract_likely_name(question, MEDICINE_HINTS)
        if candidate:
            output = run_tool("medicines_checker", {"name": candidate})
            tool_calls.append(
                {"name": "medicines_checker", "input": {"name": candidate}, "output": output}
            )
            return _wrap_heuristic(
                output.get("summary", "No formulary match."),
                tool_calls,
                fallback_reason,
            )

    if any(h in q for h in FACILITY_HINTS):
        candidate = _extract_likely_name(question, FACILITY_HINTS)
        if candidate:
            output = run_tool("facility_checker", {"name": candidate})
            tool_calls.append(
                {"name": "facility_checker", "input": {"name": candidate}, "output": output}
            )
            return _wrap_heuristic(
                output.get("summary", "No facility match."),
                tool_calls,
                fallback_reason,
            )

    category = None
    if any(h in q for h in ENROLLMENT_HINTS):
        category = "enrollment"
    elif any(h in q for h in DISPUTE_HINTS):
        category = "disputes"

    output = run_tool(
        "policy_retriever", {"query": question, "category": category, "k": 4}
    )
    tool_calls.append(
        {
            "name": "policy_retriever",
            "input": {"query": question, "category": category, "k": 4},
            "output": output,
        }
    )

    chunks = output.get("chunks") or []
    if not chunks:
        return _wrap_heuristic(
            "I couldn't find a clear answer in the knowledge base. Please call the NHIA "
            "Call Centre or visit your nearest NHIS district office for a definitive answer.",
            tool_calls,
            fallback_reason,
        )
    top = chunks[0]
    answer_text = (
        f"Based on the NHIS knowledge base ({top.get('source_file')}):\n\n"
        f"{top['text']}\n\n"
        "For complex or contested cases, contact the NHIA Call Centre or your district "
        "NHIS office."
    )
    return _wrap_heuristic(answer_text, tool_calls, fallback_reason)


def _wrap_heuristic(
    text: str, calls: list[dict], fallback_reason: str | None
) -> AgentResponse:
    return AgentResponse(
        answer=text,
        tool_calls=calls,
        provider="heuristic",
        fallback_reason=fallback_reason,
    )


def _extract_likely_name(question: str, hints: tuple[str, ...]) -> str | None:
    quoted = re.search(r'["\']([^"\']{2,60})["\']', question)
    if quoted:
        return quoted.group(1).strip()

    lowered = question.lower()
    for hint in hints:
        idx = lowered.find(hint)
        if idx == -1:
            continue
        tail = question[idx + len(hint) :]
        m = re.search(
            r"([A-Z][A-Za-z][\w\-]*(?:\s+[A-Z][A-Za-z][\w\-]*){0,4})", tail
        )
        if m:
            return m.group(1).strip()

    caps = re.findall(
        r"\b[A-Z][A-Za-z][\w\-]*(?:\s+[A-Z][A-Za-z][\w\-]*){0,4}\b", question
    )
    return max(caps, key=len) if caps else None
