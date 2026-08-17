"""
Unit and integration tests for Telegram telephony transport and Voice-AI layer.
"""
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.core.constants import FollowupResult, FollowupStatus, CaseStatus
from app.core.database import SessionLocal
from app.models.customer import Customer
from app.models.ai_followup import AIFollowup
from app.telephony.stt.arabic_classifier import classify_response
from app.telephony.stt.stt_service import get_stt_service
from app.telephony.tts.tts_service import get_tts_service


@pytest.fixture
def client():
    """
    TestClient configured with the same Telegram webhook secret
    expected by the actual webhook endpoint.
    """
    return TestClient(
        app,
        headers={
            "X-Telegram-Bot-Api-Secret-Token": settings.TELEGRAM_WEBHOOK_SECRET
        },
    )


def test_arabic_classifier_yes():
    assert classify_response("أيوه المشكلة اتحلت تمام") == FollowupResult.YES
    assert classify_response("الحمد لله كل حاجة شغالة تمام") == FollowupResult.YES
    assert classify_response("نعم اتحل") == FollowupResult.YES
    assert classify_response("تمام التمام") == FollowupResult.YES


def test_arabic_classifier_no():
    assert classify_response("لأ لسه المشكلة موجودة") == FollowupResult.NO
    assert classify_response("لا مش شغالة") == FollowupResult.NO
    assert classify_response("لسه عطلانة") == FollowupResult.NO
    assert classify_response("مفيش فايدة زي ما هي") == FollowupResult.NO


def test_arabic_classifier_unknown():
    assert classify_response("مش عارف والله") == FollowupResult.UNKNOWN
    assert classify_response("مش متأكد") == FollowupResult.UNKNOWN
    assert classify_response("يمكن") == FollowupResult.UNKNOWN
    assert classify_response("") == FollowupResult.UNKNOWN


def test_stt_service():
    stt = get_stt_service()
    transcript = stt.transcribe_audio(b"sample audio")
    assert isinstance(transcript, str)
    assert len(transcript) > 0


def test_tts_service():
    tts = get_tts_service()
    audio = tts.synthesize_speech("تمام جدًا، شكرًا لوقتك.")
    assert isinstance(audio, bytes)
    assert len(audio) > 0


def test_telegram_webhook_start_command(client):
    payload = {
        "update_id": 5001,
        "message": {
            "message_id": 1,
            "from": {"id": 66601, "first_name": "TestUser"},
            "chat": {"id": 66601, "type": "private"},
            "text": "/start",
        },
    }

    with patch(
        "app.telephony.telegram.client.TelegramClient.send_message",
        return_value={"ok": True},
    ):
        resp = client.post(
            "/api/v1/telephony/telegram/webhook",
            json=payload,
        )

    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


def test_telegram_webhook_text_yes_flow(client):
    chat_id = 66602

    with patch(
        "app.telephony.telegram.client.TelegramClient.send_message",
        return_value={"ok": True},
    ):
        # /start
        start_response = client.post(
            "/api/v1/telephony/telegram/webhook",
            json={
                "update_id": 5002,
                "message": {
                    "message_id": 1,
                    "chat": {"id": chat_id},
                    "from": {"id": chat_id},
                    "text": "/start",
                },
            },
        )

        assert start_response.status_code == 200

        # Customer: YES
        resp = client.post(
            "/api/v1/telephony/telegram/webhook",
            json={
                "update_id": 5003,
                "message": {
                    "message_id": 2,
                    "chat": {"id": chat_id},
                    "from": {"id": chat_id},
                    "text": "أيوه اتحلت المشكلة وشغال تمام",
                },
            },
        )

    assert resp.status_code == 200

    # Verify Database state
    db = SessionLocal()
    try:
        customer = (
            db.query(Customer)
            .filter(Customer.phone == f"TG_{chat_id}")
            .first()
        )

        assert customer is not None

        followup = (
            db.query(AIFollowup)
            .filter(AIFollowup.customer_id == customer.id)
            .order_by(AIFollowup.created_at.desc())
            .first()
        )

        assert followup is not None
        assert followup.status == FollowupStatus.COMPLETED
        assert followup.result == FollowupResult.YES
        assert followup.case.status == CaseStatus.RESOLVED
    finally:
        db.close()


def test_telegram_webhook_text_no_flow(client):
    chat_id = 66603

    with patch(
        "app.telephony.telegram.client.TelegramClient.send_message",
        return_value={"ok": True},
    ):
        # /start
        start_response = client.post(
            "/api/v1/telephony/telegram/webhook",
            json={
                "update_id": 5004,
                "message": {
                    "message_id": 1,
                    "chat": {"id": chat_id},
                    "from": {"id": chat_id},
                    "text": "/start",
                },
            },
        )

        assert start_response.status_code == 200

        # Customer: NO
        resp = client.post(
            "/api/v1/telephony/telegram/webhook",
            json={
                "update_id": 5005,
                "message": {
                    "message_id": 2,
                    "chat": {"id": chat_id},
                    "from": {"id": chat_id},
                    "text": "لأ لسه عطلانة ومش شغالة",
                },
            },
        )

    assert resp.status_code == 200

    # Verify Database state
    db = SessionLocal()
    try:
        customer = (
            db.query(Customer)
            .filter(Customer.phone == f"TG_{chat_id}")
            .first()
        )

        assert customer is not None

        followup = (
            db.query(AIFollowup)
            .filter(AIFollowup.customer_id == customer.id)
            .order_by(AIFollowup.created_at.desc())
            .first()
        )

        assert followup is not None
        assert followup.status == FollowupStatus.COMPLETED
        assert followup.result == FollowupResult.NO
        assert followup.case.status == CaseStatus.NEEDS_HUMAN
    finally:
        db.close()


def test_telegram_webhook_voice_flow(client):
    chat_id = 66604

    with (
        patch(
            "app.telephony.telegram.client.TelegramClient.get_file",
            return_value={"result": {"file_path": "voice/test.oga"}},
        ),
        patch(
            "app.telephony.telegram.client.TelegramClient.download_file",
            return_value=b"fake_audio",
        ),
        patch(
            "app.telephony.telegram.client.TelegramClient.send_voice",
            return_value={"ok": True},
        ) as mock_voice,
        patch(
            "app.telephony.stt.stt_service.STTService.transcribe_audio",
            return_value="تمام المشكلة اتحلت",
        ),
    ):
        resp = client.post(
            "/api/v1/telephony/telegram/webhook",
            json={
                "update_id": 5006,
                "message": {
                    "message_id": 1,
                    "chat": {"id": chat_id},
                    "from": {"id": chat_id},
                    "voice": {"file_id": "file_voice_123"},
                },
            },
        )

    assert resp.status_code == 200
    assert mock_voice.called