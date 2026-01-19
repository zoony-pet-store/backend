from django.db.models import Prefetch
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.core.validators import validate_email
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from google.oauth2 import id_token
from google.auth.transport import requests
from django.conf import settings
from .models import (
    Customer,
    Category,
    AnimalType,
    Brand,
    Badge,
    ProductAttributeValue,
    ProductVariant,
    ProductImage,
    ProductReview,
    Product,
)
import logging
import random


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


# ========== ANIMAL TYPE SERIALIZERS ==========
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


# ========== CATEGORY SERIALIZERS FOR ADMIN ==========
class CategoryDetailSerializer(serializers.ModelSerializer):
    animal_type = AnimalTypeSerializer(read_only=True)
    parent = serializers.SerializerMethodField()
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

    def get_parent(self, obj):
        if obj.parent:
            return {
                "id": obj.parent.id,
                "name": obj.parent.name,
                "slug": obj.parent.slug,
            }
        return None

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


# ========== CATEGORY SERIALIZERS FOR FRONTEND ==========
class CategorySerializer(serializers.ModelSerializer):
    """Basic category serializer with minimal fields"""

    class Meta:
        model = Category
        fields = ["name", "slug", "image_url"]


class CategoryTreeSerializer(CategorySerializer):
    """Recursive category serializer for tree structure"""

    subcategories = serializers.SerializerMethodField()

    class Meta(CategorySerializer.Meta):
        fields = ["name", "slug", "image_url", "subcategories"]

    def get_subcategories(self, obj):
        # Get prefetched children if available
        if hasattr(obj, "prefetched_children"):
            children = obj.prefetched_children
        elif hasattr(obj, "children"):
            children = obj.children.filter(is_active=True)
        else:
            children = Category.objects.filter(parent=obj, is_active=True)

        # Control recursion depth
        max_depth = self.context.get("max_depth", 3)
        current_depth = self.context.get("current_depth", 0)

        if current_depth >= max_depth:
            return []

        # Create context for child serializers
        child_context = self.context.copy()
        child_context["current_depth"] = current_depth + 1

        return CategoryTreeSerializer(children, many=True, context=child_context).data

    def to_representation(self, instance):
        """
        Custom representation to hide image_url for root categories.
        """
        representation = super().to_representation(instance)

        # Hide image_url for root categories (parent is None)
        if instance.parent is None:
            representation.pop("image_url", None)

        return representation


class CategoryWithChildrenSerializer(CategorySerializer):
    """Serializer for category with direct children only"""

    subcategories = serializers.SerializerMethodField()

    class Meta(CategorySerializer.Meta):
        fields = ["name", "slug", "image_url", "subcategories"]

    def get_subcategories(self, obj):
        children = obj.children.filter(is_active=True)
        return CategorySerializer(children, many=True).data


# ========== ANIMAL TYPE WITH CATEGORIES ==========
class AnimalTypeWithCategoriesSerializer(serializers.ModelSerializer):
    """Serializer for animal type with full category tree"""

    categories = serializers.SerializerMethodField()
    icon = serializers.CharField(read_only=True)

    class Meta:
        model = AnimalType
        fields = ["name", "slug", "icon", "image_url", "categories"]

    def get_categories(self, obj):
        # Get root categories with prefetched children
        root_categories = obj.categories.filter(
            parent__isnull=True, is_active=True
        ).prefetch_related(
            Prefetch(
                "children",
                queryset=Category.objects.filter(is_active=True).prefetch_related(
                    Prefetch(
                        "children", queryset=Category.objects.filter(is_active=True)
                    )
                ),
            )
        )

        max_depth = self.context.get("max_depth", 2)

        return CategoryTreeSerializer(
            root_categories,
            many=True,
            context={"max_depth": max_depth, "current_depth": 0},
        ).data


class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ["id", "name", "slug", "description", "logo_url", "is_active"]


class ProductAttributeValueSerializer(serializers.ModelSerializer):
    """Serializer for product attribute values (size, color, volume, etc.)"""

    attribute_name = serializers.CharField(source="attribute.name", read_only=True)

    class Meta:
        model = ProductAttributeValue
        fields = ["id", "attribute", "attribute_name", "value", "slug"]


class ProductImageSerializer(serializers.ModelSerializer):
    """Serializer for product images"""

    class Meta:
        model = ProductImage
        fields = ["id", "image_url", "alt_text", "is_main", "display_order"]


class ProductVariantSerializer(serializers.ModelSerializer):
    """Serializer for product variants (different sizes, colors, etc.)"""

    attributes = ProductAttributeValueSerializer(many=True, read_only=True)
    images = serializers.SerializerMethodField()

    class Meta:
        model = ProductVariant
        fields = [
            "id",
            "sku",
            "price",
            "old_price",
            "has_discount",
            "discount_percentage",
            "stock",
            "weight",
            "dimensions",
            "attributes",
            "images",
            "is_active",
        ]

    def get_images(self, obj):
        # Return variant-specific images, fallback to product images
        images = obj.images.all()
        if not images.exists():
            images = obj.product.images.all()
        return ProductImageSerializer(images, many=True).data


class ProductReviewSerializer(serializers.ModelSerializer):
    """Serializer for product reviews"""

    user_name = serializers.CharField(source="user.get_full_name", read_only=True)

    class Meta:
        model = ProductReview
        fields = [
            "id",
            "user",
            "user_name",
            "rating",
            "title",
            "comment",
            "is_verified",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["user"]


class BadgeSerializer(serializers.ModelSerializer):
    """Serializer for Badge model"""

    class Meta:
        model = Badge
        fields = ["id", "name", "slug", "label", "color", "background_color"]
        read_only_fields = ["id"]


class ProductCardSerializer(serializers.ModelSerializer):
    """Serializer for product short version (product card in listings)"""

    brand = serializers.CharField(source="brand.name")
    image_url = serializers.SerializerMethodField()
    price = serializers.SerializerMethodField()
    old_price = serializers.SerializerMethodField()
    discount_percentage = serializers.SerializerMethodField()
    in_stock = serializers.SerializerMethodField()
    badges = serializers.SerializerMethodField()
    variants_display = serializers.SerializerMethodField()
    category_slug = serializers.CharField(source="category.slug")
    animal_type_slug = serializers.CharField(source="category.animal_type.slug")

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "brand",
            "image_url",
            "price",
            "old_price",
            "discount_percentage",
            "in_stock",
            "rating",
            "review_count",
            "badges",
            "variants_display",
            "category_slug",
            "animal_type_slug",
            "is_featured",
        ]

    def get_image_url(self, obj):
        main_image = obj.images.filter(is_main=True).first()
        if main_image:
            return main_image.image_url
        first_image = obj.images.first()
        if first_image:
            return first_image.image_url
        return obj.main_image or None

    def get_price(self, obj):
        variants = obj.variants.filter(is_active=True, stock__gt=0)
        if variants.exists():
            return min(variant.price for variant in variants)
        return None

    def get_old_price(self, obj):
        variants = obj.variants.filter(is_active=True, stock__gt=0, has_discount=True)
        if variants.exists():
            old_prices = [v.old_price for v in variants if v.old_price]
            if old_prices:
                return max(old_prices)
        return None

    def get_discount_percentage(self, obj):
        variants = obj.variants.filter(is_active=True, stock__gt=0, has_discount=True)
        if variants.exists():
            discounts = [
                v.discount_percentage for v in variants if v.discount_percentage
            ]
            if discounts:
                return max(discounts)
        return None

    def get_in_stock(self, obj):
        return obj.variants.filter(is_active=True, stock__gt=0).exists()

    def get_badges(self, obj):
        badges_list = []

        badge_objects = obj.badges.filter(is_active=True)
        for badge in badge_objects:
            badges_list.append(
                {
                    "name": badge.name,
                    "label": badge.label,
                    "color": badge.color,
                    "background_color": badge.background_color,
                }
            )

        # Bestseller badge
        if (
            obj.rating >= 4.5
            and obj.review_count >= 10
            and not any(b["name"] == "bestseller" for b in badges_list)
        ):
            badges_list.append(
                {
                    "name": "bestseller",
                    "label": "Bestseller",
                    "color": "#000000",
                    "background_color": "#FFD700",
                }
            )

        # New arrival badge (last 30 days)
        if obj.created_at > timezone.now() - timezone.timedelta(days=30) and not any(
            b["name"] == "new" for b in badges_list
        ):
            badges_list.append(
                {
                    "name": "new",
                    "label": "New",
                    "color": "#FFFFFF",
                    "background_color": "#28A745",
                }
            )

        # Discount badge
        if obj.variants.filter(has_discount=True, is_active=True).exists() and not any(
            b["name"] == "discount" for b in badges_list
        ):
            badges_list.append(
                {
                    "name": "discount",
                    "label": "Discount",
                    "color": "#FFFFFF",
                    "background_color": "#DC3545",
                }
            )

        # Featured badge
        if obj.is_featured and not any(b["name"] == "featured" for b in badges_list):
            badges_list.append(
                {
                    "name": "featured",
                    "label": "Featured",
                    "color": "#FFFFFF",
                    "background_color": "#6F42C1",
                }
            )

        # Sale badge
        if obj.variants.filter(has_discount=True, is_active=True).exists():
            max_discount = 0
            for variant in obj.variants.filter(has_discount=True, is_active=True):
                if (
                    variant.discount_percentage
                    and variant.discount_percentage > max_discount
                ):
                    max_discount = variant.discount_percentage

            if max_discount >= 20 and not any(b["name"] == "sale" for b in badges_list):
                badges_list.append(
                    {
                        "name": "sale",
                        "label": f"Sale {max_discount}%",
                        "color": "#FFFFFF",
                        "background_color": "#FF6B6B",
                    }
                )

        # Trending badge
        if (
            obj.review_count >= 20
            and obj.rating >= 4.0
            and not any(b["name"] == "trending" for b in badges_list)
        ):
            badges_list.append(
                {
                    "name": "trending",
                    "label": "Trending",
                    "color": "#FFFFFF",
                    "background_color": "#FD7E14",
                }
            )

        return badges_list

    def get_variants_display(self, obj):
        """Return variant display values for product card (e.g., ['1 l', '35x62'])"""
        variants = obj.variants.filter(is_active=True, stock__gt=0)

        display_values = set()
        for variant in variants:
            attrs = variant.attributes.all()
            for attr in attrs:
                if attr.attribute.name.lower() in ["size", "volume"]:
                    display_values.add(attr.value)

        return list(display_values)[:5]


class ProductDetailSerializer(ProductCardSerializer):
    """Full product details serializer - extends card serializer"""

    variants = ProductVariantSerializer(many=True, read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    reviews = ProductReviewSerializer(many=True, read_only=True)
    available_attributes = serializers.SerializerMethodField()
    category = serializers.SerializerMethodField()
    brand = BrandSerializer(read_only=True)

    class Meta:
        model = Product
        fields = ProductCardSerializer.Meta.fields + [
            "description",
            "short_description",
            "category",
            "variants",
            "images",
            "reviews",
            "available_attributes",
            "meta_title",
            "meta_description",
            "composition",
            "nutritional_analysis",
            "feeding_guidelines",
            "ingredients",
            "nutritional_value",
            "feeding_table",
            "created_at",
        ]

    def get_category(self, obj):
        return {
            "id": obj.category.id,
            "name": obj.category.name,
            "slug": obj.category.slug,
            "animal_type": {
                "name": obj.category.animal_type.name,
                "slug": obj.category.animal_type.slug,
            },
        }

    def get_available_attributes(self, obj):
        """Get available attributes with their values for product filtering"""
        attributes = {}
        for variant in obj.variants.filter(is_active=True):
            for attr_value in variant.attributes.all():
                attr_name = attr_value.attribute.name
                if attr_name not in attributes:
                    attributes[attr_name] = {
                        "attribute_id": attr_value.attribute.id,
                        "values": [],
                    }
                if attr_value.value not in attributes[attr_name]["values"]:
                    attributes[attr_name]["values"].append(
                        {
                            "id": attr_value.id,
                            "value": attr_value.value,
                            "slug": attr_value.slug,
                        }
                    )
        return attributes


class BrandMinimalSerializer(serializers.ModelSerializer):
    """Minimal serializer for brand list (used in filters)"""

    class Meta:
        model = Brand
        fields = ["id", "name", "slug", "logo_url"]


class ProductFilterSerializer(serializers.Serializer):
    """Serializer for product filter options"""

    min_price = serializers.DecimalField(max_digits=10, decimal_places=2)
    max_price = serializers.DecimalField(max_digits=10, decimal_places=2)
    brands = BrandMinimalSerializer(many=True)
