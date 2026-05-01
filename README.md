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

`python -m scripts.eval_cases` builds 29 evaluation cases directly from the knowledge base (medicines.csv, facilities.csv, and the policy markdown files) and runs them against the agent.

Two metrics are reported per category:

- **Tool routing accuracy** — was the correct tool invoked?
- **Answer correctness** — for medicines/facilities, a hard ground-truth check against the CSV; for policy questions, an LLM-as-judge score (1–3) against the actual source section, with ≥ 2 counting as a pass.

The judge uses a separately configured model (`JUDGE_MODEL` in `.env`) so it is independent of the agent model being evaluated.
