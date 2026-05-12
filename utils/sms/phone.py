"""E.164 phone normalization for SMS (keeps utils free of apis/* imports)."""

import phonenumbers
from phonenumbers import NumberParseException


def normalize_phone_to_e164(phone: str, *, default_region: str = "GH") -> str:
    raw = str(phone).strip()
    if not raw:
        return ""
    region = (default_region or "GH").upper()
    try:
        parsed = phonenumbers.parse(raw, region)
        if phonenumbers.is_valid_number(parsed):
            return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    except NumberParseException:
        pass
    return raw
