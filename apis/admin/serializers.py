from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apis.admin.tokens import AdminRefreshToken


class AdminTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Mint staff SPA tokens with AdminRefreshToken (scope: admin)."""

    @classmethod
    def get_token(cls, user):
        return AdminRefreshToken.for_user(user)
