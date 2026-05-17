"""VSNT RAG Web Platform — FastAPI entry point."""

import asyncio
import shutil
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from config import (
    SERVER_HOST, SERVER_PORT, DOCS_DIR, DB_PATH,
    OLLAMA_MODEL, EMBED_MODEL, RERANK_MODEL,
    TEMPLATES_DIR, STATIC_DIR,
)
from src.db.database import init_db, AsyncSessionLocal
from src.models import DEFAULTS
from src.models.system_settings import SystemSettings


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _seed_defaults(session):
    """Insert missing SystemSettings defaults on first boot."""
    from sqlalchemy import select
    for key, value in DEFAULTS.items():
        result = await session.execute(select(SystemSettings).where(SystemSettings.key == key))
        if result.scalar_one_or_none() is None:
            session.add(SystemSettings(
                key=key,
                value=value,
                updated_at=datetime.now(timezone.utc),
            ))
    await session.commit()


async def _check_ollama_async():
    """Non-blocking Ollama health check — print warning, do not exit."""
    import urllib.request
    import json
    try:
        from config import OLLAMA_URL
        with urllib.request.urlopen(f"{OLLAMA_URL}/api/tags", timeout=3) as r:
            data = json.loads(r.read())
        models = [m["name"].split(":")[0] for m in data.get("models", [])]
        active = OLLAMA_MODEL
        if active not in models:
            print(f"⚠️  Modelo '{active}' não encontrado no Ollama. "
                  f"Disponíveis: {', '.join(models) or 'nenhum'}")
        else:
            print(f"✅ Ollama OK — modelo '{active}' disponível")
    except Exception:
        print("⚠️  Ollama não está rodando. Inicie com: ollama serve")
        print("   Consultas ao chat retornarão erro 503 até o Ollama iniciar.")


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure data/ directory exists
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    print(f"🔒 VSNT RAG Web Platform")
    print(f"   Server  : http://{SERVER_HOST}:{SERVER_PORT}")
    print(f"   Database: {DB_PATH}")
    print(f"   Docs    : {DOCS_DIR}")
    print(f"   LLM     : {OLLAMA_MODEL} via Ollama")
    print(f"   Embed   : {EMBED_MODEL}")

    await init_db()
    async with AsyncSessionLocal() as session:
        await _seed_defaults(session)

    await _check_ollama_async()

    # Start watchfiles folder watcher for docs/ auto-indexing (T032)
    async def _watch_docs():
        from watchfiles import awatch
        async for _ in awatch(str(DOCS_DIR)):
            async with AsyncSessionLocal() as s:
                from src.admin.indexer import run_indexing
                try:
                    await run_indexing(s)
                except Exception as e:
                    print(f"⚠️  Auto-indexing error: {e}")

    app.state.watcher_task = asyncio.create_task(_watch_docs())

    print(f"📡 Server started at http://{SERVER_HOST}:{SERVER_PORT}\n")
    yield

    # Cleanup
    if getattr(app.state, "watcher_task", None):
        app.state.watcher_task.cancel()


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(title="VSNT RAG", lifespan=lifespan)

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ── Auth middleware ───────────────────────────────────────────────────────────

PUBLIC_PATHS = {"/login", "/logout", "/setup"}

@app.middleware("http")
async def auth_guard(request: Request, call_next):
    path = request.url.path
    if path.startswith("/static") or path in PUBLIC_PATHS:
        return await call_next(request)

    from src.auth.session import get_session_data
    from src.auth.service import get_user_by_id
    from src.db.database import AsyncSessionLocal as Session

    session_data = get_session_data(request)
    if not session_data:
        return RedirectResponse("/login", status_code=302)

    # Attach current user to request state for route handlers
    async with Session() as db:
        user = await get_user_by_id(db, session_data.get("user_id"))
        if user is None or not user.is_active:
            response = RedirectResponse("/login", status_code=302)
            from src.auth.session import clear_session_cookie
            clear_session_cookie(response)
            return response
        request.state.current_user = user

    return await call_next(request)


# ── Exception handlers ────────────────────────────────────────────────────────

@app.exception_handler(403)
async def forbidden_handler(request: Request, exc):
    return templates.TemplateResponse(request, "403.html", {"current_user": getattr(request.state, "current_user", None), "messages": []}, status_code=403)

@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return templates.TemplateResponse(request, "404.html", {"current_user": getattr(request.state, "current_user", None), "messages": []}, status_code=404)


# ── Routers ───────────────────────────────────────────────────────────────────
from src.auth.routes import router as auth_router
from src.chat.routes import router as chat_router

app.include_router(auth_router)
app.include_router(chat_router)

# Admin — users (T028)
from src.admin.users import router as users_router
app.include_router(users_router)

@app.get("/admin")
async def admin_redirect():
    return RedirectResponse("/admin/documents", status_code=302)

# Admin — documents (T032)
from src.admin.documents import router as documents_router
app.include_router(documents_router)

# Admin — audit (T038)
from src.admin.audit import router as audit_router
app.include_router(audit_router)

# Admin — settings (T041)
from src.admin.settings import router as settings_router
app.include_router(settings_router)


if __name__ == "__main__":
    uvicorn.run("app:app", host=SERVER_HOST, port=SERVER_PORT, reload=False)
