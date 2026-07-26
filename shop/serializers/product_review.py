from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

from ..models import ProductReview


class ProductReviewItemSerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()
    image_urls = serializers.SerializerMethodField()

    class Meta:
        model = ProductReview
        fields = [
            "id",
            "username",
            "created_at",
            "rating",
            "image_urls",
            "updated_at",
            "title",
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
            "positive_comment",
            "negative_comment",
            "is_verified",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["user"]


class ProductReviewCreateSerializer(serializers.ModelSerializer):
    rating = serializers.IntegerField(
        min_value=1,
        max_value=5,
    )
    title = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=200,
    )
    comment = serializers.CharField(
        required=True,
        allow_blank=False,
        min_length=1,
    )
    positive_comment = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
    )
    negative_comment = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
    )

    class Meta:
        model = ProductReview
        fields = [
            "rating",
            "title",
            "comment",
            "positive_comment",
            "negative_comment",
        ]

    def validate_comment(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                {"comment": _("Comment is required.")}
            )

        return value

    def validate_positive_comment(self, value):
        if value is None:
            return None

        value = value.strip()
        return value or None

    def validate_negative_comment(self, value):
        if value is None:
            return None

        value = value.strip()
        return value or None

    def create(self, validated_data):
        comment = validated_data.get("comment", "")
        title = validated_data.get("title", "").strip()

        if not title:
            title = comment[:80] or "Product review"

        validated_data["title"] = title

        return super().create(validated_data)
