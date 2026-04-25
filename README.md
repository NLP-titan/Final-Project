# NHIS Assistant

A retrieval-augmented chatbot that answers questions about Ghana's National Health Insurance Scheme (NHIS). It routes user questions to the right tool (policy retriever, medicines checker, or facility checker) and grounds its answers in NHIA source documents and structured directories.

## Architecture

```
User Message
     ↓
Agent (ReAct reasoning)
     ↓
Decides which tool to call
     ↙          ↓          ↘
Policy       Medicines    Facility
Retriever    Checker      Checker
(Vector DB)  (Structured) (Structured)
```

## Repository layout

- [`backend/`](backend/) — Python backend: knowledge base, RAG pipeline, agent tools and orchestrator, FastAPI server. See [backend/README.md](backend/README.md).
- [`frontend/`](frontend/) — Reserved for the frontend developer.

## Quick start

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env             # add ANTHROPIC_API_KEY for LLM mode (optional)
python -m scripts.ingest --reset # build the vector store from data/raw/policies/
uvicorn app.main:app --reload
```

Then `POST http://localhost:8000/api/chat` with `{ "message": "Is dialysis covered under NHIS?" }`.

## Evaluation

`python -m scripts.eval_cases` runs the 30 evaluation questions and reports tool-routing and answer-substring accuracy across the five scenario categories (coverage, drug entitlement, facility accreditation, membership/renewal, rights disputes).
