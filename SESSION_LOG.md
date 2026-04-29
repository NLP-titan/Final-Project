# Session Log

All significant changes, decisions, and actions are recorded here with date and session summary.
Each entry should include: date, what was done, key decisions made, and any blockers/notes.

---

## 2026-04-29 — Session 2

**What was done:**

Backend changes:
- Added `phone`, `region`, `nhis_number`, `membership_type` columns to `User` model (`app/db/models.py`)
- Updated `UserRegister`, `UserOut`, `UserUpdate` schemas to include new fields (`app/auth/schemas.py`)
- Updated `register` and `PATCH /me` endpoints to persist new fields (`app/api/auth_router.py`)
- Added `HealthUpdate` and `Resource` ORM models (`app/db/models.py`)
- Created `app/api/health_updates_router.py` — CRUD for health updates (public reads, admin writes)
- Created `app/api/resources_router.py` — CRUD for resources (public reads, admin writes)
- Updated `app/db/init_db.py` to seed 6 health updates and 6 resources on first startup
- Registered both new routers in `app/main.py`

Frontend scaffold (`frontend/`):
- `package.json`, `vite.config.js`, `tailwind.config.js`, `postcss.config.js`, `index.html`
- API layer: `src/api/client.js`, `auth.js`, `conversations.js`, `facilities.js`, `healthUpdates.js`, `resources.js`
- Auth: `src/context/AuthContext.jsx` (JWT in localStorage, login/register/logout/updateUser)
- Pages: AuthLayout, DashboardLayout, DashboardPage, ChatPage, FacilitiesPage, UpdatesPage, ResourcesPage, ProfilePage
- Chat page uses real backend conversations (`POST /api/conversations`, `POST /api/conversations/{id}/messages`)
- Source attribution parsed from `tool_calls` on assistant messages
- Facilities page uses Leaflet + OpenStreetMap for map view
- All pages load real data from backend API
- Vite proxy: `/api` → `http://localhost:8000` (no CORS issues in dev)
- Build passes cleanly: `npm run build` ✓
- All modified Python files pass syntax check ✓

**Key decisions:**
- Used Vite proxy instead of hardcoded base URL — no env var needed in dev
- Source attribution extracted from `tool_calls[].output.chunks[0].metadata.source_file`
- Map view only shows facilities with lat/lng fields; facilities without coords appear in list only

**Status at end of session:**
- Backend changes complete, all syntax valid
- Frontend built and passes `npm run build`
- To run: start backend (`uvicorn app.main:app --reload` from `backend/`), then start frontend (`npm run dev` from `frontend/`)
- The database will auto-migrate on first run (SQLAlchemy `create_all`) — existing DBs need to be deleted and recreated OR columns added manually via SQLite CLI

**Known issue:**
- Existing SQLite DB (if present) will not have the new User columns until recreated. Delete `backend/data/processed/nhis.db` and restart backend to pick up the schema changes.

---

## 2026-04-29 — Session 1

**What was done:**
- Created `CLAUDE.md` at repo root with commands, architecture overview, key design decisions, and env var reference.
- Created `description.md` with full plain-English project description (what it is, how it works step by step, architecture, data sources, tech stack, evaluation framework).
- Audited `description.md` against the full codebase; filled in missing details: chunking strategy, agent guardrails, all 5 policy document names, full API surface, rate limiting specifics, request logging format, startup behaviour, eval category details, exponential backoff.
- Read design brief docs (`docs/NHIS Agent.md`, `docs/NHIS Agent (1).md`) and `dummy.jsx` reference implementation.
- Established session logging (`SESSION_LOG.md`), handoff document (`HANDOFF.md`), and updated `CLAUDE.md` to reference both.

**Key decisions:**
- `description.md` is the plain-English project explainer for non-technical readers.
- `HANDOFF.md` is the must-read for any new Claude Code session starting work.
- `SESSION_LOG.md` is append-only; oldest at bottom, newest at top.

**Status at end of session:**
- Documentation complete.
- Frontend implementation pending — awaiting answers to clarifying questions (see HANDOFF.md).
- Backend untouched.

**Blockers / open questions:**
- See HANDOFF.md § Open Questions section.
