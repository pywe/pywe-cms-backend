from rest_framework_simplejwt.tokens import RefreshToken


class AdminRefreshToken(RefreshToken):
    """Refresh/access tokens for staff SPA; access payload includes scope admin."""

    @classmethod
    def for_user(cls, user):
        token = super().for_user(user)
        token["scope"] = "admin"
        access = token.access_token
        access["scope"] = "admin"
        return token
