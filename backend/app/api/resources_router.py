"""Resources / articles CRUD. Reads are public; writes require admin."""
from __future__ import annotations

import datetime as dt
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin
from app.db.base import get_db
from app.db.models import Resource


router = APIRouter(prefix="/resources", tags=["resources"])


class ResourceOut(BaseModel):
    id: int
    title: str
    category: Optional[str] = None
    read_time: Optional[str] = None
    content: Optional[str] = None
    created_at: dt.datetime

    model_config = {"from_attributes": True}


class ResourceCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    category: Optional[str] = Field(default=None, max_length=64)
    read_time: Optional[str] = Field(default=None, max_length=16)
    content: Optional[str] = None


class ResourceUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=255)
    category: Optional[str] = Field(default=None, max_length=64)
    read_time: Optional[str] = Field(default=None, max_length=16)
    content: Optional[str] = None


@router.get("", response_model=list[ResourceOut])
def list_resources(
    db: Session = Depends(get_db),
    category: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[ResourceOut]:
    stmt = select(Resource)
    if category:
        stmt = stmt.where(Resource.category == category)
    stmt = stmt.order_by(Resource.created_at.asc()).limit(limit).offset(offset)
    return [ResourceOut.model_validate(r) for r in db.execute(stmt).scalars().all()]


@router.get("/{resource_id}", response_model=ResourceOut)
def get_resource(resource_id: int, db: Session = Depends(get_db)) -> ResourceOut:
    row = db.get(Resource, resource_id)
    if not row:
        raise HTTPException(status_code=404, detail="Resource not found")
    return ResourceOut.model_validate(row)


@router.post(
    "",
    response_model=ResourceOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
def create_resource(payload: ResourceCreate, db: Session = Depends(get_db)) -> ResourceOut:
    row = Resource(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return ResourceOut.model_validate(row)


@router.patch(
    "/{resource_id}",
    response_model=ResourceOut,
    dependencies=[Depends(require_admin)],
)
def update_resource(
    resource_id: int,
    payload: ResourceUpdate,
    db: Session = Depends(get_db),
) -> ResourceOut:
    row = db.get(Resource, resource_id)
    if not row:
        raise HTTPException(status_code=404, detail="Resource not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    db.add(row)
    db.commit()
    db.refresh(row)
    return ResourceOut.model_validate(row)


@router.delete(
    "/{resource_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
)
def delete_resource(resource_id: int, db: Session = Depends(get_db)) -> Response:
    row = db.get(Resource, resource_id)
    if not row:
        raise HTTPException(status_code=404, detail="Resource not found")
    db.delete(row)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
