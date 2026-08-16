"""
Single entry point for triggering an AI follow-up call.

Delegates directly to AIFollowupService to ensure adherence to all business rules:
- Strictly reuses existing Cases
- Prevents duplicate AIFollowups and Calls
- Places the outbound call via Vonage Voice API using dynamic Arabic NCCO.
"""
from __future__ import annotations

from typing import Any, Dict
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.logging import logger
from app.services.ai_followup_service import AIFollowupService


def trigger_followup_by_case(db: Session, case_id: UUID) -> Dict[str, Any]:
    """
    Triggers an outbound AI follow-up call for the given existing Case ID.
    """
    service = AIFollowupService(db)
    return service.initiate_followup(case_id)


def trigger_followup_call(db: Session, followup_id: UUID) -> Dict[str, Any]:
    """
    Backward-compatible entry point for scheduled followup trigger.
    Looks up the case associated with the followup_id and initiates the call.
    """
    from app.repositories.followup_repository import FollowupRepository
    followup_repo = FollowupRepository(db)
    followup = followup_repo.get_by_id(followup_id)
    if not followup:
        logger.error("trigger_followup_call: AIFollowup %s not found", followup_id)
        return {"status": "error", "message": f"AIFollowup {followup_id} not found"}

    service = AIFollowupService(db)
    return service.initiate_followup(followup.case_id)