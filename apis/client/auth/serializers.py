from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from core.entities.users.models import Account


class MemberTokenObtainPairSerializer(serializers.Serializer):
    phone_number = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)

    def validate(self, attrs):
        phone = attrs["phone_number"]
        password = attrs.get("password") or ""
        try:
            account = Account.objects.get(phone_number=phone)
        except Account.DoesNotExist as exc:
            raise serializers.ValidationError(
                {"phone_number": "No account for this phone."}
            ) from exc
        if password and not account.check_password(password):
            raise serializers.ValidationError({"password": "Invalid credentials."})
        if not account.is_active:
            raise serializers.ValidationError("User inactive.")

        refresh = RefreshToken.for_user(account)
        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }
