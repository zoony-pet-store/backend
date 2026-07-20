from django.urls import path
from .views import (
    RegisterView,
    LoginView,
    GoogleAuthView,
    CustomTokenRefreshView,
    CurrentUserView,
)

urlpatterns = [
    path("register", RegisterView.as_view(), name="register"),
    path("login", LoginView.as_view(), name="login"),
    path("google", GoogleAuthView.as_view(), name="google-auth"),
    path("token/refresh", CustomTokenRefreshView.as_view(), name="token-refresh"),
    path("me", CurrentUserView.as_view(), name="current-user"),
]
