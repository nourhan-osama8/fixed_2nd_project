"""
Telegram Webhook Route for NileConnect AI Contact Center.

Receives updates from Telegram Bot API and routes text & voice messages
through the Voice-AI and Call Flow pipelines.
"""
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, Header, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.logging import logger
from app.telephony.telegram.adapter import TelegramAdapter
from app.telephony.telegram.client import get_telegram_client

router = APIRouter(prefix="/telephony/telegram")


@router.post("/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """
    Main webhook endpoint registered with Telegram Bot API.
    Handles /start, normal text messages, and voice messages.
    """
    # Verify secret token if configured
    if settings.TELEGRAM_WEBHOOK_SECRET and x_telegram_bot_api_secret_token != settings.TELEGRAM_WEBHOOK_SECRET:
        logger.warning("[Telegram] Unauthorized webhook call: secret token mismatch")
        return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content={"detail": "Invalid secret token"})

    try:
        update: Dict[str, Any] = await request.json()
    except Exception as e:
        logger.error("[Telegram] Invalid JSON in webhook request: %s", e)
        return {"ok": True}

    update_id = update.get("update_id")
    message = update.get("message") or update.get("edited_message")

    if not message:
        logger.info("[Telegram] Non-message update received (update_id: %s)", update_id)
        return {"ok": True}

    chat = message.get("chat", {})
    chat_id = chat.get("id")
    from_user = message.get("from", {})

    if not chat_id:
        logger.warning("[Telegram] Message received without chat_id")
        return {"ok": True}

    adapter = TelegramAdapter(db)

    # 1. Voice message handling
    voice = message.get("voice") or message.get("audio")
    if voice:
        file_id = voice.get("file_id")
        if file_id:
            adapter.process_voice_message(chat_id=chat_id, file_id=file_id, user_info=from_user)
            return {"ok": True}

    # 2. Text message handling
    text = message.get("text")
    if text is not None:
        adapter.process_text_message(chat_id=chat_id, text=text, user_info=from_user)
        return {"ok": True}

    logger.info("[Telegram] Unsupported message content type received for chat %s", chat_id)
    return {"ok": True}


@router.post("/register")
def register_telegram_webhook(
    webhook_url: Optional[str] = None,
    secret_token: Optional[str] = None,
):
    """
    Helper endpoint to register the public HTTPS webhook URL with Telegram Bot API.
    """
    client = get_telegram_client()
    url = webhook_url or f"{settings.PUBLIC_BASE_URL}/api/v1/telephony/telegram/webhook"
    secret = secret_token or settings.TELEGRAM_WEBHOOK_SECRET
    result = client.set_webhook(webhook_url=url, secret_token=secret)
    return result


@router.get("/info")
def get_telegram_webhook_info():
    """
    Helper endpoint to inspect current Telegram webhook registration status.
    """
    client = get_telegram_client()
    return client.get_webhook_info()


@router.post("/delete")
def delete_telegram_webhook():
    """
    Helper endpoint to delete Telegram webhook registration (e.g. to switch to polling or reset).
    """
    client = get_telegram_client()
    return client.delete_webhook(drop_pending_updates=True)
