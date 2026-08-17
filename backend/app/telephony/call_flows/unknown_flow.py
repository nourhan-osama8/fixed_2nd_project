"""
Call flow branch: speech was captured but not confidently classified as YES or NO.

Policy: give the customer one chance to repeat themselves (MAX_ATTEMPTS = 2).
If still unclear after retries, fail safe by escalating to a human rather
than guessing — same outcome/logic as the NO flow.
"""
from __future__ import annotations

from typing import Optional, Tuple
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.logging import logger
from app.telephony.call_flows.no_flow import handle_no
from app.telephony.vonage.response import NOT_UNDERSTOOD_TEXT

MAX_ATTEMPTS = 2


def handle_unknown(
    db: Session,
    followup_id: Optional[UUID],
    call_id: Optional[UUID],
    attempt: int = 1,
) -> Tuple[str, bool]:
    """
    Handles ambiguous / unclassified customer response.
    
    Returns:
        Tuple of (response_text: str, is_retry: bool)
        - If is_retry is True: the caller should ask the customer to repeat.
        - If is_retry is False: retry budget exhausted; case has been escalated to human.
    """
    logger.info("Handling UNKNOWN speech for followup=%s call=%s attempt=%d", followup_id, call_id, attempt)

    if attempt < MAX_ATTEMPTS:
        return NOT_UNDERSTOOD_TEXT, True

    # Out of retries — fail safe to human escalation rather than guessing.
    logger.info("Max retries exceeded for followup=%s. Escalating to human agent.", followup_id)
    escalate_text = handle_no(db, followup_id, call_id)
    return escalate_text, False