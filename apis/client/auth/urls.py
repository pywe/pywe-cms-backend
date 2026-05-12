from django.urls import path

from apis.client.auth.views import MemberTokenObtainPairView

urlpatterns = [
    path("token/", MemberTokenObtainPairView.as_view(), name="member-token-obtain"),
]
