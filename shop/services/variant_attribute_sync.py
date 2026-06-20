from contextlib import contextmanager
from threading import local

from shop.models import ProductAttribute, ProductVariant, ProductVariantAttribute


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


def get_product_structure_attribute_ids(product_id):
    return list(
        ProductAttribute.objects.filter(
            variant_attributes__variant__product_id=product_id,
        )
        .distinct()
        .order_by("display_order", "name")
        .values_list("id", flat=True)
    )


def ensure_attribute_for_all_product_variants(product_id, attribute_id):
    if not product_id or not attribute_id:
        return

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

    if not missing_variant_ids:
        return

    with disable_variant_attribute_sync():
        ProductVariantAttribute.objects.bulk_create(
            [
                ProductVariantAttribute(
                    variant_id=variant_id,
                    attribute_id=attribute_id,
                )
                for variant_id in missing_variant_ids
            ],
            ignore_conflicts=True,
        )


def ensure_variant_has_product_structure(variant):
    if not variant or not variant.pk or not variant.product_id:
        return

    attribute_ids = get_product_structure_attribute_ids(variant.product_id)

    if not attribute_ids:
        return

    existing_attribute_ids = set(
        ProductVariantAttribute.objects.filter(variant=variant).values_list(
            "attribute_id",
            flat=True,
        )
    )

    missing_attribute_ids = [
        attribute_id
        for attribute_id in attribute_ids
        if attribute_id not in existing_attribute_ids
    ]

    if not missing_attribute_ids:
        return

    with disable_variant_attribute_sync():
        ProductVariantAttribute.objects.bulk_create(
            [
                ProductVariantAttribute(
                    variant=variant,
                    attribute_id=attribute_id,
                )
                for attribute_id in missing_attribute_ids
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
    Ensures all variants of one product have identical attribute keys.
    Useful for manual cleanup or future management command.
    """
    if not product_id:
        return

    attribute_ids = get_product_structure_attribute_ids(product_id)

    for attribute_id in attribute_ids:
        ensure_attribute_for_all_product_variants(
            product_id=product_id,
            attribute_id=attribute_id,
        )
