from django.urls import path
from .views import RegisterView, LoginView, GoogleAuthView, CustomTokenRefreshView

urlpatterns = [
    path("register", RegisterView.as_view(), name="register"),
    path("login", LoginView.as_view(), name="login"),
    path("google", GoogleAuthView.as_view(), name="google_auth"),
    path("token/refresh", CustomTokenRefreshView.as_view(), name="token_refresh"),
]
