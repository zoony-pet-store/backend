from contextlib import contextmanager
from threading import local

from shop.models import ProductAttribute, ProductVariant, ProductVariantAttribute
from shop.models.product_attribute import normalize_numeric_attribute_to_base


_sync_state = local()


def is_variant_attribute_sync_disabled():
    return getattr(_sync_state, "disabled", False)


@contextmanager
def disable_variant_attribute_sync():
    previous_value = getattr(_sync_state, "disabled", False)
    _sync_state.disabled = True

    try:
        yield
    finally:
        _sync_state.disabled = previous_value


def get_normalized_numeric_values(item):
    if (
        item.attribute.type == ProductAttribute.AttributeType.NUMERIC
        and item.value_numeric is not None
        and item.unit
    ):
        return normalize_numeric_attribute_to_base(
            value=item.value_numeric,
            unit=item.unit,
        )
    return None, ""


def has_attribute_value(item):
    if not item:
        return False

    if item.attribute.type == ProductAttribute.AttributeType.SELECT:
        return bool(item.value_id)

    if item.attribute.type == ProductAttribute.AttributeType.NUMERIC:
        return item.value_numeric is not None and bool(item.unit)

    return False


def build_copied_attribute(item, variant_id):
    value_numeric_base, base_unit = get_normalized_numeric_values(item)

    return ProductVariantAttribute(
        variant_id=variant_id,
        attribute_id=item.attribute_id,
        value_id=item.value_id,
        value_numeric=item.value_numeric,
        unit=item.unit or "",
        value_numeric_base=value_numeric_base,
        base_unit=base_unit,
    )


def get_template_attribute_items_for_product(product_id, exclude_variant_id=None):
    """
    Returns one template ProductVariantAttribute per attribute key.

    Priority:
    1. default variant first
    2. non-empty value preferred over empty placeholder
    3. attribute display order
    """
    queryset = (
        ProductVariantAttribute.objects.filter(
            variant__product_id=product_id,
        )
        .select_related("attribute", "value", "variant")
        .order_by(
            "-variant__is_default",
            "variant__id",
            "attribute__display_order",
            "attribute__name",
        )
    )

    if exclude_variant_id:
        queryset = queryset.exclude(variant_id=exclude_variant_id)

    template_items_by_attribute_id = {}

    for item in queryset:
        current_item = template_items_by_attribute_id.get(item.attribute_id)

        if current_item is None:
            template_items_by_attribute_id[item.attribute_id] = item
            continue

        if not has_attribute_value(current_item) and has_attribute_value(item):
            template_items_by_attribute_id[item.attribute_id] = item

    return list(template_items_by_attribute_id.values())


def ensure_attribute_for_all_product_variants(source_item):
    """
    When one variant gets a new attribute, every other variant of the same product
    should receive the same attribute with the same value.

    Existing non-empty values are not overwritten.
    Empty placeholders are filled from source_item.
    """
    if not source_item or not source_item.variant_id or not source_item.attribute_id:
        return

    product_id = source_item.variant.product_id
    attribute_id = source_item.attribute_id

    variant_ids = list(
        ProductVariant.objects.filter(product_id=product_id).values_list(
            "id",
            flat=True,
        )
    )

    if not variant_ids:
        return

    existing_variant_ids = set(
        ProductVariantAttribute.objects.filter(
            variant_id__in=variant_ids,
            attribute_id=attribute_id,
        ).values_list("variant_id", flat=True)
    )

    missing_variant_ids = [
        variant_id
        for variant_id in variant_ids
        if variant_id not in existing_variant_ids
    ]

    with disable_variant_attribute_sync():
        if missing_variant_ids:
            ProductVariantAttribute.objects.bulk_create(
                [
                    build_copied_attribute(
                        item=source_item,
                        variant_id=variant_id,
                    )
                    for variant_id in missing_variant_ids
                ],
                ignore_conflicts=True,
            )

        if has_attribute_value(source_item):
            value_numeric_base, base_unit = get_normalized_numeric_values(source_item)

            ProductVariantAttribute.objects.filter(
                variant_id__in=variant_ids,
                attribute_id=attribute_id,
                value__isnull=True,
                value_numeric__isnull=True,
                unit="",
            ).exclude(
                pk=source_item.pk,
            ).update(
                value_id=source_item.value_id,
                value_numeric=source_item.value_numeric,
                unit=source_item.unit or "",
                value_numeric_base=value_numeric_base,
                base_unit=base_unit,
            )


def ensure_variant_has_product_structure(variant):
    """
    When a new variant is created, copy current product attribute structure
    together with template values.
    """
    if not variant or not variant.pk or not variant.product_id:
        return

    template_items = get_template_attribute_items_for_product(
        product_id=variant.product_id,
        exclude_variant_id=variant.id,
    )

    if not template_items:
        return

    existing_attribute_ids = set(
        ProductVariantAttribute.objects.filter(variant=variant).values_list(
            "attribute_id",
            flat=True,
        )
    )

    missing_template_items = [
        item
        for item in template_items
        if item.attribute_id not in existing_attribute_ids
    ]

    if not missing_template_items:
        return

    with disable_variant_attribute_sync():
        ProductVariantAttribute.objects.bulk_create(
            [
                build_copied_attribute(
                    item=item,
                    variant_id=variant.id,
                )
                for item in missing_template_items
            ],
            ignore_conflicts=True,
        )


def remove_attribute_from_all_product_variants(product_id, attribute_id):
    if not product_id or not attribute_id:
        return

    with disable_variant_attribute_sync():
        ProductVariantAttribute.objects.filter(
            variant__product_id=product_id,
            attribute_id=attribute_id,
        ).delete()


def normalize_product_variant_attribute_structure(product_id):
    """
    Manual cleanup helper.

    Ensures every variant has the same attribute keys and copies template values
    into missing/empty rows where possible.
    """
    if not product_id:
        return

    template_items = get_template_attribute_items_for_product(product_id=product_id)

    for item in template_items:
        ensure_attribute_for_all_product_variants(item)
