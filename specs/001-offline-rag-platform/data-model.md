# Data Model: Offline RAG Commercial Platform

**Phase 1 output** | Branch: `001-offline-rag-platform` | Date: 2026-05-16

Storage: SQLite (`data/vsnt_rag.db`) managed by SQLAlchemy async ORM.
Vector index: `.rag_index/` (LlamaIndex SimpleVectorStore — unchanged, not in this schema).

---

## Entities

### User

Represents an authenticated person with a role.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | INTEGER | PK, autoincrement | |
| `username` | TEXT | UNIQUE, NOT NULL | Case-insensitive lookup; stored lowercase |
| `password_hash` | TEXT | NOT NULL | bcrypt hash via passlib |
| `role` | TEXT | NOT NULL | `"admin"` or `"operator"` |
| `is_active` | BOOLEAN | NOT NULL, default TRUE | Inactive users cannot log in |
| `created_at` | DATETIME | NOT NULL, default now | UTC |
| `last_login_at` | DATETIME | nullable | Updated on successful login |

**Rules**:
- `username` MUST be unique (case-insensitive).
- `role` MUST be one of `{"admin", "operator"}`.
- A user with `is_active = FALSE` MUST be rejected at login.
- The system MUST contain at least one `admin` user after setup; the setup wizard
  ensures this by creating the first admin before any other access is permitted.
- Deleting the last admin account is prohibited.

**State transitions**:
```
[created] → active (is_active=TRUE)
           → deactivated (is_active=FALSE)  ← admin action
           → active (re-activated)          ← admin action
           → deleted                        ← admin action (soft-delete optional)
```

---

### AuditEvent

Immutable log of every query and authentication event.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | INTEGER | PK, autoincrement | |
| `event_type` | TEXT | NOT NULL | See event type enum below |
| `user_id` | INTEGER | FK → User.id, nullable | Nullable for failed-login events where user may not exist |
| `username_snapshot` | TEXT | NOT NULL | Denormalized; preserved if user is later deleted |
| `payload` | TEXT | NOT NULL | JSON blob; see payload schema per event type |
| `created_at` | DATETIME | NOT NULL, default now | UTC; indexed for chronological queries |

**Event types**:

| `event_type` | `payload` fields |
|---|---|
| `login_success` | `{}` |
| `login_failure` | `{"reason": "bad_password" \| "user_not_found" \| "user_inactive"}` |
| `logout` | `{}` |
| `query` | `{"question": "...", "answer": "...", "sources": ["file1.md", ...], "model": "llama3"}` |
| `document_uploaded` | `{"filename": "...", "size_bytes": 12345, "format": "pdf" \| "docx" \| "md"}` |
| `document_deleted` | `{"filename": "..."}` |
| `index_triggered` | `{"trigger": "upload" \| "folder_watch" \| "manual", "doc_count": 42}` |
| `model_changed` | `{"from": "llama3", "to": "mistral"}` |
| `user_created` | `{"target_username": "...", "role": "operator"}` |
| `user_deactivated` | `{"target_username": "..."}` |
| `user_reactivated` | `{"target_username": "..."}` |
| `user_deleted` | `{"target_username": "..."}` |
| `settings_changed` | `{"key": "session_timeout_seconds", "old": "28800", "new": "3600"}` |

**Rules**:
- Records are append-only. No UPDATE or DELETE is permitted on this table.
- `created_at` MUST have an index for efficient pagination of the audit log view.
- The admin panel displays the last 100 records in reverse chronological order (SC-005).

---

### SystemSettings

Key-value store for runtime configuration managed by the admin.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `key` | TEXT | PK | Canonical setting name |
| `value` | TEXT | NOT NULL | Always stored as string; typed at read time |
| `updated_at` | DATETIME | NOT NULL | UTC |
| `updated_by_user_id` | INTEGER | FK → User.id, nullable | Nullable for system-set defaults |

**Known keys and defaults**:

| Key | Default | Type | Description |
|---|---|---|---|
| `ollama_model` | `"llama3"` | string | Active Ollama model name |
| `session_timeout_seconds` | `"28800"` | integer | Idle session expiry (8 h) |
| `indexing_status` | `"idle"` | enum | `"idle"` \| `"running"` \| `"error"` |
| `indexing_started_at` | `""` | ISO datetime string | Set when indexing begins |
| `indexing_last_completed_at` | `""` | ISO datetime string | Set on successful completion |
| `indexing_last_error` | `""` | string | Last indexing error message, if any |
| `setup_complete` | `"false"` | boolean | Set to `"true"` after first admin created |

**Rules**:
- Settings are upserted (INSERT OR REPLACE) — no separate update path needed.
- `session_timeout_seconds` MUST be a positive integer. Invalid values are rejected
  at the API layer before being written.
- `ollama_model` MUST match a model returned by Ollama's `/api/tags` at save time;
  if the model is not installed, the change is rejected with an error message.

---

## Relationships

```
User (1) ──────────────── (N) AuditEvent
  └── user_id FK (nullable for failed logins)
  └── username_snapshot (denormalized copy)

SystemSettings ──── no FK relationships (standalone config store)
```

---

## Document Entity (filesystem, not SQLite)

Documents are not stored in SQLite — they live in `docs/` on the filesystem and are
indexed into `.rag_index/`. The admin panel reads `docs/` directly to list files.

| Attribute | Source | Notes |
|---|---|---|
| `filename` | `os.listdir("docs/")` | Display name |
| `format` | File extension | `.pdf`, `.docx`, `.md`, `.txt` |
| `size_bytes` | `os.stat()` | Displayed in admin panel |
| `modified_at` | `os.stat()` | Used to detect new/changed files |
| `indexed` | Derived | True if file present in LlamaIndex docstore |

---

## Indexes

```sql
-- Fast chronological audit log queries
CREATE INDEX idx_audit_event_created_at ON audit_event (created_at DESC);

-- Fast user lookup by username (login path)
CREATE UNIQUE INDEX idx_user_username ON user (LOWER(username));
```

---

## Initialization

On first `python app.py` startup:
1. `create_all()` creates all tables if they do not exist.
2. If `SystemSettings.setup_complete == "false"` (or key absent), redirect all requests
   to `/setup` (the first-admin wizard).
3. After admin creation, set `setup_complete = "true"` and redirect to `/login`.
4. Default `SystemSettings` rows are inserted if absent.
