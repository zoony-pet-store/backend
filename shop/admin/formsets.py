from django import forms
from django.forms.models import BaseInlineFormSet

from ..models import ProductVariant
from .helpers import unset_other_main_images


class ProductVariantAttributeInlineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()

        seen_attributes = {}
        has_duplicate_errors = False

        for form in self.forms:
            if not hasattr(form, "cleaned_data"):
                continue

            cleaned_data = form.cleaned_data

            if cleaned_data.get("DELETE"):
                continue

            attribute = cleaned_data.get("attribute")

            if not attribute:
                continue

            if attribute.id in seen_attributes:
                form.add_error(
                    "attribute",
                    (
                        f'Attribute "{attribute.name}" is selected more than once. '
                        f"Each variant can have only one value per attribute. "
                        f"Change the existing row or create another variant."
                    ),
                )
                has_duplicate_errors = True
                continue

            seen_attributes[attribute.id] = attribute

        if has_duplicate_errors:
            raise forms.ValidationError("Please correct duplicate attributes below.")


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
