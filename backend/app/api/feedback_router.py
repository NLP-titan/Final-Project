"""Feedback on assistant messages — thumbs up / down with an optional comment."""
from __future__ import annotations

import datetime as dt
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_admin
from app.db.base import get_db
from app.db.models import Conversation, Feedback, Message, User


router = APIRouter(tags=["feedback"])


class FeedbackCreate(BaseModel):
    rating: int = Field(ge=-1, le=1)  # -1, 0, +1
    comment: Optional[str] = Field(default=None, max_length=2000)


class FeedbackOut(BaseModel):
    id: int
    message_id: int
    user_id: int
    rating: int
    comment: Optional[str] = None
    created_at: dt.datetime

    model_config = {"from_attributes": True}


@router.post(
    "/messages/{message_id}/feedback",
    response_model=FeedbackOut,
    status_code=status.HTTP_201_CREATED,
)
def submit_feedback(
    message_id: int,
    payload: FeedbackCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FeedbackOut:
    msg = db.get(Message, message_id)
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    conv = db.get(Conversation, msg.conversation_id)
    if not conv or conv.user_id != user.id:
        raise HTTPException(status_code=404, detail="Message not found")
    if msg.role != "assistant":
        raise HTTPException(
            status_code=400, detail="Feedback can only be submitted on assistant messages"
        )
    existing = db.execute(
        select(Feedback).where(
            Feedback.message_id == message_id, Feedback.user_id == user.id
        )
    ).scalar_one_or_none()
    if existing:
        existing.rating = payload.rating
        existing.comment = payload.comment
        db.add(existing)
        db.commit()
        db.refresh(existing)
        return FeedbackOut.model_validate(existing)
    fb = Feedback(
        message_id=message_id,
        user_id=user.id,
        rating=payload.rating,
        comment=payload.comment,
    )
    db.add(fb)
    db.commit()
    db.refresh(fb)
    return FeedbackOut.model_validate(fb)


@router.get(
    "/admin/feedback",
    response_model=list[FeedbackOut],
    dependencies=[Depends(require_admin)],
)
def list_feedback(
    db: Session = Depends(get_db),
    rating: Optional[int] = Query(default=None, ge=-1, le=1),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[FeedbackOut]:
    stmt = select(Feedback).order_by(Feedback.created_at.desc())
    if rating is not None:
        stmt = stmt.where(Feedback.rating == rating)
    stmt = stmt.limit(limit).offset(offset)
    return [FeedbackOut.model_validate(r) for r in db.execute(stmt).scalars().all()]
