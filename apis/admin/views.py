from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView

from apis.admin.authentication import AdminJWTAuthentication
from apis.admin.serializers import AdminTokenObtainPairSerializer
from apis.utils import envelope


class AdminTokenObtainPairView(TokenObtainPairView):
    permission_classes = [AllowAny]
    serializer_class = AdminTokenObtainPairSerializer


@api_view(["GET"])
@authentication_classes([AdminJWTAuthentication])
@permission_classes([IsAuthenticated])
def me(request):
    user = request.user
    return envelope(
        True,
        data={
            "id": user.pk,
            "username": user.username,
            "is_staff": user.is_staff,
        },
    )
