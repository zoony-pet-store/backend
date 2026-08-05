from decimal import Decimal

from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

from ..models import ProductReview, ProductReviewImage
from ..models.product_review import ReviewImageModerationStatus


class ProductReviewItemSerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()
    image_urls = serializers.SerializerMethodField()
    rating = serializers.SerializerMethodField()

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
        reviewer_name = obj.reviewer_name.strip()

        if reviewer_name:
            return reviewer_name

        if obj.user:
            full_name = obj.user.get_full_name().strip()

            if full_name:
                return full_name

            if obj.user.username and "@" not in obj.user.username:
                return obj.user.username

        return "Anonymous"

    def get_image_urls(self, obj):
        images = getattr(obj, "approved_images", None)

        if images is None:
            images = obj.images.filter(
                moderation_status=ReviewImageModerationStatus.APPROVED,
            )

        return [image.secure_url for image in images]

    def get_rating(self, obj):
        return obj.rating_score / 2


class ProductReviewSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.get_full_name", read_only=True)
    rating = serializers.SerializerMethodField()

    class Meta:
        model = ProductReview
        fields = [
            "id",
            "user",
            "user_name",
            "reviewer_name",
            "reviewer_email",
            "rating",
            "title",
            "comment",
            "positive_comment",
            "negative_comment",
            "is_verified",
            "moderation_status",
            "rejection_reason",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["user"]

    def get_rating(self, obj):
        return obj.rating_score / 2


class ProductReviewCreateSerializer(serializers.ModelSerializer):
    rating = serializers.DecimalField(
        max_digits=2,
        decimal_places=1,
        min_value=Decimal("0.5"),
        max_value=Decimal("5.0"),
        write_only=True,
    )
    reviewer_name = serializers.CharField(
        required=True,
        allow_blank=False,
        max_length=120,
    )
    reviewer_email = serializers.EmailField(
        required=True,
        allow_blank=False,
        write_only=True,
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
            "reviewer_name",
            "reviewer_email",
            "comment",
            "positive_comment",
            "negative_comment",
        ]

    def validate_comment(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(_("Comment is required."))

        return value

    def validate_reviewer_name(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(_("Name is required."))

        return value

    def validate_reviewer_email(self, value):
        return value.strip().lower()

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

    def validate(self, attrs):
        rating = attrs.pop("rating")
        comment = attrs["comment"]

        if rating * 2 != int(rating * 2):
            raise serializers.ValidationError(
                {
                    "rating": _("Rating must use 0.5 steps."),
                }
            )

        attrs["rating_score"] = int(rating * 2)

        return attrs


class ProductReviewImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductReviewImage
        fields = [
            "id",
            "secure_url",
            "file_format",
            "width_px",
            "height_px",
            "position",
            "moderation_status",
            "created_at",
        ]
        read_only_fields = fields
