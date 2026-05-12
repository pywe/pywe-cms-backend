"""Django admin auth backend and DRF JWT authentication (blueprint-aligned)."""

from django.conf import settings
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken

AdminUser = get_user_model()


class BackendAuthentication(ModelBackend):
    """Authenticate AdminUser for Django admin and password-based flows."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None
        try:
            user = AdminUser.objects.get(username=username)
        except AdminUser.DoesNotExist:
            if username == settings.ADMIN_USERNAME:
                user = AdminUser.objects.create_superuser(
                    username=username,
                    password=password,
                )
                return user
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None

    def get_user(self, user_id):
        try:
            return AdminUser.objects.get(pk=user_id)
        except AdminUser.DoesNotExist:
            return None


class MemberAuthentication(JWTAuthentication):
    """DRF default: ``Account`` from JWT (not AUTH_USER_MODEL); rejects admin-scoped tokens."""

    def get_user(self, validated_token):
        from core.entities.users.models import Account

        if validated_token.get("scope") == "admin":
            raise InvalidToken("Admin token used on member endpoint.")

        try:
            member_id = validated_token[settings.SIMPLE_JWT["USER_ID_CLAIM"]]
        except KeyError as exc:
            raise InvalidToken("Token contained no recognizable user identification.") from exc

        try:
            account = Account.objects.get(pk=member_id)
        except Account.DoesNotExist as exc:
            raise AuthenticationFailed("User not found.") from exc

        if not account.is_active:
            raise AuthenticationFailed("User inactive.")

        return account


class OptionalMemberAuthentication(MemberAuthentication):
    """Same as MemberAuthentication but allows anonymous when no/invalid token."""

    def authenticate(self, request):
        header = self.get_header(request)
        if header is None:
            return None
        raw_token = self.get_raw_token(header)
        if raw_token is None:
            return None
        try:
            validated_token = self.get_validated_token(raw_token)
            return self.get_user(validated_token), validated_token
        except (InvalidToken, AuthenticationFailed):
            return None


class WorkspaceApiKeyAuthentication(BaseAuthentication):
    """
    Server-to-server access: X-CMS-API-Key or Bearer token with prefix pcm_.
    Sets request.auth to the matched Workspace (request.user stays anonymous).
    """

    header_meta = "HTTP_X_CMS_API_KEY"

    def authenticate(self, request):
        from core.entities.workspaces.models import Workspace, hash_api_key

        raw = request.META.get(self.header_meta)
        if not raw:
            auth_header = request.META.get("HTTP_AUTHORIZATION", "")
            if auth_header.lower().startswith("bearer "):
                candidate = auth_header[7:].strip()
                if candidate.startswith("pcm_"):
                    raw = candidate
        if not raw:
            return None
        hashed = hash_api_key(raw.strip())
        try:
            ws = Workspace.objects.get(api_key_hash=hashed, is_active=True)
        except Workspace.DoesNotExist:
            raise AuthenticationFailed("Invalid API key.")
        return (None, ws)
