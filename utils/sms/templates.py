"""SMS message templates (OTP, merchant verification, etc.)."""

from django.conf import settings


def _sms_brand_name() -> str:
    return str(getattr(settings, "SMS_BRAND_NAME", "Kosoton") or "Kosoton")


def _store_owner_dashboard_url() -> str:
    return str(
        getattr(settings, "STORE_OWNER_DASHBOARD_URL", "https://kosoton.com/dashboard")
        or "https://kosoton.com/dashboard"
    )


class SMSTemplate:
    """Build SMS body text for the configured SMS gateway."""

    def merchant_verification(self, code: str) -> str:
        """Store owner login: 6-digit verification code formatted as '000 000'."""
        formatted_code = f"{code[:3]} {code[3:]}" if len(code) == 6 else code
        return f"Your {_sms_brand_name()} store owner code is {formatted_code}. Do not share."

    def payment_submitted_notification(self, order_number: str, amount: str, transaction_id: str) -> str:
        """Notify store owner that customer has submitted payment SMS."""
        return (
            f"Customer has claimed payment of {amount} for order {order_number}. "
            f"Transaction ID: {transaction_id}. "
            f"Please check and confirm payment on your dashboard."
        )

    def payment_confirmed_customer(self, order_number: str, store_name: str) -> str:
        """Notify customer that their payment has been confirmed."""
        return (
            f"Your payment for order {order_number} has been confirmed by {store_name}. "
            f"Thank you for your order."
        )

    def new_order_store_owner(self, order_number: str, total: str) -> str:
        """Notify store owner of a new order so they can check dashboard and confirm payments."""
        dash = _store_owner_dashboard_url().rstrip("/")
        return (
            f"You have a new order {order_number} for {total}. "
            f"Please check your dashboard at {dash} to confirm payments."
        )

    def coupon_reward_customer(self, order_number: str, store_name: str, reward_amount: str, expires_on: str) -> str:
        """Notify customer that coupon wallet reward was credited."""
        return (
            f"You earned {reward_amount} in your {store_name} coupon wallet from order {order_number}. "
            f"Use it before {expires_on}."
        )

    def order_status_updated_customer(self, order_number: str, store_name: str, status_label: str) -> str:
        """Notify customer that order status changed."""
        return (
            f"Update from {store_name}: your order {order_number} is now {status_label}. "
            f"Track details in your account."
        )

    def customer_login_otp(self, code: str, identifier: str | None = None) -> str:
        """OTP for customer self-login via SMS (Ghana)."""
        formatted_code = f"{code[:3]} {code[3:]}" if len(code) == 6 else code
        return f"Your {_sms_brand_name()} login code is {formatted_code}. Do not share."
