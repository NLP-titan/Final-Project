# NHIS Assistant

> A retrieval-augmented, agentic web app that helps Ghanaian NHIS subscribers
> understand their coverage, find accredited facilities, and verify
> prescriptions — grounded in official NHIA policy documents and the 2025
> medicines formulary.

![Status: school project — final submission](https://img.shields.io/badge/status-final--project-blue)
![Stack](https://img.shields.io/badge/stack-FastAPI%20%2B%20React%20%2B%20Claude-3454D1)

---

## Table of contents

1. [Feature checklist](#feature-checklist)
2. [What it does](#what-it-does)
3. [Screenshots](#screenshots)
4. [Architecture](#architecture)
5. [Tech stack](#tech-stack)
6. [Repository layout](#repository-layout)
7. [Quick start (local development)](#quick-start-local-development)
8. [Configuration reference](#configuration-reference)
9. [API surface](#api-surface)
10. [Frontend pages](#frontend-pages)
11. [Knowledge base](#knowledge-base)
12. [Evaluation](#evaluation)
13. [Going live (production checklist)](#going-live-production-checklist)
14. [Operational scripts](#operational-scripts)
15. [Known limitations](#known-limitations)
16. [Future work](#future-work)
17. [Documents](#documents)

---

## Feature checklist

### Core
- [x] **Email + password authentication** with bcrypt + JWT (HS256)
- [x] **Role-based access** (`user` / `admin`) — admin endpoints gated by `Depends(require_admin)`
- [x] **Per-IP and per-user rate limiting** (sliding window, env-configurable)
- [x] **Structured request logging** with `request_id` propagation
- [x] **Idempotent startup** — DB schema, admin user, seed data created on first run
- [x] **Lightweight in-house migrations** for SQLite column adds (no Alembic dependency)

### Knowledge base & retrieval
- [x] 5 NHIA policy documents chunked + embedded (`sentence-transformers/all-MiniLM-L6-v2`) into ChromaDB
- [x] 222-row Essential Medicines List (2025 formulary) seeded into Postgres-compatible SQLite
- [x] 60-facility accredited directory seeded from the knowledge-base CSV
- [x] **Fuzzy match** lookups via `rapidfuzz.WRatio` for medicines + facilities (no exact-string-only)

### Agent
- [x] **ReAct-style orchestrator** — Claude tool-calls drive the loop, results feed back, capped by `AGENT_MAX_TOOL_ITERATIONS`
- [x] **Three tools**: `policy_retriever`, `medicines_checker`, `facility_checker`
- [x] **Heuristic fallback** — keyword router that works without any LLM key (CI-friendly)
- [x] **Multi-turn history** with capped replay (`AGENT_MAX_HISTORY_TURNS`)
- [x] **Persisted tool-call traces** (`Message.tool_calls_json`) so conversations re-render without re-running the agent
- [x] **Source attribution** in the chat UI (parsed from `tool_calls_json` per message)
- [x] **Exponential backoff retries** with jitter on every Claude call (env-configurable)

### Vision-powered features (Claude vision)
- [x] **Prescription analyzer** — `POST /api/prescriptions/analyze` accepts an image or PDF, extracts drugs (with dose + duration) and the prescribing facility, then runs both through the medicines/facility lookups
- [x] **Drug photo identifier** — `POST /api/medicines/identify` identifies a drug from a packaging/blister photo and reports coverage
- [x] Frontend single-page UI with two modes (Prescription / Drug photo), file preview, status badges, and structured result rendering
- [x] In-memory file handling (no PHI persisted), 8 MB upload cap

### Multilingual support — English + 3 Ghanaian languages
- [x] **Twi, Ga, and Ewe** runtime translation via Claude
- [x] **Language picker on signup** (4 buttons, native labels) — choice persists to backend
- [x] **Language switcher on Profile page** with hint text + loading indicator
- [x] **`/api/translate` and `/api/translate/batch`** endpoints (LRU-cached server-side)
- [x] **Refusal/length sanity check** in the translate utility — falls back to English on garbage output
- [x] **localStorage cache** keyed per-language so switching is instant after the first batch
- [x] **Per-user `language_preference`** column → agent answers translated automatically before persisting
- [x] Honest behaviour: drug names ('Paracetamol'), 'NHIS', and other technical terms intentionally kept in English

### Health updates
- [x] **Live scraper** for [Ghana Health Service](https://www.ghs.gov.gh/news-and-events) (HTML `<article>` blocks)
- [x] **Live scraper** for [MyJoyOnline Health](https://www.myjoyonline.com/news/health/) via clean RSS feed
- [x] **Idempotent dedup** by `source_url` (UNIQUE constraint)
- [x] **Admin-triggered refresh** via UI button + `POST /api/health-updates/refresh`
- [x] **Cron-friendly script** (`scripts/refresh_health_updates.py`)
- [x] **Graceful degradation** — Ghanaweb's JS challenge wall detected and skipped without errors

### Map & geocoding
- [x] **Leaflet + OpenStreetMap** facilities map with markers + popups
- [x] **Offline geocoder** with ~50 Ghanaian town centroids (instant, no API)
- [x] **Nominatim fallback** for unknown towns (rate-limited, polite UA)
- [x] **Auto-geocode on first startup** for known towns
- [x] **Click-to-directions** — every facility card and map popup deep-links to Google Maps with directions to its lat/lng (or a search by name + town when coords are missing); opens the Google Maps app on iOS/Android

### Other UX
- [x] **Conversation sidebar** with rename + delete (cascade)
- [x] **Resources library** with category cards + full-content reader
- [x] **Profile editor** for NHIS number, region, membership type, language, password
- [x] **Markdown rendering** of agent answers (lists, bold, code, headings)
- [x] **Mobile responsive** — Tailwind utility classes, `md:` / `sm:` breakpoints throughout

### Production readiness
- [x] `APP_ENV=production` mode that **refuses to start** with default JWT, default admin password, wildcard CORS, or SQLite
- [x] All knobs env-driven (rate limits, retry config, agent iteration cap, model names, embedding model, paths, CORS, ports)
- [x] Frontend `VITE_API_BASE_URL` and proxy target env vars for prod builds
- [x] `.env.example` files for both backend and frontend with prod-safety warnings
- [x] **38 of 40 backend tests pass** (the 2 failures are environmental — they assume no Anthropic key)

---

## What it does

NHIS Assistant is a single-page web app backed by a FastAPI service. A
logged-in user can:

- **Ask the agent** any NHIS question. The agent calls one of three tools
  (policy retriever, medicines checker, facility checker) and returns an
  answer with source attribution.
- **Find accredited facilities** on a list or interactive map of Ghana.
- **Check coverage from a prescription**: upload a photo or PDF of a
  prescription and the app will extract the prescribed drugs + facility name
  and tell you which drugs are NHIS-covered and whether the facility is
  accredited.
- **Identify a medicine from a photo**: upload a snapshot of medicine
  packaging or a blister pack — Claude vision identifies the drug, then the
  app checks whether NHIS covers it.
- **Browse health updates** pulled live from
  [Ghana Health Service](https://www.ghs.gov.gh/news-and-events) (HTML scrape)
  and [MyJoyOnline Health](https://www.myjoyonline.com/news/health/) (RSS).
  GhanaWeb was tried first but gates behind a JS proof-of-work challenge
  that requires a headless browser to defeat — out of scope for a school
  project.
- **Read curated resources** about NHIS rights, exclusions, dispute steps,
  enrollment, and the Essential Medicines List.
- **Use the app in Twi, Ga, or Ewe.** On signup the user picks a preferred
  language; the agent's replies and key UI labels are translated at runtime
  by Claude. Translations are cached per-language in localStorage so
  switching is instant after the first time.
- **Get directions to any facility** by tapping its card — opens Google
  Maps with turn-by-turn navigation (deep-links into the Google Maps app on
  iOS/Android).

---

## Screenshots

> _Add PNGs to `docs/screenshots/` with the filenames below — they will render
> automatically once committed._

| Page | Preview |
|---|---|
| Landing | ![Landing](docs/screenshots/01_landing.png) |
| Sign up | ![Sign up](docs/screenshots/02_signup.png) |
| Dashboard overview | ![Dashboard](docs/screenshots/03_dashboard.png) |
| Agent chat | ![Chat](docs/screenshots/04_chat.png) |
| Coverage check — prescription | ![Prescription analyzer](docs/screenshots/05_coverage_prescription.png) |
| Coverage check — drug photo | ![Drug photo identifier](docs/screenshots/06_coverage_drug_photo.png) |
| Facilities list | ![Facilities list](docs/screenshots/07_facilities_list.png) |
| Facilities map | ![Facilities map](docs/screenshots/08_facilities_map.png) |
| Health updates | ![Health updates](docs/screenshots/09_updates.png) |
| Resources | ![Resources](docs/screenshots/10_resources.png) |
| Profile | ![Profile](docs/screenshots/11_profile.png) |

---

## Architecture

```
              ┌──────────────────────────────────────────┐
              │              React + Vite UI             │
              │     localStorage JWT • Tailwind • Leaflet│
              └───────────────────────┬──────────────────┘
                                      │ HTTPS / fetch
                              ┌───────▼────────┐
                              │   FastAPI app  │
                              │  /api/* routes │
                              └───┬────┬───┬───┘
              ┌───────────────────┘    │   └─────────────────────┐
              │                        │                         │
       ┌──────▼──────┐         ┌───────▼────────┐        ┌───────▼─────────┐
       │   Agent     │         │  REST routers  │        │  Vision endpoints│
       │ orchestrator│         │ medicines /    │        │ /prescriptions/ │
       │ (ReAct loop)│         │ facilities /   │        │ analyze         │
       │             │         │ updates / etc. │        │ /medicines/     │
       │             │         │                │        │ identify        │
       └──┬───┬───┬──┘         └────────┬───────┘        └─────────┬───────┘
          │   │   │                     │                          │
   ┌──────▼┐  │   │             ┌───────▼────────┐         ┌───────▼───────┐
   │Policy │  │   │             │  SQLite / PG   │         │  Claude       │
   │vector │  │   │             │  (SQLAlchemy)  │         │  vision API   │
   │store  │  │   │             │  users • convs │         └───────────────┘
   │Chroma │  │   │             │  medicines     │
   └───────┘  │   │             │  facilities    │
       ┌──────▼┐  │             │  updates       │
       │Medi-  │  │             └────────────────┘
       │cines  │  │
       │fuzzy  │  │             ┌────────────────┐
       │match  │  │             │ Scraper        │
       └───────┘  │             │ ghs.gov.gh +   │
            ┌─────▼─┐           │ ghanaweb.com   │
            │Facil- │           └────────────────┘
            │ities  │
            │fuzzy  │
            └───────┘
```

The agent runs a ReAct-style loop: it sends the user's question and the tool
schemas to Claude, executes any tool calls Claude requests, feeds the results
back, and iterates until Claude produces a final answer (capped by
`AGENT_MAX_TOOL_ITERATIONS`). When no LLM key is configured, a heuristic
keyword router picks a tool — the API stays functional offline for testing.

---

## Tech stack

### Backend
- **FastAPI** + **Uvicorn** — async HTTP server
- **SQLAlchemy 2** + **SQLite** (dev) / **Postgres** (prod) — relational store
- **ChromaDB** + **sentence-transformers `all-MiniLM-L6-v2`** — vector search
- **Anthropic Claude `claude-sonnet-4-6`** — agent reasoning + vision
- **rapidfuzz** — fuzzy lookup for medicines / facilities
- **bcrypt** + **PyJWT** — auth
- **httpx** + **BeautifulSoup4 / lxml** — health-update scrapers

### Frontend
- **React 18** + **Vite 6**
- **Tailwind CSS** — utility styling, mobile-first
- **lucide-react** — icon set
- **react-leaflet** + **OpenStreetMap** — facilities map
- **react-markdown** — agent message rendering

### Tooling
- **pytest** for backend tests
- **ESLint** / **Prettier** (recommended; not committed)

---

## Repository layout

```
Final-Project/
├── backend/                    # FastAPI service
│   ├── app/
│   │   ├── agent/              # ReAct orchestrator + tool registry
│   │   ├── api/                # REST routers (auth, conversations, …,
│   │   │                       # prescriptions, medicines incl. /identify)
│   │   ├── auth/               # JWT + bcrypt + dependencies
│   │   ├── data_access/        # rapidfuzz fuzzy lookups
│   │   ├── db/                 # SQLAlchemy models + init/seed/migrations
│   │   ├── middleware/         # rate limiting + request logging
│   │   ├── rag/                # chunker, embedder, retriever, vector store
│   │   ├── services/           # health-update scraper
│   │   └── utils/              # logging, retry, vision helper
│   ├── data/raw/               # source CSVs + policy markdown + KB
│   ├── scripts/                # ingest, eval, geocoding, scraper cron
│   └── tests/                  # pytest suite
├── frontend/                   # React + Vite SPA
│   ├── src/
│   │   ├── api/                # fetch wrappers (incl. multipart upload)
│   │   ├── context/            # AuthContext (JWT in localStorage)
│   │   └── pages/              # one component per page
│   ├── vite.config.js          # dev proxy for /api → backend
│   └── .env.example
├── docs/                       # design briefs, screenshots
├── CLAUDE.md                   # session protocol for Claude Code
├── HANDOFF.md                  # current state & open questions
├── SESSION_LOG.md              # append-only session journal
└── README.md                   # this file
```

---

## Quick start (local development)

### Prerequisites

- Python ≥ 3.10
- Node.js ≥ 18 + npm
- An [Anthropic API key](https://console.anthropic.com) (optional but
  recommended — vision features and the LLM-graded agent require it)

### 1. Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env — at minimum set ANTHROPIC_API_KEY if you want vision/LLM features.

python -m scripts.ingest --reset            # build the policy vector store
python -m scripts.geocode_facilities        # backfill facility coords (~1 min)
uvicorn app.main:app --reload               # → http://localhost:8000
```

Visit `http://localhost:8000/docs` for the interactive Swagger UI.

### 2. Frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev                                  # → http://localhost:5173
```

Vite proxies `/api/*` to the backend on port 8000 — no CORS work needed in
dev. Sign up on the landing page to create your first user (the system also
auto-creates an admin from `INITIAL_ADMIN_*`).

### 3. (Optional) Populate live health updates

```bash
cd backend
python -m scripts.refresh_health_updates --limit 15
```

This scrapes Ghana Health Service and GhanaWeb Health and stores new posts in
the `health_updates` table. The Updates page will show them immediately. Run
on cron (e.g. every 6 hours) for ongoing freshness; admins can also click
**Refresh from sources** in the UI.

---

## Configuration reference

All backend config lives in `.env` and is parsed by `app/config.py`. Key
variables:

| Variable | Purpose | Default |
|---|---|---|
| `APP_ENV` | `development` or `production` (prod mode validates secrets) | `development` |
| `LLM_PROVIDER` | `anthropic` or `openai` | `anthropic` |
| `ANTHROPIC_API_KEY` | Required for LLM mode + vision | _(empty)_ |
| `ANTHROPIC_MODEL` | Claude model id | `claude-sonnet-4-6` |
| `EMBEDDING_MODEL` | sentence-transformers model | `all-MiniLM-L6-v2` |
| `CHROMA_PERSIST_DIR` | Vector store path | `./data/processed/chroma` |
| `DATABASE_URL` | SQLAlchemy URL | SQLite at `data/processed/app.db` |
| `JWT_SECRET` | Signing key — **must change for prod** | _dev placeholder_ |
| `INITIAL_ADMIN_EMAIL` / `_PASSWORD` | Auto-created on first run | `admin@example.com` / `changeme123` |
| `RATE_LIMIT_PER_MINUTE` | Per-IP global rate cap | `60` |
| `RATE_LIMIT_CHAT_PER_MINUTE` | Per-IP chat cap | `20` |
| `AGENT_MAX_TOOL_ITERATIONS` | ReAct loop cap | `4` |
| `AGENT_MAX_HISTORY_TURNS` | Prompt history cap | `10` |
| `LLM_RETRY_*` | Retry attempts / delays | `3` / `0.5s` / `4.0s` |
| `CORS_ORIGINS` | Comma-separated origins (`*` only in dev) | `*` |

Frontend config (`frontend/.env.local` for dev overrides, build-time env vars
for prod):

| Variable | Purpose | Default |
|---|---|---|
| `VITE_API_PROXY_TARGET` | Dev proxy target for `/api` | `http://localhost:8000` |
| `VITE_API_BASE_URL` | Absolute API base for production builds | _(empty → same-origin `/api`)_ |
| `VITE_API_TIMEOUT_MS` | Fetch timeout | `60000` |
| `VITE_DEV_PORT` | Vite dev port | `5173` |

---

## API surface

All routes are under `/api`. Public reads are unauthenticated; writes and
analyzers require a JWT.

### Auth & user
- `POST /auth/register` — create a user, returns JWT
- `POST /auth/login` — authenticate, returns JWT
- `GET /auth/me` — current user
- `PATCH /auth/me` — update profile (phone, region, NHIS number, …)
- `GET /users` (admin) — list users

### Conversations & chat
- `POST /conversations` — start a conversation
- `GET /conversations` — list conversations for the current user
- `GET /conversations/{id}` — full message history
- `POST /conversations/{id}/messages` — send a message; returns user + agent
  messages (`tool_calls_json` carries the agent's reasoning trace)
- `DELETE /conversations/{id}` — delete with cascade

### Reference data (public reads, admin writes)
- `GET /medicines` / `POST` / `PATCH /{id}` / `DELETE /{id}`
- `GET /facilities` / `POST` / `PATCH /{id}` / `DELETE /{id}`
- `GET /policies` (admin uploads + reindex)

### Coverage check (vision-powered)
- `POST /prescriptions/analyze` — multipart upload (image or PDF). Returns
  per-drug coverage + facility accreditation status.
- `POST /medicines/identify` — multipart upload (image). Returns identified
  drug + coverage status.

### Health updates & resources
- `GET /health-updates` — list (filter by `category`)
- `POST /health-updates/refresh` (admin) — scrape GHS + MyJoyOnline
- `POST /health-updates` (admin) / `PATCH /{id}` / `DELETE /{id}`
- `GET /resources` / `POST /resources` (admin) / `PATCH /{id}` / `DELETE /{id}`

### Translation
- `GET /translate/languages` — list supported languages (en, tw, gaa, ee)
- `POST /translate` — translate a single string
- `POST /translate/batch` — translate up to 200 strings (used by the
  frontend on language change)

### Feedback
- `POST /feedback` — thumbs-up/down + optional comment on a message
- `GET /feedback` (admin) — review queue

### Health
- `GET /health` — DB / vector store / LLM provider status

The full schema is at `http://localhost:8000/docs`.

---

## Frontend pages

| Tab | Source | Description |
|---|---|---|
| Overview | `pages/DashboardPage.jsx` | Greeting card, stats, quick actions |
| Agent Chat | `pages/ChatPage.jsx` | Real-time chat with the agent + sidebar history |
| Coverage Check | `pages/CoverageCheckPage.jsx` | Prescription analyzer + drug photo identifier |
| Facilities | `pages/FacilitiesPage.jsx` | Filterable list + Leaflet map of accredited facilities |
| Health Updates | `pages/UpdatesPage.jsx` | News from GHS + GhanaWeb (admin can refresh from UI) |
| Resources | `pages/ResourcesPage.jsx` | Curated explainer cards |
| Profile | `pages/ProfilePage.jsx` | NHIS number, region, membership type editor |

Auth flow: `AuthLayout.jsx` shows landing / login / signup; once
authenticated, `DashboardLayout.jsx` becomes the shell. JWT is stored in
`localStorage` under `nhis_token` and attached as `Authorization: Bearer …`
to every request.

---

## Knowledge base

The agent grounds its policy answers in the following sources, all under
`backend/data/raw/`:

- `policies/` — five Markdown documents derived from NHIA-published material
  (Act, regulations, benefit package summary, dispute mechanisms, Essential
  Medicines List overview). Chunked at the section / paragraph level into the
  Chroma collection by `scripts.ingest`.
- `medicines.csv` — small in-repo seed; the real source is the formulary
  CSV in `knowledge_base/database/nhis_medicines_formulary_2025.csv`.
- `facilities.csv` + `knowledge_base/database/nhis_hospitals.csv` — the
  accredited facilities directory. The init step prefers the larger KB CSV.
- `knowledge_base/` — Betty's curated KB package (Word docs, JSONL chunks).

---

## Evaluation

Run the test-case battery:

```bash
cd backend
python -m scripts.eval_cases                         # heuristic mode
python -m scripts.eval_cases --provider anthropic    # LLM-graded mode
```

This evaluates 30 synthetic questions across five categories (coverage, drug
entitlement, facility accreditation, membership/renewal, rights & disputes)
and reports tool-routing accuracy plus answer-substring match rate.

For unit tests:

```bash
cd backend
pytest -q
```

---

## Going live (production checklist)

> The current repo ships in a developer-friendly mode. Promoting to a public
> deployment requires the following steps. The backend will **refuse to
> start** with `APP_ENV=production` while any default secret is in place.

1. **Rotate any leaked credentials.**
   - The Anthropic API key in `backend/.env` was committed in an earlier
     iteration — go to console.anthropic.com → revoke → create a new key.
   - Run `git rm --cached backend/.env && git commit -m "stop tracking .env"`
     to untrack the file (it is already in `.gitignore`).
   - For full hygiene, scrub from history with
     [`git-filter-repo`](https://github.com/newren/git-filter-repo) before
     making the repo public.

2. **Generate a real `JWT_SECRET`.**
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(48))"
   ```

3. **Switch the database.** SQLite is fine for one user; use Postgres for
   anything public. Set `DATABASE_URL=postgresql+psycopg://…`. Run any
   pending migrations (this project ships a tiny in-house migration runner
   for column adds — see `app/db/init_db.py:_apply_lightweight_migrations`).

4. **Set a real CORS allow-list.**
   `CORS_ORIGINS=https://app.example.com,https://admin.example.com`.

5. **Build the frontend with the production API URL.**
   ```bash
   VITE_API_BASE_URL=https://api.example.com npm run build
   ```
   Serve `frontend/dist/` from any static host (Cloudflare Pages, Netlify,
   Vercel, S3 + CloudFront, …). If frontend and backend share a hostname,
   leave `VITE_API_BASE_URL` empty and the SPA will use a same-origin
   `/api` path.

6. **Pick a backend host.** Easiest paths for this stack:
   - **Render** — Docker or native Python; persistent disk for ChromaDB
   - **Railway** / **Fly.io** — same idea; mind the volume for the vector
     store
   - **AWS ECS / GCP Cloud Run** — containerised; mount EFS / Filestore for
     `CHROMA_PERSIST_DIR`

7. **Add HTTPS** (your hosting provider usually handles this) and **enforce
   `Secure` cookies if you ever switch JWT to cookies**.

8. **Schedule the health-updates scraper.**
   ```cron
   0 */6 * * * /path/to/.venv/bin/python -m scripts.refresh_health_updates
   ```

9. **Monitor.** Hook structured logs into your provider; alert on
   `request_log.WARNING+` and the `unhandled` exception path in
   `app/main.py`.

10. **Backups.** If you stay on SQLite, snapshot
    `backend/data/processed/app.db` daily; on Postgres, use the provider's
    point-in-time backups.

---

## Operational scripts

| Script | Purpose |
|---|---|
| `python -m scripts.ingest --reset` | Chunk policy markdown → embed → upsert to Chroma |
| `python -m scripts.geocode_facilities` | Backfill `lat`/`lng` (offline lookup + Nominatim fallback) |
| `python -m scripts.refresh_health_updates --limit 20` | Scrape GHS + GhanaWeb |
| `python -m scripts.eval_cases [--provider anthropic]` | Run the 30-case eval |
| `python -m scripts.seed_from_knowledge_base` | Re-seed structured tables from the KB package |

---

## Known limitations

- **SQLite in dev only.** No connection pooling, single-writer locking. For
  any concurrent traffic switch to Postgres.
- **Drug-photo identification accuracy.** Claude vision identifies medicines
  reliably from boxes / blister packs / labels with visible text. **Loose
  unbranded pills cannot be identified from a photo alone** — the response
  flags low confidence in those cases. This is a hard limit of the input,
  not the model.
- **Prescription OCR.** Quality is bounded by photo legibility. The endpoint
  returns a `confidence` field and explicit `notes` so the UI can warn when
  extraction is shaky. Handwriting on poor-resolution images may yield
  partial results.
- **Scraper fragility.** GHS doesn't expose an API; the scraper parses the
  `<article>` blocks on the news listing. Site redesigns will require an
  update to `app/services/health_updates_scraper.py` (failure mode is
  graceful — the table simply doesn't get new rows). MyJoyOnline is fed
  via RSS, which is more stable.
- **GhanaWeb is blocked.** GhanaWeb's health section gates every request
  behind a JavaScript proof-of-work challenge ("Challenge Validation"). A
  plain HTTP scraper can't solve it; you'd need Playwright / Selenium with
  a real browser. The scraper detects the challenge page and skips
  gracefully — MyJoyOnline covers the same news beat from a different angle.
- **No PHI safeguards.** Prescription uploads are processed in-memory and
  not stored, but neither are they encrypted at rest in any meaningful sense
  during processing. Don't use this with real patient data without a HIPAA /
  GDPR review.
- **Map coverage is town-level.** Facility coordinates resolve to the
  centroid of the town — they're suitable for "find a city" not "find an
  address". For street-level accuracy you'd need a paid geocoder.
- **Translation quality varies by language.** Twi gets the best output
  (Claude has the most training signal). Ga and Ewe are reasonable for
  short UI labels but can be uneven on longer sentences. Medical
  terminology (drug names, "NHIS") is intentionally kept in English — that's
  how Ghanaian Twi/Ga/Ewe speakers actually use these terms in practice.
  The translated UI is for accessibility and onboarding, not authoritative
  medical advice — that responsibility stays with the underlying English
  knowledge base.

---

## Future work

- Hand-curated coordinates for major hospitals (rather than town centroids)
- Multi-language support (Twi, Ga, Ewe — at least UI labels)
- Patient-facing SMS / USSD shim that hits the same `/api/conversations`
- A dedicated medicine-image dataset to fine-tune offline identification
- Push-notification when a new health-update of category "Disease Alerts"
  matches the user's region

---

## Documents

- [`CLAUDE.md`](CLAUDE.md) — Claude Code session protocol & architecture brief
- [`HANDOFF.md`](HANDOFF.md) — current state, open questions, decisions log
- [`SESSION_LOG.md`](SESSION_LOG.md) — append-only session journal
- [`description.md`](description.md) — plain-English project explainer
- [`docs/NHIS Agent.md`](docs/NHIS%20Agent.md) — technical build checklist
- [`docs/NHIS Agent (1).md`](docs/NHIS%20Agent%20%281%29.md) — full product / system design brief
- [`backend/README.md`](backend/README.md) — backend-only deep dive
- [`RESEARCH_REPORT.md`](RESEARCH_REPORT.md) — academic write-up

---

## License

Educational / academic use. Built as a final project for the Ashesi University
NLP course.
