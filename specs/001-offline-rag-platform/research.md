# Research: Offline RAG Commercial Platform

**Phase 0 output** | Branch: `001-offline-rag-platform` | Date: 2026-05-16

---

## 1. Web Framework

**Decision**: FastAPI + Uvicorn + Jinja2

**Rationale**:
- Async-native: LLM inference blocks for up to 60 s; async routes prevent the server
  from freezing for all other users during a query.
- File upload built-in via `python-multipart`; background tasks (`BackgroundTasks`) for
  async indexing without extra worker processes.
- Server-side rendering with Jinja2 eliminates a frontend build step, satisfying
  Principle V (Operational Simplicity) — no Node.js, no npm, no bundler.
- Single `pip install fastapi uvicorn[standard] jinja2 python-multipart` — all Python,
  no system-level dependencies.

**Alternatives considered**:
- *Streamlit*: Already in requirements but session state is process-global; cannot
  support independent authenticated sessions for multiple concurrent users (US2).
- *Flask*: Synchronous by default; requires `gevent` or `gunicorn --workers` to handle
  concurrent blocking LLM calls without freezing. More setup complexity.
- *Django*: Full ORM, admin panel out of the box, but heavy for a single-machine
  localhost app; migrations overhead adds installation friction.

---

## 2. Session Management

**Decision**: Signed cookies via `itsdangerous.URLSafeTimedSerializer`

**Rationale**:
- No additional infrastructure: sessions live in a signed, tamper-proof cookie stored
  in the user's browser; the server is stateless per request.
- Expiry is enforced by the timed serializer (`max_age` = configurable idle timeout,
  default 28800 s / 8 h).
- Cookie flags: `HttpOnly=True`, `SameSite=Lax`. `Secure=False` is acceptable because
  the server is bound to 127.0.0.1 (HTTP over loopback is not exposed to network).
- No Redis, no Memcached, no external session store — fully offline.

**Alternatives considered**:
- *JWT (PyJWT)*: Stateless but requires a secret rotation strategy and adds complexity
  around revocation (needed for "deactivate user" feature in US2).
- *Server-side sessions in SQLite*: Would support instant revocation but adds
  a session table and cleanup job; overkill for a single-machine app with ≤50 users.

---

## 3. Password Hashing

**Decision**: `passlib[bcrypt]` with default work factor (12 rounds)

**Rationale**:
- bcrypt is the established standard for offline password storage. Work factor 12
  balances security and login speed (≈ 300 ms per verification on modern hardware —
  acceptable for an infrequently used login page).
- No complexity policy enforced (as clarified in spec).
- `passlib` provides a future-proof API if the algorithm needs to change.

---

## 4. Database

**Decision**: SQLite via SQLAlchemy (async, `aiosqlite` dialect)

**Rationale**:
- Zero-server, single-file database (`data/vsnt_rag.db`) — trivially backed up and
  transferred for air-gap deployments.
- SQLAlchemy async with `aiosqlite` integrates cleanly with FastAPI's async model.
- Schema managed via SQLAlchemy `create_all()` on startup (no migration runner needed
  for a single-machine app at this scale).
- WAL mode enabled to allow concurrent reads during writes (important when audit logs
  are written while queries are in progress).

**Alternatives considered**:
- *PostgreSQL*: Correct for multi-server but requires a running server process —
  violates Principle V for single-machine localhost deployment.
- *TinyDB / shelve*: Pure Python but no concurrent write safety and no SQL query
  capabilities needed for audit log filtering.

---

## 5. PDF Parsing

**Decision**: `pdfplumber`

**Rationale**:
- Pure Python (wraps `pdfminer.six`); no `poppler`, `ghostscript`, or system binary
  required — critical for Windows cross-platform support.
- Handles multi-column layouts and extracts tables, which appear frequently in
  technical documentation.
- Outputs clean text per page, suitable for LlamaIndex `Document` construction.

**Alternatives considered**:
- *PyPDF2 / pypdf*: Faster but poor table/multi-column extraction.
- *pdfminer.six directly*: `pdfplumber` is the higher-level wrapper — same dependency,
  better API.
- *Tesseract OCR*: Required only for scanned PDFs; out of scope for v1 (assumption:
  documents are text-based PDFs).

---

## 6. DOCX Parsing

**Decision**: `python-docx`

**Rationale**:
- De facto standard Python library for DOCX. Pure Python, no LibreOffice dependency.
- Extracts paragraphs and table text, preserving heading hierarchy useful for
  LlamaIndex `MarkdownNodeParser`-equivalent chunking.

---

## 7. Frontend Approach

**Decision**: Server-side rendered HTML with Jinja2 + minimal vanilla JavaScript

**Rationale**:
- No build step (no npm, webpack, Vite) — installation stays simple (SC-003: 30 min).
- Chat streaming: use `<form>` POST with a simple JavaScript fetch that appends
  streamed tokens to the page; no React/Vue needed.
- Styling: single CSS file (~200 lines) with a clean, minimal design adequate for
  internal tooling. No external CDN dependencies (offline constraint).

**Alternatives considered**:
- *HTMX*: Would simplify streaming updates but is an external JS file (requires either
  CDN call or bundling — bundling adds complexity, CDN violates offline constraint).
- *Vue/React SPA*: Requires Node.js build toolchain, substantially increases
  installation complexity and violates Principle V.

---

## 8. Background Indexing

**Decision**: FastAPI `BackgroundTasks` + `watchfiles` for folder monitoring

**Rationale**:
- `BackgroundTasks`: when a file is uploaded via the web UI, indexing runs in the
  background so the HTTP response returns immediately with a "Indexing in progress…"
  status.
- `watchfiles`: watches `docs/` for new files dropped by the admin; triggers the same
  indexing routine automatically. Pure Python, cross-platform.
- Indexing status tracked in `SystemSettings` table (`indexing_status`, `indexing_started_at`).
- No Celery, no Redis queue — keeps the architecture simple and offline.

---

## 9. Installation Packaging

**Decision**: Shell script (`install.sh`) + batch file (`install.bat`) + `requirements_offline.txt`

**Rationale**:
- No Docker: avoids requiring Docker Desktop on Windows (licensing, system requirements).
- Scripts handle: venv creation, pip install, Ollama model availability check,
  initial `python app.py --check` validation.
- Single entry point: `python app.py` starts the server; OS startup integration
  (systemd / Task Scheduler) is documented but optional.

---

## 10. Model Switching at Runtime

**Decision**: Active model stored in `SystemSettings` table; `chat/engine.py` reads it
before each new chat session (not per-query, but on session creation/reset).

**Rationale**:
- No restart required (US5 SC-006): the engine singleton is invalidated and rebuilt
  when the admin changes the model setting.
- Available models fetched live from Ollama API (`GET /api/tags` on 127.0.0.1:11434`).
- If the selected model is unavailable, the system falls back to the previously active
  model and surfaces an error to the admin.
