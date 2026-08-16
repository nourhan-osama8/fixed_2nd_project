"""
Unit tests for AIFollowupService orchestration, eligibility verification, and duplicate prevention.
"""
from unittest.mock import patch, MagicMock
from uuid import uuid4
import pytest

from app.core.constants import CallOutcome, CallType, CaseStatus, FollowupResult, FollowupStatus
from app.core.database import SessionLocal
from app.models.ai_followup import AIFollowup
from app.models.call import Call
from app.models.case import Case
from app.models.customer import Customer
from app.repositories.case_repository import CaseRepository
from app.services.ai_followup_service import AIFollowupService


def test_get_eligible_cases():
    """Verify get_eligible_cases only returns cases with status == AI_FOLLOW_UP_SCHEDULED."""
    db = SessionLocal()
    service = AIFollowupService(db)
    eligible_cases = service.get_eligible_cases()
    assert isinstance(eligible_cases, list)
    for c in eligible_cases:
        assert c.status == CaseStatus.AI_FOLLOW_UP_SCHEDULED
    db.close()


def test_initiate_followup_preserves_case_and_creates_records():
    """
    Verify initiate_followup:
    1. Reuses the existing Case (NEVER creates a new Case).
    2. Reuses/creates AIFollowup.
    3. Reuses/creates OUTBOUND_AI Call.
    4. Builds dynamic Arabic greeting with case.issue.
    5. Prevents duplicate records on second invocation.
    """
    db = SessionLocal()
    # Create test customer and case
    customer = Customer(name="Amr Mahmoud", phone="01099887766")
    db.add(customer)
    db.commit()

    case = Case(
        customer_id=customer.id,
        issue="انقطاع خدمة الإنترنت الأرضي بعد الصيانة",
        status=CaseStatus.AI_FOLLOW_UP_SCHEDULED,
    )
    db.add(case)
    db.commit()

    cases_count_before = db.query(Case).count()

    mock_resp = {"uuid": "mock-vonage-uuid-1", "status": "started"}
    with patch("app.services.ai_followup_service.create_outbound_call", return_value=mock_resp) as mock_call:
        service = AIFollowupService(db)
        result = service.initiate_followup(case.id)

        # 1. Verify response structure
        assert result["status"] == "initiated"
        assert result["case_id"] == str(case.id)
        assert result["customer_phone"] == "01099887766"
        assert "انقطاع خدمة الإنترنت" in result["greeting_text"]
        assert mock_call.called

        # 2. Verify NO new Case was created
        cases_count_after = db.query(Case).count()
        assert cases_count_after == cases_count_before

        # 3. Verify AIFollowup created
        followups = db.query(AIFollowup).filter(AIFollowup.case_id == case.id).all()
        assert len(followups) == 1
        assert followups[0].status == FollowupStatus.IN_PROGRESS

        # 4. Verify Call created
        calls = db.query(Call).filter(Call.case_id == case.id).all()
        assert len(calls) == 1
        assert calls[0].call_type == CallType.OUTBOUND_AI
        assert calls[0].outcome == CallOutcome.PENDING

        # 5. TEST DUPLICATE PREVENTION: Trigger again for same case
        result_second = service.initiate_followup(case.id)
        assert result_second["case_id"] == str(case.id)

        # Still exactly 1 Case, 1 Followup, 1 Call
        assert db.query(Case).count() == cases_count_before
        assert db.query(AIFollowup).filter(AIFollowup.case_id == case.id).count() == 1
        assert db.query(Call).filter(Call.case_id == case.id).count() == 1

    db.close()


def test_trigger_all_scheduled_followups():
    """Verify batch triggering across eligible cases."""
    db = SessionLocal()
    service = AIFollowupService(db)
    mock_resp = {"uuid": "batch-call-uuid", "status": "started"}

    with patch("app.services.ai_followup_service.create_outbound_call", return_value=mock_resp):
        results = service.trigger_all_scheduled_followups(limit=10)
        assert isinstance(results, list)
        for r in results:
            assert "case_id" in r
            assert "success" in r

    db.close()
