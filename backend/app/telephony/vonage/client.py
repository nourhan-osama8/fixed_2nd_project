"""
Vonage Voice API Client for NileConnect AI Contact Center.

Handles authentication with Vonage Voice API using Application ID + Private Key,
and exposes application-level methods for placing outbound AI follow-up voice calls.
"""
from __future__ import annotations

from functools import lru_cache
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from vonage import Auth, Vonage
from vonage_voice import CreateCallRequest, Phone, ToPhone

from app.core.config import settings
from app.core.logging import logger


@lru_cache(maxsize=1)
def get_vonage_client() -> Vonage:
    """
    Returns a cached Vonage client initialized with Application ID and Private Key.
    """
    app_id = settings.VONAGE_APPLICATION_ID
    if not app_id:
        raise RuntimeError(
            "Vonage Application ID is missing. Set VONAGE_APPLICATION_ID in your .env file."
        )

    key_path = Path(settings.vonage_private_key_abs)
    if not key_path.exists():
        raise RuntimeError(
            f"Vonage private key file not found at: {key_path}. "
            "Please verify VONAGE_PRIVATE_KEY_PATH configuration."
        )

    # Read the private key content or pass path
    try:
        with open(key_path, "r", encoding="utf-8") as f:
            private_key_data = f.read()
    except Exception as e:
        logger.error("Failed to read Vonage private key from %s: %s", key_path, e)
        raise

    logger.info("Initializing Vonage client for application %s...", app_id[:8] if len(app_id) >= 8 else app_id)

    auth = Auth(
        application_id=app_id,
        private_key=private_key_data,
        api_key=settings.VONAGE_API_KEY,
        api_secret=settings.VONAGE_API_SECRET,
    )
    return Vonage(auth=auth)


def get_from_number() -> str:
    """Returns the configured Vonage outbound caller ID phone number."""
    if not settings.VONAGE_PHONE_NUMBER:
        raise RuntimeError("VONAGE_PHONE_NUMBER is not set in your .env file.")
    return settings.VONAGE_PHONE_NUMBER.strip()


def create_outbound_call(
    to_number: str,
    from_number: Optional[str] = None,
    ncco: Optional[List[Dict[str, Any]]] = None,
    answer_url: Optional[List[str]] = None,
    event_url: Optional[List[str]] = None,
) -> Any:
    """
    Creates an outbound phone call via Vonage Voice API.
    
    Args:
        to_number: Destination phone number (customer's phone)
        from_number: Configured outbound caller ID (defaults to settings.VONAGE_PHONE_NUMBER)
        ncco: List of NCCO action dictionaries (e.g. talk, input)
        answer_url: List of URLs for answer webhook (if not providing inline NCCO)
        event_url: List of URLs for call status/event webhooks
        
    Returns:
        Vonage API response object containing call UUID, status, etc.
    """
    client = get_vonage_client()
    caller_id = from_number or get_from_number()

    # Clean and validate destination number
    clean_to = to_number.strip().replace(" ", "").replace("-", "")
    clean_from = caller_id.strip().replace(" ", "").replace("-", "")

    req_kwargs: Dict[str, Any] = {
        "to": [ToPhone(number=clean_to)],
        "from_": Phone(number=clean_from),
    }

    if ncco:
        req_kwargs["ncco"] = ncco
    elif answer_url:
        req_kwargs["answer_url"] = answer_url

    if event_url:
        req_kwargs["event_url"] = event_url
        req_kwargs["event_method"] = "POST"

    call_request = CreateCallRequest(**req_kwargs)
    logger.info("Placing outbound Vonage call to %s from %s", clean_to, clean_from)
    response = client.voice.create_call(call_request)
    logger.info("Vonage call created successfully. Response: %s", response)
    return response
