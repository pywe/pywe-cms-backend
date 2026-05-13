from django.urls import path

from apis.public import views

urlpatterns = [
    # Headless workspace bootstrap. `slug` here is the workspace slug;
    # auth is via X-CMS-API-Key bound to that workspace.
    path(
        "sites/<slug:slug>/",
        views.SiteBootstrapView.as_view(),
        name="public-site-bootstrap",
    ),
    # Public page-by-slug lookup for the live frontend renderer. Both
    # `workspace_slug` and `site_slug` are required because site slugs are
    # only unique within a workspace. The page slug travels in `?slug=`
    # so the homepage can be fetched with `?slug=` (no path sentinel).
    path(
        "sites/<slug:workspace_slug>/<slug:site_slug>/page/",
        views.PublicPageBySlugView.as_view(),
        name="public-page-by-slug",
    ),
]
