"""Policy Retriever tool — wraps the RAG retriever.

Use this tool for narrative policy questions: what is covered, who is eligible, what to do
when denied service, how to renew, etc. For a specific medicine entitlement, prefer the
medicines_checker. For whether a specific hospital is accredited, prefer the facility_checker.
"""
from __future__ import annotations

from app.agent.tools.base import Tool


ALLOWED_CATEGORIES = ["coverage", "enrollment", "disputes", "facilities", "medicines"]

_retriever = None


def _get_retriever():
    """Lazily construct the retriever — keeps chromadb / sentence-transformers off the
    import path for callers that don't actually need RAG (e.g. structured-tool unit tests)."""
    global _retriever
    if _retriever is None:
        from app.rag.retriever import PolicyRetriever

        _retriever = PolicyRetriever()
    return _retriever


def _handler(args: dict) -> dict:
    query = (args.get("query") or "").strip()
    if not query:
        return {"error": "Missing required argument: query"}
    k = int(args.get("k", 4))
    category = args.get("category")
    if category and category not in ALLOWED_CATEGORIES:
        return {
            "error": f"Invalid category '{category}'. Allowed: {ALLOWED_CATEGORIES}",
        }
    result = _get_retriever().retrieve(query=query, k=k, category=category)
    return {
        "query": result.query,
        "category": result.category,
        "chunks": [
            {
                "text": c.text,
                "score": round(c.score, 4),
                "source_file": c.metadata.get("source_file"),
                "section": c.metadata.get("section") or c.metadata.get("title"),
                "policy_category": c.metadata.get("category"),
            }
            for c in result.chunks
        ],
    }


policy_retriever_tool = Tool(
    name="policy_retriever",
    description=(
        "Retrieve relevant passages from the NHIS policy knowledge base. "
        "Use for questions about benefit coverage, exclusions, enrolment/renewal, member "
        "rights, and dispute procedures. Returns ranked text chunks with source citations."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The user's question or a focused rephrasing of it.",
            },
            "k": {
                "type": "integer",
                "description": "Number of chunks to return (default 4).",
                "default": 4,
                "minimum": 1,
                "maximum": 10,
            },
            "category": {
                "type": "string",
                "description": (
                    "Optional category filter. One of: coverage, enrollment, disputes, "
                    "facilities, medicines."
                ),
                "enum": ALLOWED_CATEGORIES,
            },
        },
        "required": ["query"],
    },
    handler=_handler,
)
