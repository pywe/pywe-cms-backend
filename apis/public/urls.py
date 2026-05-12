from django.urls import path

from apis.public import views

urlpatterns = [
    path(
        "sites/<slug:slug>/",
        views.SiteBootstrapView.as_view(),
        name="public-site-bootstrap",
    ),
]
