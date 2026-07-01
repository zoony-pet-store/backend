import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import slugify

from .product_attribute import ProductAttribute
class ProductAttributeValue(models.Model):
    """
    Possible predefined value for SELECT attributes, e.g. Size: S, Color: Pink.

    Numeric attributes should not use this model. Their values are stored in
    ProductVariantAttribute.value_numeric + ProductVariantAttribute.unit.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    attribute = models.ForeignKey(
        ProductAttribute,
        on_delete=models.CASCADE,
        related_name="values",
    )
    value = models.CharField(max_length=255)
    slug = models.SlugField(blank=True)
    display_order = models.IntegerField(default=0)

    class Meta:
        ordering = ["attribute__display_order", "display_order", "value"]
        constraints = [
            models.UniqueConstraint(
                fields=["attribute", "slug"],
                name="unique_attribute_value_slug_per_attribute",
            )
        ]

    def clean(self):
        if (
            self.attribute_id
            and self.attribute.type == ProductAttribute.AttributeType.NUMERIC
        ):
            raise ValidationError(
                {
                    "attribute": (
                        "ProductAttributeValue can be used only for select "
                        "attributes. Numeric attributes store values directly "
                        "on ProductVariantAttribute."
                    )
                }
            )

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.generate_slug()

        self.full_clean()
        super().save(*args, **kwargs)

    def generate_slug(self):
        base_slug = slugify(self.value)
        slug = base_slug
        counter = 1

        queryset = ProductAttributeValue.objects.filter(
            attribute=self.attribute,
            slug=slug,
        )

        if self.pk:
            queryset = queryset.exclude(pk=self.pk)

        while queryset.exists():
            slug = f"{base_slug}-{counter}"
            counter += 1

            queryset = ProductAttributeValue.objects.filter(
                attribute=self.attribute,
                slug=slug,
            )

            if self.pk:
                queryset = queryset.exclude(pk=self.pk)

        return slug

    def __str__(self):
        return f"{self.attribute.name}: {self.value}"
