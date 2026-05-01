# Handoff Document

**Read this before starting any new session.** It captures the current state of the project, what has been decided, what is in progress, and what needs answering before work continues.

---

## Current State (as of 2026-05-01)

### What exists
- `backend/` — FastAPI backend with RAG pipeline, agent orchestrator, auth, CRUD, rate limiting. **Now also includes:** `app/utils/vision.py`, `app/api/prescriptions_router.py`, `POST /api/medicines/identify`, `app/services/health_updates_scraper.py`, `scripts/geocode_facilities.py`, `scripts/refresh_health_updates.py`, env-driven prod hardening with `assert_production_safe()`, lightweight SQLite column migrations.
- `frontend/` — React + Vite SPA. **Now also includes:** `pages/CoverageCheckPage.jsx` (prescription + drug photo upload), updated `FacilitiesPage.jsx` (uses real lat/lng), updated `UpdatesPage.jsx` (admin "Refresh from sources" button + `Read More` external links), `.env.example`.
- `dummy.jsx` — Reference UI implementation. Visual target.
- `docs/NHIS Agent (1).md`, `docs/NHIS Agent.md`, `CLAUDE.md`, `description.md`, `SESSION_LOG.md`, `README.md` (now comprehensive).
- `docs/screenshots/` — Empty directory; user will populate.

### What has been decided
- Frontend stack: **React + Vite + Tailwind CSS + lucide-react** (matches dummy.jsx).
- Frontend lives in `frontend/` directory.
- Design reference: `dummy.jsx` — match its visual style exactly (color palette: #3454D1 blue, white, emerald accents; rounded cards; mobile-first).
- Backend stays untouched unless a field is genuinely missing and cannot be worked around.
- Chat must call the real backend (`POST /api/conversations/{id}/messages`), not Gemini.
- JWT tokens stored in localStorage; passed as `Authorization: Bearer <token>` header.

---

## Open Questions

1. **Anthropic API key was previously committed in `backend/.env`.** Still tracked by git (`.env` is in `.gitignore` but was committed before that rule). **User must:** revoke the key, regenerate, run `git rm --cached backend/.env && git commit`. Optionally `git filter-repo` to scrub history before making the repo public.
2. **Screenshot capture** — `docs/screenshots/` exists but is empty. README references 11 expected filenames (`01_landing.png` … `11_profile.png`). User needs to start both servers and capture them.
3. **Production database choice** — currently SQLite. README documents the switch to Postgres but `DATABASE_URL` in `.env` is still SQLite.
4. **GhanaWeb scraping is blocked** by their JS proof-of-work challenge wall and cannot be solved without a headless browser. The scraper detects the challenge page and skips. **MyJoyOnline Health RSS feed is used as the second source** — works cleanly, well-categorised by their CMS, gives 50 items per fetch.

---

## Architecture of the Frontend (planned)

```
frontend/
├── src/
│   ├── api/          # All fetch calls to backend (auth, chat, facilities, conversations)
│   ├── components/   # Reusable UI pieces (MessageBubble, FacilityCard, etc.)
│   ├── pages/        # One file per page (Landing, Login, Signup, Dashboard, Chat, etc.)
│   ├── context/      # AuthContext (JWT token + user state)
│   └── App.jsx       # Router
├── index.html
├── package.json
├── tailwind.config.js
└── vite.config.js
```

### Backend API base URL
`http://localhost:8000` (dev). Set via `VITE_API_BASE_URL` env var.

### Auth flow
1. `POST /api/auth/register` → get token
2. `POST /api/auth/login` → get token
3. Store token in localStorage
4. All subsequent requests: `Authorization: Bearer <token>`

### Chat flow
1. On first message, `POST /api/conversations` to create a conversation, get `id`
2. `POST /api/conversations/{id}/messages` with `{ "content": "..." }` → returns `{ user_message, assistant_message }` 
3. `assistant_message.tool_calls_json` contains the source info for attribution
4. `GET /api/conversations` to populate sidebar history

---

## Key Backend Endpoints the Frontend Uses

| Frontend action | Endpoint |
|---|---|
| Login | `POST /api/auth/login` |
| Register | `POST /api/auth/register` |
| Get current user | `GET /api/auth/me` |
| List conversations | `GET /api/conversations` |
| Create conversation | `POST /api/conversations` |
| Send message | `POST /api/conversations/{id}/messages` |
| Delete conversation | `DELETE /api/conversations/{id}` |
| List facilities | `GET /api/facilities` |
| Health check | `GET /api/health` |

---

## Coding Rules for This Project

- Match `dummy.jsx` visually — same color palette, same card styles, same rounded-2xl borders.
- Source attribution below every agent message is **non-negotiable** (parse from `tool_calls_json`).
- Do not add features beyond what the design brief specifies.
- Do not alter the backend unless Q1-B is chosen and it's the only way to persist profile data.
- Log every session in `SESSION_LOG.md` before closing.
- Update this file when open questions are resolved.
