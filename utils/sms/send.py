"""
Send SMS via Pywe API (https://pushr.pywe.org).
Payload format and auth per SMS_IMPLEMENTATION.md.
"""
import logging

import requests
from django.conf import settings

from .phone import normalize_phone_to_e164

logger = logging.getLogger(__name__)


def _normalize_recipient(phone: str) -> str:
    """Ensure E.164 for SMS API recipients."""
    default_region = getattr(settings, "PHONENUMBER_DEFAULT_REGION", "GH")
    normalized = normalize_phone_to_e164(phone, default_region=str(default_region or "GH"))
    return normalized or str(phone).strip()


class SMSNotification:
    """Send SMS via Pywe SMS API."""

    def __init__(self, base_url=None, api_key_public=None, api_key_secret=None, sender_id=None):
        self.base_url = (base_url or getattr(settings, "SMS_API_BASE_URL", "")).rstrip("/")
        self.api_key_public = api_key_public or getattr(settings, "SMS_API_KEY_PUBLIC", "")
        self.api_key_secret = api_key_secret or getattr(settings, "SMS_API_KEY_SECRET", "")
        self.sender_id = sender_id or getattr(settings, "SMS_SENDER_ID", "")

    def send_sms(self, payload: dict):
        """
        Send SMS. Payload: body, phones (list or single str), optional sender_id.
        POST to {base_url}/api/client/sms/send-sms with Pywe JSON format.
        Raises Exception on non-201 response.
        """
        if not self.base_url or not self.api_key_public or not self.api_key_secret:
            raise ValueError("SMS_API_BASE_URL, SMS_API_KEY_PUBLIC, SMS_API_KEY_SECRET must be set")

        body = payload.get("body", "")
        phones = payload.get("phones") or payload.get("phone")
        if isinstance(phones, str):
            phones = [phones]
        recipients = [_normalize_recipient(p) for p in (phones or [])]
        if not recipients:
            raise ValueError("payload must include 'phones' or 'phone'")

        data = {
            "api_key_public": self.api_key_public,
            "api_key_secret": self.api_key_secret,
            "message": body,
            "recipients": recipients,
            "sender_id": payload.get("sender_id") or self.sender_id,
            "scheduled": payload.get("scheduled", False),
            "time_scheduled": payload.get("time_scheduled"),
        }

        url = f"{self.base_url}/api/client/sms/send-sms"
        resp = requests.post(url, json=data, timeout=30)
        if resp.status_code != 201:
            logger.warning("Pywe SMS API error: %s %s", resp.status_code, resp.text)
            raise Exception(f"SMS API error {resp.status_code}: {resp.text}")
        return resp.json()
