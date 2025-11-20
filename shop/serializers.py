from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.core.validators import validate_email
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.utils.translation import gettext_lazy as _
from google.oauth2 import id_token
from google.auth.transport import requests
from django.conf import settings
from .models import Customer, Category, AnimalType
import logging
import random

from .services.category_service import CategoryTreeService

logger = logging.getLogger(__name__)


class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True, required=True, validators=[validate_password]
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
                value, requests.Request(), settings.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY
            )
        except ValueError as e:
            logger.error(f"Google token validation failed: {e}")
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
            logger.info(f"New user created via Google Auth: {email}")

        self.context["user"] = user
        return value

    def validate(self, attrs):
        attrs["user"] = self.context["user"]
        return attrs


class AnimalTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnimalType
        fields = ["id", "name", "slug", "icon", "is_active"]
        read_only_fields = ["id"]


class AnimalTypeCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating animal types (without ID)"""

    class Meta:
        model = AnimalType
        fields = ["name", "slug", "icon", "is_active"]


class CategoryMinimalSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ["id", "name", "slug", "image_url", "level", "url"]

    def get_url(self, obj):
        return f"/{obj.animal_type.slug}/{obj.slug}/"


class CategoryDetailSerializer(serializers.ModelSerializer):
    animal_type = AnimalTypeSerializer(read_only=True)
    parent = CategoryMinimalSerializer(read_only=True)
    breadcrumbs = serializers.SerializerMethodField()
    children_count = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "image_url",
            "animal_type",
            "parent",
            "level",
            "sort_order",
            "breadcrumbs",
            "children_count",
            "url",
            "created_at",
        ]

    def get_breadcrumbs(self, obj):
        return CategoryTreeService.get_breadcrumbs(obj.slug, obj.animal_type.slug)

    def get_children_count(self, obj):
        return obj.children.filter(is_active=True).count()

    def get_url(self, obj):
        return f"/{obj.animal_type.slug}/{obj.slug}/"


class CategoryCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating categories"""

    animal_type = serializers.SlugRelatedField(
        slug_field="slug", queryset=AnimalType.objects.all()
    )
    parent = serializers.SlugRelatedField(
        slug_field="slug",
        queryset=Category.objects.all(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Category
        fields = [
            "name",
            "slug",
            "description",
            "parent",
            "animal_type",
            "image_url",
            "is_active",
            "sort_order",
        ]
        extra_kwargs = {"slug": {"required": False}}


class CategoryTreeNodeSerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "image_url",
            "level",
            "children",
            "url",
        ]

    def get_children(self, obj):
        if hasattr(obj, "children") and obj.children:
            return CategoryTreeNodeSerializer(obj.children, many=True).data
        return []

    def get_url(self, obj):
        return f"/{obj.animal_type.slug}/{obj.slug}/"


class CategoryTreeSerializer(serializers.Serializer):
    def to_representation(self, instance):
        return CategoryTreeNodeSerializer(instance, many=True).data
