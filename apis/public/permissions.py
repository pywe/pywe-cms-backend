from rest_framework.permissions import BasePermission

from core.entities.workspaces.models import Workspace


class HasWorkspaceAPIKey(BasePermission):
    message = "A valid CMS API key is required (X-CMS-API-Key)."

    def has_permission(self, request, view):
        return isinstance(getattr(request, "auth", None), Workspace)


class WorkspaceSlugMatches(BasePermission):
    """Ensure authenticated workspace matches URL slug."""

    message = "API key does not match this workspace slug."

    def has_permission(self, request, view):
        ws = getattr(request, "auth", None)
        if not isinstance(ws, Workspace):
            return False
        slug = getattr(view, "kwargs", {}).get("slug")
        return slug is not None and ws.slug == slug
