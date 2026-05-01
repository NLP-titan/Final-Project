"""Medicines CRUD + photo identification. Reads are public; writes require admin."""
from __future__ import annotations

import datetime as dt
import logging
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_admin
from app.data_access.medicines_db import search_medicine
from app.db.base import get_db
from app.db.models import Medicine, User
from app.utils.vision import (
    SUPPORTED_IMAGE_MEDIA_TYPES,
    VisionParseError,
    VisionUnavailable,
    analyze_with_claude,
    guess_media_type,
)


log = logging.getLogger(__name__)


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


# ---------------------------------------------------------------------------
# Drug photo identification (Claude vision)
# ---------------------------------------------------------------------------
_MAX_UPLOAD_BYTES = 8 * 1024 * 1024

_IDENTIFY_PROMPT = (
    "You are looking at a photograph of a medicine — typically a box, blister pack, "
    "bottle, or label. Identify the drug and respond with ONLY a JSON object — no "
    "prose, no markdown fences. Schema:\n"
    "{\n"
    '  "identified_name": "<generic / INN name if visible, else best guess>",\n'
    '  "brand": "<brand or trade name if visible, else null>",\n'
    '  "strength": "<e.g. 500mg, 250mg/5ml — if visible>",\n'
    '  "dosage_form": "<tablet|capsule|syrup|injection|cream|drops|... — if visible>",\n'
    '  "confidence": "<low|medium|high>",\n'
    '  "notes": "<short caveat about visibility, occlusion, or assumptions>"\n'
    "}\n"
    "If the image is not a medicine, return: "
    '{"identified_name": null, "brand": null, "strength": null, "dosage_form": null, '
    '"confidence": "low", "notes": "Image does not appear to show a medicine."}'
)


class DrugCoverageInfo(BaseModel):
    matched_name: Optional[str] = None
    generic_name: Optional[str] = None
    covered: Optional[bool] = None
    match_score: Optional[float] = None
    level_of_care: list[str] = []
    notes: Optional[str] = None
    status: str  # "covered" | "not_covered" | "not_found"


class MedicineIdentifyOut(BaseModel):
    identified_name: Optional[str] = None
    brand: Optional[str] = None
    strength: Optional[str] = None
    dosage_form: Optional[str] = None
    confidence: Optional[str] = None
    notes: Optional[str] = None
    coverage: DrugCoverageInfo


def _coverage_from_query(query: Optional[str]) -> DrugCoverageInfo:
    if not query:
        return DrugCoverageInfo(status="not_found", notes="No drug name extracted from the image.")
    matches = search_medicine(query, limit=1, min_score=70.0)
    if not matches:
        return DrugCoverageInfo(
            status="not_found",
            notes=f"'{query}' was not found in the NHIS Essential Medicines List.",
        )
    m = matches[0]
    return DrugCoverageInfo(
        matched_name=m.name,
        generic_name=m.generic_name,
        covered=m.covered,
        match_score=m.score,
        level_of_care=m.level_of_care,
        notes=m.notes or None,
        status="covered" if m.covered else "not_covered",
    )


@router.post("/identify", response_model=MedicineIdentifyOut)
async def identify_medicine(
    file: UploadFile = File(..., description="Photo of medicine packaging or label"),
    user: User = Depends(get_current_user),
) -> MedicineIdentifyOut:
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Empty file upload")
    if len(contents) > _MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large; max {_MAX_UPLOAD_BYTES // (1024*1024)} MB",
        )

    media_type = guess_media_type(file.filename or "", file.content_type)
    if media_type not in SUPPORTED_IMAGE_MEDIA_TYPES:
        raise HTTPException(
            status_code=415,
            detail="Drug photo identification accepts images only (PNG/JPG/WEBP/GIF).",
        )

    try:
        extracted = analyze_with_claude(contents, media_type, _IDENTIFY_PROMPT)
    except VisionUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc) + " — set ANTHROPIC_API_KEY to enable drug photo identification.",
        )
    except VisionParseError as exc:
        log.warning("Drug photo parse error for user %s: %s", user.id, exc)
        raise HTTPException(
            status_code=422,
            detail="Could not read the image clearly. Try a sharper photo with the label visible.",
        )
    except Exception:
        log.exception("Drug photo analysis failed for user %s", user.id)
        raise HTTPException(status_code=500, detail="Drug photo analysis failed unexpectedly.")

    identified = (extracted.get("identified_name") or "").strip() or None
    brand = (extracted.get("brand") or "").strip() or None
    # Prefer matching on the generic/identified name; fall back to brand if the identified
    # name is empty.
    query = identified or brand
    coverage = _coverage_from_query(query)
    return MedicineIdentifyOut(
        identified_name=identified,
        brand=brand,
        strength=extracted.get("strength"),
        dosage_form=extracted.get("dosage_form"),
        confidence=extracted.get("confidence"),
        notes=extracted.get("notes"),
        coverage=coverage,
    )
