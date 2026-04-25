"""ChromaDB-backed vector store for policy chunks.

ChromaDB and the embedder are imported lazily so simply importing this module never triggers
the heavy dependency stack (useful for unit tests and for endpoints like /health that only
*conditionally* care about the vector store).
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from app.config import settings
from app.rag.chunker import Chunk


@dataclass
class RetrievedChunk:
    text: str
    metadata: dict
    score: float


class PolicyVectorStore:
    def __init__(self, persist_dir: str | None = None, collection_name: str | None = None):
        import chromadb
        from chromadb.config import Settings as ChromaSettings

        persist_dir = persist_dir or settings.chroma_persist_dir
        Path(persist_dir).mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(
            path=persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name=collection_name or settings.chroma_collection,
            metadata={"hnsw:space": "cosine"},
        )

    @staticmethod
    def _chunk_id(chunk: Chunk, position: int) -> str:
        h = hashlib.sha1()
        h.update(chunk.text.encode("utf-8"))
        h.update(str(chunk.metadata.get("source_file", "")).encode("utf-8"))
        h.update(str(position).encode("utf-8"))
        return h.hexdigest()

    def reset(self) -> None:
        """Drop and recreate the collection."""
        name = self._collection.name
        self._client.delete_collection(name)
        self._collection = self._client.get_or_create_collection(
            name=name, metadata={"hnsw:space": "cosine"}
        )

    def add(self, chunks: Sequence[Chunk]) -> int:
        from app.rag.embedder import embed_texts

        if not chunks:
            return 0
        ids = [self._chunk_id(c, i) for i, c in enumerate(chunks)]
        documents = [c.text for c in chunks]
        metadatas = [self._normalise_meta(c.metadata) for c in chunks]
        embeddings = embed_texts(documents)
        self._collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
        )
        return len(chunks)

    @staticmethod
    def _normalise_meta(meta: dict) -> dict:
        # Chroma metadata only accepts str/int/float/bool — coerce or drop everything else.
        out: dict = {}
        for k, v in meta.items():
            if v is None:
                continue
            if isinstance(v, (str, int, float, bool)):
                out[k] = v
            else:
                out[k] = str(v)
        return out

    def query(
        self,
        query_text: str,
        k: int = 4,
        category: str | None = None,
    ) -> list[RetrievedChunk]:
        from app.rag.embedder import embed_query

        where = {"category": category} if category else None
        result = self._collection.query(
            query_embeddings=[embed_query(query_text)],
            n_results=k,
            where=where,
        )
        out: list[RetrievedChunk] = []
        documents = (result.get("documents") or [[]])[0]
        metadatas = (result.get("metadatas") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]
        for doc, meta, dist in zip(documents, metadatas, distances):
            out.append(
                RetrievedChunk(
                    text=doc,
                    metadata=meta or {},
                    score=float(1.0 - dist) if dist is not None else 0.0,
                )
            )
        return out

    def count(self) -> int:
        return self._collection.count()


_default_store: PolicyVectorStore | None = None


def get_default_store() -> PolicyVectorStore:
    global _default_store
    if _default_store is None:
        _default_store = PolicyVectorStore()
    return _default_store
