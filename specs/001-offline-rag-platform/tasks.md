---
description: "Task list for Offline RAG Commercial Platform"
---

# Tasks: Offline RAG Commercial Platform

**Input**: Design documents from `specs/001-offline-rag-platform/`

**Prerequisites**: plan.md ✅ | spec.md ✅ | research.md ✅ | data-model.md ✅ | contracts/web-routes.md ✅

**Tests**: Not requested — no test tasks included.

**Organization**: Tasks are grouped by user story to enable independent implementation
and testing of each story.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no shared dependencies)
- **[Story]**: Which user story this task belongs to (US1–US6)
- File paths are relative to the repository root

---

## Phase 1: Setup

**Purpose**: Project initialization — create directory skeleton, extend dependencies,
and add shared configuration.

- [ ] T001 Create project directory structure: `src/db/`, `src/models/`, `src/auth/`, `src/chat/`, `src/admin/`, `src/audit/`, `src/templates/admin/`, `static/css/`, `static/js/`, `data/`, `scripts/`; add `__init__.py` to every `src/` sub-package
- [ ] T002 Extend `requirements_offline.txt` with new web-layer dependencies: `fastapi>=0.111.0`, `uvicorn[standard]>=0.29.0`, `jinja2>=3.1.0`, `python-multipart>=0.0.9`, `sqlalchemy[asyncio]>=2.0.0`, `aiosqlite>=0.20.0`, `passlib[bcrypt]>=1.7.4`, `itsdangerous>=2.1.2`, `pdfplumber>=0.11.0`, `python-docx>=1.1.0`, `watchfiles>=0.21.0`
- [ ] T003 [P] Create `config.py` with central constants: `OLLAMA_MODEL`, `OLLAMA_URL`, `EMBED_MODEL`, `RERANK_MODEL`, `RERANK_TOP_N`, `DB_PATH` (`data/vsnt_rag.db`), `DOCS_DIR`, `INDEX_DIR`, `SESSION_SECRET_KEY` (read from env or generate on first run), `SESSION_TIMEOUT_SECONDS` (default 28800), `SERVER_HOST` (`127.0.0.1`), `SERVER_PORT` (8000)
- [ ] T004 [P] Create `static/css/style.css` with minimal CSS: page layout, navigation bar, chat message bubbles (user / assistant), admin tables, flash message banners, responsive form inputs — no external CDN dependencies

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Database layer, ORM models, session management, and audit logger that ALL
user stories depend on. No user story work begins until this phase is complete.

**⚠️ CRITICAL**: No user story implementation can begin until Phase 2 is complete.

- [ ] T005 Create `src/db/database.py`: async SQLAlchemy engine (`create_async_engine` with `aiosqlite`); `AsyncSession` factory; `get_db()` async dependency for FastAPI; `init_db()` function that runs `Base.metadata.create_all`, enables WAL mode (`PRAGMA journal_mode=WAL`), and enforces foreign keys (`PRAGMA foreign_keys=ON`)
- [ ] T006 [P] Create `src/models/user.py`: `User` ORM model with columns `id` (PK autoincrement), `username` (TEXT UNIQUE NOT NULL), `password_hash` (TEXT NOT NULL), `role` (TEXT NOT NULL, `"admin"` or `"operator"`), `is_active` (BOOLEAN default TRUE), `created_at` (DATETIME default now UTC), `last_login_at` (DATETIME nullable); add `UniqueConstraint` on `func.lower(username)`
- [ ] T007 [P] Create `src/models/audit_event.py`: `AuditEvent` ORM model with columns `id` (PK autoincrement), `event_type` (TEXT NOT NULL), `user_id` (INTEGER FK → User.id nullable), `username_snapshot` (TEXT NOT NULL), `payload` (TEXT NOT NULL, JSON string), `created_at` (DATETIME default now UTC); add `Index` on `created_at DESC`; define all `event_type` string constants in the same file
- [ ] T008 [P] Create `src/models/system_settings.py`: `SystemSettings` ORM model with columns `key` (TEXT PK), `value` (TEXT NOT NULL), `updated_at` (DATETIME NOT NULL), `updated_by_user_id` (INTEGER FK → User.id nullable); define default settings dict (`ollama_model`, `session_timeout_seconds`, `indexing_status`, `indexing_started_at`, `indexing_last_completed_at`, `indexing_last_error`, `setup_complete`)
- [ ] T009 Create `src/models/__init__.py`: import `User`, `AuditEvent`, `SystemSettings`, and `Base` from their modules; expose `create_all_tables(engine)` helper that calls `Base.metadata.create_all(bind=engine)` synchronously for startup use
- [ ] T010 [P] Create `src/auth/session.py`: `sign_session(data: dict) → str` using `itsdangerous.URLSafeTimedSerializer` with `SESSION_SECRET_KEY`; `verify_session(token: str, max_age: int) → dict | None` (returns None on expired/invalid); `set_session_cookie(response, data)` helper (HttpOnly=True, SameSite=Lax, Secure=False); `clear_session_cookie(response)` helper
- [ ] T011 [P] Create `src/audit/logger.py`: `log_event(db, event_type, user_id, username_snapshot, payload: dict)` async function that creates and commits an `AuditEvent` row; convenience wrappers `log_auth_event(db, event_type, user_id, username, **payload)` and `log_query(db, user_id, username, question, answer, sources, model)`
- [ ] T012 Create `src/templates/base.html`: HTML5 base layout with `<nav>` containing "Chat" link (always visible to authenticated users); flash message `<div>` rendered from Jinja2 `messages` context variable; `{% block content %}{% endblock %}`; `<link>` to `static/css/style.css`; no external CDN resources
- [ ] T013 Create `app.py`: FastAPI application instance; `lifespan` async context manager that calls `init_db()`, inserts default `SystemSettings` rows if absent, and starts the `watchfiles` watcher on `docs/`; top-level `if __name__ == "__main__": uvicorn.run(app, host=SERVER_HOST, port=SERVER_PORT)` — router mounting added in T022

**Checkpoint**: Foundation ready — database initializes, session signing works, audit logger writes to DB. User story implementation can now begin.

---

## Phase 3: User Story 1 - Operator Queries via Web Interface (Priority: P1) 🎯 MVP

**Goal**: A logged-in operator opens the browser, submits a question, and receives a sourced answer from the indexed documents. No data leaves the machine.

**Independent Test**: Start `python app.py`, open `http://127.0.0.1:8000`, complete the setup wizard, log in, submit a question, verify a sourced answer is returned within 60 s with no network traffic leaving localhost.

### Implementation for User Story 1

- [ ] T014 [P] [US1] Create `src/auth/service.py`: `create_user(db, username, password, role)` (hashes password with passlib bcrypt); `verify_password(plain, hashed) → bool`; `get_user_by_username(db, username) → User | None` (case-insensitive lookup via `func.lower()`); `require_auth(request) → User` FastAPI dependency (reads and verifies session cookie, raises 401 redirect if invalid); `require_admin(user=Depends(require_auth)) → User` dependency (raises 403 if role != "admin")
- [ ] T015 [US1] Create `src/auth/routes.py`: `GET /setup` → render `setup.html` (redirect to `/login` if `setup_complete == "true"`); `POST /setup` → validate username/password non-empty, call `create_user()` with role "admin", set `setup_complete = "true"` in SystemSettings, set session cookie, redirect to `/`; `GET /login` → render `login.html` (redirect to `/` if already authenticated); `POST /login` → look up user, verify password, check `is_active`, set session cookie or re-render login with error; `GET /logout` → clear session cookie, redirect to `/login`
- [ ] T016 [P] [US1] Create `src/templates/setup.html`: extends `base.html`; form with `username` and `password` text inputs, submit button "Create Admin Account"; inline validation error display; heading "VSNT RAG — Configuração Inicial"
- [ ] T017 [P] [US1] Create `src/templates/login.html`: extends `base.html`; form with `username` and `password` inputs, submit button "Entrar"; inline error message "Usuário ou senha inválidos" on failed login
- [ ] T018 [US1] Create `src/chat/engine.py`: module-level `_engine_instance = None` and `_engine_model = None`; `get_engine(active_model: str) → CondensePlusContextChatEngine` — returns cached instance if model unchanged, otherwise rebuilds by calling `build_settings()` and `build_chat_engine()` from `rag_vsnt_offline.py`; `invalidate_engine()` sets `_engine_instance = None`; `get_active_model(db) → str` reads `ollama_model` from SystemSettings
- [ ] T019 [US1] Create `src/chat/routes.py`: `GET /` → read `setup_complete` from SystemSettings, redirect to `/setup` if false, else render `chat.html`; `POST /chat` → read request JSON `{"question": str}`, validate non-empty ≤ 2000 chars, call `get_engine(active_model).chat(question)`, call `log_query()`, return `{"answer": str, "sources": [str], "model": str}`; `POST /chat/reset` → call `get_engine().reset()`, return `{"status": "cleared"}`
- [ ] T020 [US1] Create `src/templates/chat.html`: extends `base.html`; scrollable `<div>` for message history; `<form>` with textarea input and submit button; source file list displayed below each answer; "Limpar conversa" reset button; calls `static/js/chat.js` for async submit
- [ ] T021 [P] [US1] Create `static/js/chat.js`: intercepts form submit; `fetch('POST /chat', {body: JSON.stringify({question})})` with `Content-Type: application/json`; appends user question and assistant answer to the message `<div>`; displays source filenames; shows "Serviço LLM indisponível" on 503 response; disables submit button during pending request
- [ ] T022 [US1] Update `app.py`: import and mount `auth_router` (prefix `""`) and `chat_router` (prefix `""`); add `Middleware` that checks session cookie on every non-`/setup`, non-`/login`, non-`/static` request and redirects to `/login` if invalid; mount `StaticFiles` at `/static`; add `Jinja2Templates` instance pointing to `src/templates/`

**Checkpoint**: US1 fully functional — setup wizard, login, chat, sourced answers, logout all work independently.

---

## Phase 4: User Story 6 - Simple Installation on Windows and Linux (Priority: P1)

**Goal**: A non-technical user installs the system from scratch and has it running within 30 minutes by following `quickstart.md`.

**Independent Test**: Follow `quickstart.md` on a clean Ubuntu 22.04 VM and a clean Windows 11 VM. Verify system is running and answering queries without additional troubleshooting.

### Implementation for User Story 6

- [ ] T023 [US6] Create `install.sh`: check Python ≥ 3.11 (`python3 --version`); create `.venv/` with `python3 -m venv`; activate and `pip install -r requirements_offline.txt`; `mkdir -p data docs`; check `ollama` binary exists and print warning if not; print "✅ Instalação concluída. Execute: python app.py"
- [ ] T024 [P] [US6] Create `install.bat`: Windows equivalent of `install.sh` using `cmd` syntax: check `python --version`, create `.venv\`, activate with `.venv\Scripts\activate.bat`, `pip install -r requirements_offline.txt`, `mkdir data`, `mkdir docs` (if not exist); print success message
- [ ] T025 [US6] Add startup health check in `app.py` lifespan: call `_check_ollama()` from `rag_vsnt_offline.py`; on failure, print a warning banner to stdout but do NOT exit — the web UI will display the Ollama unavailable message (503) at query time, allowing the admin panel to still be accessible

**Checkpoint**: US6 independently testable — install scripts run without error on clean VMs; `quickstart.md` steps produce a running system.

---

## Phase 5: User Story 2 - Administrator Manages Users (Priority: P2)

**Goal**: Admin creates, deactivates, and deletes operator accounts. Operators cannot access the admin panel.

**Independent Test**: Log in as admin, create an operator account, log in as that operator, attempt to access `/admin/users` directly, verify 403 is returned.

### Implementation for User Story 2

- [ ] T026 [P] [US2] Create `src/admin/users.py`: `GET /admin/users` → query all `User` rows ordered by `created_at`, render `admin/users.html`; `POST /admin/users` → validate unique username, create user with bcrypt-hashed temp password, flash temp password once, redirect; `POST /admin/users/{id}/toggle-active` → flip `is_active`, guard against deactivating the last active admin (return 400 with message), redirect; `POST /admin/users/{id}/delete` → guard last admin, delete row, redirect; all routes use `require_admin` dependency
- [ ] T027 [P] [US2] Create `src/templates/admin/users.html`: extends `base.html`; table of users (username, role, active status, last login, actions); "New User" form (username, role select); toggle-active and delete buttons with confirmation; flash message area for temp password display
- [ ] T028 [US2] Mount admin router in `app.py`: create `admin_router` with prefix `/admin` and `require_admin` dependency applied at router level; include `users_router` sub-router; add `GET /admin` redirect to `/admin/documents` (placeholder — documents router added in T032)

**Checkpoint**: US2 independently testable — admin creates operator, operator login succeeds, operator accessing `/admin` receives 403, admin can deactivate user.

---

## Phase 6: User Story 3 - Administrator Ingests Documents (Priority: P2)

**Goal**: Admin uploads PDF, DOCX, or Markdown files via the web UI or drops them in `docs/`. Documents are indexed without restarting the server.

**Independent Test**: Upload a PDF through `/admin/documents`, wait for indexing to complete, submit a query whose answer exists only in that PDF, verify correct sourced answer.

### Implementation for User Story 3

- [ ] T029 [P] [US3] Create `src/admin/indexer.py`: `extract_text_from_pdf(path) → str` (pdfplumber: concatenate page text); `extract_text_from_docx(path) → str` (python-docx: concatenate paragraph text); `save_uploaded_file(file: UploadFile, docs_dir: Path)` saves to `docs/` with original filename; `run_indexing(db)` async function: set `indexing_status = "running"`, delete `.rag_index/` with `shutil.rmtree`, call `load_or_build_index()` from `rag_vsnt_offline.py`, call `invalidate_engine()`, update `indexing_status = "idle"` and `indexing_last_completed_at`; on exception set `indexing_status = "error"` and `indexing_last_error`
- [ ] T030 [P] [US3] Create `src/admin/documents.py`: `GET /admin/documents` → list `docs/` files with name, extension, size, modified_at; render `admin/documents.html`; `POST /admin/documents/upload` → validate extension in `{.pdf, .docx, .doc, .md, .txt}` and size ≤ 100 MB, call `save_uploaded_file()`, enqueue `run_indexing()` as `BackgroundTask`, log `document_uploaded` event, redirect; `POST /admin/documents/{filename}/delete` → `Path("docs/filename").unlink()`, enqueue `run_indexing()`, log `document_deleted` event, redirect; `POST /admin/documents/reindex` → enqueue `run_indexing()`, log `index_triggered` event, redirect; `GET /api/admin/indexing-status` → return JSON from SystemSettings (`indexing_status`, `indexing_started_at`, `indexing_last_completed_at`, `indexing_last_error`)
- [ ] T031 [P] [US3] Create `src/templates/admin/documents.html`: extends `base.html`; file table (name, format, size, modified date, indexed indicator); upload form (`<input type="file" accept=".pdf,.docx,.doc,.md,.txt">`); "Index Now" reindex button; indexing status badge that auto-polls `GET /api/admin/indexing-status` every 3 s via `setInterval` JS and stops when status returns to `"idle"`
- [ ] T032 [US3] Include `documents_router` in the admin router in `app.py`; add `watchfiles` watcher in `app.py` lifespan: `async for changes in awatch("docs/"): await run_indexing(db)` — triggers automatic reindex when files are added/modified via the filesystem

**Checkpoint**: US3 independently testable — upload PDF and DOCX, observe indexing badge change to "idle", query content from those files, receive sourced answer.

---

## Phase 7: User Story 4 - System Produces Audit Logs (Priority: P3)

**Goal**: Every query and authentication event is recorded locally. Admin views the last 100 events in the admin panel.

**Independent Test**: Submit 5 queries and perform 2 logins. Open `/admin/audit` and verify each event appears with timestamp, username, and correct event type.

### Implementation for User Story 4

- [ ] T033 [P] [US4] Add `log_auth_event()` calls in `src/auth/routes.py`: `login_success` on successful POST /login; `login_failure` with `reason` field on failed POST /login; `logout` on GET /logout; `user_created` on successful POST /setup
- [ ] T034 [P] [US4] Add `log_query()` call in `src/chat/routes.py` POST `/chat`: called after the LLM response is received, passing `question`, `answer`, `sources` list, and active `model` name
- [ ] T035 [P] [US4] Add `log_auth_event()` calls in `src/admin/documents.py`: `document_uploaded` on upload success; `document_deleted` on delete success; `index_triggered` on manual reindex
- [ ] T036 [US4] Create `src/admin/audit.py`: `GET /admin/audit` → query last 100 `AuditEvent` rows ordered by `created_at DESC`, render `admin/audit.html`; `GET /api/admin/audit` → paginated JSON query (params: `limit`, `offset`, optional `event_type` filter)
- [ ] T037 [P] [US4] Create `src/templates/admin/audit.html`: extends `base.html`; table of audit events (id, timestamp formatted as `YYYY-MM-DD HH:MM:SS UTC`, event_type badge, username_snapshot, payload summary truncated to 120 chars); newest events at top
- [ ] T038 [US4] Include `audit_router` in the admin router in `app.py`; add "Auditoria" link to admin nav in `base.html`

**Checkpoint**: US4 independently testable — all query and auth events appear in `/admin/audit` in correct chronological order; no events are missing under normal operation.

---

## Phase 8: User Story 5 - Administrator Selects Active LLM Model (Priority: P3)

**Goal**: Admin selects a different locally installed Ollama model from the settings page. The next query uses the new model with no restart.

**Independent Test**: Install a second Ollama model (`ollama pull mistral`), switch to it in `/admin/settings`, submit a query, verify the audit log shows the new model name in the query event payload.

### Implementation for User Story 5

- [ ] T039 [P] [US5] Create `src/admin/settings.py`: `GET /admin/settings` → fetch available models from `GET http://127.0.0.1:11434/api/tags`, read current `ollama_model` and `session_timeout_seconds` from SystemSettings, render `admin/settings.html`; `POST /admin/settings` → validate `ollama_model` exists in Ollama tags response (return 400 if not installed), validate `session_timeout_seconds` is integer 60–86400, upsert both SystemSettings keys, call `invalidate_engine()`, log `model_changed` and `settings_changed` audit events, redirect with flash "Configurações salvas"
- [ ] T040 [P] [US5] Create `src/templates/admin/settings.html`: extends `base.html`; `<select>` dropdown of available Ollama model names (populated from template context); session timeout `<input type="number">` field with current value; Save button; current active model displayed prominently
- [ ] T041 [US5] Include `settings_router` in the admin router in `app.py`; add "Configurações" link to admin nav in `base.html`

**Checkpoint**: US5 independently testable — model switch takes effect on next query; reverting to previous model also works; selecting an uninstalled model shows validation error.

---

## Phase N: Polish & Cross-Cutting Concerns

**Purpose**: Final integration, navigation, error handling, and audit coverage completing all user stories.

- [ ] T042 [P] Update `src/templates/base.html`: add admin-only `<nav>` section (visible only when `current_user.role == "admin"`) with links to `/admin/documents`, `/admin/users`, `/admin/settings`, `/admin/audit`; pass `current_user` from all route handlers to template context
- [ ] T043 [P] Create `src/templates/403.html` and `src/templates/404.html` error page templates; register `@app.exception_handler(403)` and `@app.exception_handler(404)` in `app.py` returning these templates
- [ ] T044 [P] Add `log_auth_event()` calls for user management events in `src/admin/users.py`: `user_created`, `user_deactivated`, `user_reactivated`, `user_deleted` for every admin action on user accounts
- [ ] T045 [P] Add `log_auth_event()` calls in `src/admin/settings.py` already scaffolded in T039: verify `model_changed` and `settings_changed` events include `old` and `new` values in payload
- [ ] T046 Verify WAL mode and foreign key enforcement are applied in `src/db/database.py` `init_db()` before any queries execute; test by checking `PRAGMA journal_mode` returns `"wal"` in a startup log line
- [ ] T047 [P] Create `scripts/register-task.bat`: Windows batch script that registers VSNT RAG as a Task Scheduler entry running `pythonw.exe app.py` at logon for the current user; include `schtasks /create` command with appropriate flags
- [ ] T048 End-to-end installation validation: follow `quickstart.md` on a clean Ubuntu 22.04 environment and a clean Windows 11 environment; update `quickstart.md` with any corrections found; verify SC-003 (≤ 30 min to first query)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Requires Phase 1 completion — **BLOCKS all user stories**
- **US1 (Phase 3)**: Requires Phase 2 — first user story to implement (auth + chat core)
- **US6 (Phase 4)**: Requires Phase 3 (app.py must exist to write accurate install scripts)
- **US2 (Phase 5)**: Requires Phase 3 (depends on `require_admin` from auth service T014)
- **US3 (Phase 6)**: Requires Phase 3 (depends on `require_admin`; indexer uses chat engine)
- **US4 (Phase 7)**: Requires Phase 3 + Phase 5 + Phase 6 (adds log calls to their routes)
- **US5 (Phase 8)**: Requires Phase 3 (depends on `invalidate_engine()` from T018)
- **Polish (Phase N)**: Requires all story phases complete

### User Story Dependencies

- **US1 (P1)**: Can start after Phase 2 — no story dependencies
- **US6 (P1)**: Can start after US1 — needs working `app.py` entry point
- **US2 (P2)**: Can start after US1 — reuses `require_admin` from T014
- **US3 (P2)**: Can start after US1 — reuses `require_admin` and `invalidate_engine()`
- **US4 (P3)**: Can start after US1, US2, US3 — adds logging to all their routes
- **US5 (P3)**: Can start after US1 — reuses `invalidate_engine()` from T018

### Within Each User Story

- Models/services before routes
- Routes before templates
- Engine before routes that call it
- Commit after each checkpoint

### Parallel Opportunities After US1 (Phase 3) Completes

Once Phase 3 is complete, these phases can proceed in parallel:

```
US1 done
├── US6 (Phase 4): install scripts
├── US2 (Phase 5): user management
├── US3 (Phase 6): document ingestion
└── US5 (Phase 8): model selection
    ↓
US4 (Phase 7): audit log integration — depends on US2 and US3 routes existing
    ↓
Phase N: polish
```

---

## Parallel Example: User Story 3 (US3)

```bash
# Launch all [P] tasks for US3 together:
Task: "Create src/admin/indexer.py"           # T029 [P]
Task: "Create src/admin/documents.py"          # T030 [P]
Task: "Create src/templates/admin/documents.html"  # T031 [P]

# Then sequentially:
Task: "Wire documents router into app.py and add watchfiles watcher"  # T032
```

---

## Implementation Strategy

### MVP First (US1 Only)

1. Complete Phase 1: Setup (T001–T004)
2. Complete Phase 2: Foundational (T005–T013) — **CRITICAL**
3. Complete Phase 3: US1 (T014–T022)
4. **STOP and VALIDATE**: Setup wizard → login → query → sourced answer
5. Demo to stakeholders — core value proposition delivered

### Incremental Delivery

1. Setup + Foundational → foundation ready
2. US1 → web chat working → **MVP demo**
3. US6 → installation scripts → **deployable package**
4. US2 + US3 in parallel → multi-user + document management
5. US4 → audit logs → **compliance-ready**
6. US5 → model switching → **operationally flexible**
7. Polish → **production-ready**

### Parallel Team Strategy (3 developers)

After Phase 3 (US1) completes:
- **Dev A**: US2 (user management) → US4 audit calls for auth/users
- **Dev B**: US3 (document ingestion) → US4 audit calls for documents
- **Dev C**: US6 (installation) → US5 (model selection) → Phase N polish

---

## Notes

- `[P]` tasks operate on different files and have no dependency on incomplete tasks in the same phase
- `[USn]` label maps each task to its user story for traceability
- Each story phase ends with an independent test checkpoint — stop and validate before moving on
- `rag_vsnt_offline.py` and `manage_index.py` are NEVER modified — they are imported by the new layer
- The `docs/` and `.rag_index/` directories are shared between terminal mode and web mode
- Avoid cross-story route dependencies at implementation time; wire them at integration points (T022, T028, T032, T038, T041, T042)
