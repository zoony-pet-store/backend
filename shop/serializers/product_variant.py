from rest_framework import serializers

from ..models import ProductAttribute, ProductVariant, translated_field
from .badge import BadgeSerializer
from .product_attribute import serialize_variant_attribute_raw
from .product_image import ProductImageSerializer


class ProductVariantSerializer(serializers.ModelSerializer):
    description = serializers.SerializerMethodField()
    short_description = serializers.SerializerMethodField()
    attributes = serializers.SerializerMethodField()
    attributes_raw = serializers.SerializerMethodField()
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
            "attributes_raw",
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
            translated_field(item.attribute, "name"): self._get_attribute_display_value(
                item
            )
            for item in obj.variant_attributes.all()
        }

    def get_attributes_raw(self, obj):
        return {
            translated_field(item.attribute, "name"): serialize_variant_attribute_raw(
                item
            )
            for item in obj.variant_attributes.all()
        }

    def get_description(self, obj):
        return translated_field(obj, "description")

    def get_short_description(self, obj):
        return translated_field(obj, "short_description")

    def _get_attribute_display_value(self, item):
        if item.attribute.type == ProductAttribute.AttributeType.NUMERIC:
            return item.display_value

        if item.value_id:
            return translated_field(item.value, "value")

        return ""

    def get_images(self, obj):
        images = list(obj.images.all())
        return ProductImageSerializer(images, many=True).data


class ProductVariantCardSerializer(serializers.ModelSerializer):
    attributes = serializers.SerializerMethodField()
    attributes_raw = serializers.SerializerMethodField()
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
            "attributes_raw",
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
            translated_field(item.attribute, "name"): self._get_attribute_display_value(
                item
            )
            for item in obj.variant_attributes.all()
        }

    def get_attributes_raw(self, obj):
        return {
            translated_field(item.attribute, "name"): serialize_variant_attribute_raw(
                item
            )
            for item in obj.variant_attributes.all()
        }

    def _get_attribute_display_value(self, item):
        if item.attribute.type == ProductAttribute.AttributeType.NUMERIC:
            return item.display_value

        if item.value_id:
            return translated_field(item.value, "value")

        return ""

    def get_image_url(self, obj):
        images = list(obj.images.all())

        main_image = next((image for image in images if image.is_main), None)
        if main_image:
            return main_image.image_url

        first_image = images[0] if images else None
        if first_image:
            return first_image.image_url

        return None


class CatalogVariantCardSerializer(ProductVariantCardSerializer):
    variant_id = serializers.UUIDField(source="id", read_only=True)
    product_id = serializers.UUIDField(read_only=True)

    name = serializers.SerializerMethodField()
    slug = serializers.CharField(
        source="product.slug",
        read_only=True,
    )
    brand = serializers.SerializerMethodField()
    rating = serializers.SerializerMethodField()
    badges = serializers.SerializerMethodField()

    review_count = serializers.IntegerField(
        source="product.review_count",
        read_only=True,
    )

    category_slug = serializers.CharField(
        source="product.category.slug",
        read_only=True,
    )

    animal_type_slug = serializers.CharField(
        source="product.category.animal_type.slug",
        read_only=True,
    )

    class Meta(ProductVariantCardSerializer.Meta):
        model = ProductVariant
        fields = [
            *ProductVariantCardSerializer.Meta.fields,
            "variant_id",
            "product_id",
            "name",
            "slug",
            "brand",
            "rating",
            "review_count",
            "category_slug",
            "animal_type_slug",
        ]

    def get_name(self, obj):
        return translated_field(obj.product, "name")

    def get_brand(self, obj):
        brand = obj.product.brand

        if brand is None:
            return None

        return {
            "id": str(brand.id),
            "name": brand.name,
            "slug": brand.slug,
            "logo_url": brand.logo_url,
        }

    def get_rating(self, obj):
        return float(obj.product.rating or 0)

    def get_image_url(self, obj):
        variant_image_url = super().get_image_url(obj)

        if variant_image_url:
            return variant_image_url

        product = obj.product

        product_images = getattr(
            product,
            "catalog_product_images",
            None,
        )

        if product_images is None:
            product_images = list(
                product.images.filter(
                    variant__isnull=True,
                ).order_by("display_order", "id")
            )

        main_image = next(
            (image for image in product_images if image.is_main),
            None,
        )

        if main_image is not None:
            return main_image.image_url

        if product_images:
            return product_images[0].image_url

        return product.main_image or None

    def get_badges(self, obj):
        badges_by_slug = {}

        badge_sources = (
            obj.product.badges.all(),
            obj.badges.all(),
        )

        for badges in badge_sources:
            for badge in badges:
                if not badge.is_active:
                    continue

                badges_by_slug[badge.slug] = badge

        return BadgeSerializer(
            list(badges_by_slug.values()),
            many=True,
            context=self.context,
        ).data
