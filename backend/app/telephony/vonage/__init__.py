"""
Vonage Telephony Integration Package.
"""
from app.telephony.vonage.client import get_vonage_client, create_outbound_call
from app.telephony.vonage.response import (
    build_greeting_ncco,
    build_retry_ncco,
    build_resolved_ncco,
    build_escalate_ncco,
    build_no_answer_ncco,
    GOODBYE_RESOLVED_TEXT,
    GOODBYE_ESCALATE_TEXT,
    NOT_UNDERSTOOD_TEXT,
    GREETING_DEFAULT_TEXT,
)

__all__ = [
    "get_vonage_client",
    "create_outbound_call",
    "build_greeting_ncco",
    "build_retry_ncco",
    "build_resolved_ncco",
    "build_escalate_ncco",
    "build_no_answer_ncco",
    "GOODBYE_RESOLVED_TEXT",
    "GOODBYE_ESCALATE_TEXT",
    "NOT_UNDERSTOOD_TEXT",
    "GREETING_DEFAULT_TEXT",
]
