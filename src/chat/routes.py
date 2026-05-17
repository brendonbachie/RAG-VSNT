"""Chat routes: GET / (chat UI), POST /chat, POST /chat/reset."""

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import TEMPLATES_DIR
from src.db.database import get_db
from src.models.system_settings import SystemSettings
from src.auth.service import require_auth
from src.models.user import User
from src.chat.engine import get_engine, get_active_model, invalidate_engine
from src.audit.logger import log_query

router = APIRouter()
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


class ChatRequest(BaseModel):
    question: str

    @field_validator("question")
    @classmethod
    def question_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Pergunta não pode ser vazia.")
        if len(v) > 2000:
            raise ValueError("Pergunta muito longa (máx. 2000 caracteres).")
        return v


@router.get("/", response_class=HTMLResponse)
async def chat_page(request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SystemSettings).where(SystemSettings.key == "setup_complete"))
    row = result.scalar_one_or_none()
    if not row or row.value != "true":
        return HTMLResponse(status_code=302, headers={"Location": "/setup"})

    current_user = getattr(request.state, "current_user", None)
    return templates.TemplateResponse("chat.html", {
        "request": request,
        "current_user": current_user,
        "messages": [],
    })


@router.post("/chat")
async def chat_submit(
    request: Request,
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    current_user: User = getattr(request.state, "current_user", None)

    active_model = await get_active_model(db)
    try:
        engine = get_engine(active_model)
        response = engine.chat(body.question)
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="Serviço LLM indisponível. Verifique se o Ollama está rodando."
        ) from exc

    sources = []
    seen = set()
    if response.source_nodes:
        for node in response.source_nodes:
            src = node.metadata.get("file_name", "")
            if src and src not in seen:
                sources.append(src)
                seen.add(src)

    if current_user:
        await log_query(db, current_user.id, current_user.username,
                        body.question, str(response.response), sources, active_model)

    return JSONResponse({"answer": str(response.response), "sources": sources, "model": active_model})


@router.post("/chat/reset")
async def chat_reset(request: Request):
    current_user: User = getattr(request.state, "current_user", None)
    active_model_key = getattr(request.state, "active_model", "llama3")
    try:
        from src.chat.engine import _engine_instance
        if _engine_instance is not None:
            _engine_instance.reset()
    except Exception:
        pass
    return JSONResponse({"status": "cleared"})
