"""Central configuration for VSNT RAG Web Platform."""

import os
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).parent

# ── Paths ─────────────────────────────────────────────────────────────────────
DOCS_DIR    = BASE_DIR / "docs"
INDEX_DIR   = BASE_DIR / ".rag_index"
DB_PATH     = BASE_DIR / "data" / "vsnt_rag.db"
TEMPLATES_DIR = BASE_DIR / "src" / "templates"
STATIC_DIR  = BASE_DIR / "static"

# ── Ollama / RAG ──────────────────────────────────────────────────────────────
OLLAMA_MODEL  = os.getenv("OLLAMA_MODEL", "llama3")
OLLAMA_URL    = os.getenv("OLLAMA_URL", "http://localhost:11434")
EMBED_MODEL   = os.getenv("EMBED_MODEL", "BAAI/bge-base-en-v1.5")
RERANK_MODEL  = os.getenv("RERANK_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
RERANK_TOP_N  = int(os.getenv("RERANK_TOP_N", "3"))

# ── Web server ────────────────────────────────────────────────────────────────
SERVER_HOST = os.getenv("SERVER_HOST", "127.0.0.1")
SERVER_PORT = int(os.getenv("SERVER_PORT", "8000"))

# ── Session ───────────────────────────────────────────────────────────────────
_SECRET_FILE = BASE_DIR / ".session_secret"

def _load_or_create_secret() -> str:
    if _SECRET_FILE.exists():
        return _SECRET_FILE.read_text().strip()
    secret = secrets.token_hex(32)
    _SECRET_FILE.write_text(secret)
    _SECRET_FILE.chmod(0o600)
    return secret

SESSION_SECRET_KEY      = os.getenv("SESSION_SECRET_KEY") or _load_or_create_secret()
SESSION_TIMEOUT_SECONDS = int(os.getenv("SESSION_TIMEOUT_SECONDS", "28800"))  # 8 h default

# ── Upload limits ─────────────────────────────────────────────────────────────
MAX_UPLOAD_BYTES = 100 * 1024 * 1024  # 100 MB
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc", ".md", ".txt"}
