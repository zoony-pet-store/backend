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


def build_saved_variant_signature_map(variant):
    """
    Return a mapping:

        attribute_id -> normalized signature item or None

    None means that the variant has an empty placeholder for this attribute.
    """
    signature_items_by_attribute_id = {}

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
                signature_item = build_variant_attribute_signature_item(
                    attribute=attribute,
                    value_numeric=variant_attribute.value_numeric,
                    unit=variant_attribute.unit,
                )

        else:
            signature_item = None

        signature_items_by_attribute_id[variant_attribute.attribute_id] = signature_item

    return signature_items_by_attribute_id


def validate_unique_variant_combinations_after_sync(
    *,
    variant,
    current_signature,
    propagated_signature_items_by_attribute_id,
    removed_attribute_ids=None,
):
    """
    Validate projected variant signatures after attribute synchronization.

    Attribute synchronization can:

    - add a missing attribute and its value to sibling variants;
    - fill empty placeholders in sibling variants;
    - remove an attribute from every variant.

    Validation must account for those changes before the database is updated.
    """
    if not variant or not variant.product_id:
        return

    removed_attribute_ids = set(removed_attribute_ids or ())

    other_variants = ProductVariant.objects.filter(
        product_id=variant.product_id,
    )

    if variant.pk:
        other_variants = other_variants.exclude(pk=variant.pk)

    other_variants = other_variants.prefetch_related(
        "variant_attributes__attribute",
    )

    projected_variants = [
        {
            "identifier": get_variant_identifier(variant),
            "signature": current_signature,
            "changed": True,
        }
    ]

    for other_variant in other_variants:
        signature_map = build_saved_variant_signature_map(other_variant)
        signature_changed = False

        # Deleting an attribute from one variant removes it
        # from every variant of the product.
        for attribute_id in removed_attribute_ids:
            if attribute_id in signature_map:
                signature_map.pop(attribute_id)
                signature_changed = True

        # Synchronization copies the value only into missing
        # or completely empty sibling rows.
        for (
            attribute_id,
            source_signature_item,
        ) in propagated_signature_items_by_attribute_id.items():
            existing_signature_item = signature_map.get(attribute_id)

            if existing_signature_item is not None:
                continue

            signature_map[attribute_id] = source_signature_item
            signature_changed = True

        projected_signature = frozenset(
            signature_item
            for signature_item in signature_map.values()
            if signature_item is not None
        )

        projected_variants.append(
            {
                "identifier": get_variant_identifier(other_variant),
                "signature": projected_signature,
                "changed": signature_changed,
            }
        )

    variants_by_signature = {}

    for projected_variant in projected_variants:
        signature = projected_variant["signature"]
        existing_variant = variants_by_signature.get(signature)

        if existing_variant is None:
            variants_by_signature[signature] = projected_variant
            continue

        # Do not block the operation because of an unrelated legacy
        # duplicate that already existed before this request.
        if not (existing_variant["changed"] or projected_variant["changed"]):
            continue

        raise ValidationError(
            _(
                "Saving these attribute changes would create duplicate "
                'variant combinations: "%(first_variant)s" and '
                '"%(second_variant)s". At least one attribute value '
                "must be different."
            )
            % {
                "first_variant": existing_variant["identifier"],
                "second_variant": projected_variant["identifier"],
            }
        )


def get_variant_identifier(variant):
    if variant.sku:
        return variant.sku

    if variant.pk:
        return str(variant.pk)

    return _("new variant")
