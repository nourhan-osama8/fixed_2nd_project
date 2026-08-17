"""
AI Follow-up Orchestration Service for NileConnect AI Contact Center.

Handles the end-to-end orchestration of outbound AI follow-up calls:
1. Identifies existing eligible cases in PostgreSQL (status == AI_FOLLOW_UP_SCHEDULED).
2. Verifies eligibility and retrieves existing Customer details.
3. Finds or reuses an existing AIFollowup (idempotent, prevents duplicate follow-ups).
4. Finds or creates an OUTBOUND_AI Call linked to the existing Case.
5. Builds a dynamic Arabic greeting referencing the customer's specific issue.
6. Dispatches the outbound call via the Vonage Voice API using NCCO.
7. Tracks initiation status and supports retries/failures gracefully.
8. CRITICAL RULE: NEVER creates a new Case — the existing Case is the single source of truth.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.constants import CallOutcome, CallType, CaseStatus, FollowupStatus
from app.core.exceptions import NotFoundError, BadRequestError
from app.core.logging import logger
from app.models.ai_followup import AIFollowup
from app.models.call import Call
from app.models.case import Case
from app.models.customer import Customer
from app.repositories.call_repository import CallRepository
from app.repositories.case_repository import CaseRepository
from app.repositories.customer_repository import CustomerRepository
from app.repositories.followup_repository import FollowupRepository
from app.telephony.vonage.client import create_outbound_call
from app.telephony.vonage.response import build_greeting_ncco, GREETING_DEFAULT_TEXT


class AIFollowupService:
    def __init__(self, db: Session):
        self.db = db
        self.case_repo = CaseRepository(db)
        self.customer_repo = CustomerRepository(db)
        self.followup_repo = FollowupRepository(db)
        self.call_repo = CallRepository(db)

    def get_eligible_cases(self, limit: int = 100) -> List[Case]:
        """
        Queries all existing Cases eligible for AI follow-up:
        status == CaseStatus.AI_FOLLOW_UP_SCHEDULED
        """
        return self.case_repo.get_ai_followup_cases(limit=limit)

    def build_dynamic_greeting(
        self,
        case: Case,
        customer: Optional[Customer] = None,
        previous_call: Optional[Call] = None,
    ) -> str:
        """
        Generates dynamic Arabic greeting text incorporating customer name,
        case issue, and previous call summary if available.
        """
        cust = customer or (case.customer if hasattr(case, "customer") else None)
        cust_name = cust.name if cust and cust.name else ""

        # Title / Greeting
        salutation = f"أهلاً بحضرتك يا أستاذ {cust_name}" if cust_name and not cust_name.startswith("TG_") else "أهلاً بحضرتك يا فندم"

        # Reference specific issue if present
        issue_text = case.issue.strip() if case.issue else ""
        if issue_text:
            return (
                f"{salutation}، معاك نظام المتابعة الذكي من نايل كونكت. "
                f"كنا بنتابع مع حضرتك بخصوص: '{issue_text}'. "
                f"حابين نتأكد هل المشكلة اتحلت واستكملت الخدمة بنجاح؟"
            )

        # Fallback to category if issue is blank
        category_text = str(case.category.value) if hasattr(case.category, "value") else str(case.category)
        if category_text and category_text != "OTHER":
            return (
                f"{salutation}، معاك نظام المتابعة الذكي من نايل كونكت. "
                f"كنا بنتابع مع حضرتك بخصوص طلب الدعم الفني الخاص بـ {category_text}. "
                f"حابين نتأكد هل المشكلة اتحلت واستكملت الخدمة بنجاح؟"
            )

        return GREETING_DEFAULT_TEXT

    def initiate_followup(self, case_id: UUID) -> Dict[str, Any]:
        """
        Initiates an outbound AI follow-up call for an EXISTING case.
        Strictly reuses the existing Case and prevents duplicate records.
        """
        # 1. Fetch & verify Case
        case = self.case_repo.get_by_id(case_id)
        if not case:
            raise NotFoundError(f"Case {case_id} not found")

        if case.status != CaseStatus.AI_FOLLOW_UP_SCHEDULED:
            logger.warning(
                "Case %s status is %s (expected %s). Proceeding with follow-up as requested.",
                case_id, case.status, CaseStatus.AI_FOLLOW_UP_SCHEDULED
            )

        # 2. Fetch Customer & Validate Phone
        customer = case.customer or self.customer_repo.get_by_id(case.customer_id)
        if not customer or not customer.phone:
            raise BadRequestError(f"Case {case_id} has no valid customer phone number to dial")

        phone_to_dial = customer.phone.strip()
        now = datetime.now(timezone.utc)

        # 3. Idempotent AIFollowup: Find active/scheduled or create one
        followup = self.followup_repo.get_active_by_case_id(case.id)
        if not followup:
            followup = AIFollowup(
                case_id=case.id,
                customer_id=case.customer_id,
                scheduled_at=now,
                status=FollowupStatus.IN_PROGRESS,
                attempt_number=1,
            )
            followup = self.followup_repo.create(followup)
            logger.info("Created new AIFollowup %s for existing Case %s", followup.id, case.id)
        else:
            followup.status = FollowupStatus.IN_PROGRESS
            followup.attempt_number = (followup.attempt_number or 1)
            self.followup_repo.update(followup)
            logger.info("Reusing existing AIFollowup %s for Case %s", followup.id, case.id)

        # 4. Idempotent Call: Find existing pending OUTBOUND_AI call or create one
        call = None
        if followup.call_id:
            call = self.call_repo.get_by_id(followup.call_id)

        if not call or call.outcome != CallOutcome.PENDING:
            call = self.call_repo.get_pending_outbound_ai_call(case.id)

        if not call:
            call = Call(
                customer_id=case.customer_id,
                case_id=case.id,
                call_type=CallType.OUTBOUND_AI,
                started_at=now,
                outcome=CallOutcome.PENDING,
            )
            call = self.call_repo.create(call)
            logger.info("Created OUTBOUND_AI Call %s for Case %s", call.id, case.id)

        followup.call_id = call.id
        self.followup_repo.update(followup)

        # 5. Build dynamic Arabic greeting
        greeting_text = self.build_dynamic_greeting(case=case, customer=customer)

        # 6. Construct Webhook URLs for Vonage
        speech_url = (
            f"{settings.PUBLIC_BASE_URL}/api/v1/telephony/vonage/speech"
            f"?followup_id={followup.id}&call_id={call.id}&attempt=1"
        )
        event_url = (
            f"{settings.PUBLIC_BASE_URL}/api/v1/telephony/vonage/event"
            f"?followup_id={followup.id}&call_id={call.id}"
        )

        ncco = build_greeting_ncco(speech_webhook_url=speech_url, greeting_text=greeting_text)

        # 7. Call Vonage Voice API
        vonage_response = None
        try:
            vonage_response = create_outbound_call(
                to_number=phone_to_dial,
                from_number=settings.VONAGE_PHONE_NUMBER,
                ncco=ncco,
                event_url=[event_url],
            )
            logger.info("Outbound call placed successfully for case %s: %s", case_id, vonage_response)
        except Exception as exc:
            logger.exception("Vonage call dispatch failed for case %s: %s", case_id, exc)
            # Mark followup as failed rather than leaving it stuck
            followup.status = FollowupStatus.FAILED
            self.followup_repo.update(followup)
            raise

        return {
            "status": "initiated",
            "case_id": str(case.id),
            "customer_id": str(customer.id),
            "customer_phone": phone_to_dial,
            "followup_id": str(followup.id),
            "call_id": str(call.id),
            "greeting_text": greeting_text,
            "vonage_response": str(vonage_response),
        }

    def trigger_all_scheduled_followups(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Batch processor for scheduled follow-ups.
        Scans all eligible cases and initiates Vonage outbound calls.
        """
        eligible_cases = self.get_eligible_cases(limit=limit)
        logger.info("Found %d eligible cases for AI follow-up", len(eligible_cases))
        results = []

        for case in eligible_cases:
            try:
                res = self.initiate_followup(case.id)
                results.append({"case_id": str(case.id), "success": True, "details": res})
            except Exception as exc:
                logger.error("Failed to initiate follow-up for case %s: %s", case.id, exc)
                results.append({"case_id": str(case.id), "success": False, "error": str(exc)})

        return results
