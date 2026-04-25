"""Direct tool invocation + health endpoints.

The full chat endpoint and persistent conversation history live in
`app.api.conversations_router`. This router stays thin so frontend devs and the eval script
can call the underlying tools without going through the agent.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.agent.tools import TOOL_REGISTRY, run_tool
from app.auth.dependencies import require_admin
from app.config import settings
from app.db.base import get_engine
from app.db.models import User
from app.rag.vector_store import get_default_store


router = APIRouter()


class ToolCallRequest(BaseModel):
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


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


@router.post("/tools/call", dependencies=[Depends(require_admin)])
def call_tool(req: ToolCallRequest, _: User = Depends(require_admin)) -> dict:
    """Direct tool invocation — admin only because it bypasses the agent's safety prompts."""
    if req.name not in TOOL_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Unknown tool: {req.name}")
    return run_tool(req.name, req.arguments)


@router.get("/health")
def health() -> dict:
    info: dict[str, Any] = {
        "status": "ok",
        "llm_provider": settings.llm_provider,
        "embedding_model": settings.embedding_model,
    }
    try:
        info["vector_store_chunks"] = get_default_store().count()
    except Exception as exc:
        info["vector_store_chunks"] = f"error: {exc}"
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.exec_driver_sql("SELECT 1")
        info["database"] = "ok"
    except Exception as exc:
        info["database"] = f"error: {exc}"
    return info


@router.get("/")
def root() -> dict:
    return {
        "service": "NHIS Assistant Backend",
        "version": "0.2.0",
        "docs": "/docs",
        "health": "/api/health",
    }
