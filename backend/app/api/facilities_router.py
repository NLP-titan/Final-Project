"""Facilities CRUD. Reads are public; writes require admin."""
from __future__ import annotations

import datetime as dt
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin
from app.db.base import get_db
from app.db.models import Facility


router = APIRouter(prefix="/facilities", tags=["facilities"])


class FacilityOut(BaseModel):
    id: int
    name: str
    type: Optional[str] = None
    region: Optional[str] = None
    district: Optional[str] = None
    town: Optional[str] = None
    accredited: bool
    accreditation_status: Optional[str] = None
    services: Optional[str] = None
    phone: Optional[str] = None
    created_at: dt.datetime
    updated_at: dt.datetime

    model_config = {"from_attributes": True}


class FacilityCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    type: Optional[str] = Field(default=None, max_length=128)
    region: Optional[str] = Field(default=None, max_length=128)
    district: Optional[str] = Field(default=None, max_length=128)
    town: Optional[str] = Field(default=None, max_length=128)
    accredited: bool = True
    accreditation_status: Optional[str] = Field(default=None, max_length=64)
    services: Optional[str] = Field(default=None, max_length=512)
    phone: Optional[str] = Field(default=None, max_length=64)


class FacilityUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255)
    type: Optional[str] = Field(default=None, max_length=128)
    region: Optional[str] = Field(default=None, max_length=128)
    district: Optional[str] = Field(default=None, max_length=128)
    town: Optional[str] = Field(default=None, max_length=128)
    accredited: Optional[bool] = None
    accreditation_status: Optional[str] = Field(default=None, max_length=64)
    services: Optional[str] = Field(default=None, max_length=512)
    phone: Optional[str] = Field(default=None, max_length=64)


@router.get("", response_model=list[FacilityOut])
def list_facilities(
    db: Session = Depends(get_db),
    q: Optional[str] = Query(default=None, description="Substring filter on name/town/district"),
    region: Optional[str] = None,
    accredited: Optional[bool] = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[FacilityOut]:
    stmt = select(Facility)
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(
            or_(
                Facility.name.ilike(like),
                Facility.town.ilike(like),
                Facility.district.ilike(like),
            )
        )
    if region:
        stmt = stmt.where(Facility.region.ilike(region))
    if accredited is not None:
        stmt = stmt.where(Facility.accredited == accredited)
    stmt = stmt.order_by(Facility.name).limit(limit).offset(offset)
    return [FacilityOut.model_validate(r) for r in db.execute(stmt).scalars().all()]


@router.get("/{facility_id}", response_model=FacilityOut)
def get_facility(facility_id: int, db: Session = Depends(get_db)) -> FacilityOut:
    row = db.get(Facility, facility_id)
    if not row:
        raise HTTPException(status_code=404, detail="Facility not found")
    return FacilityOut.model_validate(row)


@router.post(
    "",
    response_model=FacilityOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
def create_facility(payload: FacilityCreate, db: Session = Depends(get_db)) -> FacilityOut:
    row = Facility(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return FacilityOut.model_validate(row)


@router.patch(
    "/{facility_id}",
    response_model=FacilityOut,
    dependencies=[Depends(require_admin)],
)
def update_facility(
    facility_id: int,
    payload: FacilityUpdate,
    db: Session = Depends(get_db),
) -> FacilityOut:
    row = db.get(Facility, facility_id)
    if not row:
        raise HTTPException(status_code=404, detail="Facility not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    db.add(row)
    db.commit()
    db.refresh(row)
    return FacilityOut.model_validate(row)


@router.delete(
    "/{facility_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
)
def delete_facility(facility_id: int, db: Session = Depends(get_db)) -> Response:
    row = db.get(Facility, facility_id)
    if not row:
        raise HTTPException(status_code=404, detail="Facility not found")
    db.delete(row)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
