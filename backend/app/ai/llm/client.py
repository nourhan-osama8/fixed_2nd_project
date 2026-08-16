"""
Groq LLM client — thin singleton wrapper.

Usage:
    from app.ai.llm.client import groq_client
    response = groq_client.chat.completions.create(...)
"""

from groq import Groq
from app.core.config import settings

# ── Singleton ─────────────────────────────────────────────────────────────────

def _make_client() -> Groq:
    if not settings.GROQ_API_KEY:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Add it to backend/.env"
        )
    return Groq(api_key=settings.GROQ_API_KEY)


groq_client: Groq = _make_client()
