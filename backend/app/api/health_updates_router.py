"""Health Updates CRUD. Reads are public; writes require admin."""
from __future__ import annotations

import datetime as dt
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin
from app.db.base import get_db
from app.db.models import HealthUpdate


router = APIRouter(prefix="/health-updates", tags=["health-updates"])


class HealthUpdateOut(BaseModel):
    id: int
    title: str
    source: Optional[str] = None
    category: Optional[str] = None
    summary: Optional[str] = None
    published_date: Optional[str] = None
    created_at: dt.datetime

    model_config = {"from_attributes": True}


class HealthUpdateCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    source: Optional[str] = Field(default=None, max_length=128)
    category: Optional[str] = Field(default=None, max_length=64)
    summary: Optional[str] = None
    published_date: Optional[str] = Field(default=None, max_length=32)


class HealthUpdateUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=255)
    source: Optional[str] = Field(default=None, max_length=128)
    category: Optional[str] = Field(default=None, max_length=64)
    summary: Optional[str] = None
    published_date: Optional[str] = Field(default=None, max_length=32)


@router.get("", response_model=list[HealthUpdateOut])
def list_updates(
    db: Session = Depends(get_db),
    category: Optional[str] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[HealthUpdateOut]:
    stmt = select(HealthUpdate)
    if category:
        stmt = stmt.where(HealthUpdate.category == category)
    stmt = stmt.order_by(HealthUpdate.created_at.desc()).limit(limit).offset(offset)
    return [HealthUpdateOut.model_validate(r) for r in db.execute(stmt).scalars().all()]


@router.get("/{update_id}", response_model=HealthUpdateOut)
def get_update(update_id: int, db: Session = Depends(get_db)) -> HealthUpdateOut:
    row = db.get(HealthUpdate, update_id)
    if not row:
        raise HTTPException(status_code=404, detail="Update not found")
    return HealthUpdateOut.model_validate(row)


@router.post(
    "",
    response_model=HealthUpdateOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
def create_update(payload: HealthUpdateCreate, db: Session = Depends(get_db)) -> HealthUpdateOut:
    row = HealthUpdate(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return HealthUpdateOut.model_validate(row)


@router.patch(
    "/{update_id}",
    response_model=HealthUpdateOut,
    dependencies=[Depends(require_admin)],
)
def update_update(
    update_id: int,
    payload: HealthUpdateUpdate,
    db: Session = Depends(get_db),
) -> HealthUpdateOut:
    row = db.get(HealthUpdate, update_id)
    if not row:
        raise HTTPException(status_code=404, detail="Update not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    db.add(row)
    db.commit()
    db.refresh(row)
    return HealthUpdateOut.model_validate(row)


@router.delete(
    "/{update_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
)
def delete_update(update_id: int, db: Session = Depends(get_db)) -> Response:
    row = db.get(HealthUpdate, update_id)
    if not row:
        raise HTTPException(status_code=404, detail="Update not found")
    db.delete(row)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
