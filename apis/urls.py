from django.urls import include, path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions
from rest_framework_simplejwt.views import TokenRefreshView

schema_view = get_schema_view(
    openapi.Info(
        title="Pywe CMS API",
        default_version="v1",
        description="HTTP API for pywe-cms-backend",
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("client/", include("apis.client.urls")),
    path("manager/", include("apis.manager.urls")),
    path("content/", include("apis.public.urls")),
    path("admin/", include("apis.admin.urls")),
    path(
        "swagger/",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    path(
        "redoc/",
        schema_view.with_ui("redoc", cache_timeout=0),
        name="schema-redoc",
    ),
]
