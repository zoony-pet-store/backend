import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils.text import slugify

from .badge import (
    AUTO_DISCOUNT_BADGE_SLUG,
    AUTO_SALE_BADGE_SLUG,
    AUTO_SALE_MIN_PERCENTAGE,
    Badge,
    get_or_create_auto_price_badge,
)
from .product import Product


class ProductVariant(models.Model):
    """
    Concrete SKU / physical item.

    This is what user adds to cart.
    Price, old_price and stock belong here, not on Product.

    Variant options such as weight, size, color or package size
    should be stored through ProductVariantAttribute, not hardcoded fields.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="variants",
    )

    sku = models.CharField(max_length=100, unique=True, blank=True)

    price = models.DecimalField(max_digits=10, decimal_places=2)
    old_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    cost_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )

    stock = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    # Optional overrides for selected variant.
    description = models.TextField(blank=True)
    short_description = models.TextField(blank=True)
    badges = models.ManyToManyField(Badge, blank=True, related_name="variants")

    auto_badges_enabled = models.BooleanField(
        default=True,
        help_text=(
            "If enabled, Discount and Sale badges are managed automatically "
            "based on old_price and price."
        ),
    )

    is_default = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_default", "price", "id"]
        indexes = [
            models.Index(fields=["product", "is_active"]),
            models.Index(fields=["product", "is_default"]),
            models.Index(fields=["sku"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["product"],
                condition=Q(is_default=True),
                name="unique_default_variant_per_product",
            )
        ]

    def clean(self):
        if self.old_price is not None and self.price is not None:
            if self.old_price <= self.price:
                raise ValidationError(
                    {"old_price": "Old price must be greater than current price."}
                )

    def save(self, *args, **kwargs):
        if not self.sku:
            self.sku = self.generate_sku()
        else:
            self.sku = self.sku.strip().upper()

        if self.product_id and not self.is_default:
            has_default_variant = (
                ProductVariant.objects.filter(
                    product_id=self.product_id,
                    is_default=True,
                )
                .exclude(pk=self.pk)
                .exists()
            )

            if not has_default_variant:
                self.is_default = True

        if self.product_id and self.is_default:
            ProductVariant.objects.filter(
                product_id=self.product_id,
                is_default=True,
            ).exclude(pk=self.pk).update(is_default=False)

        self.full_clean()
        super().save(*args, **kwargs)

        self.sync_auto_price_badges()

    def generate_sku(self):
        """
        Hybrid SKU approach:
        - if admin provides SKU manually, we keep it;
        - if SKU is empty, backend generates stable SKU.
        """
        if not self.id:
            self.id = uuid.uuid4()

        product_part = slugify(self.product.slug or self.product.name or "product")
        product_part = product_part.replace("-", "").upper()[:24]

        return f"{product_part}-{self.id.hex[:8].upper()}"

    def sync_auto_price_badges(self):
        """
        Synchronize DB-backed automatic price badges.

        Only Discount and Sale are managed automatically.
        New, Bestseller and Trending should be managed manually in admin.
        """
        if not self.auto_badges_enabled:
            return

        discount_badge = get_or_create_auto_price_badge(AUTO_DISCOUNT_BADGE_SLUG)
        sale_badge = get_or_create_auto_price_badge(AUTO_SALE_BADGE_SLUG)

        if self.has_discount:
            self.badges.add(discount_badge)
        else:
            self.badges.remove(discount_badge)

        if self.has_discount and self.discount_percentage >= AUTO_SALE_MIN_PERCENTAGE:
            self.badges.add(sale_badge)
        else:
            self.badges.remove(sale_badge)

    @property
    def has_discount(self):
        return bool(self.old_price and self.old_price > self.price)

    @property
    def discount_percentage(self):
        if self.has_discount:
            return round((self.old_price - self.price) / self.old_price * 100)

        return 0

    @property
    def in_stock(self):
        return self.is_active and self.stock > 0

    def __str__(self):
        return f"{self.product.name} - {self.sku}"
