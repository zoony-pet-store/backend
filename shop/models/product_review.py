import uuid

from django.db import models

from .customer import Customer
from .product import Product


class ReviewImageModerationStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"


class ProductReview(models.Model):
    """Product review."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    user = models.ForeignKey(
        Customer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    title = models.CharField(max_length=200)
    comment = models.TextField()

    positive_comment = models.TextField(blank=True, null=True)
    negative_comment = models.TextField(blank=True, null=True)

    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "product_reviews"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["product", "is_active"]),
            models.Index(fields=["user"]),
        ]

    def __str__(self):
        return f"Review for {self.product.name} by {self.user}"


class ProductReviewImage(models.Model):
    """Image uploaded by a user for a product review."""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    review = models.ForeignKey(
        ProductReview,
        on_delete=models.CASCADE,
        related_name="images",
    )

    cloudinary_asset_id = models.CharField(
        max_length=255,
        unique=True,
    )
    cloudinary_public_id = models.CharField(
        max_length=255,
        unique=True,
    )
    secure_url = models.URLField(max_length=1000)

    file_size_bytes = models.PositiveBigIntegerField()
    file_format = models.CharField(max_length=20)

    width_px = models.PositiveIntegerField()
    height_px = models.PositiveIntegerField()

    position = models.PositiveSmallIntegerField(default=0)

    moderation_status = models.CharField(
        max_length=10,
        choices=ReviewImageModerationStatus.choices,
        default=ReviewImageModerationStatus.PENDING,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["position", "created_at"]
        indexes = [
            models.Index(fields=["review", "position"]),
            models.Index(fields=["review", "moderation_status"]),
        ]

    def __str__(self):
        return f"Image for review {self.review_id}"
