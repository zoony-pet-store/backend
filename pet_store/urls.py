from django.contrib import admin
from django.urls import path, include
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

from shop import views
from shop.views import index

schema_view = get_schema_view(
    openapi.Info(
        title="Zoony API",
        default_version="v1",
        description="Full Zoony API",
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    path("admin", admin.site.urls),
    path(
        "api/docs",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    path("api/auth/", include("shop.auth_urls")),
    path("api/", include("shop.urls")),
    path("", index, name="home"),
    path("health/", views.health_check, name="health-check"),
]

urlpatterns += staticfiles_urlpatterns()
