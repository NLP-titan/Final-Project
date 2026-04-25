"""High-level retriever that the agent's Policy Retriever tool wraps."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.rag.vector_store import PolicyVectorStore, RetrievedChunk, get_default_store


@dataclass
class RetrievalResult:
    query: str
    category: Optional[str]
    chunks: list[RetrievedChunk]

    def as_context_block(self, max_chars: int = 4000) -> str:
        """Render retrieved chunks as a context block suitable for prompting an LLM."""
        parts: list[str] = []
        used = 0
        for i, chunk in enumerate(self.chunks, start=1):
            source = chunk.metadata.get("source_file", "unknown")
            section = chunk.metadata.get("section") or chunk.metadata.get("title") or ""
            header = f"[{i}] source={source}"
            if section:
                header += f" | section={section}"
            block = f"{header}\n{chunk.text}"
            if used + len(block) > max_chars:
                break
            parts.append(block)
            used += len(block) + 2
        return "\n\n".join(parts)


class PolicyRetriever:
    def __init__(self, store: PolicyVectorStore | None = None, default_k: int = 4):
        self._store = store or get_default_store()
        self._default_k = default_k

    def retrieve(
        self,
        query: str,
        k: int | None = None,
        category: str | None = None,
    ) -> RetrievalResult:
        chunks = self._store.query(query, k=k or self._default_k, category=category)
        return RetrievalResult(query=query, category=category, chunks=chunks)
