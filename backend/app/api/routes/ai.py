"""
AI routes:
  POST /api/v1/ai/ask          — ask the agent a question (any authenticated user)
  POST /api/v1/ai/rag/rebuild  — force RAG index rebuild (admin only)
  GET  /api/v1/ai/rag/status   — RAG index status (admin only)
"""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.dependencies import get_current_user, require_admin
from app.models.user import User
from app.ai.agent.agent import ask_agent
from app.ai.rag.pipeline import rag
from app.core.config import settings

logger = logging.getLogger("nileconnect")

router = APIRouter(prefix="/ai")


# ── Schemas ───────────────────────────────────────────────────────────────────

class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)


class AskResponse(BaseModel):
    answer: str


class RagStatusResponse(BaseModel):
    is_ready: bool
    document_count: int
    docs_dir: str


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/ask", response_model=AskResponse)
async def ask(
    body: AskRequest,
    current_user: User = Depends(get_current_user),
) -> AskResponse:
    """
    Ask the AI agent a question.

    Runs the blocking agent loop in a thread-pool worker so uvicorn's
    async event loop is never blocked — this prevents timeouts on other
    concurrent requests while one long-running agent call is in flight.
    """
    logger.info("AI ask from user=%s: %s", current_user.email, body.question[:100])
    answer = await asyncio.to_thread(ask_agent, body.question)
    return AskResponse(answer=answer)


@router.post("/rag/rebuild", status_code=200)
def rebuild_rag(
    current_user: User = Depends(require_admin),
) -> dict:
    """Trigger a full rebuild of the RAG index (admin only)."""
    logger.info("RAG rebuild triggered by admin: %s", current_user.email)
    rag.build()
    return {"message": f"RAG index rebuilt. {rag.document_count} chunks indexed."}


@router.get("/rag/status", response_model=RagStatusResponse)
def rag_status(
    current_user: User = Depends(require_admin),
) -> RagStatusResponse:
    """Return RAG index status (admin only)."""
    return RagStatusResponse(
        is_ready=rag.is_ready,
        document_count=rag.document_count,
        docs_dir=settings.rag_docs_dir_abs,
    )
