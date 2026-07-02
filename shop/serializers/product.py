from rest_framework import serializers

from ..models import Product, ProductAttribute
from .catalog import BrandMinimalSerializer, BrandSerializer
from .product_attribute import serialize_numeric_attribute_value
from .product_image import ProductImageSerializer
from .product_review import ProductReviewItemSerializer
from .product_variant import ProductVariantCardSerializer, ProductVariantSerializer


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
                attribute = item.attribute
                attr_name = attribute.name

                if attr_name not in attributes:
                    attributes[attr_name] = {
                        "attribute_id": str(attribute.id),
                        "type": attribute.type,
                        "values": [],
                    }

                if attribute.type == ProductAttribute.AttributeType.NUMERIC:
                    if item.value_numeric is None:
                        continue

                    value_data = serialize_numeric_attribute_value(item)
                    value_key = (
                        value_data["value_decimal"],
                        value_data["unit"],
                    )

                    existing_value_keys = {
                        (
                            existing_value.get("value_decimal"),
                            existing_value.get("unit"),
                        )
                        for existing_value in attributes[attr_name]["values"]
                    }

                    if value_key not in existing_value_keys:
                        attributes[attr_name]["values"].append(value_data)

                    continue

                if not item.value_id:
                    continue

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
