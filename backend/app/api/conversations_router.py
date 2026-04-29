"""Conversations + chat persistence.

Endpoints:
  GET    /conversations                       — list mine
  POST   /conversations                       — create
  GET    /conversations/{id}                  — fetch with messages
  PATCH  /conversations/{id}                  — rename
  DELETE /conversations/{id}                  — drop the conversation and its messages
  POST   /conversations/{id}/messages         — post a user message; returns the assistant reply
  POST   /chat                                — stateless one-shot (kept for the frontend dev)

The assistant reply is persisted with its tool call trace so the conversation can be
re-rendered later without re-running the agent.
"""
from __future__ import annotations

import datetime as dt
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.agent.orchestrator import answer as agent_answer
from app.auth.dependencies import get_current_user, get_optional_user
from app.db.base import get_db
from app.db.models import Conversation, Message, User
from app.middleware.rate_limit import chat_rate_limit_dependency


router = APIRouter(tags=["chat"])


class ConversationCreate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=255)


class ConversationRename(BaseModel):
    title: str = Field(min_length=1, max_length=255)


class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    provider: Optional[str] = None
    tool_calls: list[dict] = []
    created_at: dt.datetime

    @classmethod
    def from_model(cls, m: Message) -> "MessageOut":
        return cls(
            id=m.id,
            role=m.role,
            content=m.content,
            provider=m.provider,
            tool_calls=m.tool_calls,
            created_at=m.created_at,
        )


class ConversationOut(BaseModel):
    id: int
    title: Optional[str] = None
    created_at: dt.datetime
    updated_at: dt.datetime
    message_count: int = 0


class ConversationDetailOut(ConversationOut):
    messages: list[MessageOut] = []


class PostMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


class PostMessageResponse(BaseModel):
    user_message: MessageOut
    assistant_message: MessageOut


def _to_summary(conv: Conversation) -> ConversationOut:
    return ConversationOut(
        id=conv.id,
        title=conv.title,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        message_count=len(conv.messages),
    )


@router.get("/conversations", response_model=list[ConversationOut])
def list_conversations(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ConversationOut]:
    convs = (
        db.execute(
            select(Conversation)
            .where(Conversation.user_id == user.id)
            .options(selectinload(Conversation.messages))
            .order_by(Conversation.updated_at.desc())
        )
        .scalars()
        .all()
    )
    return [_to_summary(c) for c in convs]


@router.post(
    "/conversations",
    response_model=ConversationOut,
    status_code=status.HTTP_201_CREATED,
)
def create_conversation(
    payload: ConversationCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConversationOut:
    conv = Conversation(user_id=user.id, title=payload.title)
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return _to_summary(conv)


def _load_owned_conversation(conv_id: int, user: User, db: Session) -> Conversation:
    conv = (
        db.execute(
            select(Conversation)
            .where(Conversation.id == conv_id, Conversation.user_id == user.id)
            .options(selectinload(Conversation.messages))
        )
        .scalar_one_or_none()
    )
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


@router.get("/conversations/{conv_id}", response_model=ConversationDetailOut)
def get_conversation(
    conv_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConversationDetailOut:
    conv = _load_owned_conversation(conv_id, user, db)
    summary = _to_summary(conv).model_dump()
    summary["messages"] = [MessageOut.from_model(m) for m in conv.messages]
    return ConversationDetailOut(**summary)


@router.patch("/conversations/{conv_id}", response_model=ConversationOut)
def rename_conversation(
    conv_id: int,
    payload: ConversationRename,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConversationOut:
    conv = _load_owned_conversation(conv_id, user, db)
    conv.title = payload.title
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return _to_summary(conv)


@router.delete(
    "/conversations/{conv_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_conversation(
    conv_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    conv = _load_owned_conversation(conv_id, user, db)
    db.delete(conv)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/conversations/{conv_id}/messages",
    response_model=PostMessageResponse,
    dependencies=[Depends(chat_rate_limit_dependency)],
)
def post_message(
    conv_id: int,
    payload: PostMessageRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PostMessageResponse:
    conv = _load_owned_conversation(conv_id, user, db)

    user_msg = Message(conversation_id=conv.id, role="user", content=payload.content)
    db.add(user_msg)
    db.flush()

    history = [{"role": m.role, "content": m.content} for m in conv.messages]
    response = agent_answer(payload.content, history=history)

    asst_msg = Message(
        conversation_id=conv.id,
        role="assistant",
        content=response.answer,
        provider=response.provider,
    )
    asst_msg.set_tool_calls(response.tool_calls)
    db.add(asst_msg)

    if not conv.title:
        conv.title = payload.content[:60]
    conv.updated_at = dt.datetime.now(dt.timezone.utc)
    db.add(conv)

    db.commit()
    db.refresh(user_msg)
    db.refresh(asst_msg)

    return PostMessageResponse(
        user_message=MessageOut.from_model(user_msg),
        assistant_message=MessageOut.from_model(asst_msg),
    )


# ---------------------------------------------------------------------------
# Stateless one-shot — kept for the frontend dev who hasn't wired auth yet.
# ---------------------------------------------------------------------------
class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    history: list[dict] = Field(default_factory=list)


class ChatResponse(BaseModel):
    answer: str
    tool_calls: list[dict]
    provider: str
    fallback_reason: Optional[str] = None


@router.post(
    "/chat",
    response_model=ChatResponse,
    dependencies=[Depends(chat_rate_limit_dependency)],
)
def chat(
    req: ChatRequest,
    _: Optional[User] = Depends(get_optional_user),
) -> ChatResponse:
    response = agent_answer(req.message, history=req.history)
    return ChatResponse(**response.to_dict())
