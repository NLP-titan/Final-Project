"""Medicines CRUD. Reads are public; writes require admin."""
from __future__ import annotations

import datetime as dt
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin
from app.db.base import get_db
from app.db.models import Medicine


router = APIRouter(prefix="/medicines", tags=["medicines"])


class MedicineOut(BaseModel):
    id: int
    name: str
    generic_name: str
    strength: Optional[str] = None
    form: Optional[str] = None
    therapeutic_class: Optional[str] = None
    covered: bool
    level_of_care: Optional[str] = None
    notes: Optional[str] = None
    created_at: dt.datetime
    updated_at: dt.datetime

    model_config = {"from_attributes": True}


class MedicineCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    generic_name: str = Field(min_length=1, max_length=255)
    strength: Optional[str] = Field(default=None, max_length=64)
    form: Optional[str] = Field(default=None, max_length=64)
    therapeutic_class: Optional[str] = Field(default=None, max_length=128)
    covered: bool = True
    level_of_care: Optional[str] = Field(default=None, max_length=255)
    notes: Optional[str] = None


class MedicineUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255)
    generic_name: Optional[str] = Field(default=None, max_length=255)
    strength: Optional[str] = Field(default=None, max_length=64)
    form: Optional[str] = Field(default=None, max_length=64)
    therapeutic_class: Optional[str] = Field(default=None, max_length=128)
    covered: Optional[bool] = None
    level_of_care: Optional[str] = Field(default=None, max_length=255)
    notes: Optional[str] = None


@router.get("", response_model=list[MedicineOut])
def list_medicines(
    db: Session = Depends(get_db),
    q: Optional[str] = Query(default=None, description="Substring filter on name/generic"),
    covered: Optional[bool] = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[MedicineOut]:
    stmt = select(Medicine)
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(
            or_(Medicine.name.ilike(like), Medicine.generic_name.ilike(like))
        )
    if covered is not None:
        stmt = stmt.where(Medicine.covered == covered)
    stmt = stmt.order_by(Medicine.name).limit(limit).offset(offset)
    return [MedicineOut.model_validate(r) for r in db.execute(stmt).scalars().all()]


@router.get("/{medicine_id}", response_model=MedicineOut)
def get_medicine(medicine_id: int, db: Session = Depends(get_db)) -> MedicineOut:
    row = db.get(Medicine, medicine_id)
    if not row:
        raise HTTPException(status_code=404, detail="Medicine not found")
    return MedicineOut.model_validate(row)


@router.post(
    "",
    response_model=MedicineOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
def create_medicine(payload: MedicineCreate, db: Session = Depends(get_db)) -> MedicineOut:
    row = Medicine(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return MedicineOut.model_validate(row)


@router.patch(
    "/{medicine_id}",
    response_model=MedicineOut,
    dependencies=[Depends(require_admin)],
)
def update_medicine(
    medicine_id: int,
    payload: MedicineUpdate,
    db: Session = Depends(get_db),
) -> MedicineOut:
    row = db.get(Medicine, medicine_id)
    if not row:
        raise HTTPException(status_code=404, detail="Medicine not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    db.add(row)
    db.commit()
    db.refresh(row)
    return MedicineOut.model_validate(row)


@router.delete(
    "/{medicine_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
)
def delete_medicine(medicine_id: int, db: Session = Depends(get_db)) -> Response:
    row = db.get(Medicine, medicine_id)
    if not row:
        raise HTTPException(status_code=404, detail="Medicine not found")
    db.delete(row)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
