"""
Call flow branch: customer indicated the issue is NOT resolved (NO) or requested human assistance.

Escalates to human:
- Call.outcome -> ESCALATED, Call.ended_at -> now
- AIFollowup.status -> COMPLETED, AIFollowup.result -> NO, AIFollowup.completed_at -> now
- Case.status -> NEEDS_HUMAN (escalates the existing case, NEVER creates a new one)

Returns the Arabic response text to be rendered by the calling transport (Vonage NCCO or Telegram).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.constants import CallOutcome, CaseStatus, FollowupResult, FollowupStatus
from app.core.logging import logger
from app.repositories.call_repository import CallRepository
from app.repositories.case_repository import CaseRepository
from app.repositories.followup_repository import FollowupRepository
from app.telephony.vonage.response import GOODBYE_ESCALATE_TEXT


def handle_no(db: Session, followup_id: Optional[UUID], call_id: Optional[UUID]) -> str:
    """
    Executes business logic for NO outcome / human escalation.
    Marks the call escalated, followup completed with NO, and case escalated to NEEDS_HUMAN.
    """
    followup_repo = FollowupRepository(db)
    call_repo = CallRepository(db)
    case_repo = CaseRepository(db)

    now = datetime.now(timezone.utc)

    if call_id:
        call = call_repo.get_by_id(call_id)
        if call:
            call.outcome = CallOutcome.ESCALATED
            call.ended_at = now
            call_repo.update(call)
            logger.info("Call %s updated: outcome=ESCALATED", call_id)

    if followup_id:
        followup = followup_repo.get_by_id(followup_id)
        if followup:
            followup.status = FollowupStatus.COMPLETED
            followup.result = FollowupResult.NO
            followup.completed_at = now
            followup_repo.update(followup)
            logger.info("AIFollowup %s updated: status=COMPLETED, result=NO", followup_id)

            case = case_repo.get_by_id(followup.case_id)
            if case:
                case.status = CaseStatus.NEEDS_HUMAN
                case_repo.update(case)
                logger.info("Case %s escalated to status=NEEDS_HUMAN", case.id)

    return GOODBYE_ESCALATE_TEXT