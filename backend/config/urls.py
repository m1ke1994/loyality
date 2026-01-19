from django.contrib import admin
from django.http import JsonResponse
from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path("healthz", lambda request: JsonResponse({"status": "ok"})),
    path("admin/", admin.site.urls),
    path("api/v1/auth/refresh", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/v1/", include("loyalty.urls")),
]
