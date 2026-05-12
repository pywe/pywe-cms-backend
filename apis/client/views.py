from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

from apis.utils import envelope


@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    return envelope(True, data={"status": "ok"})
