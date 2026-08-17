"""
Call flow branch: customer confirmed the issue IS resolved (YES).

Updates in order:
- Call.outcome -> RESOLVED, Call.ended_at -> now
- AIFollowup.status -> COMPLETED, AIFollowup.result -> YES, AIFollowup.completed_at -> now
- Case.status -> RESOLVED, Case.resolved_at -> now

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
from app.telephony.vonage.response import GOODBYE_RESOLVED_TEXT


def handle_yes(db: Session, followup_id: Optional[UUID], call_id: Optional[UUID]) -> str:
    """
    Executes business logic for YES outcome.
    Marks the call resolved, followup completed with YES, and case resolved.
    """
    followup_repo = FollowupRepository(db)
    call_repo = CallRepository(db)
    case_repo = CaseRepository(db)

    now = datetime.now(timezone.utc)

    if call_id:
        call = call_repo.get_by_id(call_id)
        if call:
            call.outcome = CallOutcome.RESOLVED
            call.ended_at = now
            call_repo.update(call)
            logger.info("Call %s updated: outcome=RESOLVED", call_id)

    if followup_id:
        followup = followup_repo.get_by_id(followup_id)
        if followup:
            followup.status = FollowupStatus.COMPLETED
            followup.result = FollowupResult.YES
            followup.completed_at = now
            followup_repo.update(followup)
            logger.info("AIFollowup %s updated: status=COMPLETED, result=YES", followup_id)

            case = case_repo.get_by_id(followup.case_id)
            if case:
                case.status = CaseStatus.RESOLVED
                case.resolved_at = now
                case_repo.update(case)
                logger.info("Case %s updated: status=RESOLVED", case.id)

    return GOODBYE_RESOLVED_TEXT