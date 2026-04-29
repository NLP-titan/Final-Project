# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Session Protocol (do this every run)

1. **Read `HANDOFF.md` first** — it captures current project state, open questions, and what was decided last session.
2. **Before closing any session**, append an entry to `SESSION_LOG.md` with: date, what was done, key decisions, and any new open questions.
3. Update `HANDOFF.md` whenever an open question is resolved or the project state changes significantly.

## Project Overview

NHIS Assistant — a RAG-powered chatbot for Ghana's National Health Insurance Scheme. Users ask questions about coverage, medicines, and accredited facilities; the agent retrieves answers from policy documents and structured data.

## Setup

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # fill in at minimum ANTHROPIC_API_KEY or OPENAI_API_KEY
python -m scripts.ingest --reset   # chunk policy docs → embed → upsert to ChromaDB
```

## Common Commands

```bash
# Run server (dev)
uvicorn app.main:app --reload

# Run all tests
pytest -q

# Run a single test file
pytest tests/test_chunker.py -v

# Evaluate agent on 30 test cases
python -m scripts.eval_cases                       # heuristic mode (no API key)
python -m scripts.eval_cases --provider anthropic  # LLM-graded mode

# Re-ingest after adding/changing policy documents
python -m scripts.ingest --reset
```

API docs are at `http://localhost:8000/docs` when the server is running.

## Architecture

The backend is a FastAPI application with three logical tiers:

### 1. API Layer (`app/api/`)
Routers for: `auth`, `conversations` (chat + history), `medicines`, `facilities`, `policies`, `feedback`, `users`, and top-level `routes` (tool spec/call, health). All routes are mounted under `/api`. The health endpoint reports DB, vector store, and LLM provider status.

### 2. Agent Layer (`app/agent/`)
`orchestrator.py` drives a ReAct-style loop with two execution paths:
- **LLM path** — sends conversation history + tool schemas to Claude (Anthropic) or OpenAI; model picks tools natively.
- **Heuristic fallback** — keyword-based router that works without any API key; deterministic.

Three tools the agent can invoke:
- `policy_retriever` — vector similarity search over ChromaDB
- `medicines_checker` — fuzzy lookup against the medicines SQL table
- `facility_checker` — fuzzy lookup against the facilities SQL table

### 3. Data Layer

**RAG pipeline** (`app/rag/`):
- `chunker.py` — splits markdown policy docs into section/paragraph chunks with metadata (source, category)
- `embedder.py` — wraps sentence-transformers (`all-MiniLM-L6-v2` by default)
- `vector_store.py` — ChromaDB persistent client
- `retriever.py` — similarity search with optional metadata filters

**SQL store** (`app/db/`): SQLAlchemy ORM over SQLite (default). Models: `User`, `Conversation`, `Message` (stores `tool_calls_json`), `Medicine`, `Facility`, `Feedback`. Admin user + seed data are created automatically on first startup.

**Fuzzy lookup** (`app/data_access/`): rapidfuzz substring matching over `medicines_db.py` and `facilities_db.py`.

### Cross-cutting concerns
- `app/auth/` — JWT (HS256) + bcrypt; Bearer token extraction; role-based access (user / admin)
- `app/middleware/` — sliding-window rate limiter (per IP and per user); request logging with `request_id` propagation
- `app/utils/` — structured logging setup; `retry_call` with exponential backoff for LLM calls
- `app/config.py` — Pydantic `BaseSettings` singleton; all configuration flows through here from `.env`

### Data files (raw inputs, committed)
- `backend/data/raw/policies/` — 5 markdown policy documents (the primary knowledge base)
- `backend/data/raw/medicines.csv` — NHIS medicines entitlements
- `backend/data/raw/facilities.csv` — accredited facilities directory
- `backend/data/raw/knowledge_base/` — extended KB (Word docs, CSVs, JSONL chunks)

Processed artifacts (`*.db`, `chroma/`) are gitignored and built by `scripts.ingest`.

## Key Design Decisions

- **Dual-mode agent**: the heuristic fallback means the API remains functional without LLM API keys, which matters for local testing and CI.
- **Lazy imports** of chromadb/sentence-transformers keep startup fast; unit tests that don't need the vector store don't pay the load cost.
- **`tool_calls_json`** on `Message` records the full tool trace so conversation history can replay agent reasoning.
- **Idempotent startup**: lifespan hook in `main.py` creates DB tables, seeds admin user, and loads seed CSVs if missing — no separate migration step needed for development.

## Environment Variables (key ones)

| Variable | Purpose |
|---|---|
| `LLM_PROVIDER` | `anthropic` or `openai` (default: `anthropic`) |
| `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` | LLM credentials; omit both to use heuristic fallback |
| `EMBEDDING_MODEL` | sentence-transformers model name |
| `CHROMA_PERSIST_DIR` | path to ChromaDB storage |
| `DATABASE_URL` | SQLAlchemy URL (default: SQLite at `data/processed/nhis.db`) |
| `JWT_SECRET_KEY` | signing key for auth tokens |
| `CORS_ORIGINS` | comma-separated allowed origins (`*` in dev) |
