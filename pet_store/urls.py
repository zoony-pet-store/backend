from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from shop import views
from shop.views import index, health_check

schema_view = get_schema_view(
    openapi.Info(
        title="Auth API",
        default_version="v1",
        description="User authentication API",
    ),
    public=True,
    permission_classes=[
        permissions.AllowAny,
    ],
    authentication_classes=[],
)


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("shop.urls")),
    path(
        "api/docs",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    path("", index, name="home"),
    path("health/", views.health_check, name="health-check"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

schema_view.public = True
schema_view.permission_classes = (permissions.AllowAny,)
schema_view.authentication_classes = []
