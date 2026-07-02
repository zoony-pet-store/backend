from rest_framework import serializers

from ..models import ProductVariant
from .badge import BadgeSerializer
from .product_attribute import serialize_variant_attribute_raw
from .product_image import ProductImageSerializer


class ProductVariantSerializer(serializers.ModelSerializer):
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
            item.attribute.name: item.display_value
            for item in obj.variant_attributes.all()
        }

    def get_attributes_raw(self, obj):
        return {
            item.attribute.name: serialize_variant_attribute_raw(item)
            for item in obj.variant_attributes.all()
        }

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
            item.attribute.name: item.display_value
            for item in obj.variant_attributes.all()
        }

    def get_attributes_raw(self, obj):
        return {
            item.attribute.name: serialize_variant_attribute_raw(item)
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
