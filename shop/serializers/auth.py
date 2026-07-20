import logging
import random

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.validators import validate_email
from django.utils.translation import gettext_lazy as _
from google.auth.transport import requests
from google.oauth2 import id_token
from rest_framework import serializers

from ..models import Customer


logger = logging.getLogger("shop.serializers")


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "phone_number",
            "address",
            "email_verified",
        )
        read_only_fields = fields


class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
    )
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = Customer
        fields = ("email", "password", "password2")
        extra_kwargs = {
            "email": {"required": True},
        }

    def validate_email(self, value):
        try:
            validate_email(value)
        except ValidationError:
            raise serializers.ValidationError(_("Enter a valid email address."))

        if Customer.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                _("A user with that email already exists.")
            )

        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError(
                {"password": _("Password fields didn't match.")}
            )

        return attrs

    def create(self, validated_data):
        validated_data.pop("password2")

        user = Customer.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
        )
        user.email_verified = True
        user.save()

        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get("email")
        password = attrs.get("password")

        try:
            user = Customer.objects.get(email=email)
        except ObjectDoesNotExist:
            raise serializers.ValidationError(_("Invalid email or password."))

        if not user.check_password(password):
            raise serializers.ValidationError(_("Invalid email or password."))

        if not user.is_active:
            raise serializers.ValidationError(_("User account disabled."))

        if not user.email_verified:
            raise serializers.ValidationError(_("Email not verified."))

        attrs["user"] = user
        return attrs


class GoogleAuthSerializer(serializers.Serializer):
    token = serializers.CharField()

    def generate_username(self, email):
        base_username = email.split("@")[0]
        username = base_username
        counter = 1

        while Customer.objects.filter(username=username).exists():
            username = f"{base_username}_{random.randint(100, 999)}"
            counter += 1

            if counter > 10:
                username = f"user_{random.randint(1000, 9999)}"
                break

        return username

    def validate_token(self, value):
        try:
            idinfo = id_token.verify_oauth2_token(
                value,
                requests.Request(),
                settings.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY,
            )
        except ValueError as error:
            logger.error("Google token validation failed: %s", error)
            raise serializers.ValidationError(_("Invalid Google token."))

        if idinfo.get("iss") not in [
            "accounts.google.com",
            "https://accounts.google.com",
        ]:
            raise serializers.ValidationError(_("It is not a Google account."))

        if idinfo.get("aud") != settings.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY:
            raise serializers.ValidationError(_("Token audience mismatch."))

        email = idinfo.get("email")

        if not email:
            raise serializers.ValidationError(_("No email in token."))

        if not idinfo.get("email_verified", False):
            raise serializers.ValidationError(_("Google account email not verified."))

        user, created = Customer.objects.get_or_create(
            email=email,
            defaults={
                "username": self.generate_username(email),
            },
        )

        if created:
            logger.info("New user created via Google Auth: %s", email)

        self.context["user"] = user
        return value

    def validate(self, attrs):
        attrs["user"] = self.context["user"]
        return attrs
