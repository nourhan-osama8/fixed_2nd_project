<<<<<<< HEAD
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List, Optional

_ENV_PATH = Path(__file__).resolve().parent.parent.parent / ".env"
=======
from __future__ import annotations

import os
from pathlib import Path

from pydantic_settings import BaseSettings
from typing import List
>>>>>>> origin/main

# ── Backend root directory (absolute, regardless of CWD) ──────────────────────
# This file lives at: backend/app/core/config.py
# BACKEND_ROOT  →  backend/
_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    # App
    APP_NAME: str = "NileConnect AI Contact Center"
    DEBUG: bool = True
    ENVIRONMENT: str = "development"

    # Database
    DATABASE_URL: str

    # JWT
    SECRET_KEY: str = "change-me-to-a-long-random-secret-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 hours

    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:8501"

    # Storage — relative values from .env are resolved against BACKEND_ROOT
    UPLOAD_DIR: str = "uploads"

    # URLs
    FRONTEND_URL: str = "http://localhost:8501"
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
<<<<<<< HEAD
    PUBLIC_BASE_URL: str = "http://localhost:8000"

    # Phase 2 — AI
    OPENAI_API_KEY: Optional[str] = None
    EMBEDDING_MODEL: Optional[str] = None
    VECTOR_DB_URL: Optional[str] = None

    # Phase 3 — Telephony (Twilio legacy transport)
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_PHONE_NUMBER: Optional[str] = None

    # Telegram Bot Transport
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_WEBHOOK_SECRET: Optional[str] = None
=======
    # Public base URL used by Twilio webhooks — set to your ngrok/tunnel URL in production
    PUBLIC_BASE_URL: str = "http://localhost:8000"

    # ── AI / LLM ──────────────────────────────────────────────────────────────
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "openai/gpt-oss-20b"
    TAVILY_API_KEY: str = ""

    # ── RAG ───────────────────────────────────────────────────────────────────
    RAG_DOCS_DIR: str = "uploads/rag_docs"
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"

    # ── Resolved absolute paths ────────────────────────────────────────────────
    @property
    def upload_dir_abs(self) -> str:
        """Absolute path to the uploads directory."""
        p = Path(self.UPLOAD_DIR)
        return str(p if p.is_absolute() else _BACKEND_ROOT / p)

    @property
    def rag_docs_dir_abs(self) -> str:
        """Absolute path to the RAG documents directory."""
        p = Path(self.RAG_DOCS_DIR)
        return str(p if p.is_absolute() else _BACKEND_ROOT / p)
>>>>>>> origin/main

    @property
    def allowed_origins_list(self) -> List[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",")]

    model_config = {
        "env_file": str(_ENV_PATH) if _ENV_PATH.exists() else ".env",
        "case_sensitive": True,
        "extra": "ignore",
    }


settings = Settings()

