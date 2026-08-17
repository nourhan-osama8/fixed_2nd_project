"""
Telegram transport package for NileConnect telephony integration.
"""
from app.telephony.telegram.client import TelegramClient, get_telegram_client
from app.telephony.telegram.adapter import TelegramAdapter

__all__ = ["TelegramClient", "get_telegram_client", "TelegramAdapter"]
