"""
NCCO Response Builder for Vonage Voice API (Arabic).

Constructs Vonage Call Control Objects (NCCO) for dynamic outbound follow-up calls,
Arabic speech synthesis (talk action), and speech recognition (input action).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

# Standard Arabic (Egypt / Gulf) voice language codes for Vonage Voice
VOICE_LANGUAGE = "ar-XA"       # TTS Language for Vonage
ASR_LANGUAGE = "ar-EG"         # STT Language for Speech Input

# Default static fallbacks for Arabic responses
GREETING_DEFAULT_TEXT = "أهلاً بيك، معاك نظام المتابعة الذكي من نايل كونكت. كنا حابين نتأكد هل المشكلة اللي كانت عندك اتحلت واستكملت الإجراءات ولا لسه؟"
NOT_UNDERSTOOD_TEXT = "معلش، ممكن تعيد تاني، اتحلت المشكلة ولا لأ؟"
GOODBYE_RESOLVED_TEXT = "تمام جدًا، شكرًا لوقتك. يوم سعيد."
GOODBYE_ESCALATE_TEXT = "تمام، هنبعت حد من فريقنا الفني يتواصل معاك تاني في أقرب وقت. شكرًا لوقتك."
NO_ANSWER_TEXT = "مفيش حد رد، هنحاول نتصل بحضرتك تاني لاحقًا. مع السلامة."


def build_greeting_ncco(speech_webhook_url: str, greeting_text: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Initial NCCO sent when the customer answers the call:
    1. Speaks the dynamic greeting / follow-up question.
    2. Listens for the customer's spoken reply via ASR and POSTs to speech_webhook_url.
    3. If timeout occurs with no speech, falls through to polite goodbye.
    """
    text = greeting_text or GREETING_DEFAULT_TEXT
    return [
        {
            "action": "talk",
            "text": text,
            "language": VOICE_LANGUAGE,
            "bargeIn": True,
        },
        {
            "action": "input",
            "type": ["speech"],
            "speech": {
                "language": ASR_LANGUAGE,
                "endOnSilence": 1.5,
            },
            "eventUrl": [speech_webhook_url],
            "eventMethod": "POST",
        },
        {
            "action": "talk",
            "text": NO_ANSWER_TEXT,
            "language": VOICE_LANGUAGE,
        },
    ]


def build_retry_ncco(speech_webhook_url: str, retry_text: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    NCCO played when customer speech is unclear / unclassified:
    Asks the customer to repeat once and captures their reply.
    """
    text = retry_text or NOT_UNDERSTOOD_TEXT
    return [
        {
            "action": "talk",
            "text": text,
            "language": VOICE_LANGUAGE,
            "bargeIn": True,
        },
        {
            "action": "input",
            "type": ["speech"],
            "speech": {
                "language": ASR_LANGUAGE,
                "endOnSilence": 1.5,
            },
            "eventUrl": [speech_webhook_url],
            "eventMethod": "POST",
        },
        {
            "action": "talk",
            "text": NO_ANSWER_TEXT,
            "language": VOICE_LANGUAGE,
        },
    ]


def build_resolved_ncco(message: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Terminal NCCO for YES branch (problem resolved):
    Confirms resolution with the customer and hangs up.
    """
    return [
        {
            "action": "talk",
            "text": message or GOODBYE_RESOLVED_TEXT,
            "language": VOICE_LANGUAGE,
        }
    ]


def build_escalate_ncco(message: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Terminal NCCO for NO / Escalate branch (problem persists or human requested):
    Informs the customer of human agent handoff and hangs up.
    """
    return [
        {
            "action": "talk",
            "text": message or GOODBYE_ESCALATE_TEXT,
            "language": VOICE_LANGUAGE,
        }
    ]


def build_no_answer_ncco(message: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Terminal NCCO for no response.
    """
    return [
        {
            "action": "talk",
            "text": message or NO_ANSWER_TEXT,
            "language": VOICE_LANGUAGE,
        }
    ]
