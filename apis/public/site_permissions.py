from rest_framework.permissions import BasePermission

from core.entities.sites.models import Site
from core.entities.workspaces.models import Workspace


class WorkspaceSiteSlugMatches(BasePermission):
    """API key workspace must match URL workspace_slug; site must exist under it."""

    message = "API key does not match this workspace/site."

    def has_permission(self, request, view):
        ws = getattr(request, "auth", None)
        if not isinstance(ws, Workspace):
            return False
        workspace_slug = getattr(view, "kwargs", {}).get("workspace_slug")
        site_slug = getattr(view, "kwargs", {}).get("site_slug")
        if not workspace_slug or not site_slug:
            return False
        if ws.slug != workspace_slug:
            return False
        return Site.objects.filter(workspace=ws, slug=site_slug).exists()
