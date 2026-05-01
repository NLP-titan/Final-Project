"""Prescription analyzer.

Workflow:
1. Client uploads a prescription (image or PDF).
2. Claude vision extracts drugs + facility name as JSON.
3. Each drug is checked against the medicines fuzzy lookup.
4. Facility name is checked against the facilities fuzzy lookup.
5. Single response: per-drug coverage report + facility accreditation status.

Auth: requires a logged-in user (consistent with chat). No file is persisted —
the bytes live in memory for the lifetime of the request only.
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel

from app.auth.dependencies import get_current_user
from app.data_access.facilities_db import search_facility
from app.data_access.medicines_db import search_medicine
from app.db.models import User
from app.utils.vision import (
    SUPPORTED_IMAGE_MEDIA_TYPES,
    SUPPORTED_PDF_MEDIA_TYPE,
    VisionParseError,
    VisionUnavailable,
    analyze_with_claude,
    guess_media_type,
)


log = logging.getLogger(__name__)


router = APIRouter(prefix="/prescriptions", tags=["prescriptions"])


MAX_UPLOAD_BYTES = 8 * 1024 * 1024  # 8 MB

EXTRACTION_PROMPT = (
    "You are reviewing a medical prescription. Extract the following information and "
    "respond with ONLY a JSON object — no prose, no markdown fences. Schema:\n"
    "{\n"
    '  "drugs": [\n'
    '    {"name": "<medicine name as written>", "dosage": "<e.g. 500mg twice daily>", "duration": "<if stated>"}\n'
    "  ],\n"
    '  "facility": "<name of the prescribing hospital/clinic if visible, else null>",\n'
    '  "doctor": "<name if visible, else null>",\n'
    '  "patient": "<patient name or null — never include identifiable details if unsure>",\n'
    '  "issued_date": "<date if visible, else null>",\n'
    '  "confidence": "<low|medium|high>",\n'
    '  "notes": "<short caveats about legibility, partial info, etc.>"\n'
    "}\n"
    "If the image is not a prescription, return: "
    '{"drugs": [], "facility": null, "doctor": null, "patient": null, "issued_date": null, '
    '"confidence": "low", "notes": "Image does not appear to be a prescription."}'
)


class DrugCoverageResult(BaseModel):
    queried_name: str
    dosage: Optional[str] = None
    duration: Optional[str] = None
    matched_name: Optional[str] = None
    generic_name: Optional[str] = None
    covered: Optional[bool] = None
    match_score: Optional[float] = None
    level_of_care: list[str] = []
    notes: Optional[str] = None
    status: str  # "covered" | "not_covered" | "not_found"


class FacilityCoverageResult(BaseModel):
    queried_name: Optional[str] = None
    matched_name: Optional[str] = None
    type: Optional[str] = None
    region: Optional[str] = None
    town: Optional[str] = None
    accredited: Optional[bool] = None
    accreditation_status: Optional[str] = None
    match_score: Optional[float] = None
    status: str  # "accredited" | "not_accredited" | "not_found" | "not_provided"


class PrescriptionAnalysisOut(BaseModel):
    drugs: list[DrugCoverageResult]
    facility: FacilityCoverageResult
    doctor: Optional[str] = None
    patient: Optional[str] = None
    issued_date: Optional[str] = None
    confidence: Optional[str] = None
    notes: Optional[str] = None
    summary: str


def _check_drug(name: str, dosage: Optional[str], duration: Optional[str]) -> DrugCoverageResult:
    matches = search_medicine(name, limit=1, min_score=70.0)
    if not matches:
        return DrugCoverageResult(
            queried_name=name,
            dosage=dosage,
            duration=duration,
            status="not_found",
            notes="No matching entry found in the NHIS Essential Medicines List.",
        )
    m = matches[0]
    return DrugCoverageResult(
        queried_name=name,
        dosage=dosage,
        duration=duration,
        matched_name=m.name,
        generic_name=m.generic_name,
        covered=m.covered,
        match_score=m.score,
        level_of_care=m.level_of_care,
        notes=m.notes or None,
        status="covered" if m.covered else "not_covered",
    )


def _check_facility(name: Optional[str]) -> FacilityCoverageResult:
    if not name:
        return FacilityCoverageResult(status="not_provided")
    matches = search_facility(name, limit=1, min_score=60.0)
    if not matches:
        return FacilityCoverageResult(
            queried_name=name,
            status="not_found",
        )
    f = matches[0]
    return FacilityCoverageResult(
        queried_name=name,
        matched_name=f.name,
        type=f.type or None,
        region=f.region or None,
        town=f.town or None,
        accredited=f.accredited,
        accreditation_status=f.accreditation_status or None,
        match_score=f.score,
        status="accredited" if f.accredited else "not_accredited",
    )


def _build_summary(drugs: list[DrugCoverageResult], facility: FacilityCoverageResult) -> str:
    if not drugs and facility.status == "not_provided":
        return "Could not detect any prescribed drugs or a facility name in this image."
    covered = sum(1 for d in drugs if d.status == "covered")
    not_covered = sum(1 for d in drugs if d.status == "not_covered")
    not_found = sum(1 for d in drugs if d.status == "not_found")
    parts: list[str] = []
    if drugs:
        parts.append(
            f"Detected {len(drugs)} drug(s): {covered} covered by NHIS, "
            f"{not_covered} not covered, {not_found} not on the list."
        )
    if facility.status == "accredited":
        parts.append(f"Facility '{facility.matched_name}' is NHIS-accredited.")
    elif facility.status == "not_accredited":
        parts.append(f"Facility '{facility.matched_name}' is NOT NHIS-accredited.")
    elif facility.status == "not_found":
        parts.append(f"Could not match facility '{facility.queried_name}' in the directory.")
    return " ".join(parts) or "Analysis completed."


@router.post("/analyze", response_model=PrescriptionAnalysisOut)
async def analyze_prescription(
    file: UploadFile = File(..., description="Prescription image or PDF"),
    notes: Optional[str] = Form(default=None),
    user: User = Depends(get_current_user),
) -> PrescriptionAnalysisOut:
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Empty file upload")
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large; max {MAX_UPLOAD_BYTES // (1024*1024)} MB",
        )

    media_type = guess_media_type(file.filename or "", file.content_type)
    if (
        media_type not in SUPPORTED_IMAGE_MEDIA_TYPES
        and media_type != SUPPORTED_PDF_MEDIA_TYPE
    ):
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type {media_type!r}; upload PNG/JPG/WEBP/GIF or PDF",
        )

    try:
        extracted = analyze_with_claude(contents, media_type, EXTRACTION_PROMPT)
    except VisionUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc) + " — set ANTHROPIC_API_KEY to enable prescription analysis.",
        )
    except VisionParseError as exc:
        log.warning("Prescription parse error for user %s: %s", user.id, exc)
        raise HTTPException(
            status_code=422,
            detail="The image could not be analysed. Try a clearer photo or a different angle.",
        )
    except Exception:
        log.exception("Prescription analysis failed for user %s", user.id)
        raise HTTPException(status_code=500, detail="Prescription analysis failed unexpectedly.")

    raw_drugs = extracted.get("drugs") or []
    drug_results = [
        _check_drug(
            (d.get("name") or "").strip(),
            d.get("dosage"),
            d.get("duration"),
        )
        for d in raw_drugs
        if (d.get("name") or "").strip()
    ]
    facility_result = _check_facility(extracted.get("facility"))

    return PrescriptionAnalysisOut(
        drugs=drug_results,
        facility=facility_result,
        doctor=extracted.get("doctor"),
        patient=extracted.get("patient"),
        issued_date=extracted.get("issued_date"),
        confidence=extracted.get("confidence"),
        notes=extracted.get("notes") or notes,
        summary=_build_summary(drug_results, facility_result),
    )
