# NHIS Assistant — Backend

Python backend for the NHIS chatbot. Implements:

1. **Knowledge base construction** — sample seed corpus for the NHIS Benefit Package, membership and renewal guidelines, member rights and dispute procedures, accreditation rules, and the NHIS Medicines List. Replaceable with the official source documents.
2. **RAG pipeline** — section-aware chunking, sentence-transformer embeddings, and a persistent ChromaDB vector store with metadata filtering by policy category.
3. **Agent tools** — `policy_retriever`, `medicines_checker`, `facility_checker`, all exposed both directly via HTTP and to the agent via Anthropic / OpenAI tool calling.
4. **Agent orchestrator** — ReAct-style loop with native tool-calling on Anthropic Claude (default) or OpenAI, plus a deterministic heuristic fallback so the API works without an API key.
5. **FastAPI server** — `/api/chat`, `/api/tools`, `/api/tools/call`, `/api/health`.

## Project layout

```
backend/
├── app/
│   ├── agent/
│   │   ├── orchestrator.py        # ReAct loop + heuristic fallback
│   │   ├── prompts.py
│   │   └── tools/                 # policy_retriever, medicines_checker, facility_checker
│   ├── api/routes.py              # FastAPI routes
│   ├── data_access/               # Pandas + rapidfuzz lookups for medicines & facilities
│   ├── rag/                       # chunker, embedder, vector_store, retriever
│   ├── config.py
│   └── main.py
├── data/
│   ├── raw/
│   │   ├── medicines.csv
│   │   ├── facilities.csv
│   │   └── policies/              # md/txt/pdf — drop NHIA source docs here
│   └── processed/                 # ChromaDB lives here (gitignored)
├── scripts/
│   ├── ingest.py                  # Build / refresh the vector store
│   └── eval_cases.py              # 30 evaluation cases across the 5 scenario categories
├── tests/
└── requirements.txt
```

## Setup

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env       # fill in your API key if you want LLM-driven answers
```

The first ingest will download the sentence-transformer model (~90 MB) once.

## Build the knowledge base

```bash
python -m scripts.ingest --reset
```

Drop additional `.md` / `.txt` / `.pdf` files into `data/raw/policies/` and re-run `ingest`. PDFs are extracted page-by-page; markdown files are chunked by heading.

## Run the API

```bash
uvicorn app.main:app --reload
# or:
python -m app.main
```

Endpoints (default `http://localhost:8000`):

| Method | Path             | Purpose                                   |
| ------ | ---------------- | ----------------------------------------- |
| POST   | `/api/chat`      | `{ "message": "..." }` → agent answer     |
| GET    | `/api/tools`     | List the three tool specs                 |
| POST   | `/api/tools/call`| `{ "name": "...", "arguments": {...} }`   |
| GET    | `/api/health`    | Provider, vector store size, model name   |

## Tools

| Tool              | When the agent calls it                                                       |
| ----------------- | ------------------------------------------------------------------------------ |
| policy_retriever  | Coverage / exclusions / enrolment / renewal / member rights / dispute steps    |
| medicines_checker | "Is this medicine covered?" — fuzzy lookup on `medicines.csv`                  |
| facility_checker  | "Is this hospital accredited?" — fuzzy lookup on `facilities.csv` with region  |

## Tests

```bash
pytest -q
```

The orchestrator tests use only the heuristic fallback, so no API key is required.

## Evaluation

```bash
python -m scripts.eval_cases
# or with the LLM
python -m scripts.eval_cases --provider anthropic
```

Runs 30 cases (6 per scenario category: coverage, drug entitlement, facility accreditation, membership/renewal, rights disputes) and prints tool-routing and answer-substring accuracy. Detailed JSON is written to `data/processed/eval_results.json`.

## Configuration

All settings live in `.env` (see `.env.example`). Key knobs:

- `LLM_PROVIDER` — `anthropic` or `openai`. If the corresponding key is missing, the orchestrator falls back to heuristic routing.
- `EMBEDDING_MODEL` — any sentence-transformer hub name; default is `all-MiniLM-L6-v2`.
- `CHROMA_PERSIST_DIR` / `CHROMA_COLLECTION` — where the vector store lives.
- `MEDICINES_CSV` / `FACILITIES_CSV` / `POLICIES_DIR` — point to alternate sources without code changes.

## Replacing the seed data

The seed CSVs and policy markdown files are clearly marked sample data. To use real NHIA data:

1. Drop the official PDFs / markdown into `data/raw/policies/`.
2. Replace `data/raw/medicines.csv` with the latest NHIS Medicines List (same column names).
3. Replace `data/raw/facilities.csv` with the latest accredited facilities directory (same column names).
4. Re-run `python -m scripts.ingest --reset`.
