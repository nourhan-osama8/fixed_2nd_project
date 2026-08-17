"""
Unit tests for transport-independent call flow handlers (yes_flow, no_flow, unknown_flow).
"""
from uuid import uuid4
import pytest

from app.core.constants import CallOutcome, CaseStatus, FollowupResult, FollowupStatus
from app.core.database import SessionLocal
from app.models.ai_followup import AIFollowup
from app.models.call import Call
from app.models.case import Case
from app.models.customer import Customer
from app.telephony.call_flows.no_flow import handle_no
from app.telephony.call_flows.unknown_flow import handle_unknown
from app.telephony.call_flows.yes_flow import handle_yes
from app.telephony.vonage.response import (
    GOODBYE_RESOLVED_TEXT,
    GOODBYE_ESCALATE_TEXT,
    NOT_UNDERSTOOD_TEXT,
)


def unique_test_phone():
    """Generate a unique phone value for each test run."""
    return f"TEST_{uuid4().hex[:10]}"


def test_handle_yes():
    """Verify handle_yes marks call resolved, followup YES completed, and case resolved."""
    db = SessionLocal()
    customer = Customer(
        name="Flow Test User 1",
        phone=unique_test_phone(),
    )
    db.add(customer)
    db.commit()

    case = Case(
        customer_id=customer.id,
        issue="عطل مؤقت",
        status=CaseStatus.AI_FOLLOW_UP_SCHEDULED,
    )
    db.add(case)
    db.commit()

    followup = AIFollowup(
        case_id=case.id,
        customer_id=customer.id,
        scheduled_at=case.created_at,
        status=FollowupStatus.IN_PROGRESS,
    )
    db.add(followup)
    db.commit()

    call = Call(
        customer_id=customer.id,
        case_id=case.id,
        call_type="OUTBOUND_AI",
        outcome=CallOutcome.PENDING,
    )
    db.add(call)
    db.commit()

    resp_text = handle_yes(db, followup.id, call.id)
    assert resp_text == GOODBYE_RESOLVED_TEXT

    db.refresh(case)
    db.refresh(followup)
    db.refresh(call)

    assert case.status == CaseStatus.RESOLVED
    assert case.resolved_at is not None
    assert followup.status == FollowupStatus.COMPLETED
    assert followup.result == FollowupResult.YES
    assert followup.completed_at is not None
    assert call.outcome == CallOutcome.RESOLVED
    assert call.ended_at is not None
    db.close()


def test_handle_no():
    """Verify handle_no marks call escalated, followup NO completed, and case NEEDS_HUMAN."""
    db = SessionLocal()
    customer = Customer(
        name="Flow Test User 2",
        phone=unique_test_phone(),
    )
    db.add(customer)
    db.commit()

    case = Case(
        customer_id=customer.id,
        issue="توقف الخدمة",
        status=CaseStatus.AI_FOLLOW_UP_SCHEDULED,
    )
    db.add(case)
    db.commit()

    followup = AIFollowup(
        case_id=case.id,
        customer_id=customer.id,
        scheduled_at=case.created_at,
        status=FollowupStatus.IN_PROGRESS,
    )
    db.add(followup)
    db.commit()

    call = Call(
        customer_id=customer.id,
        case_id=case.id,
        call_type="OUTBOUND_AI",
        outcome=CallOutcome.PENDING,
    )
    db.add(call)
    db.commit()

    resp_text = handle_no(db, followup.id, call.id)
    assert resp_text == GOODBYE_ESCALATE_TEXT

    db.refresh(case)
    db.refresh(followup)
    db.refresh(call)

    assert case.status == CaseStatus.NEEDS_HUMAN
    assert followup.status == FollowupStatus.COMPLETED
    assert followup.result == FollowupResult.NO
    assert followup.completed_at is not None
    assert call.outcome == CallOutcome.ESCALATED
    assert call.ended_at is not None
    db.close()


def test_handle_unknown_retry_and_exhaustion():
    """Verify handle_unknown retries on attempt 1 and escalates on attempt 2."""
    db = SessionLocal()
    customer = Customer(
        name="Flow Test User 3",
        phone=unique_test_phone(),
    )
    db.add(customer)
    db.commit()

    case = Case(
        customer_id=customer.id,
        issue="استفسار غير واضح",
        status=CaseStatus.AI_FOLLOW_UP_SCHEDULED,
    )
    db.add(case)
    db.commit()

    followup = AIFollowup(
        case_id=case.id,
        customer_id=customer.id,
        scheduled_at=case.created_at,
        status=FollowupStatus.IN_PROGRESS,
    )
    db.add(followup)
    db.commit()

    call = Call(
        customer_id=customer.id,
        case_id=case.id,
        call_type="OUTBOUND_AI",
        outcome=CallOutcome.PENDING,
    )
    db.add(call)
    db.commit()

    # Attempt 1 -> should ask to repeat
    resp_text, is_retry = handle_unknown(
        db,
        followup.id,
        call.id,
        attempt=1,
    )
    assert resp_text == NOT_UNDERSTOOD_TEXT
    assert is_retry is True

    # Attempt 2 -> out of retries, should escalate to human
    resp_text_2, is_retry_2 = handle_unknown(
        db,
        followup.id,
        call.id,
        attempt=2,
    )
    assert resp_text_2 == GOODBYE_ESCALATE_TEXT
    assert is_retry_2 is False

    db.refresh(case)
    assert case.status == CaseStatus.NEEDS_HUMAN
    db.close()