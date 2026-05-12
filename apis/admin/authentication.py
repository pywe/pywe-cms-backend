from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken

AdminUser = get_user_model()


class AdminJWTAuthentication(JWTAuthentication):
    """Validate JWT with scope admin and resolve AdminUser."""

    def get_user(self, validated_token):
        if validated_token.get("scope") != "admin":
            raise InvalidToken("Not an admin token.")

        try:
            user_id = validated_token[settings.SIMPLE_JWT["USER_ID_CLAIM"]]
        except KeyError as exc:
            raise InvalidToken("Token contained no recognizable user identification.") from exc

        try:
            user = AdminUser.objects.get(pk=user_id)
        except AdminUser.DoesNotExist as exc:
            raise InvalidToken("User not found.") from exc

        if not user.is_active:
            raise InvalidToken("User inactive.")

        return user
