from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from ..serializers import GoogleAuthSerializer, LoginSerializer, UserRegisterSerializer


def get_token_for_user(user):
    refresh = RefreshToken.for_user(user)

    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }


class RegisterView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="Registration new user",
        request_body=UserRegisterSerializer,
        responses={201: openapi.Response("User registered successfully")},
    )
    def post(self, request):
        serializer = UserRegisterSerializer(data=request.data)

        if serializer.is_valid():
            user = serializer.save()
            tokens = get_token_for_user(user)

            return Response(
                {"message": "User registered successfully", "tokens": tokens},
                status=status.HTTP_201_CREATED,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="Login with email and password",
        request_body=LoginSerializer,
        responses={200: openapi.Response("Login successfully")},
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})

        if serializer.is_valid():
            user = serializer.validated_data["user"]
            tokens = get_token_for_user(user)

            return Response({"message": "Login successfully", "tokens": tokens})

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GoogleAuthView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="Login with Google OAuth2",
        request_body=GoogleAuthSerializer,
        responses={200: openapi.Response("Google authentication successfully")},
    )
    def post(self, request):
        serializer = GoogleAuthSerializer(data=request.data)

        if serializer.is_valid():
            user = serializer.validated_data["user"]
            tokens = get_token_for_user(user)

            return Response(
                {"message": "Google authentication successfully", "tokens": tokens}
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CustomTokenRefreshView(TokenRefreshView):
    @swagger_auto_schema(
        operation_description="Updating the access token using a refresh token",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "refresh": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Refresh token",
                ),
            },
            required=["refresh"],
        ),
        responses={200: openapi.Response("Access token updated successfully")},
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)
