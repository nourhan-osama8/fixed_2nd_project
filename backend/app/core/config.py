from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional

from pydantic_settings import BaseSettings

# ── Backend root directory (absolute, regardless of CWD) ──────────────────────
# This file lives at: backend/app/core/config.py
# BACKEND_ROOT  →  backend/
_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
_ENV_PATH = _BACKEND_ROOT / ".env"


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
    PUBLIC_BASE_URL: str = "http://localhost:8000"

    # ── AI / LLM ──────────────────────────────────────────────────────────────
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "openai/gpt-oss-20b"
    TAVILY_API_KEY: str = ""
    OPENAI_API_KEY: Optional[str] = None
    VECTOR_DB_URL: Optional[str] = None

    # ── RAG ───────────────────────────────────────────────────────────────────
    RAG_DOCS_DIR: str = "uploads/rag_docs"
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"

    # ── Telephony: Vonage (Sole Voice Provider) ──────────────────────────────
    VONAGE_API_KEY: Optional[str] = None
    VONAGE_API_SECRET: Optional[str] = None
    VONAGE_APPLICATION_ID: Optional[str] = None
    VONAGE_PRIVATE_KEY_PATH: str = "app/telephony/vonage/private.key"
    VONAGE_PHONE_NUMBER: Optional[str] = None

    # ── Testing Transport: Telegram ───────────────────────────────────────────
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_WEBHOOK_SECRET: Optional[str] = None

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

    @property
    def vonage_private_key_abs(self) -> str:
        """Absolute path to the Vonage application private key file."""
        p = Path(self.VONAGE_PRIVATE_KEY_PATH)
        return str(p if p.is_absolute() else _BACKEND_ROOT / p)

    @property
    def allowed_origins_list(self) -> List[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",")]

    model_config = {
        "env_file": str(_ENV_PATH) if _ENV_PATH.exists() else ".env",
        "case_sensitive": True,
        "extra": "ignore",
    }


settings = Settings()
