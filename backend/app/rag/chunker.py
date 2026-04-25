"""Section-aware chunker for NHIS policy documents.

Strategy:
1. If a document has Markdown-style headings (`#`, `##`, `###`), chunk by heading section.
2. Otherwise fall back to paragraph-based chunking.
3. Always cap chunk size with a soft character limit so individual sections don't blow up the
   embedding context window. Sections that exceed the cap are split on paragraph boundaries.

Each chunk carries metadata describing its source file, section path and category, so the
retriever can both display citations and filter by category when a tool requests it.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
FM_LINE_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.*)$")
SOFT_CHAR_CAP = 1200
HARD_CHAR_CAP = 2000


@dataclass
class Chunk:
    text: str
    metadata: dict = field(default_factory=dict)


def _parse_frontmatter(raw: str) -> tuple[dict, str]:
    if not raw.startswith("---"):
        return {}, raw
    end = raw.find("\n---", 3)
    if end == -1:
        return {}, raw
    fm_block = raw[3:end].strip()
    body = raw[end + 4 :].lstrip("\n")
    meta: dict = {}
    for line in fm_block.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = FM_LINE_RE.match(line)
        if m:
            key, value = m.group(1), m.group(2).strip()
            if (value.startswith('"') and value.endswith('"')) or (
                value.startswith("'") and value.endswith("'")
            ):
                value = value[1:-1]
            meta[key] = value
    return meta, body


def _split_long_section(text: str) -> list[str]:
    """Split a too-long section on paragraph boundaries while staying under HARD_CHAR_CAP."""
    if len(text) <= SOFT_CHAR_CAP:
        return [text]

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    buf: list[str] = []
    buf_len = 0
    for para in paragraphs:
        if buf_len + len(para) + 2 > HARD_CHAR_CAP and buf:
            chunks.append("\n\n".join(buf))
            buf = [para]
            buf_len = len(para)
        else:
            buf.append(para)
            buf_len += len(para) + 2
    if buf:
        chunks.append("\n\n".join(buf))
    return chunks


def chunk_markdown(text: str, base_metadata: dict | None = None) -> list[Chunk]:
    """Chunk a markdown-ish document by heading hierarchy."""
    base_metadata = dict(base_metadata or {})
    fm, body = _parse_frontmatter(text)
    base_metadata.update({k: v for k, v in fm.items() if v is not None})

    lines = body.splitlines()
    sections: list[tuple[list[str], list[str]]] = []  # (heading_path, lines)
    current_path: list[str] = []
    current_lines: list[str] = []

    def flush() -> None:
        if current_lines:
            sections.append((list(current_path), list(current_lines)))

    for line in lines:
        m = HEADING_RE.match(line)
        if m:
            flush()
            current_lines = []
            level = len(m.group(1))
            heading = m.group(2).strip()
            current_path = current_path[: level - 1] + [heading]
        else:
            current_lines.append(line)
    flush()

    if not sections:
        # No headings — chunk as paragraphs
        return _paragraph_chunks(body, base_metadata)

    chunks: list[Chunk] = []
    for path, sec_lines in sections:
        section_text = "\n".join(sec_lines).strip()
        if not section_text:
            continue
        if path:
            section_text = f"# {' > '.join(path)}\n\n{section_text}"
        for piece in _split_long_section(section_text):
            meta = dict(base_metadata)
            meta["section"] = " > ".join(path) if path else ""
            chunks.append(Chunk(text=piece, metadata=meta))
    return chunks


def _paragraph_chunks(text: str, base_metadata: dict) -> list[Chunk]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[Chunk] = []
    buf: list[str] = []
    buf_len = 0
    for para in paragraphs:
        if buf_len + len(para) + 2 > SOFT_CHAR_CAP and buf:
            chunks.append(Chunk(text="\n\n".join(buf), metadata=dict(base_metadata)))
            buf = [para]
            buf_len = len(para)
        else:
            buf.append(para)
            buf_len += len(para) + 2
    if buf:
        chunks.append(Chunk(text="\n\n".join(buf), metadata=dict(base_metadata)))
    return chunks


def chunk_file(path: Path) -> list[Chunk]:
    suffix = path.suffix.lower()
    base_meta = {"source_file": path.name}
    if suffix in {".md", ".markdown", ".txt"}:
        return chunk_markdown(path.read_text(encoding="utf-8"), base_meta)
    if suffix == ".pdf":
        return _chunk_pdf(path, base_meta)
    return []


def _chunk_pdf(path: Path, base_meta: dict) -> list[Chunk]:
    from pypdf import PdfReader  # imported lazily so non-PDF runs avoid the dep cost

    reader = PdfReader(str(path))
    chunks: list[Chunk] = []
    for i, page in enumerate(reader.pages):
        text = (page.extract_text() or "").strip()
        if not text:
            continue
        meta = dict(base_meta)
        meta["page"] = i + 1
        for piece in _split_long_section(text):
            chunks.append(Chunk(text=piece, metadata=dict(meta)))
    return chunks


def chunk_directory(directory: Path) -> Iterable[Chunk]:
    for path in sorted(directory.rglob("*")):
        if path.is_file() and path.suffix.lower() in {".md", ".markdown", ".txt", ".pdf"}:
            yield from chunk_file(path)
