from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from ..serializers import (
    CustomerSerializer,
    GoogleAuthSerializer,
    LoginSerializer,
    UserRegisterSerializer,
)


def create_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)

    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }


class RegisterView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="Register a new user",
        request_body=UserRegisterSerializer,
        responses={
            201: openapi.Response(
                description="User registered successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                        "user": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                        ),
                        "tokens": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "refresh": openapi.Schema(type=openapi.TYPE_STRING),
                                "access": openapi.Schema(type=openapi.TYPE_STRING),
                            },
                        ),
                    },
                ),
            ),
        },
    )
    def post(self, request):
        serializer = UserRegisterSerializer(data=request.data)

        if serializer.is_valid():
            user = serializer.save()
            tokens = create_tokens_for_user(user)

            return Response(
                {
                    "message": "User registered successfully",
                    "user": CustomerSerializer(user).data,
                    "tokens": tokens,
                },
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
        serializer = LoginSerializer(
            data=request.data,
            context={"request": request},
        )

        if serializer.is_valid():
            user = serializer.validated_data["user"]
            tokens = create_tokens_for_user(user)

            return Response(
                {
                    "message": "Login successfully",
                    "user": CustomerSerializer(user).data,
                    "tokens": tokens,
                },
                status=status.HTTP_200_OK,
            )

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
            tokens = create_tokens_for_user(user)

            return Response(
                {
                    "message": "Google authentication successfully",
                    "user": CustomerSerializer(user).data,
                    "tokens": tokens,
                },
                status=status.HTTP_200_OK,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Get current authenticated user",
        responses={
            200: CustomerSerializer,
            401: openapi.Response("Authentication credentials were not provided"),
        },
    )
    def get(self, request):
        serializer = CustomerSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CustomTokenRefreshView(TokenRefreshView):
    @swagger_auto_schema(
        operation_description="Update the access token using a refresh token",
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
