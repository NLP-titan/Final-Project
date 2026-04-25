# Frontend

Reserved for the frontend developer. The backend exposes:

- `POST /api/chat` — `{ "message": "..." }` returns `{ answer, tool_calls, provider }`
- `GET /api/tools` — list of tool specs
- `POST /api/tools/call` — direct tool invocation `{ "name": "...", "arguments": {...} }`
- `GET /api/health`

CORS is open by default during development.
