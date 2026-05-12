from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apis.public.permissions import HasWorkspaceAPIKey, WorkspaceSlugMatches
from apis.utils import envelope
from pywe_cms_backend.authentication import WorkspaceApiKeyAuthentication


class SiteBootstrapView(APIView):
    """
    Headless bootstrap for a workspace. Authenticate with X-CMS-API-Key only.
    Content models will extend this payload later.
    """

    authentication_classes = [WorkspaceApiKeyAuthentication]
    permission_classes = [AllowAny, HasWorkspaceAPIKey, WorkspaceSlugMatches]

    def get(self, request, slug, *args, **kwargs):
        ws = request.auth
        return Response(
            envelope(
                True,
                data={
                    "workspace": {
                        "id": ws.pk,
                        "name": ws.name,
                        "slug": ws.slug,
                    },
                    "content": {},
                },
            ),
        )
