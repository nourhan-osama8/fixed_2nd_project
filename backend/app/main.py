import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
<<<<<<< HEAD
from app.api.routes import (
    auth,
    users,
    customers,
    cases,
    calls,
    followups,
    documents,
    reports,
    audit_logs,
    health,
)
from app.telephony.webhooks import (
    incoming as telephony_incoming,
    speech as telephony_speech,
    status as telephony_status,
    telegram as telephony_telegram,
)
=======
from app.telephony.webhooks import incoming as telephony_incoming
>>>>>>> origin/main

from app.core.config import settings
from app.core.logging import setup_logging, logger
from app.core.database import create_all_tables

from app.api.routes import (
    auth,
    users,
    customers,
    cases,
    calls,
    followups,
    documents,
    reports,
    audit_logs,
    health,
    ai,
    success_metrics,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown events."""
    setup_logging()
    logger.info("Starting NileConnect AI Contact Center backend...")

    # Ensure upload directory exists (uses absolute path, independent of CWD)
    upload_dir = settings.upload_dir_abs
    os.makedirs(upload_dir, exist_ok=True)
    logger.info(f"Upload directory: {upload_dir}")

    # Ensure RAG docs directory exists
    rag_dir = settings.rag_docs_dir_abs
    os.makedirs(rag_dir, exist_ok=True)
    logger.info(f"RAG docs directory: {rag_dir}")

    # Create database tables
    create_all_tables()
    logger.info("Database tables ready.")

    # ── Pre-warm RAG index in background so the server starts fast ────────────
    def _warm_rag() -> None:
        try:
            from app.ai.rag.pipeline import rag
            logger.info("RAG: starting index build at startup...")
            rag.build()
            logger.info(
                "RAG: startup build complete — %d chunks indexed.", rag.document_count
            )
        except Exception as exc:
            logger.error("RAG: startup build failed: %s", exc)

    import threading
    threading.Thread(target=_warm_rag, daemon=True, name="rag-startup").start()

    yield

    logger.info("Backend shutting down.")



app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="AI-powered Telecom/ISP Contact Center — Phase 1 API",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── CORS ───────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ────────────────────────────────────────────────────────────────────
PREFIX = "/api/v1"

app.include_router(health.router,              prefix=PREFIX, tags=["Health"])
app.include_router(auth.router,               prefix=PREFIX, tags=["Authentication"])
app.include_router(users.router,              prefix=PREFIX, tags=["Users"])
app.include_router(customers.router,          prefix=PREFIX, tags=["Customers"])
app.include_router(cases.router,              prefix=PREFIX, tags=["Cases"])
app.include_router(calls.router,              prefix=PREFIX, tags=["Calls"])
app.include_router(followups.router,          prefix=PREFIX, tags=["Follow-ups"])
app.include_router(documents.router,          prefix=PREFIX, tags=["Documents"])
app.include_router(reports.router,            prefix=PREFIX, tags=["Reports"])
app.include_router(audit_logs.router,         prefix=PREFIX, tags=["Audit Logs"])
app.include_router(ai.router,                prefix=PREFIX, tags=["AI Assistant"])
app.include_router(telephony_incoming.router, prefix=PREFIX, tags=["Telephony"])
<<<<<<< HEAD
app.include_router(telephony_speech.router,   prefix=PREFIX, tags=["Telephony"])
app.include_router(telephony_status.router,   prefix=PREFIX, tags=["Telephony"])
app.include_router(telephony_telegram.router, prefix=PREFIX, tags=["Telephony"])
=======
app.include_router(success_metrics.router,    prefix=PREFIX, tags=["Success Metrics"])


>>>>>>> origin/main

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled error on {request.method} {request.url}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred."},
    )
