"""
Testing script for Telegram Voice/Text AI Follow-up demonstration.

Proves the AI logic and call flow functions work by testing on Telegram.
"""
from app.core.constants import FollowupResult
from app.core.database import SessionLocal
from app.telephony.call_flows.no_flow import handle_no
from app.telephony.call_flows.yes_flow import handle_yes
from app.telephony.call_flows.unknown_flow import MAX_ATTEMPTS
from app.telephony.stt.arabic_classifier import classify_response
from app.telephony.vonage.response import GREETING_DEFAULT_TEXT, NOT_UNDERSTOOD_TEXT
from app.core.config import settings

BOT_TOKEN = settings.TELEGRAM_BOT_TOKEN or ""

FOLLOWUP_ID = None
CALL_ID = None