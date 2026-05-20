from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apis.manager.serializers import SiteMediaReadSerializer
from apis.public.permissions import HasWorkspaceAPIKey, WorkspaceSlugMatches
from apis.public.site_permissions import WorkspaceSiteSlugMatches
from apis.utils import envelope
from core.entities.sites.models import Page, Site, SiteContentSlot, SiteMedia
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


class PublicPageReadSerializer(serializers.ModelSerializer):
    """Public-safe projection of a `Page`.

    Drops the manager-internal `id` and `status` fields (the public endpoint
    only ever returns published rows, so status is redundant). `created_at`
    is also omitted — `updated_at` is enough for cache invalidation on the
    consumer side.
    """

    class Meta:
        model = Page
        fields = ("slug", "title", "body", "seo", "updated_at")


class PublicPageBySlugView(APIView):
    """Return a single published `Page` for a site, looked up by slug.

    URL shape:
        GET /api/content/sites/<workspace_slug>/<site_slug>/page/?slug=<page_slug>

    Notes:
      - Anonymous (`AllowAny`) — public sites need to be readable without
        an API key so a Next.js / static frontend can fetch them. If/when
        we offer "private" sites, gate this view on a per-site flag rather
        than reintroducing auth at the URL level.
      - `slug=` may be empty; an empty slug looks up the site's homepage
        (`Page.slug == ""`). Query-param form lets the homepage have a
        clean URL without sentinel path segments like `/_home`.
      - Drafts are intentionally invisible from this endpoint — only
        `status == "published"` rows are returned.
    """

    permission_classes = [AllowAny]

    def get(self, request, workspace_slug, site_slug, *args, **kwargs):
        site = (
            Site.objects.filter(
                workspace__slug=workspace_slug,
                slug=site_slug,
            )
            .select_related("workspace")
            .first()
        )
        if site is None:
            return Response(
                envelope(False, message="Site not found."),
                status=status.HTTP_404_NOT_FOUND,
            )

        # Empty `slug` (homepage) is a perfectly valid query — distinguish
        # "not provided" from "provided as empty" so callers can ask for
        # the homepage without quirky URL encoding.
        raw_slug = request.query_params.get("slug", "")
        page_slug = raw_slug.strip().strip("/").lower()

        page = (
            Page.objects.filter(
                site=site,
                slug=page_slug,
                status=Page.Status.PUBLISHED,
            )
            .first()
        )
        if page is None:
            return Response(
                envelope(False, message="Page not found."),
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            envelope(True, data={"page": PublicPageReadSerializer(page).data}),
            status=status.HTTP_200_OK,
        )


class PublicContentSlotReadSerializer(serializers.ModelSerializer):
    """Public-safe projection of a `SiteContentSlot` for the live site renderer."""

    class Meta:
        model = SiteContentSlot
        fields = ("id", "key", "subtype", "label", "body", "updated_at")


class PublicSiteContentSlotsView(APIView):
    """List content slots for a site (entries, hero, footer, …).

    URL shape:
        GET /api/content/sites/<workspace_slug>/<site_slug>/slots/
            ?key=entry&subtype=focusarea

    Authenticate with `X-CMS-API-Key` (or `Authorization: Bearer pcm_…`).
    The key must belong to the workspace in the URL; the site must exist under
    that workspace.
    """

    authentication_classes = [WorkspaceApiKeyAuthentication]
    permission_classes = [AllowAny, HasWorkspaceAPIKey, WorkspaceSiteSlugMatches]

    def get(self, request, workspace_slug, site_slug, *args, **kwargs):
        site = (
            Site.objects.filter(
                workspace__slug=workspace_slug,
                slug=site_slug,
            )
            .select_related("workspace")
            .first()
        )
        if site is None:
            return Response(
                envelope(False, message="Site not found."),
                status=status.HTTP_404_NOT_FOUND,
            )

        slots = SiteContentSlot.objects.filter(site=site)
        key_filter = (request.query_params.get("key") or "").strip()
        if key_filter:
            allowed = {c.value for c in SiteContentSlot.SlotType}
            if key_filter not in allowed:
                return Response(
                    {"detail": "Invalid key filter."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            slots = slots.filter(key=key_filter)
        subtype_filter = (request.query_params.get("subtype") or "").strip()
        if subtype_filter:
            slots = slots.filter(subtype__iexact=subtype_filter)
        slots = slots.order_by("key", "id")

        return Response(
            envelope(
                True,
                data={"slots": PublicContentSlotReadSerializer(slots, many=True).data},
            ),
            status=status.HTTP_200_OK,
        )


class PublicSiteMediaView(APIView):
    """List site media with absolute URLs for the live renderer.

    URL shape:
        GET /api/content/sites/<workspace_slug>/<site_slug>/media/
            ?kind=image&ids=1,2,3

    Authenticate with `X-CMS-API-Key` (same as `/slots/`).
    """

    authentication_classes = [WorkspaceApiKeyAuthentication]
    permission_classes = [AllowAny, HasWorkspaceAPIKey, WorkspaceSiteSlugMatches]

    def get(self, request, workspace_slug, site_slug, *args, **kwargs):
        site = (
            Site.objects.filter(
                workspace__slug=workspace_slug,
                slug=site_slug,
            )
            .select_related("workspace")
            .first()
        )
        if site is None:
            return Response(
                envelope(False, message="Site not found."),
                status=status.HTTP_404_NOT_FOUND,
            )

        rows = SiteMedia.objects.filter(site=site).select_related("group").order_by("-created_at", "-id")
        kind_filter = (request.query_params.get("kind") or "").strip()
        if kind_filter in (SiteMedia.MediaKind.IMAGE, SiteMedia.MediaKind.VIDEO):
            rows = rows.filter(kind=kind_filter)
        ids_raw = (request.query_params.get("ids") or "").strip()
        if ids_raw:
            id_list: list[int] = []
            for part in ids_raw.split(","):
                part = part.strip()
                if part.isdigit():
                    id_list.append(int(part))
            if id_list:
                rows = rows.filter(pk__in=id_list)

        return Response(
            envelope(
                True,
                data={
                    "media": SiteMediaReadSerializer(
                        rows,
                        many=True,
                        context={"request": request},
                    ).data
                },
            ),
            status=status.HTTP_200_OK,
        )
