import uuid

from django.core.exceptions import ValidationError
from django.db import models

from .product_attribute import (
    ProductAttribute,
    format_numeric_attribute_value,
    normalize_numeric_attribute_to_base,
)
from .product_attribute_value import ProductAttributeValue
from .product_variant import ProductVariant


class ProductVariantAttribute(models.Model):
    """
    Attribute selected for concrete variant.

    SELECT attribute example:
    Variant: BED-S-PINK
    Attribute: Color
    Value: Pink

    NUMERIC attribute example:
    Variant: FOOD-10KG
    Attribute: Weight
    value_numeric: 10
    unit: kg

    Constraint:
    One variant can have only one value for the same attribute.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.CASCADE,
        related_name="variant_attributes",
    )
    attribute = models.ForeignKey(
        ProductAttribute,
        on_delete=models.CASCADE,
        related_name="variant_attributes",
    )

    # Used only when attribute.type == SELECT.
    value = models.ForeignKey(
        ProductAttributeValue,
        on_delete=models.CASCADE,
        related_name="variant_attributes",
        null=True,
        blank=True,
    )

    # Used only when attribute.type == NUMERIC.
    value_numeric = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        null=True,
        blank=True,
        help_text="Numeric value for numeric attributes, e.g. 10.",
    )
    unit = models.CharField(
        max_length=20,
        blank=True,
        default="",
        help_text="Unit for numeric attributes, e.g. kg, g, ml, l.",
    )

    value_numeric_base = models.DecimalField(
        max_digits=18,
        decimal_places=3,
        null=True,
        blank=True,
        db_index=True,
        editable=False,
        help_text=(
            "Normalized numeric value in base unit for filtering/sorting. "
            "Example: 7 kg -> 7000 g."
        ),
    )

    base_unit = models.CharField(
        max_length=20,
        blank=True,
        default="",
        editable=False,
        help_text="Base unit for normalized numeric value, e.g. g, ml, mm.",
    )

    class Meta:
        db_table = "product_variant_attributes"
        ordering = [
            "attribute__display_order",
            "value__display_order",
            "value_numeric",
            "unit",
        ]
        indexes = [
            models.Index(fields=["attribute", "value"]),
            models.Index(fields=["attribute", "value_numeric", "unit"]),
            models.Index(fields=["attribute", "value_numeric_base", "base_unit"]),
            models.Index(fields=["variant", "attribute"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["variant", "attribute"],
                name="unique_attribute_per_variant",
            )
        ]

    @property
    def display_value(self):
        if self.attribute.type == ProductAttribute.AttributeType.NUMERIC:
            if self.value_numeric is None:
                return ""

            return (
                f"{format_numeric_attribute_value(self.value_numeric)} {self.unit}"
            ).strip()

        if self.value_id:
            return self.value.value

        return ""

    @property
    def raw_value(self):
        if self.attribute.type == ProductAttribute.AttributeType.NUMERIC:
            return {
                "type": ProductAttribute.AttributeType.NUMERIC,
                "display_value": self.display_value,
                "value": (
                    float(self.value_numeric)
                    if self.value_numeric is not None
                    else None
                ),
                "value_decimal": (
                    str(self.value_numeric) if self.value_numeric is not None else None
                ),
                "unit": self.unit or None,
            }

        return {
            "type": ProductAttribute.AttributeType.SELECT,
            "display_value": self.display_value,
            "value_id": str(self.value_id) if self.value_id else None,
            "value": self.value.value if self.value_id else None,
            "slug": self.value.slug if self.value_id else None,
        }

    def clean(self):
        errors = {}

        if self.variant_id and self.attribute_id:
            allowed_categories = self.attribute.categories.all()

            if allowed_categories.exists():
                is_allowed_for_category = allowed_categories.filter(
                    id=self.variant.product.category_id
                ).exists()

                if not is_allowed_for_category:
                    errors["attribute"] = (
                        "This attribute is not allowed for product category."
                    )

        if self.attribute_id:
            if self.attribute.type == ProductAttribute.AttributeType.SELECT:
                if self.value_numeric is not None:
                    errors["value_numeric"] = (
                        "Numeric value must be empty for select attribute."
                    )

                if self.unit:
                    errors["unit"] = "Unit must be empty for select attribute."

            elif self.attribute.type == ProductAttribute.AttributeType.NUMERIC:
                if self.value_id:
                    errors["value"] = "Text value must be empty for numeric attribute."

                has_numeric_value = self.value_numeric is not None
                has_unit = bool(self.unit)

                if has_numeric_value and not has_unit:
                    errors["unit"] = "Unit is required when numeric value is filled."

                if has_unit and not has_numeric_value:
                    errors["value_numeric"] = (
                        "Numeric value is required when unit is filled."
                    )

                if self.unit:
                    supported_units = {
                        unit for unit, _label in ProductAttribute.UNIT_CHOICES
                    }

                    if self.unit not in supported_units:
                        errors["unit"] = f'Unsupported unit "{self.unit}".'

                    available_units = self.attribute.available_units or []

                    if available_units and self.unit not in available_units:
                        errors["unit"] = (
                            f'Unit "{self.unit}" is not allowed for this attribute.'
                        )

        if self.value_id and self.attribute_id:
            if self.value.attribute_id != self.attribute_id:
                errors["value"] = (
                    "Selected value does not belong to selected attribute."
                )

        if errors:
            raise ValidationError(errors)

    def sync_normalized_numeric_value(self):
        if (
            self.attribute_id
            and self.attribute.type == ProductAttribute.AttributeType.NUMERIC
            and self.value_numeric is not None
            and self.unit
        ):
            self.value_numeric_base, self.base_unit = (
                normalize_numeric_attribute_to_base(
                    value=self.value_numeric,
                    unit=self.unit,
                )
            )
            return

        self.value_numeric_base = None
        self.base_unit = ""

    def save(self, *args, **kwargs):
        self.sync_normalized_numeric_value()
        self.full_clean()

        update_fields = kwargs.get("update_fields")

        if update_fields is not None:
            update_fields = set(update_fields)

            normalization_source_fields = {
                "attribute",
                "attribute_id",
                "value_numeric",
                "unit",
            }
            if update_fields & normalization_source_fields:
                update_fields.update(
                    {
                        "value_numeric_base",
                        "base_unit",
                    }
                )
                kwargs["update_fields"] = update_fields

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.variant} | {self.attribute.name}: {self.display_value}"
