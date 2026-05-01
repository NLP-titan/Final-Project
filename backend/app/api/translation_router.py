"""Translation endpoints for runtime UI localisation.

The frontend ships English UI strings. When a user picks a Ghanaian language,
it batch-calls `/api/translate/batch` once per language change and caches the
results in localStorage — so subsequent renders are instant and free.
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.auth.dependencies import get_current_user
from app.db.models import User
from app.utils.translate import (
    SUPPORTED_LANGUAGES,
    TranslationUnavailable,
    normalise_lang,
    translate,
    translate_batch,
)


log = logging.getLogger(__name__)


router = APIRouter(prefix="/translate", tags=["translate"])


class TranslateIn(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    target_lang: str = Field(pattern="^(en|tw|gaa|ee)$")


class TranslateOut(BaseModel):
    text: str
    target_lang: str


class TranslateBatchIn(BaseModel):
    texts: list[str] = Field(min_length=1, max_length=200)
    target_lang: str = Field(pattern="^(en|tw|gaa|ee)$")


class TranslateBatchOut(BaseModel):
    texts: list[str]
    target_lang: str


class LanguagesOut(BaseModel):
    languages: dict[str, str]


@router.get("/languages", response_model=LanguagesOut)
def list_languages() -> LanguagesOut:
    return LanguagesOut(languages=SUPPORTED_LANGUAGES)


@router.post("", response_model=TranslateOut)
def translate_one(
    payload: TranslateIn,
    _: Optional[User] = Depends(get_current_user),
) -> TranslateOut:
    target = normalise_lang(payload.target_lang)
    try:
        out = translate(payload.text, target)
    except TranslationUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc) + " — translation requires ANTHROPIC_API_KEY.",
        )
    return TranslateOut(text=out, target_lang=target)


@router.post("/batch", response_model=TranslateBatchOut)
def translate_many(
    payload: TranslateBatchIn,
    _: Optional[User] = Depends(get_current_user),
) -> TranslateBatchOut:
    target = normalise_lang(payload.target_lang)
    if any(len(t) > 1000 for t in payload.texts):
        raise HTTPException(
            status_code=413, detail="Each text in batch must be <= 1000 chars"
        )
    try:
        out = translate_batch(payload.texts, target)
    except TranslationUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc) + " — translation requires ANTHROPIC_API_KEY.",
        )
    return TranslateBatchOut(texts=out, target_lang=target)
