from django.urls import include, path

from apis.client import views

urlpatterns = [
    path("health/", views.health, name="client-health"),
    path("auth/", include("apis.client.auth.urls")),
]
