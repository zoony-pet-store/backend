from django import forms
from django.forms.models import BaseInlineFormSet

from ..models import ProductVariant
from .helpers import unset_other_main_images
from ..validators.product_variants import (
    validate_unique_variant_attribute_combination,
    build_variant_attribute_signature_item,
)


class ProductVariantAttributeInlineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()

        if any(self.errors):
            return

        seen_attribute_ids = set()
        signature_items = []
        has_duplicate_attributes = False

        for form in self.forms:
            if self.can_delete and self._should_delete_form(form):
                continue

            cleaned_data = form.cleaned_data
            attribute = cleaned_data.get("attribute")

            # Empty extra inline form.
            if not attribute:
                continue

            if attribute.pk in seen_attribute_ids:
                form.add_error(
                    "attribute",
                    (
                        f'Attribute "{attribute.name}" is selected more than once. '
                        "Each variant can have only one value per attribute. "
                        "Change the existing row or create another variant."
                    ),
                )
                has_duplicate_attributes = True
                continue

            seen_attribute_ids.add(attribute.pk)

            value = cleaned_data.get("value")

            signature_item = build_variant_attribute_signature_item(
                attribute=attribute,
                value_id=value.pk if value is not None else None,
                value_numeric=cleaned_data.get("value_numeric"),
                unit=cleaned_data.get("unit") or "",
            )

            if signature_item is not None:
                signature_items.append(signature_item)

        if has_duplicate_attributes:
            raise forms.ValidationError("Please correct duplicate attributes below.")

        current_signature = frozenset(signature_items)

        validate_unique_variant_attribute_combination(
            variant=self.instance,
            current_signature=current_signature,
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
