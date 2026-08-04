from django import forms
from django.forms.models import BaseInlineFormSet

from ..models import ProductVariant, ProductAttribute
from .helpers import unset_other_main_images
from ..services.variant_attribute_sync import get_template_attribute_items_for_product
from ..validators.product_variants import (
    build_variant_attribute_signature_item,
    validate_unique_variant_combinations_after_sync,
)


class ProductVariantAttributeInlineFormSet(BaseInlineFormSet):
    @staticmethod
    def get_initial_attribute_id(form):
        value = form.initial.get("attribute")

        if hasattr(value, "pk"):
            value = value.pk

        if value in (None, ""):
            return None

        return ProductAttribute._meta.pk.to_python(value)

    def clean(self):
        super().clean()

        if any(self.errors):
            return

        seen_attribute_ids = set()
        removed_attribute_ids = set()

        current_signature_items_by_attribute_id = {}
        propagated_signature_items_by_attribute_id = {}

        has_duplicate_attributes = False

        for form in self.forms:
            cleaned_data = getattr(form, "cleaned_data", None)

            if not cleaned_data:
                continue

            initial_attribute_id = self.get_initial_attribute_id(form)

            if self.can_delete and self._should_delete_form(form):
                if initial_attribute_id:
                    removed_attribute_ids.add(initial_attribute_id)

                continue

            attribute = cleaned_data.get("attribute")

            # Empty extra inline form.
            if not attribute:
                continue

            if attribute.pk in seen_attribute_ids:
                form.add_error(
                    "attribute",
                    (
                        f'Attribute "{attribute.name}" is selected '
                        "more than once. Each variant can have only "
                        "one value per attribute. Change the existing "
                        "row or create another variant."
                    ),
                )
                has_duplicate_attributes = True
                continue

            seen_attribute_ids.add(attribute.pk)

            # Changing the attribute key removes the old key
            # from every variant before synchronizing the new one.
            if initial_attribute_id and initial_attribute_id != attribute.pk:
                removed_attribute_ids.add(initial_attribute_id)

            value = cleaned_data.get("value")

            signature_item = build_variant_attribute_signature_item(
                attribute=attribute,
                value_id=(value.pk if value is not None else None),
                value_numeric=cleaned_data.get("value_numeric"),
                unit=cleaned_data.get("unit") or "",
            )

            if signature_item is None:
                continue

            current_signature_items_by_attribute_id[attribute.pk] = signature_item

            # Only changed/new inline rows trigger post_save
            # synchronization.
            if form.has_changed():
                propagated_signature_items_by_attribute_id[attribute.pk] = (
                    signature_item
                )

        if has_duplicate_attributes:
            raise forms.ValidationError("Please correct duplicate attributes below.")

        product_id = getattr(
            self.instance,
            "product_id",
            None,
        )

        # Simulate values that ensure_variant_has_product_structure()
        # will copy into the new/current variant.
        if product_id:
            template_items = get_template_attribute_items_for_product(
                product_id=product_id,
                exclude_variant_id=(self.instance.pk if self.instance.pk else None),
            )

            for template_item in template_items:
                attribute_id = template_item.attribute_id

                if attribute_id in seen_attribute_ids:
                    continue

                if attribute_id in removed_attribute_ids:
                    continue

                template_signature_item = build_variant_attribute_signature_item(
                    attribute=template_item.attribute,
                    value_id=template_item.value_id,
                    value_numeric=(template_item.value_numeric),
                    unit=template_item.unit or "",
                )

                if template_signature_item is not None:
                    current_signature_items_by_attribute_id[attribute_id] = (
                        template_signature_item
                    )

        current_signature = frozenset(current_signature_items_by_attribute_id.values())

        validate_unique_variant_combinations_after_sync(
            variant=self.instance,
            current_signature=current_signature,
            propagated_signature_items_by_attribute_id=(
                propagated_signature_items_by_attribute_id
            ),
            removed_attribute_ids=removed_attribute_ids,
        )


class ProductVariantSummaryInlineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()

        default_count = 0
        active_variant_count = 0

        for form in self.forms:
            if not hasattr(form, "cleaned_data"):
                continue

            cleaned_data = form.cleaned_data

            if cleaned_data.get("DELETE"):
                continue

            instance = form.instance

            if not instance or not instance.pk:
                continue

            if instance.is_active:
                active_variant_count += 1

            if cleaned_data.get("is_default"):
                default_count += 1

                if not instance.is_active:
                    form.add_error(
                        "is_default",
                        "Inactive variant cannot be selected as default.",
                    )

        if default_count > 1:
            raise forms.ValidationError(
                "Only one product variant can be selected as default."
            )

        if active_variant_count > 0 and default_count == 0:
            raise forms.ValidationError("Select one active variant as default.")


class ProductImageInlineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()

        main_count = 0

        for form in self.forms:
            if not hasattr(form, "cleaned_data"):
                continue

            cleaned_data = form.cleaned_data

            if cleaned_data.get("DELETE"):
                continue

            if cleaned_data.get("is_main"):
                main_count += 1

        if main_count > 1:
            raise forms.ValidationError(
                "Only one main product image is allowed for one product."
            )

    def save_new(self, form, commit=True):
        image = super().save_new(form, commit=False)
        image.variant = None
        unset_other_main_images(image)

        if commit:
            image.save()
            form.save_m2m()

        return image

    def save_existing(self, form, instance, commit=True):
        image = super().save_existing(form, instance, commit=False)
        image.variant = None
        unset_other_main_images(image)

        if commit:
            image.save()
            form.save_m2m()

        return image


class ProductVariantImageInlineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()

        main_count = 0

        for form in self.forms:
            if not hasattr(form, "cleaned_data"):
                continue

            cleaned_data = form.cleaned_data

            if cleaned_data.get("DELETE"):
                continue

            if cleaned_data.get("is_main"):
                main_count += 1

        if main_count > 1:
            raise forms.ValidationError(
                "Only one main image is allowed for one product variant."
            )

    def save_new(self, form, commit=True):
        image = super().save_new(form, commit=False)
        image.product = self.instance.product
        image.variant = self.instance
        unset_other_main_images(image)

        if commit:
            image.save()
            form.save_m2m()

        return image

    def save_existing(self, form, instance, commit=True):
        image = super().save_existing(form, instance, commit=False)
        image.product = self.instance.product
        image.variant = self.instance
        unset_other_main_images(image)

        if commit:
            image.save()
            form.save_m2m()

        return image


class ProductVariantImagesOnProductInlineFormSet(BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        variants = ProductVariant.objects.none()

        if self.instance and self.instance.pk:
            variants = self.instance.variants.all().order_by(
                "-is_default",
                "sku",
                "price",
                "id",
            )

        for form in self.forms:
            if "variant" in form.fields:
                form.fields["variant"].queryset = variants
                form.fields["variant"].required = True

    def clean(self):
        super().clean()

        main_count_by_variant_id = {}

        for form in self.forms:
            if not hasattr(form, "cleaned_data"):
                continue

            cleaned_data = form.cleaned_data

            if cleaned_data.get("DELETE"):
                continue

            variant = cleaned_data.get("variant")

            if not variant:
                continue

            if variant.product_id != self.instance.id:
                raise forms.ValidationError(
                    f"Variant {variant.sku} does not belong to this product."
                )

            if cleaned_data.get("is_main"):
                main_count_by_variant_id[variant.id] = (
                    main_count_by_variant_id.get(variant.id, 0) + 1
                )

        for _variant_id, main_count in main_count_by_variant_id.items():
            if main_count > 1:
                raise forms.ValidationError(
                    "Only one main image is allowed for one product variant."
                )

    def save_new(self, form, commit=True):
        image = super().save_new(form, commit=False)
        image.product = self.instance
        unset_other_main_images(image)

        if commit:
            image.save()
            form.save_m2m()

        return image

    def save_existing(self, form, instance, commit=True):
        image = super().save_existing(form, instance, commit=False)
        image.product = self.instance
        unset_other_main_images(image)

        if commit:
            image.save()
            form.save_m2m()

        return image
