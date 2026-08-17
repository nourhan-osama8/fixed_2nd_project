"""
Unit & integration tests for Vonage Voice API integration, NCCO builders, and webhooks.
"""
from unittest.mock import patch, MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.constants import CallOutcome, CaseStatus, FollowupResult, FollowupStatus
from app.core.database import SessionLocal
from app.models.ai_followup import AIFollowup
from app.models.call import Call
from app.models.case import Case
from app.models.customer import Customer
from app.telephony.vonage.client import create_outbound_call, get_from_number
from app.telephony.vonage.response import (
    build_greeting_ncco,
    build_retry_ncco,
    build_resolved_ncco,
    build_escalate_ncco,
    build_no_answer_ncco,
    GOODBYE_RESOLVED_TEXT,
    GOODBYE_ESCALATE_TEXT,
    NOT_UNDERSTOOD_TEXT,
)


@pytest.fixture
def client():
    return TestClient(app)


def unique_test_phone():
    """Generate a unique phone value for each test run."""
    return f"TEST_{uuid4().hex[:10]}"


def test_ncco_builders():
    """Verify all NCCO builder functions generate valid Vonage action structures."""
    # 1. Greeting NCCO
    speech_url = "https://example.com/speech"
    greeting_ncco = build_greeting_ncco(
        speech_webhook_url=speech_url,
        greeting_text="مرحبا",
    )

    assert isinstance(greeting_ncco, list)
    assert len(greeting_ncco) == 3
    assert greeting_ncco[0]["action"] == "talk"
    assert greeting_ncco[0]["text"] == "مرحبا"
    assert greeting_ncco[1]["action"] == "input"
    assert greeting_ncco[1]["speech"]["language"] == "ar-EG"
    assert greeting_ncco[1]["eventUrl"] == [speech_url]

    # 2. Retry NCCO
    retry_ncco = build_retry_ncco(speech_webhook_url=speech_url)

    assert retry_ncco[0]["action"] == "talk"
    assert retry_ncco[0]["text"] == NOT_UNDERSTOOD_TEXT
    assert retry_ncco[1]["action"] == "input"

    # 3. Resolved NCCO
    resolved_ncco = build_resolved_ncco()

    assert resolved_ncco[0]["action"] == "talk"
    assert resolved_ncco[0]["text"] == GOODBYE_RESOLVED_TEXT

    # 4. Escalate NCCO
    escalate_ncco = build_escalate_ncco()

    assert escalate_ncco[0]["action"] == "talk"
    assert escalate_ncco[0]["text"] == GOODBYE_ESCALATE_TEXT

    # 5. No Answer NCCO
    no_ans_ncco = build_no_answer_ncco()

    assert no_ans_ncco[0]["action"] == "talk"


def test_vonage_create_outbound_call():
    """Verify outbound Vonage call request construction using the Auth/Vonage/CreateCallRequest pattern."""
    mock_voice = MagicMock()
    mock_voice.create_call.return_value = {
        "uuid": "vonage-call-uuid-1234",
        "status": "started",
    }

    mock_client = MagicMock()
    mock_client.voice = mock_voice

    with patch(
        "app.telephony.vonage.client.get_vonage_client",
        return_value=mock_client,
    ):
        resp = create_outbound_call(
            to_number="01012345678",
            from_number="01099999999",
            ncco=[{"action": "talk", "text": "تجربة اتصال"}],
            event_url=["https://example.com/event"],
        )

        assert resp["uuid"] == "vonage-call-uuid-1234"
        assert mock_voice.create_call.called

        call_req = mock_voice.create_call.call_args[0][0]

        assert call_req.to[0].number == "01012345678"
        assert call_req.from_.number == "01099999999"


def test_vonage_answer_webhook(client):
    """Verify Vonage answer webhook returns valid initial greeting NCCO."""
    resp = client.get(
        "/api/v1/telephony/vonage/answer"
        "?followup_id=00000000-0000-0000-0000-000000000001"
        "&call_id=00000000-0000-0000-0000-000000000002"
    )

    assert resp.status_code == 200

    ncco = resp.json()

    assert isinstance(ncco, list)
    assert any(item.get("action") == "talk" for item in ncco)
    assert any(item.get("action") == "input" for item in ncco)


def test_vonage_speech_webhook_yes(client):
    """Verify Vonage speech webhook processes YES, updates DB to RESOLVED, and returns goodbye NCCO."""
    db = SessionLocal()

    # Create test customer, case, followup, call
    customer = Customer(
        name="Vonage Test User 1",
        phone=unique_test_phone(),
    )
    db.add(customer)
    db.commit()

    case = Case(
        customer_id=customer.id,
        issue="مشكلة الراوتر",
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

    followup.call_id = call.id
    db.commit()

    payload = {
        "speech": {
            "results": [
                {
                    "text": "أيوه المشكلة اتحلت تمام وشغال كويس",
                    "confidence": "0.95",
                }
            ]
        }
    }

    resp = client.post(
        f"/api/v1/telephony/vonage/speech"
        f"?followup_id={followup.id}"
        f"&call_id={call.id}"
        f"&attempt=1",
        json=payload,
    )

    assert resp.status_code == 200

    ncco = resp.json()

    assert ncco[0]["text"] == GOODBYE_RESOLVED_TEXT

    # Check DB state
    db.refresh(case)
    db.refresh(followup)
    db.refresh(call)

    assert case.status == CaseStatus.RESOLVED
    assert followup.status == FollowupStatus.COMPLETED
    assert followup.result == FollowupResult.YES
    assert call.outcome == CallOutcome.RESOLVED
    assert "أيوه المشكلة اتحلت" in (call.transcript or "")

    db.close()


def test_vonage_speech_webhook_no(client):
    """Verify Vonage speech webhook processes NO, escalates to NEEDS_HUMAN, and returns escalate NCCO."""
    db = SessionLocal()

    # Create test customer, case, followup, call
    customer = Customer(
        name="Vonage Test User 2",
        phone=unique_test_phone(),
    )
    db.add(customer)
    db.commit()

    case = Case(
        customer_id=customer.id,
        issue="بطء سرعة التحميل",
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

    followup.call_id = call.id
    db.commit()

    payload = {
        "speech": {
            "results": [
                {
                    "text": "لأ لسه المشكلة موجودة ومش شغال",
                    "confidence": "0.92",
                }
            ]
        }
    }

    resp = client.post(
        f"/api/v1/telephony/vonage/speech"
        f"?followup_id={followup.id}"
        f"&call_id={call.id}"
        f"&attempt=1",
        json=payload,
    )

    assert resp.status_code == 200

    ncco = resp.json()

    assert ncco[0]["text"] == GOODBYE_ESCALATE_TEXT

    db.refresh(case)
    db.refresh(followup)
    db.refresh(call)

    assert case.status == CaseStatus.NEEDS_HUMAN
    assert followup.status == FollowupStatus.COMPLETED
    assert followup.result == FollowupResult.NO
    assert call.outcome == CallOutcome.ESCALATED

    db.close()


def test_vonage_event_webhook_failure(client):
    """Verify Vonage event webhook handles failed/busy/no-answer events."""
    db = SessionLocal()

    # Create test customer, case, followup, call
    customer = Customer(
        name="Vonage Test User 3",
        phone=unique_test_phone(),
    )
    db.add(customer)
    db.commit()

    case = Case(
        customer_id=customer.id,
        issue="انقطاع متكرر",
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

    followup.call_id = call.id
    db.commit()

    resp = client.post(
        f"/api/v1/telephony/vonage/event"
        f"?followup_id={followup.id}"
        f"&call_id={call.id}",
        json={
            "status": "busy",
            "duration": "0",
        },
    )

    assert resp.status_code == 200
    assert resp.json() == {"ok": True}

    db.refresh(followup)
    db.refresh(call)

    assert followup.status == FollowupStatus.FAILED
    assert followup.result == FollowupResult.NO_ANSWER
    assert call.outcome == CallOutcome.NO_ANSWER

    db.close()