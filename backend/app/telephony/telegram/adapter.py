"""
Telegram Transport Adapter for NileConnect Voice-AI Architecture.

Acts as the testing transport bridge between the Telegram Bot API and the existing
application layer (STT, AI classifier, Call Flows, Database Models, and TTS).

CRITICAL RULE:
- NEVER creates a new Case.
- Binds strictly to existing eligible Cases in PostgreSQL (status == AI_FOLLOW_UP_SCHEDULED).
- Reuses existing Cases, AIFollowups, and Calls.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple
from uuid import UUID
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.constants import CallOutcome, CallType, CaseStatus, FollowupResult, FollowupStatus
from app.core.logging import logger
from app.models.ai_followup import AIFollowup
from app.models.call import Call
from app.models.case import Case
from app.models.customer import Customer
from app.repositories.call_repository import CallRepository
from app.repositories.case_repository import CaseRepository
from app.repositories.customer_repository import CustomerRepository
from app.repositories.followup_repository import FollowupRepository
from app.services.ai_followup_service import AIFollowupService
from app.telephony.call_flows.no_flow import handle_no
from app.telephony.call_flows.unknown_flow import MAX_ATTEMPTS, handle_unknown
from app.telephony.call_flows.yes_flow import handle_yes
from app.telephony.stt.arabic_classifier import classify_response
from app.telephony.stt.stt_service import get_stt_service
from app.telephony.tts.tts_service import get_tts_service
from app.telephony.telegram.client import get_telegram_client
from app.telephony.vonage.response import (
    GREETING_DEFAULT_TEXT,
    NOT_UNDERSTOOD_TEXT,
    GOODBYE_RESOLVED_TEXT,
    GOODBYE_ESCALATE_TEXT,
)

NO_SCHEDULED_CASES_MSG = (
    "أهلاً بك في نظام نايل كونكت لاختبار المتابعة الذكية.\n"
    "لا توجد حالياً أي حالات مجدولة للمتابعة (AI_FOLLOW_UP_SCHEDULED).\n"
    "برجاء جدولة متابعة لحالة قائمة من لوحة التحكم لتجربة الاختبار."
)


class TelegramAdapter:
    """
    Session & Orchestration manager for Telegram testing transport.
    """
    def __init__(self, db: Session):
        self.db = db
        self.telegram_client = get_telegram_client()
        self.stt_service = get_stt_service()
        self.tts_service = get_tts_service()

        self.customer_repo = CustomerRepository(db)
        self.case_repo = CaseRepository(db)
        self.followup_repo = FollowupRepository(db)
        self.call_repo = CallRepository(db)
        self.ai_service = AIFollowupService(db)

    def _get_or_bind_session(
        self,
        chat_id: int | str,
        user_info: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Optional[AIFollowup], Optional[Call], Optional[Case]]:
        """
        Retrieves an active follow-up session or binds to an existing eligible Case
        (CaseStatus.AI_FOLLOW_UP_SCHEDULED).
        
        CRITICAL: NEVER creates a new Case.
        """
        user_name = "Telegram User"
        if user_info:
            first = user_info.get("first_name", "")
            last = user_info.get("last_name", "")
            user_name = f"{first} {last}".strip() or user_info.get("username", "Telegram User")

        phone_num = f"TG_{chat_id}"

        # 1. Ensure/get Customer for this Telegram user
        customer = self.customer_repo.get_by_phone(phone_num)
        if not customer:
            customer = Customer(
                name=user_name,
                phone=phone_num,
                notes=f"Telegram Chat ID: {chat_id}",
            )
            customer = self.customer_repo.create(customer)

        # 2. Check if customer already has an active follow-up in progress
        active_followups = self.followup_repo.get_all(
            customer_id=customer.id,
            status=FollowupStatus.IN_PROGRESS,
            limit=1,
        )
        if active_followups:
            followup = active_followups[0]
            case = self.case_repo.get_by_id(followup.case_id)
            call = self.call_repo.get_by_id(followup.call_id) if followup.call_id else None
            return followup, call, case

        # 3. Find an existing eligible Case in PostgreSQL
        eligible_cases = self.case_repo.get_ai_followup_cases(limit=1)
        if not eligible_cases:
            logger.info("[Telegram] No eligible AI_FOLLOW_UP_SCHEDULED cases found in DB.")
            return None, None, None

        case = eligible_cases[0]
        logger.info("[Telegram] Binding Telegram session to existing Case %s (Issue: %r)", case.id, case.issue)

        # 4. Find or reuse AIFollowup for this existing Case
        now = datetime.now(timezone.utc)
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
        else:
            followup.status = FollowupStatus.IN_PROGRESS
            self.followup_repo.update(followup)

        # 5. Find or create OUTBOUND_AI Call row
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

        followup.call_id = call.id
        self.followup_repo.update(followup)

        return followup, call, case

    def process_start_command(
        self,
        chat_id: int | str,
        user_info: Optional[Dict[str, Any]] = None,
        as_voice: bool = False,
    ) -> None:
        """
        Handles the /start command from Telegram user.
        Binds to an existing eligible Case and greets the user with dynamic issue details.
        NEVER creates a new Case.
        """
        logger.info("[Telegram] /start command received for chat %s", chat_id)

        followup, call, case = self._get_or_bind_session(chat_id, user_info)

        if not followup or not case:
            self.telegram_client.send_message(chat_id, NO_SCHEDULED_CASES_MSG)
            logger.info("[Telegram] No eligible case found; informed tester without creating records.")
            return

        followup.attempt_number = 1
        self.followup_repo.update(followup)

        # Dynamic greeting referencing the existing case's issue
        greeting_text = self.ai_service.build_dynamic_greeting(case=case)

        logger.info("[Telegram] Sending greeting for case %s: %r", case.id, greeting_text)
        if as_voice:
            audio_bytes = self.tts_service.synthesize_speech(greeting_text)
            if audio_bytes:
                self.telegram_client.send_voice(chat_id, audio_bytes, caption=greeting_text)
            else:
                self.telegram_client.send_message(chat_id, greeting_text)
        else:
            self.telegram_client.send_message(chat_id, greeting_text)

    def process_text_message(
        self,
        chat_id: int | str,
        text: str,
        user_info: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Handles incoming text messages from Telegram testing transport.
        """
        logger.info("[Telegram] Text message received for chat %s: %r", chat_id, text)

        if text.strip().startswith("/start"):
            self.process_start_command(chat_id, user_info, as_voice=False)
            return {"ok": True, "action": "start"}

        followup, call, case = self._get_or_bind_session(chat_id, user_info)

        if not followup or not call:
            self.telegram_client.send_message(chat_id, NO_SCHEDULED_CASES_MSG)
            return {"ok": False, "error": "no_active_case"}

        # AI Classification
        result = classify_response(text)
        logger.info("[AI] Classified text %r as: %s", text, result.value)

        # Update Call transcript
        current_transcript = call.transcript or ""
        call.transcript = (current_transcript + f"\nCustomer: {text}").strip()
        self.call_repo.update(call)

        response_text = self._execute_call_flow(followup, call, result)

        self.telegram_client.send_message(chat_id, response_text)
        return {"ok": True, "result": result.value, "response": response_text}

    def process_voice_message(
        self,
        chat_id: int | str,
        file_id: str,
        user_info: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Handles incoming voice messages from Telegram testing transport:
        Download Audio -> STT -> Classifier -> Call Flow -> DB Update -> TTS -> Voice Response
        """
        logger.info("[Telegram] Voice message received for chat %s (file_id: %s)", chat_id, file_id)

        # 1. Download voice audio from Telegram
        file_info = self.telegram_client.get_file(file_id)
        file_path = file_info.get("result", {}).get("file_path")
        if not file_path:
            logger.error("[Telegram] Could not obtain file_path for file_id: %s", file_id)
            err_msg = "عذرًا، حدث خطأ أثناء تحميل الرسالة الصوتية. برجاء المحاولة مرة أخرى."
            self.telegram_client.send_message(chat_id, err_msg)
            return {"ok": False, "error": "file_download_failed"}

        audio_bytes = self.telegram_client.download_file(file_path)

        # 2. Run STT
        transcribed_text = self.stt_service.transcribe_audio(
            audio_bytes=audio_bytes,
            filename=file_path.split("/")[-1] if "/" in file_path else "voice.oga",
        )

        followup, call, case = self._get_or_bind_session(chat_id, user_info)

        if not followup or not call:
            self.telegram_client.send_message(chat_id, NO_SCHEDULED_CASES_MSG)
            return {"ok": False, "error": "no_active_case"}

        # 3. AI / Classification
        result = classify_response(transcribed_text)
        logger.info("[AI] Classified voice transcript %r as: %s", transcribed_text, result.value)

        # Update Call transcript
        current_transcript = call.transcript or ""
        call.transcript = (current_transcript + f"\nCustomer (Voice): {transcribed_text}").strip()
        self.call_repo.update(call)

        # 4. Call Flows
        response_text = self._execute_call_flow(followup, call, result)

        # 5. Run TTS & Send response
        audio_response = self.tts_service.synthesize_speech(response_text)
        if audio_response:
            self.telegram_client.send_voice(
                chat_id=chat_id,
                voice_bytes=audio_response,
                filename="response.mp3",
                caption=f"🗣️ {response_text}",
            )
        else:
            self.telegram_client.send_message(chat_id, response_text)

        return {
            "ok": True,
            "transcription": transcribed_text,
            "result": result.value,
            "response": response_text,
        }

    def _execute_call_flow(
        self,
        followup: AIFollowup,
        call: Call,
        result: FollowupResult,
    ) -> str:
        """
        Executes the business logic / database updates from the shared call flow handlers.
        """
        if result == FollowupResult.YES:
            return handle_yes(self.db, followup.id, call.id)

        elif result == FollowupResult.NO:
            return handle_no(self.db, followup.id, call.id)

        else:
            # Unknown / ambiguous response
            attempt = followup.attempt_number or 1
            resp_text, is_retry = handle_unknown(self.db, followup.id, call.id, attempt=attempt)
            if is_retry:
                followup.attempt_number = attempt + 1
                self.followup_repo.update(followup)
            return resp_text
