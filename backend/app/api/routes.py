from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.agent.orchestrator import answer
from app.agent.tools import TOOL_REGISTRY, run_tool
from app.config import settings
from app.rag.vector_store import get_default_store


router = APIRouter()


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)


class ChatResponse(BaseModel):
    answer: str
    tool_calls: list[dict]
    provider: str


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    result = answer(req.message)
    return ChatResponse(**result.to_dict())


class ToolCallRequest(BaseModel):
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


@router.post("/tools/call")
def call_tool(req: ToolCallRequest) -> dict:
    if req.name not in TOOL_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Unknown tool: {req.name}")
    return run_tool(req.name, req.arguments)


@router.get("/tools")
def list_tools() -> dict:
    return {
        "tools": [
            {
                "name": t.name,
                "description": t.description,
                "input_schema": t.input_schema,
            }
            for t in TOOL_REGISTRY.values()
        ]
    }


@router.get("/health")
def health() -> dict:
    try:
        store_count = get_default_store().count()
    except Exception as exc:
        store_count = f"error: {exc}"
    return {
        "status": "ok",
        "llm_provider": settings.llm_provider,
        "vector_store_chunks": store_count,
        "embedding_model": settings.embedding_model,
    }
