from django.urls import include, path

from apis.manager import views

urlpatterns = [
    path("auth/register/", views.ManagerRegisterView.as_view(), name="manager-register"),
    path("auth/otp/request/", views.ManagerOtpRequestView.as_view(), name="manager-otp-request"),
    path("auth/otp/verify/", views.ManagerOtpVerifyView.as_view(), name="manager-otp-verify"),
    path("auth/", include("apis.client.auth.urls")),
    path("profile/", views.ManagerProfileView.as_view(), name="manager-profile"),
    path("workspaces/", views.WorkspaceListCreateView.as_view(), name="manager-workspaces"),
    path(
        "workspaces/api-key/rotate/",
        views.WorkspaceRotateApiKeyView.as_view(),
        name="manager-workspace-rotate-api-key",
    ),
    path("sites/", views.SiteListCreateView.as_view(), name="manager-sites"),
    path(
        "sites/<slug:site_slug>/content-slot-types/",
        views.SiteContentSlotTypesView.as_view(),
        name="manager-site-content-slot-types",
    ),
    path(
        "sites/<slug:site_slug>/content-slots/<int:slot_id>/",
        views.SiteContentSlotDetailView.as_view(),
        name="manager-site-content-slot-detail",
    ),
    path(
        "sites/<slug:site_slug>/content-slots/",
        views.SiteContentSlotListCreateView.as_view(),
        name="manager-site-content-slots",
    ),
    path(
        "sites/<slug:site_slug>/media/bulk-group/",
        views.SiteMediaBulkGroupView.as_view(),
        name="manager-site-media-bulk-group",
    ),
    path(
        "sites/<slug:site_slug>/media/bulk-delete/",
        views.SiteMediaBulkDeleteView.as_view(),
        name="manager-site-media-bulk-delete",
    ),
    path(
        "sites/<slug:site_slug>/media/groups/<int:group_id>/",
        views.SiteMediaGroupDetailView.as_view(),
        name="manager-site-media-group-detail",
    ),
    path(
        "sites/<slug:site_slug>/media/groups/",
        views.SiteMediaGroupListCreateView.as_view(),
        name="manager-site-media-groups",
    ),
    path(
        "sites/<slug:site_slug>/media/",
        views.SiteMediaListCreateView.as_view(),
        name="manager-site-media",
    ),
    path("sites/<slug:site_slug>/", views.SiteDetailView.as_view(), name="manager-site-detail"),
]
