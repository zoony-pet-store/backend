import logging
import random

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.validators import validate_email
from django.db.models import Prefetch
from django.utils.translation import gettext_lazy as _
from google.auth.transport import requests
from google.oauth2 import id_token
from rest_framework import serializers

from .models import (
    AnimalType,
    Badge,
    Brand,
    Category,
    Customer,
    Product,
    ProductImage,
    ProductReview,
    ProductVariant,
)


logger = logging.getLogger(__name__)


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


class AnimalTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnimalType
        fields = ["id", "name", "slug", "icon", "is_active"]
        read_only_fields = ["id"]


class AnimalTypeCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnimalType
        fields = ["name", "slug", "icon", "is_active"]


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
        if not obj.parent:
            return None

        return {
            "id": str(obj.parent.id),
            "name": obj.parent.name,
            "slug": obj.parent.slug,
        }

    def get_breadcrumbs(self, obj):
        breadcrumbs = []
        current = obj

        while current:
            breadcrumbs.append(
                {
                    "id": str(current.id),
                    "name": current.name,
                    "slug": current.slug,
                }
            )
            current = current.parent

        return list(reversed(breadcrumbs))

    def get_children_count(self, obj):
        return obj.children.filter(is_active=True).count()

    def get_url(self, obj):
        return f"/{obj.animal_type.slug}/{obj.slug}/"


class CategoryCreateUpdateSerializer(serializers.ModelSerializer):
    animal_type = serializers.SlugRelatedField(
        slug_field="slug",
        queryset=AnimalType.objects.all(),
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


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["name", "slug", "image_url"]


class CategoryTreeSerializer(CategorySerializer):
    subcategories = serializers.SerializerMethodField()

    class Meta(CategorySerializer.Meta):
        fields = ["name", "slug", "image_url", "subcategories"]

    def get_subcategories(self, obj):
        if hasattr(obj, "prefetched_children"):
            children = obj.prefetched_children
        elif hasattr(obj, "children"):
            children = obj.children.filter(is_active=True)
        else:
            children = Category.objects.filter(parent=obj, is_active=True)

        max_depth = self.context.get("max_depth", 3)
        current_depth = self.context.get("current_depth", 0)

        if current_depth >= max_depth:
            return []

        child_context = self.context.copy()
        child_context["current_depth"] = current_depth + 1

        return CategoryTreeSerializer(
            children,
            many=True,
            context=child_context,
        ).data

    def to_representation(self, instance):
        representation = super().to_representation(instance)

        if instance.parent is None:
            representation.pop("image_url", None)

        return representation


class CategoryWithChildrenSerializer(CategorySerializer):
    subcategories = serializers.SerializerMethodField()

    class Meta(CategorySerializer.Meta):
        fields = ["name", "slug", "image_url", "subcategories"]

    def get_subcategories(self, obj):
        children = obj.children.filter(is_active=True)
        return CategorySerializer(children, many=True).data


class AnimalTypeWithCategoriesSerializer(serializers.ModelSerializer):
    categories = serializers.SerializerMethodField()
    icon = serializers.CharField(read_only=True)

    class Meta:
        model = AnimalType
        fields = ["name", "slug", "icon", "image_url", "categories"]

    def get_categories(self, obj):
        root_categories = obj.categories.filter(
            parent__isnull=True,
            is_active=True,
        ).prefetch_related(
            Prefetch(
                "children",
                queryset=Category.objects.filter(is_active=True).prefetch_related(
                    Prefetch(
                        "children",
                        queryset=Category.objects.filter(is_active=True),
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


class BrandMinimalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ["id", "name", "slug", "logo_url"]


class BadgeSerializer(serializers.ModelSerializer):
    id = serializers.SerializerMethodField()

    class Meta:
        model = Badge
        fields = ["id", "name", "slug", "label", "color", "background_color"]

    def get_id(self, obj):
        return str(obj.id)


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ["id", "image_url", "alt_text", "is_main", "display_order"]


class ProductVariantSerializer(serializers.ModelSerializer):
    attributes = serializers.SerializerMethodField()
    images = serializers.SerializerMethodField()
    badges = BadgeSerializer(many=True, read_only=True)
    has_discount = serializers.BooleanField(read_only=True)
    discount_percentage = serializers.IntegerField(read_only=True)
    in_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = ProductVariant
        fields = [
            "id",
            "sku",
            "attributes",
            "price",
            "old_price",
            "has_discount",
            "discount_percentage",
            "stock",
            "in_stock",
            "description",
            "short_description",
            "badges",
            "images",
            "is_default",
            "is_active",
        ]

    def get_attributes(self, obj):
        return {
            item.attribute.name: {
                "id": str(item.value.id),
                "value": item.value.value,
                "slug": item.value.slug,
            }
            for item in obj.variant_attributes.all()
        }

    def get_images(self, obj):
        images = list(obj.images.all())
        return ProductImageSerializer(images, many=True).data


class ProductVariantCardSerializer(serializers.ModelSerializer):
    attributes = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()
    badges = BadgeSerializer(many=True, read_only=True)
    has_discount = serializers.BooleanField(read_only=True)
    discount_percentage = serializers.IntegerField(read_only=True)
    in_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = ProductVariant
        fields = [
            "id",
            "sku",
            "attributes",
            "price",
            "old_price",
            "has_discount",
            "discount_percentage",
            "stock",
            "in_stock",
            "image_url",
            "badges",
            "is_default",
        ]

    def get_attributes(self, obj):
        return {
            item.attribute.name: item.value.value
            for item in obj.variant_attributes.all()
        }

    def get_image_url(self, obj):
        images = list(obj.images.all())

        main_image = next((image for image in images if image.is_main), None)
        if main_image:
            return main_image.image_url

        first_image = images[0] if images else None
        if first_image:
            return first_image.image_url

        return None


class ProductReviewItemSerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()
    image_urls = serializers.SerializerMethodField()
    positive_comment = serializers.SerializerMethodField()
    negative_comment = serializers.SerializerMethodField()

    class Meta:
        model = ProductReview
        fields = [
            "id",
            "username",
            "created_at",
            "rating",
            "image_urls",
            "updated_at",
            "comment",
            "positive_comment",
            "negative_comment",
        ]

    def get_username(self, obj):
        if obj.user:
            full_name = obj.user.get_full_name().strip()

            if full_name:
                return full_name

            if obj.user.username:
                return obj.user.username

            if obj.user.email:
                return obj.user.email.split("@")[0]

        return "Anonymous"

    def get_image_urls(self, obj):
        del obj
        return []

    def get_positive_comment(self, obj):
        del obj
        return None

    def get_negative_comment(self, obj):
        del obj
        return None


class ProductReviewSerializer(serializers.ModelSerializer):
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


class ProductCardSerializer(serializers.ModelSerializer):
    brand = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()
    price = serializers.SerializerMethodField()
    old_price = serializers.SerializerMethodField()
    discount_percentage = serializers.SerializerMethodField()
    in_stock = serializers.BooleanField(read_only=True)

    badges = serializers.SerializerMethodField()
    product_badges = serializers.SerializerMethodField()
    default_variant_badges = serializers.SerializerMethodField()

    variants = serializers.SerializerMethodField()
    available_attributes = serializers.SerializerMethodField()
    default_variant_id = serializers.SerializerMethodField()
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
            "product_badges",
            "default_variant_badges",
            "available_attributes",
            "default_variant_id",
            "variants",
            "category_slug",
            "animal_type_slug",
        ]

    def _get_active_variants(self, obj):
        if hasattr(obj, "active_variants"):
            return list(obj.active_variants)

        return list(
            obj.variants.filter(is_active=True)
            .prefetch_related(
                "badges",
                "images",
                "variant_attributes__attribute",
                "variant_attributes__value",
            )
            .order_by("-is_default", "price", "id")
        )

    def _get_default_variant(self, obj):
        variants = self._get_active_variants(obj)

        if not variants:
            return None

        default_variant = next(
            (variant for variant in variants if variant.is_default),
            None,
        )

        if default_variant:
            return default_variant

        return variants[0]

    def _serialize_badge(self, badge):
        return {
            "id": str(badge.id),
            "name": badge.name,
            "slug": badge.slug,
            "label": badge.label,
            "color": badge.color,
            "background_color": badge.background_color,
        }

    def _get_unique_serialized_badges(self, badges):
        badges_by_slug = {}

        for badge in badges:
            if not badge.is_active:
                continue

            badges_by_slug[badge.slug] = self._serialize_badge(badge)

        return list(badges_by_slug.values())

    def get_brand(self, obj):
        if not obj.brand:
            return None

        return {
            "id": str(obj.brand.id),
            "name": obj.brand.name,
            "slug": obj.brand.slug,
            "logo_url": obj.brand.logo_url,
        }

    def get_price(self, obj):
        default_variant = self._get_default_variant(obj)

        if not default_variant:
            return None

        return str(default_variant.price)

    def get_old_price(self, obj):
        default_variant = self._get_default_variant(obj)

        if not default_variant or not default_variant.has_discount:
            return None

        return str(default_variant.old_price)

    def get_image_url(self, obj):
        default_variant = self._get_default_variant(obj)

        if default_variant:
            variant_images = list(default_variant.images.all())

            variant_main_image = next(
                (image for image in variant_images if image.is_main),
                None,
            )
            if variant_main_image:
                return variant_main_image.image_url

            variant_first_image = variant_images[0] if variant_images else None
            if variant_first_image:
                return variant_first_image.image_url

        product_images = [
            image for image in obj.images.all() if image.variant_id is None
        ]

        product_main_image = next(
            (image for image in product_images if image.is_main),
            None,
        )
        if product_main_image:
            return product_main_image.image_url

        product_first_image = product_images[0] if product_images else None
        if product_first_image:
            return product_first_image.image_url

        return obj.main_image or None

    def get_discount_percentage(self, obj):
        default_variant = self._get_default_variant(obj)

        if default_variant and default_variant.has_discount:
            return default_variant.discount_percentage

        return None

    def get_product_badges(self, obj):
        """
        Badges attached directly to Product in admin.

        Example:
        New, Bestseller, Recommended.
        """
        return self._get_unique_serialized_badges(obj.badges.all())

    def get_default_variant_badges(self, obj):
        """
        Badges attached to default variant.

        Example:
        Discount, Sale, SKU-specific badges.
        """
        default_variant = self._get_default_variant(obj)

        if not default_variant:
            return []

        return self._get_unique_serialized_badges(default_variant.badges.all())

    def get_badges(self, obj):
        """
        Combined display badges.

        Kept for backward compatibility and simple product-card rendering.
        For exact badge source, frontend should use:
        - product_badges
        - default_variant_badges
        - variants[].badges
        """
        badges_by_slug = {}

        for badge_data in self.get_product_badges(obj):
            badges_by_slug[badge_data["slug"]] = badge_data

        for badge_data in self.get_default_variant_badges(obj):
            badges_by_slug[badge_data["slug"]] = badge_data

        return list(badges_by_slug.values())

    def get_available_attributes(self, obj):
        attributes = {}

        for variant in self._get_active_variants(obj):
            for item in variant.variant_attributes.all():
                attr_name = item.attribute.name

                if attr_name not in attributes:
                    attributes[attr_name] = {
                        "attribute_id": str(item.attribute.id),
                        "values": [],
                    }

                existing_value_ids = {
                    value_data["id"] for value_data in attributes[attr_name]["values"]
                }

                value_id = str(item.value.id)

                if value_id not in existing_value_ids:
                    attributes[attr_name]["values"].append(
                        {
                            "id": value_id,
                            "value": item.value.value,
                            "slug": item.value.slug,
                        }
                    )

        return attributes

    def get_default_variant_id(self, obj):
        default_variant = self._get_default_variant(obj)

        if not default_variant:
            return None

        return str(default_variant.id)

    def get_variants(self, obj):
        variants = self._get_active_variants(obj)
        return ProductVariantCardSerializer(variants, many=True).data


class ProductDetailSerializer(ProductCardSerializer):
    variants = serializers.SerializerMethodField()
    images = serializers.SerializerMethodField()
    reviews = serializers.SerializerMethodField()
    category = serializers.SerializerMethodField()
    content_blocks = serializers.SerializerMethodField()
    brand = BrandSerializer(read_only=True)

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
            "product_badges",
            "default_variant_badges",
            "available_attributes",
            "default_variant_id",
            "category_slug",
            "animal_type_slug",
            "description",
            "short_description",
            "category",
            "variants",
            "images",
            "reviews",
            "content_blocks",
            "meta_title",
            "meta_description",
            "created_at",
        ]

    def get_category(self, obj):
        return {
            "id": str(obj.category.id),
            "name": obj.category.name,
            "slug": obj.category.slug,
            "animal_type": {
                "name": obj.category.animal_type.name,
                "slug": obj.category.animal_type.slug,
            },
        }

    def get_images(self, obj):
        product_images = [
            image for image in obj.images.all() if image.variant_id is None
        ]
        return ProductImageSerializer(product_images, many=True).data

    def get_reviews(self, obj):
        return {
            "rating": float(obj.rating) if obj.rating is not None else 0,
            "review_count": obj.review_count or 0,
            "reviews": ProductReviewItemSerializer(obj.reviews.all(), many=True).data,
        }

    def get_variants(self, obj):
        variants = self._get_active_variants(obj)
        return ProductVariantSerializer(variants, many=True).data

    def get_content_blocks(self, obj):
        return [
            self._normalize_content_block(block)
            for block in obj.content_blocks or []
            if isinstance(block, dict)
        ]

    def _normalize_content_block(self, block):
        block_type = block.get("type")
        content = block.get("content") or {}

        normalized_block = {
            "key": block.get("key"),
            "type": block_type,
            "title": block.get("title"),
        }

        if block_type == "text":
            normalized_block["content"] = {
                "text": content.get("text", ""),
            }

        elif block_type == "key_value":
            normalized_block["content"] = {
                "items": content.get("items") or [],
            }

        elif block_type == "table":
            normalized_block["content"] = {
                "columns": content.get("columns") or [],
                "rows": content.get("rows") or [],
            }

        else:
            normalized_block["content"] = self._remove_empty_content_values(content)

        return normalized_block

    def _remove_empty_content_values(self, content):
        return {
            key: value
            for key, value in content.items()
            if value not in ("", None, [], {})
        }


class ProductFilterSerializer(serializers.Serializer):
    min_price = serializers.DecimalField(max_digits=10, decimal_places=2)
    max_price = serializers.DecimalField(max_digits=10, decimal_places=2)
    brands = BrandMinimalSerializer(many=True)
