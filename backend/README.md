# NHIS Assistant — Backend

Python backend for the NHIS chatbot. Implements:

1. **Knowledge base construction** — sample seed corpus for the NHIS Benefit Package, membership and renewal guidelines, member rights and dispute procedures, accreditation rules, and the NHIS Medicines List. Replaceable with the official source documents.
2. **RAG pipeline** — section-aware chunking, sentence-transformer embeddings, and a persistent ChromaDB vector store with metadata filtering by policy category.
3. **Agent tools** — `policy_retriever`, `medicines_checker`, `facility_checker`, exposed both directly via HTTP and to the agent via Anthropic / OpenAI tool calling.
4. **Agent orchestrator** — ReAct-style loop with native tool-calling on Anthropic Claude (default) or OpenAI, with retry-on-failure plus a deterministic heuristic fallback so the API works without an API key.
5. **Persistent storage** — SQLite/SQLAlchemy with users, conversations, messages (including persisted tool-call traces), feedback, medicines, facilities, and policy documents.
6. **Auth** — bcrypt + JWT with `user` / `admin` roles. Initial admin auto-created on startup.
7. **CRUD APIs** — full create/read/update/delete for medicines, facilities, conversations, policy documents, plus user management for admins and feedback capture for any user.
8. **Robustness** — request logging, sliding-window rate limiting (global + chat-specific), exponential-backoff retries on LLM calls, validation/integrity/unhandled exception handlers, request-id propagation, and a `/health` endpoint that probes both the DB and the vector store.

## Project layout

```
backend/
├── app/
│   ├── agent/
│   │   ├── orchestrator.py        # ReAct loop + retries + heuristic fallback
│   │   ├── prompts.py
│   │   └── tools/                 # policy_retriever, medicines_checker, facility_checker
│   ├── api/
│   │   ├── auth_router.py         # /auth/register, /auth/login, /auth/me
│   │   ├── users_router.py        # /users (admin)
│   │   ├── medicines_router.py    # /medicines CRUD
│   │   ├── facilities_router.py   # /facilities CRUD
│   │   ├── conversations_router.py # /conversations + persisted /chat
│   │   ├── policies_router.py     # /policies upload / reingest (admin)
│   │   ├── feedback_router.py     # /messages/{id}/feedback + /admin/feedback
│   │   └── routes.py              # /tools, /tools/call (admin), /health, /
│   ├── auth/                      # JWT, hashing, dependencies
│   ├── db/                        # SQLAlchemy models, engine, init_db
│   ├── data_access/               # Fuzzy lookups against the DB
│   ├── middleware/                # request logging, rate limiting
│   ├── rag/                       # chunker, embedder, vector_store, retriever
│   ├── utils/                     # logging, retry-with-backoff
│   ├── config.py
│   └── main.py
├── data/
│   ├── raw/                       # CSV + policy markdown seeds
│   └── processed/                 # SQLite + ChromaDB live here (gitignored)
├── scripts/
│   ├── ingest.py                  # Build / refresh the vector store
│   └── eval_cases.py              # 29 KB-sourced eval cases + LLM-as-judge
├── tests/                         # 40 tests covering tools, auth, CRUD, chat, rate limit, retry
└── requirements.txt
```

## Setup

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env       # adjust JWT_SECRET, INITIAL_ADMIN_PASSWORD, optional API keys
```

The first ingest will download the sentence-transformer model (~90 MB) once.

## Build the knowledge base

```bash
python -m scripts.ingest --reset
```

Drop additional `.md` / `.txt` / `.pdf` files into `data/raw/policies/` and re-run `ingest`. Admins can also upload via `POST /api/policies` and trigger reindexing via `POST /api/policies/reingest`.

## Run the API

```bash
uvicorn app.main:app --reload
# or:
python -m app.main
```

On first startup the app creates the SQLite DB, seeds medicines/facilities from CSV, and creates the initial admin (`INITIAL_ADMIN_EMAIL` / `INITIAL_ADMIN_PASSWORD`). Subsequent startups are idempotent.

## API surface

All routes are prefixed `/api`.

### Auth
| Method | Path           | Auth   | Description                                  |
| ------ | -------------- | ------ | -------------------------------------------- |
| POST   | /auth/register | public | Create user + return JWT                     |
| POST   | /auth/login    | public | Login + return JWT                           |
| GET    | /auth/me       | bearer | Current user                                 |
| PATCH  | /auth/me       | bearer | Update name and/or password                  |
| POST   | /auth/logout   | bearer | No-op (stateless JWT — clients drop the token) |

### Chat / Conversations
| Method | Path                                  | Auth   | Description                                          |
| ------ | ------------------------------------- | ------ | ---------------------------------------------------- |
| POST   | /chat                                 | optional | Stateless one-shot — `{ "message": "..." }`         |
| GET    | /conversations                        | bearer | List my conversations                                |
| POST   | /conversations                        | bearer | Create a conversation                                |
| GET    | /conversations/{id}                   | bearer | Conversation + messages                              |
| PATCH  | /conversations/{id}                   | bearer | Rename                                               |
| DELETE | /conversations/{id}                   | bearer | Delete (cascades messages and feedback)              |
| POST   | /conversations/{id}/messages          | bearer | Post a user message; returns assistant reply too     |
| POST   | /messages/{id}/feedback               | bearer | Submit / update feedback on an assistant message     |
| GET    | /admin/feedback                       | admin  | List all feedback (for evaluation)                   |

### Resource CRUD
| Method | Path                                  | Auth   |
| ------ | ------------------------------------- | ------ |
| GET    | /medicines, /medicines/{id}           | public |
| POST/PATCH/DELETE | /medicines, /medicines/{id} | admin  |
| GET    | /facilities, /facilities/{id}         | public |
| POST/PATCH/DELETE | /facilities, /facilities/{id} | admin |
| GET    | /policies                             | admin  |
| POST   | /policies (multipart upload)          | admin  |
| DELETE | /policies/{id}                        | admin  |
| POST   | /policies/reingest                    | admin  |
| GET    | /users, /users/{id}                   | admin  |
| PATCH/DELETE | /users/{id}                     | admin  |

### Tools / health
| Method | Path             | Auth   | Description                                |
| ------ | ---------------- | ------ | ------------------------------------------ |
| GET    | /tools           | public | List the three tool specs                  |
| POST   | /tools/call      | admin  | Direct tool invocation (bypasses agent)    |
| GET    | /health          | public | DB + vector store + provider status        |

## Tools

| Tool              | When the agent calls it                                                       |
| ----------------- | ------------------------------------------------------------------------------ |
| policy_retriever  | Coverage / exclusions / enrolment / renewal / member rights / dispute steps    |
| medicines_checker | "Is this medicine covered?" — fuzzy lookup on the medicines table              |
| facility_checker  | "Is this hospital accredited?" — fuzzy lookup on the facilities table          |

## Tests

```bash
pytest -q
```

40 tests cover the chunker, the three tools, orchestrator routing, auth, medicines/facilities CRUD, conversation persistence, feedback, rate limiting and retry utilities.

## Evaluation

```bash
python -m scripts.eval_cases                              # heuristic fallback, no LLM judge
python -m scripts.eval_cases --provider openai            # LLM agent + LLM judge
python -m scripts.eval_cases --provider openai \
    --judge-model openai/gpt-4o                           # override judge model at runtime
```

Runs 29 cases built from the knowledge base itself:

| Source | Cases | Check |
|---|---|---|
| `medicines.csv` | 6 (3 covered, 3 not-covered) | Hard ground-truth match |
| `facilities.csv` | 6 (5 accredited, 1 not-accredited) | Hard ground-truth match |
| `data/raw/policies/*.md` | 17 (6 coverage, 6 enrollment, 5 disputes) | LLM-as-judge (score 1–3, pass ≥ 2) |

Reports **tool routing accuracy** and **answer correctness** overall and per category. For policy cases the per-category average judge score is also printed.

The judge model is configured independently of the agent model to avoid self-grading — set `JUDGE_MODEL` in `.env` (e.g. `JUDGE_MODEL=openai/gpt-4o`). Both route through OpenRouter using `OPENAI_API_KEY`.

Detailed JSON is written to `data/processed/eval_results.json`; generated cases are saved to `data/processed/eval_cases_generated.json` for inspection.

## Configuration

All settings live in `.env` (see `.env.example`). Highlights:

- `LLM_PROVIDER` — `anthropic` or `openai`. Missing key → heuristic fallback.
- `JUDGE_MODEL` — OpenRouter model string for the eval LLM judge (e.g. `openai/gpt-4o`). Should differ from the agent model to avoid self-grading.
- `DATABASE_URL` — defaults to SQLite at `data/processed/app.db`. Any SQLAlchemy URL works (PostgreSQL, etc.).
- `JWT_SECRET` — change in production. Tokens expire after `JWT_EXPIRES_MINUTES`.
- `INITIAL_ADMIN_EMAIL` / `INITIAL_ADMIN_PASSWORD` — auto-created admin on first boot.
- `RATE_LIMIT_PER_MINUTE` / `RATE_LIMIT_CHAT_PER_MINUTE` — sliding-window per-IP / per-user limits.
- `EMBEDDING_MODEL` — any sentence-transformer hub name; default `all-MiniLM-L6-v2`.
- `CHROMA_PERSIST_DIR` / `CHROMA_COLLECTION` — vector store paths.
- `MEDICINES_CSV` / `FACILITIES_CSV` / `POLICIES_DIR` — seed sources used on first startup.

## Replacing the seed data

The CSVs and policy markdown files are clearly marked sample data. To use real NHIA data:

1. Drop the official PDFs / markdown into `data/raw/policies/` (or upload via `/api/policies`).
2. Replace `data/raw/medicines.csv` with the latest NHIS Medicines List, or use the medicines CRUD API.
3. Replace `data/raw/facilities.csv` with the latest accredited facilities directory, or use the facilities CRUD API.
4. Re-run `python -m scripts.ingest --reset` (or `POST /api/policies/reingest?reset=true` as admin).
