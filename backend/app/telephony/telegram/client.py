"""
Telegram Bot API Client for NileConnect Transport Layer.

Provides clean HTTP communication with Telegram Bot API:
- Sending text messages
- Sending voice notes / audio responses
- Downloading voice messages
- Setting and checking webhook configuration

Safety: Bot token is NEVER exposed in logs.
"""
from functools import lru_cache
from typing import Optional, Dict, Any
import httpx

from app.core.config import settings
from app.core.logging import logger


class TelegramClient:
    def __init__(self, token: Optional[str] = None):
        self._token = token or settings.TELEGRAM_BOT_TOKEN
        if not self._token:
            logger.warning("[Telegram] TELEGRAM_BOT_TOKEN is not set in configuration")
        self._base_url = f"https://api.telegram.org/bot{self._token}"
        self._file_base_url = f"https://api.telegram.org/file/bot{self._token}"

    @property
    def is_configured(self) -> bool:
        return bool(self._token)

    def _safe_url_log(self, endpoint: str) -> str:
        return f"https://api.telegram.org/bot[REDACTED]/{endpoint}"

    def send_message(
        self,
        chat_id: int | str,
        text: str,
        parse_mode: Optional[str] = None,
        reply_to_message_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Send a text message to a Telegram chat.
        """
        if not self.is_configured:
            logger.error("[Telegram] Cannot send message: bot token not configured")
            return {"ok": False, "error": "Token not configured"}

        payload: Dict[str, Any] = {
            "chat_id": chat_id,
            "text": text,
        }
        if parse_mode:
            payload["parse_mode"] = parse_mode
        if reply_to_message_id:
            payload["reply_to_message_id"] = reply_to_message_id

        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.post(f"{self._base_url}/sendMessage", json=payload)
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            logger.error("[Telegram] Error sending message to chat %s: %s", chat_id, e)
            return {"ok": False, "error": str(e)}

    def send_voice(
        self,
        chat_id: int | str,
        voice_bytes: bytes,
        filename: str = "voice.mp3",
        caption: Optional[str] = None,
        duration: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Send a voice note or audio file to a Telegram chat.
        """
        if not self.is_configured:
            logger.error("[Telegram] Cannot send voice: bot token not configured")
            return {"ok": False, "error": "Token not configured"}

        if not voice_bytes:
            logger.warning("[Telegram] Cannot send empty voice bytes")
            return {"ok": False, "error": "Empty audio"}

        data: Dict[str, Any] = {"chat_id": str(chat_id)}
        if caption:
            data["caption"] = caption
        if duration:
            data["duration"] = str(duration)

        files = {
            "voice": (filename, voice_bytes, "audio/mpeg" if filename.endswith(".mp3") else "audio/ogg"),
        }

        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.post(f"{self._base_url}/sendVoice", data=data, files=files)
                # If sendVoice rejects MP3 format on older API versions, fall back to sendAudio
                if resp.status_code != 200:
                    files = {"audio": (filename, voice_bytes, "audio/mpeg")}
                    resp = client.post(f"{self._base_url}/sendAudio", data=data, files=files)
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            logger.error("[Telegram] Error sending voice to chat %s: %s", chat_id, e)
            return {"ok": False, "error": str(e)}

    def get_file(self, file_id: str) -> Dict[str, Any]:
        """
        Retrieve file metadata including file_path from Telegram.
        """
        if not self.is_configured:
            return {"ok": False, "error": "Token not configured"}

        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.get(f"{self._base_url}/getFile", params={"file_id": file_id})
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            logger.error("[Telegram] Error getting file info for file_id %s: %s", file_id, e)
            return {"ok": False, "error": str(e)}

    def download_file(self, file_path: str) -> bytes:
        """
        Download raw binary content of a file from Telegram.
        """
        if not self.is_configured:
            return b""

        download_url = f"{self._file_base_url}/{file_path}"
        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.get(download_url)
                resp.raise_for_status()
                return resp.content
        except Exception as e:
            logger.error("[Telegram] Error downloading file from %s: %s", file_path, e)
            return b""

    def set_webhook(
        self,
        webhook_url: str,
        secret_token: Optional[str] = None,
        drop_pending_updates: bool = False,
    ) -> Dict[str, Any]:
        """
        Register a public HTTPS webhook URL with Telegram Bot API.
        """
        if not self.is_configured:
            return {"ok": False, "description": "Token not configured"}

        payload: Dict[str, Any] = {
            "url": webhook_url,
            "drop_pending_updates": drop_pending_updates,
            "allowed_updates": ["message", "edited_message", "callback_query"],
        }
        if secret_token:
            payload["secret_token"] = secret_token

        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.post(f"{self._base_url}/setWebhook", json=payload)
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            logger.error("[Telegram] Error setting webhook: %s", e)
            return {"ok": False, "description": str(e)}

    def get_webhook_info(self) -> Dict[str, Any]:
        """
        Check current Telegram webhook status and diagnostic info.
        """
        if not self.is_configured:
            return {"ok": False, "description": "Token not configured"}

        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.get(f"{self._base_url}/getWebhookInfo")
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            logger.error("[Telegram] Error fetching webhook info: %s", e)
            return {"ok": False, "description": str(e)}

    def delete_webhook(self, drop_pending_updates: bool = False) -> Dict[str, Any]:
        """
        Remove current webhook registration from Telegram.
        """
        if not self.is_configured:
            return {"ok": False, "description": "Token not configured"}

        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.post(
                    f"{self._base_url}/deleteWebhook",
                    json={"drop_pending_updates": drop_pending_updates},
                )
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            logger.error("[Telegram] Error deleting webhook: %s", e)
            return {"ok": False, "description": str(e)}


@lru_cache(maxsize=1)
def get_telegram_client() -> TelegramClient:
    return TelegramClient()
