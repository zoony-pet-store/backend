import uuid
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import slugify

from .category import Category


class ProductAttribute(models.Model):
    """
    Attribute type, e.g. Size, Color, Weight, Flavor.

    type:
    - SELECT: value is selected from ProductAttributeValue
    - NUMERIC: value is entered as number + unit on ProductVariantAttribute

    categories is optional:
    - empty means global attribute
    - filled means this attribute is relevant only for selected categories
    """

    class AttributeType(models.TextChoices):
        SELECT = "select", "Select"
        NUMERIC = "numeric", "Numeric"

    UNIT_CHOICES = [
        ("g", "g"),
        ("kg", "kg"),
        ("ml", "ml"),
        ("l", "l"),
        ("mm", "mm"),
        ("cm", "cm"),
        ("m", "m"),
        ("pcs", "pcs"),
        ("pack", "pack"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True)

    type = models.CharField(
        max_length=20,
        choices=AttributeType.choices,
        default=AttributeType.SELECT,
        db_index=True,
        help_text=(
            "Select = predefined text values. " "Numeric = number + unit, e.g. 10 kg."
        ),
    )

    available_units = models.JSONField(
        default=list,
        blank=True,
        help_text=(
            "Only for numeric attributes. Example: ['kg', 'g']. "
            "Leave empty to allow all supported units."
        ),
    )

    filterable = models.BooleanField(default=True)
    display_order = models.IntegerField(default=0)

    categories = models.ManyToManyField(
        Category,
        blank=True,
        db_table="product_attribute_categories",
        related_name="attributes",
    )

    class Meta:
        db_table = "product_attributes"
        ordering = ["display_order", "name"]

    @property
    def is_select(self):
        return self.type == self.AttributeType.SELECT

    @property
    def is_numeric(self):
        return self.type == self.AttributeType.NUMERIC

    @property
    def allowed_units(self):
        if self.available_units:
            return self.available_units

        return [unit for unit, _label in self.UNIT_CHOICES]

    def clean(self):
        errors = {}

        supported_units = {unit for unit, _label in self.UNIT_CHOICES}
        invalid_units = [
            unit for unit in self.available_units if unit not in supported_units
        ]

        if invalid_units:
            errors["available_units"] = "Unsupported units: " + ", ".join(
                sorted(invalid_units)
            )

        if self.type == self.AttributeType.SELECT and self.available_units:
            errors["available_units"] = (
                "Available units should be empty for select attributes."
            )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)

        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


def format_numeric_attribute_value(value):
    if value is None:
        return ""

    normalized_value = value.normalize()
    display_value = format(normalized_value, "f")

    if "." in display_value:
        display_value = display_value.rstrip("0").rstrip(".")

    return display_value


UNIT_BASE_CONVERSIONS = {
    "g": ("g", Decimal("1")),
    "kg": ("g", Decimal("1000")),
    "ml": ("ml", Decimal("1")),
    "l": ("ml", Decimal("1000")),
    "mm": ("mm", Decimal("1")),
    "cm": ("mm", Decimal("10")),
    "m": ("mm", Decimal("1000")),
    # Do not convert pack to pcs automatically.
    # 1 pack can contain different number of items.
    "pcs": ("pcs", Decimal("1")),
    "pack": ("pack", Decimal("1")),
}


def normalize_numeric_attribute_to_base(value, unit):
    if value is None or not unit:
        return None, ""

    conversion = UNIT_BASE_CONVERSIONS.get(unit)

    if not conversion:
        return None, ""

    base_unit, multiplier = conversion
    base_value = Decimal(str(value)) * multiplier

    return base_value.quantize(Decimal("0.001")), base_unit
