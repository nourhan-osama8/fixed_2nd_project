"""
Text-to-Speech (TTS) Service for NileConnect Voice-AI.

Synthesizes Arabic response text into audio bytes (MP3/OGG format)
to be sent back to the customer over Telegram (or other telephony channels).
Uses gTTS (Google Translate Arabic TTS) and optionally OpenAI TTS when configured.
"""
import io
from typing import Optional
import httpx

from app.core.config import settings
from app.core.logging import logger

try:
    from gtts import gTTS
    HAS_GTTS = True
except ImportError:
    HAS_GTTS = False


class TTSService:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.OPENAI_API_KEY

    def synthesize_speech(
        self,
        text: str,
        language: str = "ar",
        voice: str = "alloy",
    ) -> bytes:
        """
        Synthesize text into audio bytes.

        Logs:
            [TTS] Generating audio
            [TTS] Audio generated
        """
        logger.info("[TTS] Generating audio (text_len: %d chars, lang: %s)", len(text), language)

        if not text or not text.strip():
            logger.warning("[TTS] Empty text provided for TTS")
            return b""

        # Option 1: OpenAI TTS (if API key configured)
        if self.api_key:
            try:
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                }
                payload = {
                    "model": "tts-1",
                    "input": text,
                    "voice": voice,
                    "response_format": "mp3",
                }
                with httpx.Client(timeout=30.0) as client:
                    response = client.post(
                        "https://api.openai.com/v1/audio/speech",
                        headers=headers,
                        json=payload,
                    )
                    response.raise_for_status()
                    audio_bytes = response.content
                    logger.info("[TTS] Audio generated via OpenAI TTS (size: %d bytes)", len(audio_bytes))
                    return audio_bytes
            except Exception as e:
                logger.warning("[TTS] OpenAI TTS failed, falling back to gTTS: %s", e)

        # Option 2: gTTS (built-in, no API key needed, high-quality Arabic)
        if HAS_GTTS:
            try:
                tts = gTTS(text=text, lang=language, slow=False)
                fp = io.BytesIO()
                tts.write_to_fp(fp)
                audio_bytes = fp.getvalue()
                logger.info("[TTS] Audio generated via gTTS (size: %d bytes)", len(audio_bytes))
                return audio_bytes
            except Exception as e:
                logger.error("[TTS] gTTS synthesis error: %s", e)

        # Fallback empty audio
        logger.warning("[TTS] No TTS engine succeeded; returning empty audio bytes")
        return b""


_tts_service_instance: Optional[TTSService] = None


def get_tts_service() -> TTSService:
    global _tts_service_instance
    if _tts_service_instance is None:
        _tts_service_instance = TTSService()
    return _tts_service_instance


def synthesize_speech(text: str, language: str = "ar") -> bytes:
    """Convenience functional interface for TTS synthesis."""
    return get_tts_service().synthesize_speech(text, language=language)