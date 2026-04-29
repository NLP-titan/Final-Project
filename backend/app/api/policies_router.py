"""Policy document management. Admin uploads markdown/text/PDF and triggers reingest."""
from __future__ import annotations

import datetime as dt
import logging
import re
from pathlib import Path
from typing import Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Response,
    UploadFile,
    status,
)
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin
from app.config import settings
from app.db.base import get_db
from app.db.models import PolicyDocument, User


router = APIRouter(prefix="/policies", tags=["policies"], dependencies=[Depends(require_admin)])
log = logging.getLogger(__name__)

ALLOWED_SUFFIXES = {".md", ".markdown", ".txt", ".pdf"}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB


class PolicyDocumentOut(BaseModel):
    id: int
    filename: str
    title: Optional[str] = None
    category: Optional[str] = None
    size_bytes: int
    chunks_indexed: int
    uploaded_by_id: Optional[int] = None
    created_at: dt.datetime
    last_indexed_at: Optional[dt.datetime] = None

    model_config = {"from_attributes": True}


class IngestStatus(BaseModel):
    indexed_files: list[str]
    total_chunks_in_store: int
    documents_updated: int


def _safe_filename(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._")
    return cleaned or "upload"


def _policies_dir() -> Path:
    p = Path(settings.policies_dir)
    p.mkdir(parents=True, exist_ok=True)
    return p


@router.get("", response_model=list[PolicyDocumentOut])
def list_documents(db: Session = Depends(get_db)) -> list[PolicyDocumentOut]:
    rows = db.execute(
        select(PolicyDocument).order_by(PolicyDocument.created_at.desc())
    ).scalars().all()
    return [PolicyDocumentOut.model_validate(r) for r in rows]


@router.post(
    "",
    response_model=PolicyDocumentOut,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    file: UploadFile = File(...),
    title: Optional[str] = Form(default=None),
    category: Optional[str] = Form(default=None),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> PolicyDocumentOut:
    raw_name = file.filename or "upload"
    suffix = Path(raw_name).suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type {suffix}. Allowed: {sorted(ALLOWED_SUFFIXES)}",
        )

    safe_name = _safe_filename(raw_name)
    target = _policies_dir() / safe_name

    size = 0
    with target.open("wb") as out:
        while chunk := await file.read(64 * 1024):
            size += len(chunk)
            if size > MAX_UPLOAD_BYTES:
                target.unlink(missing_ok=True)
                raise HTTPException(status_code=413, detail="File too large (max 10 MB)")
            out.write(chunk)

    existing = db.execute(
        select(PolicyDocument).where(PolicyDocument.filename == safe_name)
    ).scalar_one_or_none()
    if existing:
        existing.size_bytes = size
        existing.title = title or existing.title
        existing.category = category or existing.category
        existing.uploaded_by_id = admin.id
        row = existing
    else:
        row = PolicyDocument(
            filename=safe_name,
            title=title,
            category=category,
            size_bytes=size,
            uploaded_by_id=admin.id,
        )
        db.add(row)
    db.commit()
    db.refresh(row)
    return PolicyDocumentOut.model_validate(row)


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(doc_id: int, db: Session = Depends(get_db)) -> Response:
    row = db.get(PolicyDocument, doc_id)
    if not row:
        raise HTTPException(status_code=404, detail="Document not found")
    target = _policies_dir() / row.filename
    if target.exists() and target.is_file():
        target.unlink()
    db.delete(row)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _run_ingest_sync(reset: bool) -> IngestStatus:
    """Reingest the policies directory into the vector store and update DB rows."""
    from app.rag.chunker import chunk_directory, chunk_file
    from app.rag.vector_store import PolicyVectorStore

    policies_dir = _policies_dir()
    store = PolicyVectorStore()
    if reset:
        store.reset()

    indexed_files: list[str] = []
    documents_updated = 0

    chunks_by_file: dict[str, list] = {}
    for chunk in chunk_directory(policies_dir):
        chunks_by_file.setdefault(chunk.metadata.get("source_file", "?"), []).append(chunk)

    if chunks_by_file:
        flat = [c for cs in chunks_by_file.values() for c in cs]
        store.add(flat)
        indexed_files = sorted(chunks_by_file.keys())

    # Update PolicyDocument rows
    from app.db.base import session_scope

    now = dt.datetime.now(dt.timezone.utc)
    with session_scope() as db:
        for path in policies_dir.iterdir():
            if not path.is_file() or path.suffix.lower() not in ALLOWED_SUFFIXES:
                continue
            row = db.execute(
                select(PolicyDocument).where(PolicyDocument.filename == path.name)
            ).scalar_one_or_none()
            chunk_count = len(chunks_by_file.get(path.name, []))
            if row:
                row.size_bytes = path.stat().st_size
                row.chunks_indexed = chunk_count
                row.last_indexed_at = now
                db.add(row)
                documents_updated += 1
            else:
                # Auto-register seed files that were never uploaded through the API.
                meta = chunk_file(path)
                title = meta[0].metadata.get("title") if meta else None
                category = meta[0].metadata.get("category") if meta else None
                db.add(
                    PolicyDocument(
                        filename=path.name,
                        title=title,
                        category=category,
                        size_bytes=path.stat().st_size,
                        chunks_indexed=chunk_count,
                        last_indexed_at=now,
                    )
                )
                documents_updated += 1

    return IngestStatus(
        indexed_files=indexed_files,
        total_chunks_in_store=store.count(),
        documents_updated=documents_updated,
    )


@router.post("/reingest", response_model=IngestStatus)
def reingest_now(
    background_tasks: BackgroundTasks,
    reset: bool = False,
) -> IngestStatus:
    """Synchronous reingest. The background_tasks parameter is reserved for future async use."""
    try:
        return _run_ingest_sync(reset=reset)
    except Exception as exc:
        log.exception("Reingest failed")
        raise HTTPException(status_code=500, detail=f"Reingest failed: {exc}") from exc
