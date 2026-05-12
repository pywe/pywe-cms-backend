from django.urls import path

from apis.admin import views

urlpatterns = [
    path("token/", views.AdminTokenObtainPairView.as_view(), name="admin-token-obtain"),
    path("me/", views.me, name="admin-me"),
]
