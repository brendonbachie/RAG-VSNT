"""Admin document management routes."""

import os
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import DOCS_DIR, TEMPLATES_DIR, MAX_UPLOAD_BYTES, ALLOWED_EXTENSIONS
from src.db.database import get_db
from src.models.system_settings import SystemSettings
from src.models.audit_event import DOCUMENT_UPLOADED, DOCUMENT_DELETED, INDEX_TRIGGERED
from src.auth.service import require_admin
from src.audit.logger import log_auth_event
from src.admin.indexer import save_uploaded_file, run_indexing

router = APIRouter(prefix="/admin/documents")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def _list_docs():
    docs = []
    if DOCS_DIR.exists():
        for p in sorted(DOCS_DIR.iterdir()):
            if p.name.startswith("."):
                continue
            stat = p.stat()
            docs.append({
                "name": p.name,
                "ext": p.suffix.lower(),
                "size_bytes": stat.st_size,
                "size_human": _human_size(stat.st_size),
                "modified_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).strftime("%Y-%m-%d %H:%M"),
            })
    return docs


def _human_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f} {unit}"
        n /= 1024
    return f"{n:.1f} GB"


@router.get("", response_class=HTMLResponse)
async def documents_list(request: Request, db: AsyncSession = Depends(get_db)):
    require_admin(request)
    docs = _list_docs()
    result = await db.execute(select(SystemSettings).where(
        SystemSettings.key.in_(["indexing_status", "indexing_last_completed_at", "indexing_last_error"])
    ))
    settings = {row.key: row.value for row in result.scalars()}
    return templates.TemplateResponse(request, "admin/documents.html", {
        "current_user": request.state.current_user,
        "messages": [],
        "docs": docs,
        "indexing_status": settings.get("indexing_status", "idle"),
        "indexing_completed": settings.get("indexing_last_completed_at", ""),
        "indexing_error": settings.get("indexing_last_error", ""),
    })


@router.post("/upload")
async def documents_upload(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    require_admin(request)
    admin = request.state.current_user

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Tipo de arquivo não suportado: {ext}")

    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Arquivo muito grande (máx. 100 MB).")

    dest = DOCS_DIR / file.filename
    dest.write_bytes(content)

    await log_auth_event(db, DOCUMENT_UPLOADED, admin.id, admin.username,
                         filename=file.filename, size_bytes=len(content), format=ext.lstrip("."))

    async def _index():
        from src.db.database import AsyncSessionLocal
        async with AsyncSessionLocal() as s:
            await run_indexing(s)
            await log_auth_event(s, INDEX_TRIGGERED, admin.id, admin.username,
                                 trigger="upload", doc_count=len(_list_docs()))

    background_tasks.add_task(_index)
    return RedirectResponse("/admin/documents", status_code=302)


@router.post("/{filename}/delete")
async def documents_delete(
    filename: str,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    require_admin(request)
    admin = request.state.current_user

    target = DOCS_DIR / filename
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado.")

    target.unlink()
    await log_auth_event(db, DOCUMENT_DELETED, admin.id, admin.username, filename=filename)

    async def _index():
        from src.db.database import AsyncSessionLocal
        async with AsyncSessionLocal() as s:
            await run_indexing(s)
            await log_auth_event(s, INDEX_TRIGGERED, admin.id, admin.username,
                                 trigger="delete", doc_count=len(_list_docs()))

    background_tasks.add_task(_index)
    return RedirectResponse("/admin/documents", status_code=302)


@router.post("/reindex")
async def documents_reindex(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    require_admin(request)
    admin = request.state.current_user
    await log_auth_event(db, INDEX_TRIGGERED, admin.id, admin.username,
                         trigger="manual", doc_count=len(_list_docs()))

    async def _index():
        from src.db.database import AsyncSessionLocal
        async with AsyncSessionLocal() as s:
            await run_indexing(s)

    background_tasks.add_task(_index)
    return RedirectResponse("/admin/documents", status_code=302)


@router.get("/indexing-status")
async def indexing_status(request: Request, db: AsyncSession = Depends(get_db)):
    require_admin(request)
    result = await db.execute(select(SystemSettings).where(
        SystemSettings.key.in_(["indexing_status", "indexing_started_at",
                                 "indexing_last_completed_at", "indexing_last_error"])
    ))
    s = {row.key: row.value for row in result.scalars()}
    return JSONResponse({
        "status":       s.get("indexing_status", "idle"),
        "started_at":   s.get("indexing_started_at") or None,
        "completed_at": s.get("indexing_last_completed_at") or None,
        "error":        s.get("indexing_last_error") or None,
    })
