import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from .product import Product
from .product_variant import ProductVariant


class MediaAsset(models.Model):
    """
    Reusable image from media library.

    Admin can upload/select image once and reuse it for:
    - base product images;
    - variant images;
    - future brand/category images if needed.
    """

    SOURCE_MANUAL = "manual"
    SOURCE_CLOUDINARY = "cloudinary"
    SOURCE_EXTERNAL = "external"

    SOURCE_CHOICES = [
        (SOURCE_MANUAL, "Manual"),
        (SOURCE_CLOUDINARY, "Cloudinary"),
        (SOURCE_EXTERNAL, "External URL"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    title = models.CharField(
        max_length=255,
        blank=True,
        help_text="Human-readable name for admin media library.",
    )
    image_url = models.URLField(max_length=1000)
    alt_text = models.CharField(max_length=255, blank=True)

    cloudinary_public_id = models.CharField(
        max_length=255,
        blank=True,
        default="",
        db_index=True,
    )

    source = models.CharField(
        max_length=20,
        choices=SOURCE_CHOICES,
        default=SOURCE_MANUAL,
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "title"]
        indexes = [
            models.Index(fields=["source"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["cloudinary_public_id"]),
        ]
        verbose_name = "Media asset"
        verbose_name_plural = "Media assets"

    def clean(self):
        if not self.image_url:
            raise ValidationError({"image_url": "Image URL is required."})

    def save(self, *args, **kwargs):
        if not self.title:
            self.title = self.generate_title()

        self.full_clean()
        super().save(*args, **kwargs)

    def generate_title(self):
        if self.cloudinary_public_id:
            return self.cloudinary_public_id.split("/")[-1]

        if self.image_url:
            return self.image_url.rstrip("/").split("/")[-1][:255]

        return "Untitled image"

    def __str__(self):
        return self.title or self.image_url


class ProductImage(models.Model):
    """
    Product image.

    If variant is empty: common product image.
    If variant is filled: image belongs to specific variant.

    Image can be selected from MediaAsset library or provided as direct URL.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="images",
    )
    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.CASCADE,
        related_name="images",
        null=True,
        blank=True,
    )

    asset = models.ForeignKey(
        MediaAsset,
        on_delete=models.SET_NULL,
        related_name="product_images",
        null=True,
        blank=True,
        help_text=(
            "Select an existing image from media library. "
            "If selected, image_url and cloudinary_public_id can be filled automatically."
        ),
    )

    image_url = models.URLField(
        max_length=1000,
        blank=True,
        help_text=(
            "Direct image URL fallback. "
            "Can be auto-filled from selected media asset."
        ),
    )
    alt_text = models.CharField(max_length=255, blank=True)
    is_main = models.BooleanField(default=False)
    display_order = models.IntegerField(default=0)
    cloudinary_public_id = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        ordering = ["display_order", "id"]
        indexes = [
            models.Index(fields=["product", "variant"]),
            models.Index(fields=["product", "is_main"]),
            models.Index(fields=["variant", "is_main"]),
            models.Index(fields=["asset"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["product"],
                condition=Q(is_main=True, variant__isnull=True),
                name="unique_main_product_image",
            ),
            models.UniqueConstraint(
                fields=["variant"],
                condition=Q(is_main=True, variant__isnull=False),
                name="unique_main_variant_image",
            ),
        ]

    def clean(self):
        errors = {}

        if self.variant_id and self.product_id:
            if self.variant.product_id != self.product_id:
                errors["variant"] = "Variant must belong to the selected product."

        if not self.asset_id and not self.image_url:
            errors["image_url"] = (
                "Select image from media library or provide direct image URL."
            )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self.asset_id:
            if not self.image_url:
                self.image_url = self.asset.image_url

            if not self.cloudinary_public_id:
                self.cloudinary_public_id = self.asset.cloudinary_public_id

            if not self.alt_text:
                self.alt_text = self.asset.alt_text

        if not self.alt_text and self.product_id:
            self.alt_text = self.product.name

        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        if self.variant_id:
            return f"Image for {self.variant}"

        return f"Image for {self.product.name}"
