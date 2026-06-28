from django.db import transaction
from django.db.models import QuerySet
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from shop.models import Product, ProductVariant, ProductVariantAttribute
from shop.services.variant_attribute_sync import (
    ensure_attribute_for_all_product_variants,
    ensure_variant_has_product_structure,
    is_variant_attribute_sync_disabled,
    remove_attribute_from_all_product_variants,
)


@receiver(post_save, sender=ProductVariant)
def sync_structure_after_variant_created(sender, instance, created, **kwargs):
    if is_variant_attribute_sync_disabled():
        return

    if not created:
        return

    transaction.on_commit(lambda: ensure_variant_has_product_structure(instance))


@receiver(pre_save, sender=ProductVariantAttribute)
def remember_previous_attribute(sender, instance, **kwargs):
    if not instance.pk:
        instance._previous_attribute_id = None
        return

    instance._previous_attribute_id = (
        ProductVariantAttribute.objects.filter(pk=instance.pk)
        .values_list("attribute_id", flat=True)
        .first()
    )


@receiver(post_save, sender=ProductVariantAttribute)
def sync_structure_after_attribute_saved(sender, instance, **kwargs):
    if is_variant_attribute_sync_disabled():
        return

    if not instance.variant_id or not instance.attribute_id:
        return

    product_id = instance.variant.product_id
    previous_attribute_id = getattr(instance, "_previous_attribute_id", None)

    def sync():
        if previous_attribute_id and previous_attribute_id != instance.attribute_id:
            remove_attribute_from_all_product_variants(
                product_id=product_id,
                attribute_id=previous_attribute_id,
            )

        ensure_attribute_for_all_product_variants(instance)

    transaction.on_commit(sync)


def is_delete_caused_by_product_or_variant_cascade(origin):
    if isinstance(origin, (Product, ProductVariant)):
        return True

    if isinstance(origin, QuerySet):
        return origin.model in {Product, ProductVariant}

    return False


@receiver(post_delete, sender=ProductVariantAttribute)
def sync_structure_after_attribute_deleted(sender, instance, **kwargs):
    if is_variant_attribute_sync_disabled():
        return

    origin = kwargs.get("origin")

    if is_delete_caused_by_product_or_variant_cascade(origin):
        return

    if not instance.variant_id or not instance.attribute_id:
        return

    product_id = instance.variant.product_id
    attribute_id = instance.attribute_id

    transaction.on_commit(
        lambda: remove_attribute_from_all_product_variants(
            product_id=product_id,
            attribute_id=attribute_id,
        )
    )
