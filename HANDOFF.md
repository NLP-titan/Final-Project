# Handoff Document

**Read this before starting any new session.** It captures the current state of the project, what has been decided, what is in progress, and what needs answering before work continues.

---

## Current State (as of 2026-04-29)

### What exists
- `backend/` — Complete FastAPI backend with RAG pipeline, agent orchestrator, auth, CRUD, rate limiting. **Do not change without strong reason.**
- `frontend/` — Empty (only a README). **This is where the React frontend will live.**
- `dummy.jsx` — Reference UI implementation. This is the visual/UX target. It currently calls Gemini directly (not the backend) and uses all mock data. The goal is to build a proper React app that matches this design but connects to the FastAPI backend.
- `docs/NHIS Agent (1).md` — Full product and system design brief (8 pages, key user flows, architecture spec).
- `docs/NHIS Agent.md` — Technical build checklist.
- `CLAUDE.md` — Development reference (commands, architecture, env vars).
- `description.md` — Plain-English project explainer.
- `SESSION_LOG.md` — Running log of all sessions and changes.

### What has been decided
- Frontend stack: **React + Vite + Tailwind CSS + lucide-react** (matches dummy.jsx).
- Frontend lives in `frontend/` directory.
- Design reference: `dummy.jsx` — match its visual style exactly (color palette: #3454D1 blue, white, emerald accents; rounded cards; mobile-first).
- Backend stays untouched unless a field is genuinely missing and cannot be worked around.
- Chat must call the real backend (`POST /api/conversations/{id}/messages`), not Gemini.
- JWT tokens stored in localStorage; passed as `Authorization: Bearer <token>` header.

---

## Open Questions

All questions from the previous session have been answered and implemented. No open questions remain.

All questions resolved in Session 2 — see SESSION_LOG.md for details.

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
