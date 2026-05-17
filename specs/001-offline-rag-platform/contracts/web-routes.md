# Web Routes Contract: Offline RAG Commercial Platform

**Phase 1 output** | Branch: `001-offline-rag-platform` | Date: 2026-05-16

Base URL: `http://127.0.0.1:8000`
Auth: signed session cookie (`vsnt_session`), `HttpOnly=True`, `SameSite=Lax`
All HTML routes return `text/html`. All `/api/` routes return `application/json`.
Unauthenticated requests to protected routes redirect to `GET /login`.

---

## Auth Routes (`src/auth/routes.py`)

### `GET /setup`

**Access**: Public (only when `setup_complete == "false"`)
**Purpose**: Display first-run setup wizard to create the first admin account.
**Behavior**: If `setup_complete == "true"`, redirect to `GET /login`.
**Response**: `200 OK` — renders `setup.html`

---

### `POST /setup`

**Access**: Public (only when `setup_complete == "false"`)
**Request body** (form): `username: str`, `password: str`
**Validation**:
- `username`: non-empty, ≤ 64 chars, alphanumeric + underscore + hyphen
- `password`: non-empty (no complexity rule)
**Success**: Creates admin user, sets `setup_complete = "true"`, logs `user_created`
audit event, sets session cookie, redirects to `GET /`.
**Error**: Re-renders `setup.html` with inline validation error.

---

### `GET /login`

**Access**: Public
**Purpose**: Display login form.
**Behavior**: If already authenticated, redirect to `GET /`.
**Response**: `200 OK` — renders `login.html`

---

### `POST /login`

**Access**: Public
**Request body** (form): `username: str`, `password: str`
**Validation**: Verify user exists, is active, and password matches hash.
**Success**: Sets `vsnt_session` cookie (max_age = `session_timeout_seconds`), logs
`login_success` event, redirects to `GET /`.
**Error**: Logs `login_failure` event, re-renders `login.html` with generic error
("Invalid username or password" — do not distinguish user-not-found from wrong-password).

---

### `GET /logout`

**Access**: Authenticated
**Success**: Clears `vsnt_session` cookie, logs `logout` event, redirects to `GET /login`.

---

## Chat Routes (`src/chat/routes.py`)

### `GET /`

**Access**: Authenticated (any role)
**Purpose**: Main chat interface.
**Response**: `200 OK` — renders `chat.html` with empty conversation or session history.

---

### `POST /chat`

**Access**: Authenticated (any role)
**Request body** (JSON): `{"question": "string"}`
**Validation**: `question` non-empty, ≤ 2000 chars.
**Behavior**:
1. Passes question to `chat/engine.py` (existing `CondensePlusContextChatEngine`).
2. Returns answer with source file list.
3. Logs `query` audit event.
**Response**:
```json
{
  "answer": "string",
  "sources": ["filename.md", "manual.pdf"],
  "model": "llama3"
}
```
**Error** (Ollama unavailable): `503 Service Unavailable`
```json
{"error": "LLM service unavailable. Verify Ollama is running."}
```

---

### `POST /chat/reset`

**Access**: Authenticated (any role)
**Purpose**: Clear the current session's conversation history.
**Behavior**: Calls `chat_engine.reset()` for this session's engine instance.
**Response**: `200 OK` — `{"status": "cleared"}`

---

## Admin Routes (`src/admin/`)

All admin routes require `role == "admin"`. Operators receive `403 Forbidden`.

### `GET /admin`

Redirects to `GET /admin/documents`.

---

### User Management (`src/admin/users.py`)

#### `GET /admin/users`

**Response**: `200 OK` — renders `admin/users.html` with full user list
(id, username, role, is_active, created_at, last_login_at).

#### `POST /admin/users`

**Request body** (form): `username: str`, `role: str ("admin"|"operator")`
**Behavior**: Creates user with a temporary password displayed once on screen (operator
must change it on first login — logged as `user_created`).
**Validation**: Username unique, role valid.
**Response**: Redirect to `GET /admin/users` with flash message.

#### `POST /admin/users/{user_id}/toggle-active`

**Behavior**: Flips `is_active`. Cannot deactivate the last active admin. Logs
`user_deactivated` or `user_reactivated` event.
**Response**: Redirect to `GET /admin/users`.

#### `POST /admin/users/{user_id}/delete`

**Behavior**: Deletes user. Cannot delete the last admin. Logs `user_deleted` event.
**Response**: Redirect to `GET /admin/users`.

---

### Document Management (`src/admin/documents.py`)

#### `GET /admin/documents`

**Response**: `200 OK` — renders `admin/documents.html` with file list from `docs/`
(filename, format, size, modified_at, indexed status) plus current indexing status.

#### `POST /admin/documents/upload`

**Request**: `multipart/form-data`, field `file` (PDF, DOCX, or MD).
**Validation**: Extension MUST be `.pdf`, `.docx`, `.doc`, `.md`, `.txt`. Max size: 100 MB.
**Behavior**:
1. Save file to `docs/`.
2. Enqueue background indexing task.
3. Log `document_uploaded` event.
**Response**: Redirect to `GET /admin/documents` with flash "Indexing started…"

#### `POST /admin/documents/{filename}/delete`

**Behavior**: Removes file from `docs/`. Triggers full reindex (necessary to remove
document from vector store). Logs `document_deleted` event.
**Response**: Redirect to `GET /admin/documents`.

#### `POST /admin/documents/reindex`

**Behavior**: Triggers a full index rebuild (`rm -rf .rag_index/` + rebuild).
Sets `indexing_status = "running"` in SystemSettings. Logs `index_triggered` event.
**Response**: Redirect to `GET /admin/documents`.

#### `GET /api/admin/indexing-status`

**Purpose**: Polled by the admin documents page to show live indexing progress.
**Response**:
```json
{
  "status": "idle" | "running" | "error",
  "started_at": "2026-05-16T10:00:00Z" | null,
  "completed_at": "2026-05-16T10:04:22Z" | null,
  "error": null | "error message string"
}
```

---

### Settings (`src/admin/settings.py`)

#### `GET /admin/settings`

**Response**: `200 OK` — renders `admin/settings.html` with current values for:
- Active Ollama model (dropdown from live Ollama `/api/tags`)
- Session timeout (text input, seconds)
- Indexing trigger mode (manual / folder-watch)

#### `POST /admin/settings`

**Request body** (form): `ollama_model: str`, `session_timeout_seconds: int`
**Validation**:
- `ollama_model`: MUST exist in Ollama `/api/tags` response at time of save.
- `session_timeout_seconds`: positive integer, 60–86400 (1 min to 24 h).
**Behavior**:
1. Upserts values in SystemSettings.
2. Invalidates chat engine singleton (forces rebuild on next query with new model).
3. Logs `model_changed` and/or `settings_changed` audit events.
**Response**: Redirect to `GET /admin/settings` with flash "Settings saved."

---

### Audit Log (`src/admin/audit.py`)

#### `GET /admin/audit`

**Response**: `200 OK` — renders `admin/audit.html` with last 100 `AuditEvent` rows
in reverse chronological order (id, created_at, event_type, username_snapshot, payload summary).

#### `GET /api/admin/audit`

**Query params**: `limit: int = 100`, `offset: int = 0`, `event_type: str (optional)`
**Response**:
```json
{
  "total": 1042,
  "events": [
    {
      "id": 1042,
      "created_at": "2026-05-16T14:33:01Z",
      "event_type": "query",
      "username": "op.joao",
      "payload": {"question": "...", "model": "llama3"}
    }
  ]
}
```

---

## Error Pages

| Code | Condition | Response |
|---|---|---|
| 401 | No valid session cookie | Redirect to `GET /login` |
| 403 | Operator accessing admin route | Renders `403.html` ("Access denied") |
| 404 | Unknown route | Renders `404.html` |
| 503 | Ollama not running | JSON error on `/chat`, inline warning on chat page |
