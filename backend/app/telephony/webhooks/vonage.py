"""
Vonage Voice API Webhooks for NileConnect AI Contact Center.

Handles Vonage Voice Call Control lifecycle:
- /answer: Dispatches initial NCCO on call connection.
- /speech: Processes customer speech from Vonage ASR, runs Arabic classifier,
           executes transport-independent call flows, and returns next NCCO.
- /event:  Tracks call lifecycle statuses (completed, busy, failed, no-answer).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.constants import CallOutcome, FollowupResult, FollowupStatus
from app.core.database import get_db
from app.core.logging import logger
from app.repositories.call_repository import CallRepository
from app.repositories.followup_repository import FollowupRepository
from app.telephony.call_flows.no_flow import handle_no
from app.telephony.call_flows.unknown_flow import handle_unknown
from app.telephony.call_flows.yes_flow import handle_yes
from app.telephony.stt.arabic_classifier import classify_response
from app.telephony.vonage.response import (
    build_escalate_ncco,
    build_greeting_ncco,
    build_no_answer_ncco,
    build_resolved_ncco,
    build_retry_ncco,
)

router = APIRouter(prefix="/telephony/vonage")

# Statuses indicating that the customer never answered or the call could not complete
NO_CONNECT_STATUSES = {"busy", "failed", "timeout", "rejected", "unanswered", "cancelled"}


@router.api_route("/answer", methods=["GET", "POST"])
async def handle_vonage_answer(
    request: Request,
    followup_id: Optional[UUID] = Query(None),
    call_id: Optional[UUID] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Called when customer answers the outbound call.
    Returns the initial NCCO containing the dynamic Arabic greeting and ASR speech gather.
    """
    logger.info("Vonage Answer webhook received: followup_id=%s, call_id=%s", followup_id, call_id)

    speech_webhook_url = (
        f"{settings.PUBLIC_BASE_URL}/api/v1/telephony/vonage/speech"
        f"?followup_id={followup_id}&call_id={call_id}&attempt=1"
    )

    ncco = build_greeting_ncco(speech_webhook_url=speech_webhook_url)
    return JSONResponse(content=ncco)


@router.post("/speech")
async def handle_vonage_speech(
    request: Request,
    followup_id: UUID = Query(...),
    call_id: UUID = Query(...),
    attempt: int = Query(1),
    db: Session = Depends(get_db),
):
    """
    Webhook called by Vonage when the customer speaks their reply.
    Receives transcribed speech text, classifies Arabic response into YES/NO/UNKNOWN,
    executes corresponding call flow, and returns the next NCCO.
    """
    try:
        body: Dict[str, Any] = await request.json()
    except Exception:
        body = {}

    speech_obj = body.get("speech", {})
    results = speech_obj.get("results", [])
    speech_text = results[0].get("text", "").strip() if results else ""

    logger.info(
        "Vonage Speech webhook: followup=%s call=%s attempt=%d text=%r",
        followup_id, call_id, attempt, speech_text
    )

    # 1. Update Call transcript
    call_repo = CallRepository(db)
    call = call_repo.get_by_id(call_id)
    if call and speech_text:
        current_transcript = call.transcript or ""
        call.transcript = (current_transcript + f"\nCustomer: {speech_text}").strip()
        call_repo.update(call)

    # 2. Classify response
    if not speech_text:
        # No speech captured or silence timeout
        logger.warning("Vonage Speech webhook received empty speech text")
        result = FollowupResult.UNKNOWN
    else:
        result = classify_response(speech_text)

    logger.info("Vonage Speech classified as: %s", result.value)

    # 3. Route to call flows
    if result == FollowupResult.YES:
        handle_yes(db, followup_id, call_id)
        return JSONResponse(content=build_resolved_ncco())

    elif result == FollowupResult.NO:
        handle_no(db, followup_id, call_id)
        return JSONResponse(content=build_escalate_ncco())

    else:
        # Unknown / ambiguous response
        resp_text, is_retry = handle_unknown(db, followup_id, call_id, attempt=attempt)
        if is_retry:
            next_attempt = attempt + 1
            retry_speech_url = (
                f"{settings.PUBLIC_BASE_URL}/api/v1/telephony/vonage/speech"
                f"?followup_id={followup_id}&call_id={call_id}&attempt={next_attempt}"
            )
            return JSONResponse(content=build_retry_ncco(speech_webhook_url=retry_speech_url, retry_text=resp_text))
        else:
            return JSONResponse(content=build_escalate_ncco(message=resp_text))


@router.post("/event")
async def handle_vonage_event(
    request: Request,
    followup_id: Optional[UUID] = Query(None),
    call_id: Optional[UUID] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Webhook called by Vonage on call events (ringing, answered, completed, busy, failed, timeout).
    """
    try:
        body: Dict[str, Any] = await request.json()
    except Exception:
        body = {}

    call_status = body.get("status", "")
    duration_str = body.get("duration")
    logger.info("Vonage Event webhook: followup=%s call=%s status=%s", followup_id, call_id, call_status)

    call_repo = CallRepository(db)
    followup_repo = FollowupRepository(db)

    now = datetime.now(timezone.utc)

    # Update call duration on completion if provided
    if call_id and duration_str:
        call = call_repo.get_by_id(call_id)
        if call:
            try:
                call.duration = int(duration_str)
                call_repo.update(call)
            except ValueError:
                pass

    if call_status in NO_CONNECT_STATUSES:
        logger.warning("Vonage call failed to connect with status %s", call_status)
        if call_id:
            call = call_repo.get_by_id(call_id)
            if call and call.outcome == CallOutcome.PENDING:
                call.outcome = CallOutcome.NO_ANSWER
                call.ended_at = now
                call_repo.update(call)

        if followup_id:
            followup = followup_repo.get_by_id(followup_id)
            if followup and followup.status == FollowupStatus.IN_PROGRESS:
                followup.status = FollowupStatus.FAILED
                followup.result = FollowupResult.NO_ANSWER
                followup.completed_at = now
                followup_repo.update(followup)

    return {"ok": True}
