"""Ingest policy documents into the vector store.

Usage (from the backend directory):
    python -m scripts.ingest                # incremental upsert
    python -m scripts.ingest --reset        # drop and rebuild the collection
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow running as `python scripts/ingest.py` from the backend root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings  # noqa: E402
from app.rag.chunker import chunk_directory  # noqa: E402
from app.rag.vector_store import PolicyVectorStore  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest NHIS policy documents into the vector store.")
    parser.add_argument(
        "--reset", action="store_true", help="Drop and rebuild the collection from scratch."
    )
    parser.add_argument(
        "--policies-dir",
        default=settings.policies_dir,
        help="Directory containing policy documents (md/txt/pdf).",
    )
    args = parser.parse_args()

    policies_dir = Path(args.policies_dir)
    if not policies_dir.exists():
        print(f"Policies directory not found: {policies_dir}", file=sys.stderr)
        return 1

    store = PolicyVectorStore()
    if args.reset:
        print("Resetting collection...")
        store.reset()

    chunks = list(chunk_directory(policies_dir))
    if not chunks:
        print(f"No documents found in {policies_dir}.")
        return 0

    sources = sorted({c.metadata.get("source_file", "?") for c in chunks})
    print(f"Embedding {len(chunks)} chunks from {len(sources)} files: {', '.join(sources)}")
    added = store.add(chunks)
    print(f"Upserted {added} chunks. Collection now contains {store.count()} chunks.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
