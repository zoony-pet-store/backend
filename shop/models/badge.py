from django.db import models
from django.utils.text import slugify


class Badge(models.Model):
    """Product or variant badge, e.g. New, Sale, Bestseller."""

    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True, blank=True)
    label = models.CharField(max_length=50)
    color = models.CharField(max_length=7, default="#000000")
    background_color = models.CharField(max_length=7, default="#FFFFFF")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "badges"
        ordering = ["label"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)

        super().save(*args, **kwargs)

    def __str__(self):
        return self.label


AUTO_DISCOUNT_BADGE_SLUG = "discount"
AUTO_SALE_BADGE_SLUG = "sale"
AUTO_SALE_MIN_PERCENTAGE = 20


AUTO_PRICE_BADGE_DEFINITIONS = {
    AUTO_DISCOUNT_BADGE_SLUG: {
        "name": "discount",
        "slug": "discount",
        "label": "Discount",
        "color": "#FFFFFF",
        "background_color": "#DC3545",
    },
    AUTO_SALE_BADGE_SLUG: {
        "name": "sale",
        "slug": "sale",
        "label": "Sale",
        "color": "#FFFFFF",
        "background_color": "#FF6B6B",
    },
}


def get_or_create_auto_price_badge(slug):
    badge_data = AUTO_PRICE_BADGE_DEFINITIONS[slug]

    badge, _ = Badge.objects.get_or_create(
        slug=badge_data["slug"],
        defaults={
            "name": badge_data["name"],
            "label": badge_data["label"],
            "color": badge_data["color"],
            "background_color": badge_data["background_color"],
            "is_active": True,
        },
    )

    updated_fields = []

    if badge.name != badge_data["name"]:
        badge.name = badge_data["name"]
        updated_fields.append("name")

    if badge.label != badge_data["label"]:
        badge.label = badge_data["label"]
        updated_fields.append("label")

    if badge.color != badge_data["color"]:
        badge.color = badge_data["color"]
        updated_fields.append("color")

    if badge.background_color != badge_data["background_color"]:
        badge.background_color = badge_data["background_color"]
        updated_fields.append("background_color")

    if not badge.is_active:
        badge.is_active = True
        updated_fields.append("is_active")

    if updated_fields:
        badge.save(update_fields=updated_fields)

    return badge
