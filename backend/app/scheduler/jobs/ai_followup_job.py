"""
Scheduled Job for Outbound AI Voice Follow-ups.

Periodically queries all eligible Cases (CaseStatus.AI_FOLLOW_UP_SCHEDULED)
and triggers the AI follow-up workflow via AIFollowupService.
"""
from __future__ import annotations

from typing import Any, Dict, List
from app.core.database import SessionLocal
from app.core.logging import logger
from app.services.ai_followup_service import AIFollowupService


def run_ai_followups_job() -> List[Dict[str, Any]]:
    """
    Executes a single cycle of the AI outbound follow-up scheduler.
    Finds all eligible cases and triggers outbound calls via Vonage.
    """
    logger.info("[Scheduler] Starting AI Outbound Follow-up job...")
    db = SessionLocal()
    try:
        service = AIFollowupService(db)
        results = service.trigger_all_scheduled_followups()
        logger.info("[Scheduler] AI Outbound Follow-up job completed with %d results", len(results))
        return results
    except Exception as exc:
        logger.exception("[Scheduler] Error running AI Outbound Follow-up job: %s", exc)
        return []
    finally:
        db.close()
