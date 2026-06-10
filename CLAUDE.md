# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A NotebookLM-style academic assistant ("學業輔助系統"). A student logs in, uploads
lecture notes (PDF/DOCX/TXT/MD), the backend parses + analyses them, then offers
"learning direction" cards (fixed + LLM-generated). Picking a direction opens a
streaming chat session scoped to that document. All UI copy is Traditional Chinese (zh-TW).

`agents.md` is the living design spec (in Chinese) and is the source of truth for
intended behaviour. `project.md` describes an **older, abandoned** "homework draft
generator" system — ignore it; it is being deleted.

## Commands

```bash
# Dev (backend :8002 with reload, frontend Vite :5173). Kills stale processes first.
./start-dev.sh

# Backend only (from backend/)
.venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8002

# Frontend (from frontend/)
npm run dev          # Vite dev server :5173, proxies /api → localhost:8002
npm run build        # tsc -b && vite build  — run this to type-check
npm run lint         # eslint

# Full stack via Docker (frontend :8001, backend :8002)
docker compose up --build
```

There is **no test suite**. "Verifying" means running the app and exercising the flow.
Backend Python deps are managed with the `.venv` in `backend/` (installed from `pyproject.toml`).

## Ports (easy to trip over)

| Context | Frontend | Backend |
|---|---|---|
| `start-dev.sh` / Vite dev | 5173 | 8002 |
| Docker Compose | 8001 | 8002 (→ container 8000) |
| Vite proxy + nginx | both forward `/api` → backend | — |

The backend always listens on `app.main:app`; the container maps 8000→8002.

## Architecture

Backend is **fully async** FastAPI + SQLAlchemy 2.0 (async engine) over SQLite
(`backend/data/app.db`). Layering is strict: `routers/` (HTTP + Pydantic schemas) →
`services/` (business logic) → `models/` (ORM) / `utils/`. ChromaDB and uploaded files
live in `backend/data/` (gitignored), not in SQLite.

Request lifecycle: `deps.get_current_user` reads the `session_token` httponly cookie →
`auth_service.get_session` (validates + lazily deletes expired sessions) → loads `User`.
Every document/session query is filtered by `user_id`, which is how per-user data
isolation works despite a **shared login password**.

### Auth model
One shared password (`SHARED_LOGIN_PASSWORD`) for everyone. Login takes
`{nickname, password}`; any nickname not seen before **auto-creates a User**. So
"accounts" are just nicknames; the password gates entry, the nickname scopes data.

### Document ingestion (`document_service` + `utils/file_parsers`)
On upload: save to `data/uploads/<uuid>.<ext>`, parse to text, count tokens (tiktoken
`cl100k_base`), persist `parsed_text` on the `Document` row.

PDF parsing has two paths, chosen automatically by `_is_scanned_pdf` (>50% of pages have
fewer than `pdf_text_threshold`=80 chars):
- **Text PDF** → `pymupdf4llm.to_markdown` (synchronous).
- **Scanned/mixed PDF** → `parse_pdf_vision` (async): per 5-page batch, text-rich pages go
  through pymupdf4llm and sparse pages are rendered to JPEG and sent to `VISION_MODEL`.

### RAG (`rag_service`)
Threshold-based, **not** always-on RAG. `get_context(doc_id, token_count, full_text, query)`:
- `token_count < RAG_TOKEN_THRESHOLD` (12000) → return the **entire** document text.
- Otherwise → embed the query, ChromaDB top-k (5) over the per-document collection
  (`doc_<id>`), join chunks. Falls back to `full_text[:8000]` if nothing indexed.

Indexing only happens at upload time when `token_count >= 12000`. **Caveat:** the upload
router hardcodes `12000` instead of reading `settings.rag_token_threshold` — keep these in
sync if you change the threshold. Chunks are 500 tokens with 50 overlap, embedded via
`EMBEDDING_MODEL`. Deleting a document also deletes its Chroma collection.

### Directions (`direction_service`)
Four `FIXED_DIRECTIONS` (qa / summary / explain / quiz), each with a hardcoded system
prompt in `DIRECTION_SYSTEM_PROMPTS`. Plus 4 **dynamic** directions: the LLM reads the
first ~3000 chars and returns a JSON array of `{key,label,description,emoji}`. Dynamic
directions get `is_dynamic: true` and a generic system prompt keyed off their label.
Results are cached in `Document.directions_cache` (JSON text column); the
`GET /{id}/directions?refresh=true` query param forces regeneration.

### Chat streaming (`chat_service` + SSE)
`POST /api/sessions/{id}/messages` returns a `StreamingResponse` (`text/event-stream`,
`X-Accel-Buffering: no`). The flow: build context via `get_context` → pick the direction's
system prompt and append the lecture context to it → replay prior `ChatMessage` history →
stream from the OpenAI-compatible chat completion.

**SSE wire format is custom, not standard SSE data framing** — match both ends if you
touch it:
- Each token is sent as `data: <delta>\n\n`, with literal newlines in the delta escaped to
  the two characters `\n` (backslash-n), because a real newline would terminate the SSE event.
- The frontend (`ChatPage.tsx`) reads the stream with `fetch` + `getReader()`, strips
  `data: `, and **un-escapes `\\n` back to newlines**.
- Sentinels: `[DONE]` ends the stream; `[ERROR] <msg>` signals failure. The user message is
  persisted before streaming; the assistant message is persisted only after `[DONE]`.

Assistant output may contain a `<think>...</think>` block; the frontend splits it out and
renders it as a collapsible "思考過程" (reasoning) panel separate from the answer.

## LLM configuration

All model calls go through one OpenAI-compatible endpoint (default OpenRouter), configured
in `.env` (see `.env.example`): `OPENAI_COMPATIBLE_BASE_URL/_API_KEY/_MODEL`, plus
`EMBEDDING_MODEL` and `VISION_MODEL`. Clients are constructed ad-hoc with
`AsyncOpenAI(base_url=..., api_key=... or "none")`. Settings load via pydantic-settings from
`../.env` relative to `backend/app/` (see `config.py`).

## Frontend notes

React 19 + TypeScript + Vite + Tailwind, React Router 7. `api/client.ts` is an axios
instance (`baseURL: /api`, `withCredentials: true`) whose interceptor redirects to `/login`
on any 401. `SessionContext` + `RequireAuth` gate routes. Pages: Login → Home (doc list +
upload) → Document (directions) → Chat (streaming) → History. Note chat streaming uses raw
`fetch` (not the axios client) so it can read the SSE body.
