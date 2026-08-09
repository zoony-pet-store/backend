from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

from ..models import ProductAttribute, ProductVariant
from ..models.product_attribute import normalize_numeric_attribute_to_base


def build_variant_attribute_signature_item(
    *,
    attribute,
    value_id=None,
    value_numeric=None,
    unit="",
):
    """
    Build a normalized signature item for one variant attribute.

    SELECT:
        ("select", attribute_id, value_id)

    NUMERIC:
        ("numeric", attribute_id, normalized_value, base_unit)
    """
    if attribute.type == ProductAttribute.AttributeType.SELECT:
        if value_id is None:
            return None

        return (
            "select",
            attribute.pk,
            value_id,
        )

    if attribute.type == ProductAttribute.AttributeType.NUMERIC:
        if value_numeric is None or not unit:
            return None

        normalized_value, base_unit = normalize_numeric_attribute_to_base(
            value=value_numeric,
            unit=unit,
        )

        return (
            "numeric",
            attribute.pk,
            normalized_value,
            base_unit,
        )

    return None


def build_saved_variant_signature(variant):
    """
    Build the complete normalized signature of a variant stored in DB.
    """
    signature_items = []

    for variant_attribute in variant.variant_attributes.all():
        attribute = variant_attribute.attribute

        if attribute.type == ProductAttribute.AttributeType.SELECT:
            signature_item = build_variant_attribute_signature_item(
                attribute=attribute,
                value_id=variant_attribute.value_id,
            )

        elif attribute.type == ProductAttribute.AttributeType.NUMERIC:
            normalized_value = variant_attribute.value_numeric_base
            base_unit = variant_attribute.base_unit

            if normalized_value is not None and base_unit:
                signature_item = (
                    "numeric",
                    variant_attribute.attribute_id,
                    normalized_value,
                    base_unit,
                )
            else:
                # Fallback for old rows without populated normalized fields.
                signature_item = build_variant_attribute_signature_item(
                    attribute=attribute,
                    value_numeric=variant_attribute.value_numeric,
                    unit=variant_attribute.unit,
                )

        else:
            signature_item = None

        if signature_item is not None:
            signature_items.append(signature_item)

    return frozenset(signature_items)


def validate_unique_variant_attribute_combination(
    *,
    variant,
    current_signature,
):
    """
    Ensure no other variant of the same product has this exact signature.
    """
    if not variant or not variant.product_id:
        return

    other_variants = ProductVariant.objects.filter(product_id=variant.product_id)

    if variant.pk:
        other_variants = other_variants.exclude(pk=variant.pk)

    other_variants = other_variants.prefetch_related("variant_attributes__attribute")

    for other_variant in other_variants:
        other_signature = build_saved_variant_signature(other_variant)

        if other_signature != current_signature:
            continue

        variant_identifier = other_variant.sku or str(other_variant.pk)

        raise ValidationError(
            _(
                "A variant with the same attribute combination already exists: "
                '"%(variant_identifier)s". '
                "At least one attribute value must be different."
            )
            % {"variant_identifier": variant_identifier}
        )
