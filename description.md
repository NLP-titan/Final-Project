# NHIS Assistant — Project Description

## What It Is

A retrieval-augmented chatbot for Ghana's **National Health Insurance Scheme (NHIS)**. Users ask questions in plain English — *"Is dialysis covered?"*, *"Is Korle Bu Teaching Hospital accredited?"*, *"How do I renew my NHIS card?"* — and receive accurate, cited answers grounded in real NHIA source documents and structured data.

---

## The Problem It Solves

NHIS policy documents are dense and scattered across multiple sources. An ordinary user cannot easily find out:

- Which medicines are covered under the scheme
- Which hospitals and clinics accept NHIS
- What their rights are if they are denied treatment
- How to register or renew their membership

This system makes all of that information instantly queryable in conversational English, without needing to read through official PDFs or visit a district office.

---

## Architecture Overview

```
User / Frontend
      ↓ HTTP
FastAPI Server  ←→  SQLite DB (users, conversations, messages, medicines, facilities)
      ↓
Agent Orchestrator
      ↓ picks tools dynamically
 ┌────────────────────────────────────────────────┐
 │  policy_retriever  →  ChromaDB  (vector search) │
 │  medicines_checker →  SQLite    (fuzzy lookup)  │
 │  facility_checker  →  SQLite    (fuzzy lookup)  │
 └────────────────────────────────────────────────┘
```

---

## How It Works — Step by Step

### Step 1: Building the Knowledge Base (offline, run once)

Before the server starts, an ingestion script (`scripts/ingest.py`) processes the source documents:

1. Five **NHIS policy documents** are split into focused chunks using a **markdown-aware hierarchical chunker** that splits on heading levels (`#`, `##`, `###`) first, then falls back to paragraph boundaries if no headings exist.
2. Chunks are capped at a **soft limit of 1,200 characters** and a **hard limit of 2,000 characters**. Long sections are always split on paragraph boundaries — never mid-sentence.
3. Each chunk carries metadata: `source_file`, `section` heading, and `page` (for PDF sources). YAML frontmatter in documents is parsed and attached automatically.
4. Chunks are **embedded** — converted into numerical vectors that capture semantic meaning — using a sentence-transformers model (`all-MiniLM-L6-v2`).
5. Those vectors are stored in **ChromaDB** with metadata for category-filtered retrieval.

This becomes the searchable library the chatbot draws from. PDFs are also supported via lazy-loaded `pypdf`.

### Step 2: A User Sends a Message

The user sends a message to the API — e.g. *"Is Metformin covered by NHIS?"* — either as a one-shot request (`POST /api/chat`) or within a persistent conversation that retains history across turns.

### Step 3: The Agent Decides What to Do

The agent orchestrator (`app/agent/orchestrator.py`) runs a **ReAct loop** — it reasons about the question, acts by calling a tool, reads the result, and reasons again. It has three tools available:

| Tool | What it does |
|---|---|
| `policy_retriever` | Semantic search over ChromaDB — finds policy text by meaning, not just keywords. Supports filtering by policy category. |
| `medicines_checker` | Fuzzy name lookup in the NHIS medicines database (e.g. "metformin" matches "Metformin 500mg Tablet") |
| `facility_checker` | Fuzzy name lookup in the accredited hospitals/clinics database |

The agent **must call at least one tool** before making any coverage, formulary, or accreditation claim. It can call multiple tools in sequence (up to 4 iterations per question) for multi-part questions. Answers are cited by source filename (e.g. `01_benefits_package.md`), kept to 2–6 sentences in plain English, and the agent never invents specific figures like premiums, tariffs, or phone numbers.

### Step 4: Two Execution Modes

**LLM Mode** — with an API key (Anthropic Claude or OpenAI):
> The question and tool results are sent to the LLM. The model decides which tools to call, reads their outputs, and writes a natural language answer. This path is intelligent, flexible, and handles nuanced or multi-part questions. LLM calls use **exponential backoff** with up to 3 retry attempts before failing.

**Heuristic Fallback** — no API key required:
> A deterministic keyword router routes the question to the most appropriate tool. Words like "medicine", "drug", or "tablet" trigger the medicines checker; "hospital" or "clinic" triggers the facility checker; enrollment keywords ("renew", "register", "premium") and dispute keywords ("turned away", "denied", "complaint") steer the policy retriever to the right category. Always works, less nuanced.

If the LLM call fails (network error, rate limit, etc.), the system **automatically falls back** to the heuristic path so the API never goes fully down.

### Step 5: The Answer Is Stored

Every message — user and assistant — is persisted to SQLite along with the full tool call trace (which tools were called, with what inputs, and what they returned). This means conversations have memory across sessions, and the reasoning behind every answer is auditable.

---

## The Data

Three real NHIS datasets are committed to the repository:

| Dataset | Description |
|---|---|
| **Medicines Formulary 2025** | Official list of drugs the NHIS covers, with coverage categories |
| **Accredited Facilities** | Directory of hospitals and clinics across Ghana that accept NHIS |
| **Policy Documents (×5)** | Authoritative NHIA rules (see below) |

### The Five Policy Documents

| File | Topic |
|---|---|
| `01_benefits_package.md` | Coverage rules, exclusions, and the full benefits package |
| `02_membership_and_renewal.md` | Registration, card renewal, activation, and membership tiers |
| `03_disputes_and_rights.md` | Member rights, complaint filing, and dispute resolution |
| `04_facilities_and_referral.md` | Facility accreditation and referral pathways |
| `05_medicines_formulary.md` | NHIS medicines list and coverage categories |

---

## API Surface

All routes are under `/api`. Authentication uses JWT Bearer tokens.

| Group | Key Endpoints | Auth |
|---|---|---|
| **Auth** | `POST /auth/register`, `/auth/login`, `GET /auth/me` | Public / Token |
| **Chat** | `POST /chat` (one-shot), `POST /conversations/{id}/messages` (persistent) | Token |
| **Conversations** | `GET/POST /conversations`, `PATCH/DELETE /conversations/{id}` | Token |
| **Medicines** | `GET/POST /medicines`, `PATCH/DELETE /medicines/{id}` | Token / Admin |
| **Facilities** | `GET/POST /facilities`, `PATCH/DELETE /facilities/{id}` | Token / Admin |
| **Policies** | `POST /policies/upload`, `POST /policies/reingest` | Admin |
| **Feedback** | `POST /feedback`, `GET /feedback` (admin review) | Token / Admin |
| **Tools** | `GET /tools` (spec list), `POST /tools/call` (direct invocation) | Admin |
| **Health** | `GET /health` | Public |

The health endpoint reports live status of the database, vector store, and LLM provider. It is always reachable — exempt from rate limiting.

---

## Middleware & Infrastructure

### Rate Limiting
A **sliding-window algorithm** (60-second window) enforces two separate limits:
- **Global limit** — applied to all requests
- **Chat-specific limit** — applied only to `/api/chat` and conversation message endpoints

Requests are bucketed by authenticated `user_id` if logged in, otherwise by `X-Forwarded-For` header, otherwise by IP address. When a limit is exceeded the API returns `429` with a `Retry-After` header. The health, docs, and OpenAPI endpoints are always exempt. Rate limit state is process-local (suitable for development; needs Redis for multi-process production).

### Request Logging & Tracing
Every request gets a `request_id` (taken from the `X-Request-Id` header if provided, otherwise a generated UUID). The access logger (`nhis.access`) writes one line per request:
```
rid={request_id} user={user_id} METHOD /path -> STATUS {duration_ms}ms
```
The `x-request-id` and `X-RateLimit-Remaining` headers are exposed to clients in CORS responses, making tracing possible from the frontend.

### Startup & Error Handling
On startup, a lifespan hook initialises the database, runs table creation, seeds an admin user (credentials from `.env`), and loads the medicines and facilities CSVs. If initialisation fails, the server continues and logs a warning rather than crashing — the API degrades gracefully.

Three exception handlers are registered:
- `RequestValidationError` → `422` with field-level detail
- `IntegrityError` (duplicate records) → `409 Conflict`
- Unhandled exceptions → `500` with the `request_id` for log correlation

---

## Evaluation Framework

`scripts/eval_cases.py` runs **30 test questions** across five categories (6 per category) and reports two metrics: **tool-routing accuracy** (did the agent call the right tool?) and **answer recall** (does the answer contain the expected substring?).

| Category | Example Questions |
|---|---|
| **Coverage** | Is dialysis covered? Is caesarean section free? Is IVF included? |
| **Medicines** | Is Paracetamol on the formulary? What about Insulin? Is Imatinib covered? |
| **Facilities** | Is Korle Bu accredited? What about Nyaho Clinic? Is Trust Hospital (Osu) on the list? |
| **Enrollment** | How do I renew my card? Can I renew via *929#? How long is the activation wait? |
| **Disputes** | What if I'm turned away without cash? How do I file a complaint? Can a facility charge me a co-payment? |

Results are written to `data/processed/eval_results.json`.

---

## Technology Stack

| Layer | Technology |
|---|---|
| Web framework | FastAPI + Uvicorn |
| Database | SQLAlchemy ORM over SQLite (PostgreSQL-compatible) |
| Vector store | ChromaDB (local, persistent) |
| Embeddings | sentence-transformers (`all-MiniLM-L6-v2`) |
| LLM providers | Anthropic Claude, OpenAI (both optional) |
| Fuzzy matching | rapidfuzz |
| Authentication | JWT (HS256) + bcrypt |
| PDF parsing | pypdf (lazy-loaded) |
| Testing | pytest (40+ tests) |

---

## What Makes This RAG

This project follows the **Retrieval-Augmented Generation** pattern: instead of relying on an LLM's training data (which may be outdated or hallucinated), the system first retrieves relevant facts from a trusted, curated source, then uses those facts to construct the answer.

The key design choices that make this more than a basic RAG demo:

- **Three specialised retrieval strategies** (vector search, medicines fuzzy lookup, facilities fuzzy lookup) with an agent that dynamically routes to the right one
- **Mandatory tool use** — the agent is instructed never to answer factual claims from memory alone
- **Heuristic fallback** — the system works without any LLM API key, making it testable and resilient
- **Markdown-aware chunker** — preserves document structure so retrieved chunks are coherent, self-contained, and attributable to a specific section
- **Full auditability** — every conversation stores the complete tool call trace, so every answer can be traced back to its source
