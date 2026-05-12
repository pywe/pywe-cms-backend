"""JWT helpers: AdminUser is admin-site only; Account backs API JWTs."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.settings import api_settings

from core.entities.users.models import Account


class AccountAwareTokenRefreshSerializer(TokenRefreshSerializer):
    """
    SimpleJWT's default refresh resolves AUTH_USER_MODEL (AdminUser).

    Account tokens (manager, client, …) resolve ``Account``; staff SPA tokens
    use ``AdminRefreshToken`` with ``scope: admin`` on the refresh payload.
    """

    def _resolve_user(self, refresh):
        UserModel = get_user_model()
        user_id = refresh.payload.get(api_settings.USER_ID_CLAIM)
        if user_id is None:
            return None

        if refresh.payload.get("scope") == "admin":
            try:
                return UserModel.objects.get(
                    **{api_settings.USER_ID_FIELD: user_id},
                )
            except UserModel.DoesNotExist as exc:
                raise AuthenticationFailed(
                    self.error_messages["no_active_account"],
                    "no_active_account",
                ) from exc

        try:
            return Account.objects.get(
                **{api_settings.USER_ID_FIELD: user_id},
            )
        except Account.DoesNotExist as exc:
            raise AuthenticationFailed(
                self.error_messages["no_active_account"],
                "no_active_account",
            ) from exc

    def validate(self, attrs):
        refresh = self.token_class(attrs["refresh"])

        user_id = refresh.payload.get(api_settings.USER_ID_CLAIM, None)
        if user_id:
            user = self._resolve_user(refresh)
            if user is not None and not api_settings.USER_AUTHENTICATION_RULE(user):
                raise AuthenticationFailed(
                    self.error_messages["no_active_account"],
                    "no_active_account",
                )

        data = {"access": str(refresh.access_token)}

        if api_settings.ROTATE_REFRESH_TOKENS:
            if api_settings.BLACKLIST_AFTER_ROTATION:
                try:
                    refresh.blacklist()
                except AttributeError:
                    pass

            refresh.set_jti()
            refresh.set_exp()
            refresh.set_iat()
            refresh.outstand()

            data["refresh"] = str(refresh)

        return data
