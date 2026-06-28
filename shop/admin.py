from decimal import Decimal, ROUND_HALF_UP
from urllib.parse import urlencode

import cloudinary.uploader
from django import forms
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.db.models import Count, DecimalField, ExpressionWrapper, F, Q, Sum
from django.forms.models import BaseInlineFormSet
from django.urls import reverse
from django.utils.html import format_html
from django_jsonform.widgets import JSONFormWidget
from unfold.admin import ModelAdmin, StackedInline, TabularInline

from .models import (
    AnimalType,
    Badge,
    Brand,
    Cart,
    CartItem,
    Category,
    Customer,
    MediaAsset,
    Product,
    PRODUCT_CONTENT_BLOCKS_SCHEMA,
    ProductAttribute,
    ProductAttributeValue,
    ProductImage,
    ProductReview,
    ProductVariant,
    ProductVariantAttribute,
)


CLOUDINARY_PRODUCT_IMAGES_FOLDER = "zoony/product-images"


def image_preview(image_url, height=60):
    if image_url:
        return format_html(
            '<img src="{}" style="height:{}px; border-radius:8px; object-fit:cover;" />',
            image_url,
            height,
        )
    return "-"


def upload_image_to_cloudinary(uploaded_file):
    try:
        return cloudinary.uploader.upload(
            uploaded_file,
            folder=CLOUDINARY_PRODUCT_IMAGES_FOLDER,
            resource_type="image",
        )
    except Exception as error:
        raise forms.ValidationError(
            {"upload_file": f"Image upload failed: {error}"}
        ) from error


def create_media_asset_from_upload(uploaded_file, alt_text=""):
    upload_result = upload_image_to_cloudinary(uploaded_file)

    image_url = upload_result.get("secure_url") or upload_result.get("url")
    public_id = upload_result.get("public_id", "")

    if not image_url:
        raise forms.ValidationError(
            {"upload_file": "Cloudinary did not return image URL."}
        )

    return MediaAsset.objects.create(
        title=uploaded_file.name,
        image_url=image_url,
        alt_text=alt_text,
        cloudinary_public_id=public_id,
        source=MediaAsset.SOURCE_CLOUDINARY,
        is_active=True,
    )


def get_or_create_media_asset_from_url(
    image_url,
    alt_text="",
    cloudinary_public_id="",
):
    if not image_url:
        return None

    source = (
        MediaAsset.SOURCE_CLOUDINARY
        if cloudinary_public_id
        else MediaAsset.SOURCE_EXTERNAL
    )

    asset, created = MediaAsset.objects.get_or_create(
        image_url=image_url,
        defaults={
            "title": alt_text or image_url.rstrip("/").split("/")[-1][:255],
            "alt_text": alt_text,
            "cloudinary_public_id": cloudinary_public_id or "",
            "source": source,
            "is_active": True,
        },
    )

    update_fields = []

    if alt_text and not asset.alt_text:
        asset.alt_text = alt_text
        update_fields.append("alt_text")

    if cloudinary_public_id and not asset.cloudinary_public_id:
        asset.cloudinary_public_id = cloudinary_public_id
        asset.source = MediaAsset.SOURCE_CLOUDINARY
        update_fields.extend(["cloudinary_public_id", "source"])

    if not asset.is_active:
        asset.is_active = True
        update_fields.append("is_active")

    if update_fields:
        asset.save(update_fields=update_fields)

    return asset


def unset_other_main_images(image):
    if not image.is_main or not image.product_id:
        return

    if image.variant_id:
        ProductImage.objects.filter(
            product=image.product,
            variant=image.variant,
            is_main=True,
        ).exclude(pk=image.pk).update(is_main=False)
    else:
        ProductImage.objects.filter(
            product=image.product,
            variant__isnull=True,
            is_main=True,
        ).exclude(pk=image.pk).update(is_main=False)


def sync_product_variants_auto_badges(product):
    variants = product.variants.all().prefetch_related("badges")

    for variant in variants:
        variant.sync_auto_price_badges()


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = "__all__"

    def clean(self):
        cleaned = super().clean()
        parent = cleaned.get("parent")

        node = parent
        while node:
            if node == self.instance:
                raise forms.ValidationError("Circular category hierarchy detected.")
            node = node.parent

        return cleaned


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = "__all__"
        widgets = {
            "content_blocks": JSONFormWidget(schema=PRODUCT_CONTENT_BLOCKS_SCHEMA),
        }


class ProductAttributeAdminForm(forms.ModelForm):
    available_units = forms.MultipleChoiceField(
        required=False,
        choices=ProductAttribute.UNIT_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        help_text=(
            "Only for numeric attributes. " "Leave empty to allow all supported units."
        ),
    )

    class Meta:
        model = ProductAttribute
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()

        attribute_type = cleaned_data.get("type")
        available_units = list(cleaned_data.get("available_units") or [])

        if attribute_type == ProductAttribute.AttributeType.SELECT:
            cleaned_data["available_units"] = []

        elif attribute_type == ProductAttribute.AttributeType.NUMERIC:
            cleaned_data["available_units"] = available_units

        return cleaned_data


class ProductVariantForm(forms.ModelForm):
    discount_percent = forms.DecimalField(
        required=False,
        min_value=Decimal("0.01"),
        max_value=Decimal("99.99"),
        decimal_places=2,
        max_digits=5,
        label="Discount %",
        help_text=(
            "Optional. If filled, Price will be calculated from Old price. "
            "Example: old price 1000 and discount 20 means price 800."
        ),
    )

    class Meta:
        model = ProductVariant
        fields = "__all__"
        help_texts = {
            "sku": (
                "Optional. Leave empty to auto-generate SKU. "
                "Fill manually if you have supplier/internal SKU."
            ),
            "is_default": (
                "Default variant is used for product card price/image "
                "before customer selects another option."
            ),
            "is_active": (
                "Inactive variants are hidden from API and cannot be selected "
                "by customers."
            ),
            "cost_price": (
                "Internal purchase/cost price. Customers do not see this value."
            ),
            "auto_badges_enabled": (
                "If enabled, Discount and Sale badges are managed automatically "
                "based on Old price and Price. Disable this if you want to manage "
                "variant badges fully manually."
            ),
            "badges": (
                "Manual badges for this variant. Discount/Sale can be auto-managed "
                "when Auto badges enabled is checked."
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["price"].required = False

        instance = self.instance
        if instance and instance.pk and instance.old_price and instance.price:
            if instance.old_price > instance.price:
                discount = (
                    (instance.old_price - instance.price)
                    / instance.old_price
                    * Decimal("100")
                )
                self.fields["discount_percent"].initial = discount.quantize(
                    Decimal("0.01")
                )

    def clean(self):
        cleaned_data = super().clean()

        price = cleaned_data.get("price")
        old_price = cleaned_data.get("old_price")
        discount_percent = cleaned_data.get("discount_percent")

        if discount_percent is not None:
            if not old_price:
                raise forms.ValidationError(
                    {
                        "discount_percent": (
                            "Old price is required to calculate discount."
                        )
                    }
                )

            multiplier = (Decimal("100") - discount_percent) / Decimal("100")
            cleaned_data["price"] = (old_price * multiplier).quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP,
            )
            return cleaned_data

        if price is None:
            raise forms.ValidationError(
                {"price": "Price is required if discount percent is not provided."}
            )

        return cleaned_data


class AttributeSelectWidget(forms.Select):
    def __init__(self, *args, **kwargs):
        self.attribute_map = {}
        super().__init__(*args, **kwargs)

    def create_option(
        self,
        name,
        value,
        label,
        selected,
        index,
        subindex=None,
        attrs=None,
    ):
        option = super().create_option(
            name,
            value,
            label,
            selected,
            index,
            subindex=subindex,
            attrs=attrs,
        )

        if not value:
            return option

        attribute = getattr(value, "instance", None)

        if attribute is None:
            attribute = self.attribute_map.get(str(value))

        if attribute is None:
            return option

        option["attrs"]["data-attribute-type"] = attribute.type
        option["attrs"]["data-available-units"] = ",".join(
            attribute.available_units or []
        )

        return option


class AttributeValueSelectWidget(forms.Select):
    def __init__(self, *args, **kwargs):
        self.value_map = {}
        super().__init__(*args, **kwargs)

    def create_option(
        self,
        name,
        value,
        label,
        selected,
        index,
        subindex=None,
        attrs=None,
    ):
        option = super().create_option(
            name,
            value,
            label,
            selected,
            index,
            subindex=subindex,
            attrs=attrs,
        )

        if not value:
            return option

        attribute_value = getattr(value, "instance", None)

        if attribute_value is None:
            attribute_value = self.value_map.get(str(value))

        if attribute_value is None:
            return option

        option["attrs"]["data-attribute-id"] = str(attribute_value.attribute_id)

        return option


def get_unit_choices_for_attribute(attribute=None):
    unit_choices = list(ProductAttribute.UNIT_CHOICES)

    if (
        attribute
        and attribute.type == ProductAttribute.AttributeType.NUMERIC
        and attribute.available_units
    ):
        allowed_units = set(attribute.available_units)
        unit_choices = [
            (unit, label) for unit, label in unit_choices if unit in allowed_units
        ]

    return [("", "---------")] + unit_choices


class ProductVariantAttributeForm(forms.ModelForm):
    unit = forms.ChoiceField(
        required=False,
        choices=[("", "---------")] + ProductAttribute.UNIT_CHOICES,
    )

    class Meta:
        model = ProductVariantAttribute
        fields = "__all__"
        widgets = {
            "attribute": AttributeSelectWidget,
            "value": AttributeValueSelectWidget,
        }

    class Media:
        js = ("shop/admin/js/product_variant_attribute_inline.js",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        attributes = ProductAttribute.objects.all().order_by(
            "display_order",
            "name",
        )
        values = ProductAttributeValue.objects.select_related("attribute").order_by(
            "attribute__display_order",
            "attribute__name",
            "display_order",
            "value",
        )

        self.fields["attribute"].queryset = attributes
        self.fields["value"].queryset = values

        self.fields["attribute"].widget.attribute_map = {
            str(attribute.pk): attribute for attribute in attributes
        }
        self.fields["value"].widget.value_map = {
            str(attribute_value.pk): attribute_value for attribute_value in values
        }

        selected_attribute_id = None

        if self.data:
            selected_attribute_id = self.data.get(self.add_prefix("attribute"))

        if not selected_attribute_id and self.initial.get("attribute"):
            selected_attribute_id = self.initial.get("attribute")

        if (
            not selected_attribute_id
            and self.instance
            and self.instance.pk
            and self.instance.attribute_id
        ):
            selected_attribute_id = self.instance.attribute_id

        selected_attribute = None

        if selected_attribute_id:
            selected_attribute = next(
                (
                    attribute
                    for attribute in attributes
                    if str(attribute.pk) == str(selected_attribute_id)
                ),
                None,
            )

        self.fields["unit"].choices = get_unit_choices_for_attribute(selected_attribute)

    def clean(self):
        cleaned_data = super().clean()

        attribute = cleaned_data.get("attribute")
        value = cleaned_data.get("value")
        value_numeric = cleaned_data.get("value_numeric")
        unit = cleaned_data.get("unit")

        if not attribute:
            return cleaned_data

        if attribute.type == ProductAttribute.AttributeType.SELECT:
            if value and value.attribute_id != attribute.id:
                raise forms.ValidationError(
                    "Selected value does not belong to selected attribute."
                )

            cleaned_data["value_numeric"] = None
            cleaned_data["unit"] = ""

        elif attribute.type == ProductAttribute.AttributeType.NUMERIC:
            if value:
                raise forms.ValidationError(
                    "Text value must be empty for numeric attribute."
                )

            has_numeric_value = value_numeric is not None
            has_unit = bool(unit)

            if has_numeric_value and not has_unit:
                raise forms.ValidationError(
                    "Unit is required when numeric value is filled."
                )

            if has_unit and not has_numeric_value:
                raise forms.ValidationError(
                    "Numeric value is required when unit is filled."
                )

            if (
                unit
                and attribute.available_units
                and unit not in attribute.available_units
            ):
                raise forms.ValidationError(
                    f"Unit '{unit}' is not allowed for {attribute.name}."
                )

            cleaned_data["value"] = None

        return cleaned_data


class MediaAssetAdminForm(forms.ModelForm):
    upload_file = forms.ImageField(
        required=False,
        label="Upload image",
        help_text="Upload image from your computer/device to Cloudinary.",
    )

    class Meta:
        model = MediaAsset
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if "image_url" in self.fields:
            self.fields["image_url"].required = False

    def clean(self):
        cleaned_data = super().clean()

        upload_file = cleaned_data.get("upload_file")
        image_url = cleaned_data.get("image_url") or getattr(
            self.instance,
            "image_url",
            "",
        )

        if not upload_file and not image_url:
            raise forms.ValidationError(
                "Upload image file or provide direct image URL."
            )

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)

        upload_file = self.cleaned_data.get("upload_file")

        if upload_file:
            upload_result = upload_image_to_cloudinary(upload_file)

            image_url = upload_result.get("secure_url") or upload_result.get("url")
            public_id = upload_result.get("public_id", "")

            if not image_url:
                raise forms.ValidationError(
                    {"upload_file": "Cloudinary did not return image URL."}
                )

            instance.image_url = image_url
            instance.cloudinary_public_id = public_id
            instance.source = MediaAsset.SOURCE_CLOUDINARY

            if not instance.title:
                instance.title = upload_file.name

        if commit:
            instance.save()
            self.save_m2m()

        return instance


class ProductImageAdminForm(forms.ModelForm):
    upload_file = forms.ImageField(
        required=False,
        label="Upload new image",
        help_text=(
            "Upload a new image from your computer/device. "
            "It will be uploaded to Cloudinary and saved to Media assets automatically."
        ),
    )

    class Meta:
        model = ProductImage
        fields = "__all__"
        help_texts = {
            "asset": "Select existing image from media library.",
            "image_url": (
                "Advanced fallback direct URL. "
                "Usually filled automatically from uploaded/selected image."
            ),
            "cloudinary_public_id": (
                "Filled automatically for images uploaded to Cloudinary."
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if "asset" in self.fields:
            self.fields["asset"].queryset = MediaAsset.objects.filter(
                is_active=True
            ).order_by("-created_at", "title")
            self.fields["asset"].label = "Select existing image"

        if "image_url" in self.fields:
            self.fields["image_url"].required = False

        if "cloudinary_public_id" in self.fields:
            self.fields["cloudinary_public_id"].required = False

    def clean(self):
        cleaned_data = super().clean()

        if cleaned_data.get("DELETE"):
            return cleaned_data

        upload_file = cleaned_data.get("upload_file")
        asset = cleaned_data.get("asset")
        image_url = cleaned_data.get("image_url")
        cloudinary_public_id = cleaned_data.get("cloudinary_public_id", "")

        existing_asset = getattr(self.instance, "asset", None)
        existing_image_url = getattr(self.instance, "image_url", "")

        is_empty_extra_form = (
            not self.instance.pk
            and not upload_file
            and not asset
            and not image_url
            and not cleaned_data.get("alt_text")
            and not cleaned_data.get("is_main")
        )

        if is_empty_extra_form:
            return cleaned_data

        if upload_file:
            alt_text = cleaned_data.get("alt_text") or ""

            if not alt_text and getattr(self.instance, "product_id", None):
                alt_text = self.instance.product.name

            uploaded_asset = create_media_asset_from_upload(
                uploaded_file=upload_file,
                alt_text=alt_text,
            )

            cleaned_data["asset"] = uploaded_asset
            cleaned_data["image_url"] = uploaded_asset.image_url
            cleaned_data["cloudinary_public_id"] = uploaded_asset.cloudinary_public_id

            self.instance.asset = uploaded_asset
            self.instance.image_url = uploaded_asset.image_url
            self.instance.cloudinary_public_id = uploaded_asset.cloudinary_public_id

            if not self.instance.alt_text:
                self.instance.alt_text = uploaded_asset.alt_text

            return cleaned_data

        if asset:
            cleaned_data["image_url"] = asset.image_url
            cleaned_data["cloudinary_public_id"] = asset.cloudinary_public_id

            self.instance.asset = asset
            self.instance.image_url = asset.image_url
            self.instance.cloudinary_public_id = asset.cloudinary_public_id

            if not self.instance.alt_text:
                self.instance.alt_text = asset.alt_text

            return cleaned_data

        if image_url:
            linked_asset = get_or_create_media_asset_from_url(
                image_url=image_url,
                alt_text=cleaned_data.get("alt_text", ""),
                cloudinary_public_id=cloudinary_public_id,
            )

            cleaned_data["asset"] = linked_asset
            self.instance.asset = linked_asset
            self.instance.image_url = image_url
            self.instance.cloudinary_public_id = cloudinary_public_id

            return cleaned_data

        if existing_asset:
            cleaned_data["asset"] = existing_asset
            cleaned_data["image_url"] = existing_asset.image_url
            cleaned_data["cloudinary_public_id"] = existing_asset.cloudinary_public_id

            self.instance.asset = existing_asset
            self.instance.image_url = existing_asset.image_url
            self.instance.cloudinary_public_id = existing_asset.cloudinary_public_id

            return cleaned_data

        if existing_image_url:
            cleaned_data["image_url"] = existing_image_url
            self.instance.image_url = existing_image_url
            return cleaned_data

        raise forms.ValidationError(
            "Upload a new image, select existing image, or provide direct image URL."
        )

    def save(self, commit=True):
        instance = super().save(commit=False)

        asset = self.cleaned_data.get("asset")

        if asset:
            instance.asset = asset
            instance.image_url = asset.image_url
            instance.cloudinary_public_id = asset.cloudinary_public_id

            if not instance.alt_text:
                instance.alt_text = asset.alt_text

        elif instance.image_url:
            instance.asset = get_or_create_media_asset_from_url(
                image_url=instance.image_url,
                alt_text=instance.alt_text,
                cloudinary_public_id=instance.cloudinary_public_id,
            )

        if commit:
            instance.save()
            self.save_m2m()

        return instance


class ProductImageInlineAdminForm(ProductImageAdminForm):
    class Meta(ProductImageAdminForm.Meta):
        widgets = {
            "image_url": forms.HiddenInput(),
            "cloudinary_public_id": forms.HiddenInput(),
        }


class ProductAttributeValueAdminForm(forms.ModelForm):
    class Meta:
        model = ProductAttributeValue
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["attribute"].queryset = ProductAttribute.objects.filter(
            type=ProductAttribute.AttributeType.SELECT
        ).order_by("display_order", "name")


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


class ProductVariantAttributeInline(StackedInline):
    model = ProductVariantAttribute
    form = ProductVariantAttributeForm
    formset = ProductVariantAttributeInlineFormSet
    extra = 1
    fields = (
        "attribute",
        "value",
        "value_numeric",
        "unit",
    )
    show_change_link = True
    verbose_name = "Variant attribute"
    verbose_name_plural = "Variant attributes"

    class Media:
        js = ("shop/admin/js/product_variant_attribute_inline.js",)

    def get_product_id_for_initial_structure(self, request, obj=None):
        if obj and obj.pk:
            return obj.product_id

        return request.GET.get("product")

    def get_initial_attribute_ids(self, request, obj=None):
        product_id = self.get_product_id_for_initial_structure(request, obj)

        if not product_id:
            return []

        return list(
            ProductAttribute.objects.filter(
                variant_attributes__variant__product_id=product_id,
            )
            .distinct()
            .order_by("display_order", "name")
            .values_list("id", flat=True)
        )

    def get_extra(self, request, obj=None, **kwargs):
        if obj and obj.pk:
            return 1

        initial_attribute_ids = self.get_initial_attribute_ids(request, obj)

        return len(initial_attribute_ids) or 1

    def get_formset(self, request, obj=None, **kwargs):
        formset_class = super().get_formset(request, obj, **kwargs)
        initial_attribute_ids = self.get_initial_attribute_ids(request, obj)

        if obj and obj.pk:
            return formset_class

        class ProductVariantAttributeInitialFormSet(formset_class):
            def __init__(self, *args, **formset_kwargs):
                if initial_attribute_ids:
                    formset_kwargs.setdefault(
                        "initial",
                        [
                            {"attribute": attribute_id}
                            for attribute_id in initial_attribute_ids
                        ],
                    )

                super().__init__(*args, **formset_kwargs)

        return ProductVariantAttributeInitialFormSet


class ProductVariantImagesInline(TabularInline):
    model = ProductImage
    form = ProductImageInlineAdminForm
    formset = ProductVariantImageInlineFormSet
    fk_name = "variant"
    extra = 1
    fields = (
        "upload_file",
        "asset",
        "image_url",
        "cloudinary_public_id",
        "alt_text",
        "is_main",
        "preview",
    )
    readonly_fields = ("preview",)
    autocomplete_fields = ("asset",)
    ordering = ("display_order", "id")
    show_change_link = True
    verbose_name = "Variant image"
    verbose_name_plural = "Variant images"

    def preview(self, obj):
        return image_preview(obj.image_url, height=80)

    preview.short_description = "Preview"


class ProductVariantsInline(TabularInline):
    model = ProductVariant
    formset = ProductVariantSummaryInlineFormSet
    extra = 0
    can_delete = False
    show_change_link = True

    fields = (
        "variant_preview",
        "sku",
        "attributes_summary",
        "price",
        "old_price",
        "stock",
        "is_active_display",
        "is_default",
    )

    readonly_fields = (
        "variant_preview",
        "sku",
        "attributes_summary",
        "price",
        "old_price",
        "stock",
        "is_active_display",
    )

    ordering = ("-is_default", "price", "id")
    verbose_name = "Product variant"
    verbose_name_plural = "Product variants"

    def has_add_permission(self, request, obj=None):
        return False

    def variant_preview(self, obj):
        if not obj.pk:
            return "-"

        image = obj.images.filter(is_main=True).first() or obj.images.first()

        if image and image.image_url:
            return image_preview(image.image_url, height=48)

        product_image = obj.product.images.filter(
            variant__isnull=True,
            is_main=True,
        ).first()

        if product_image and product_image.image_url:
            return image_preview(product_image.image_url, height=48)

        return "-"

    variant_preview.short_description = "Preview"

    def attributes_summary(self, obj):
        if not obj.pk:
            return "-"

        attributes = obj.variant_attributes.select_related(
            "attribute",
            "value",
        ).all()

        if not attributes:
            return "-"

        return ", ".join(
            f"{item.attribute.name}: {item.display_value}" for item in attributes
        )

    attributes_summary.short_description = "Attributes"

    def is_active_display(self, obj):
        if not obj.pk:
            return False

        return obj.is_active

    is_active_display.short_description = "Active"
    is_active_display.boolean = True


class ProductImagesInline(TabularInline):
    model = ProductImage
    form = ProductImageInlineAdminForm
    formset = ProductImageInlineFormSet
    fk_name = "product"
    extra = 1
    fields = (
        "upload_file",
        "asset",
        "image_url",
        "cloudinary_public_id",
        "alt_text",
        "is_main",
        "preview",
    )
    readonly_fields = ("preview",)
    autocomplete_fields = ("asset",)
    ordering = ("display_order", "id")
    show_change_link = True
    verbose_name = "Base product image"
    verbose_name_plural = "Base product images"

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .filter(variant__isnull=True)
            .select_related("asset")
        )

    def preview(self, obj):
        return image_preview(obj.image_url, height=80)

    preview.short_description = "Preview"


class ProductVariantImagesOnProductInline(TabularInline):
    model = ProductImage
    form = ProductImageInlineAdminForm
    formset = ProductVariantImagesOnProductInlineFormSet
    fk_name = "product"
    extra = 1
    fields = (
        "variant",
        "upload_file",
        "asset",
        "image_url",
        "cloudinary_public_id",
        "alt_text",
        "is_main",
        "preview",
    )
    readonly_fields = ("preview",)
    autocomplete_fields = ("variant", "asset")
    ordering = ("variant__sku", "display_order", "id")
    show_change_link = True
    verbose_name = "Variant image"
    verbose_name_plural = "Variant images"

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .filter(variant__isnull=False)
            .select_related("variant", "asset")
        )

    def preview(self, obj):
        return image_preview(obj.image_url, height=80)

    preview.short_description = "Preview"


class CartItemsInline(TabularInline):
    model = CartItem
    extra = 0
    autocomplete_fields = ("variant",)
    readonly_fields = ("total_price",)


@admin.register(Customer)
class CustomerAdmin(UserAdmin):
    ordering = ("-date_joined",)
    list_display = ("email", "first_name", "last_name", "is_active", "is_staff")
    search_fields = ("email", "first_name", "last_name")

    fieldsets = UserAdmin.fieldsets + (
        ("Verification", {"fields": ("email_verified",)}),
    )


@admin.register(MediaAsset)
class MediaAssetAdmin(ModelAdmin):
    form = MediaAssetAdminForm

    list_display = (
        "preview",
        "title",
        "source",
        "is_active",
        "cloudinary_public_id",
        "created_at",
    )
    list_filter = ("source", "is_active", "created_at")
    search_fields = ("title", "alt_text", "image_url", "cloudinary_public_id")
    readonly_fields = ("preview", "created_at", "updated_at")
    ordering = ("-created_at", "title")

    fields = (
        "upload_file",
        "title",
        "image_url",
        "alt_text",
        "cloudinary_public_id",
        "source",
        "is_active",
        "preview",
        "created_at",
        "updated_at",
    )

    def preview(self, obj):
        return image_preview(obj.image_url, height=80)

    preview.short_description = "Preview"


@admin.register(AnimalType)
class AnimalTypeAdmin(ModelAdmin):
    list_display = ("name", "is_active", "category_count", "product_count")
    search_fields = ("name", "slug")
    list_filter = ("is_active",)
    ordering = ("name",)

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .annotate(
                _category_count=Count(
                    "categories",
                    filter=Q(categories__is_active=True),
                ),
                _product_count=Count(
                    "categories__products",
                    filter=Q(categories__products__is_active=True),
                ),
            )
        )

    def category_count(self, obj):
        return obj._category_count

    category_count.short_description = "Active categories"

    def product_count(self, obj):
        return obj._product_count

    product_count.short_description = "Active products"


@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    form = CategoryForm
    list_display = (
        "name",
        "animal_type",
        "parent",
        "level",
        "sort_order",
        "is_active",
        "product_count",
    )
    list_select_related = ("animal_type", "parent")
    list_filter = ("is_active", "animal_type")
    search_fields = ("name", "slug", "parent__name", "animal_type__name")
    ordering = ("animal_type__name", "sort_order", "name")
    autocomplete_fields = ("parent",)

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .annotate(
                _product_count=Count(
                    "products",
                    filter=Q(products__is_active=True),
                )
            )
        )

    def product_count(self, obj):
        return obj._product_count

    product_count.short_description = "Active products"


@admin.register(Brand)
class BrandAdmin(ModelAdmin):
    list_display = ("name", "is_active", "product_count", "logo")
    list_filter = ("is_active",)
    search_fields = ("name", "slug")
    ordering = ("name",)

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .annotate(
                _product_count=Count(
                    "products",
                    filter=Q(products__is_active=True),
                )
            )
        )

    def product_count(self, obj):
        return obj._product_count

    product_count.short_description = "Active products"

    def logo(self, obj):
        return image_preview(obj.logo_url, height=40)

    logo.short_description = "Logo"


@admin.register(Badge)
class BadgeAdmin(ModelAdmin):
    list_display = ("label", "slug", "is_active", "color_preview", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "label", "slug")
    ordering = ("label",)

    def color_preview(self, obj):
        return format_html(
            '<span style="display:inline-block; width:24px; height:24px; '
            'border-radius:6px; background:{}; border:1px solid #ccc;"></span>',
            obj.background_color,
        )

    color_preview.short_description = "Color"


@admin.register(Product)
class ProductAdmin(ModelAdmin):
    form = ProductForm

    list_display = (
        "name",
        "brand",
        "category",
        "is_active",
        "rating",
        "review_count",
        "display_price_display",
        "min_price_display",
        "max_price_display",
        "in_stock_display",
        "created_at",
    )
    list_select_related = ("brand", "category", "category__animal_type")
    list_filter = ("is_active", "brand", "category", "category__animal_type", "badges")
    search_fields = (
        "name",
        "slug",
        "description",
        "short_description",
        "brand__name",
        "category__name",
        "meta_title",
        "meta_description",
    )
    autocomplete_fields = ("brand", "category", "badges")
    readonly_fields = (
        "created_at",
        "updated_at",
        "rating",
        "review_count",
        "display_price_display",
        "min_price_display",
        "max_price_display",
        "in_stock_display",
        "add_variant_link",
    )
    date_hierarchy = "created_at"
    save_on_top = True
    ordering = ("-created_at",)
    inlines = (
        ProductVariantsInline,
        ProductImagesInline,
        ProductVariantImagesOnProductInline,
    )

    fieldsets = (
        (
            "Basic info",
            {
                "fields": (
                    "name",
                    "slug",
                    "is_active",
                    "brand",
                    "category",
                    "badges",
                    "short_description",
                    "description",
                )
            },
        ),
        (
            "Catalog info",
            {
                "fields": (
                    "rating",
                    "review_count",
                    "display_price_display",
                    "min_price_display",
                    "max_price_display",
                    "in_stock_display",
                    "main_image",
                )
            },
        ),
        (
            "Advanced custom content blocks",
            {
                "fields": ("content_blocks",),
                "description": (
                    "Main way to manage custom product page content. "
                    "Use blocks: text, key/value, table."
                ),
            },
        ),
        (
            "SEO",
            {
                "fields": ("meta_title", "meta_description"),
                "classes": ("collapse",),
            },
        ),
        (
            "Service info",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
        (
            "Product variant management",
            {
                "fields": ("add_variant_link",),
                "description": (
                    "Variants are shown below as a compact list. "
                    "Use the button to add a new variant for this product."
                ),
            },
        ),
    )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("brand", "category", "category__animal_type")
            .prefetch_related(
                "badges",
                "variants",
                "variants__badges",
                "variants__variant_attributes__attribute",
                "variants__variant_attributes__value",
                "variants__images",
                "images",
            )
        )

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)

        product = form.instance

        default_variant = product.variants.filter(
            is_default=True,
            is_active=True,
        ).first()

        if default_variant:
            product.variants.exclude(pk=default_variant.pk).update(is_default=False)
        else:
            first_active_variant = product.variants.filter(is_active=True).first()

            if first_active_variant:
                product.variants.update(is_default=False)
                product.variants.filter(pk=first_active_variant.pk).update(
                    is_default=True
                )

        sync_product_variants_auto_badges(product)

    def add_variant_link(self, obj):
        if not obj or not obj.pk:
            return "Save product before adding variants."

        url = reverse("admin:shop_productvariant_add")
        query_string = urlencode({"product": str(obj.pk)})

        return format_html(
            '<a class="button" href="{}?{}">+ Add variant for this product</a>',
            url,
            query_string,
        )

    add_variant_link.short_description = "Add variant"

    def display_price_display(self, obj):
        return obj.display_price

    display_price_display.short_description = "Display price"

    def min_price_display(self, obj):
        return obj.min_price

    min_price_display.short_description = "Min price"

    def max_price_display(self, obj):
        return obj.max_price

    max_price_display.short_description = "Max price"

    def in_stock_display(self, obj):
        return obj.in_stock

    in_stock_display.short_description = "In stock"
    in_stock_display.boolean = True


@admin.register(ProductVariant)
class ProductVariantAdmin(ModelAdmin):
    form = ProductVariantForm

    list_display = (
        "sku",
        "product",
        "price",
        "old_price",
        "cost_price",
        "stock",
        "is_default",
        "auto_badges_enabled",
        "has_discount_display",
        "discount_percentage_display",
        "is_active",
    )
    list_select_related = ("product", "product__brand", "product__category")
    list_filter = (
        "is_active",
        "is_default",
        "auto_badges_enabled",
        "product__brand",
        "product__category",
    )
    autocomplete_fields = ("product", "badges")
    search_fields = ("sku", "product__name", "product__brand__name")
    readonly_fields = (
        "has_discount_display",
        "discount_percentage_display",
        "created_at",
        "updated_at",
    )
    ordering = ("product__name", "-is_default", "price", "id")
    inlines = (
        ProductVariantAttributeInline,
        ProductVariantImagesInline,
    )

    fieldsets = (
        (
            "Basic info",
            {
                "fields": (
                    "product",
                    "sku",
                    "is_active",
                    "is_default",
                    "stock",
                    "price",
                    "old_price",
                    "discount_percent",
                    "cost_price",
                    "has_discount_display",
                    "discount_percentage_display",
                    "auto_badges_enabled",
                    "badges",
                )
            },
        ),
        (
            "Variant content overrides",
            {
                "fields": ("short_description", "description"),
                "classes": ("collapse",),
            },
        ),
        (
            "Service info",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("product", "product__brand", "product__category")
            .prefetch_related(
                "badges",
                "images",
                "variant_attributes__attribute",
                "variant_attributes__value",
            )
        )

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        form.instance.sync_auto_price_badges()

    def has_discount_display(self, obj):
        if not obj.pk:
            return False
        return obj.has_discount

    has_discount_display.short_description = "Has discount"
    has_discount_display.boolean = True

    def discount_percentage_display(self, obj):
        if not obj.pk or not obj.has_discount:
            return "-"
        return f"{obj.discount_percentage}%"

    discount_percentage_display.short_description = "Discount %"


@admin.register(ProductVariantAttribute)
class ProductVariantAttributeAdmin(ModelAdmin):
    form = ProductVariantAttributeForm

    list_display = (
        "variant",
        "attribute",
        "attribute_type",
        "display_value",
        "value",
        "value_numeric",
        "unit",
    )
    list_select_related = ("variant", "variant__product", "attribute", "value")
    autocomplete_fields = ("variant",)
    search_fields = (
        "variant__sku",
        "variant__product__name",
        "attribute__name",
        "value__value",
        "unit",
    )
    list_filter = ("attribute", "attribute__type", "unit")
    ordering = (
        "variant__product__name",
        "variant__sku",
        "attribute__display_order",
    )
    fields = (
        "variant",
        "attribute",
        "value",
        "value_numeric",
        "unit",
    )

    def attribute_type(self, obj):
        return obj.attribute.type

    attribute_type.short_description = "Type"


@admin.register(ProductAttribute)
class ProductAttributeAdmin(ModelAdmin):
    form = ProductAttributeAdminForm

    list_display = (
        "name",
        "slug",
        "type",
        "available_units_display",
        "filterable",
        "display_order",
    )
    list_filter = ("type", "filterable")
    search_fields = ("name", "slug")
    ordering = ("display_order", "name")
    autocomplete_fields = ("categories",)
    filter_horizontal = ("categories",)

    fields = (
        "name",
        "slug",
        "description",
        "type",
        "available_units",
        "filterable",
        "display_order",
        "categories",
    )

    def available_units_display(self, obj):
        if obj.type != ProductAttribute.AttributeType.NUMERIC:
            return "-"

        if not obj.available_units:
            return "All units"

        return ", ".join(obj.available_units)

    available_units_display.short_description = "Available units"


@admin.register(ProductAttributeValue)
class ProductAttributeValueAdmin(ModelAdmin):
    form = ProductAttributeValueAdminForm

    list_display = ("attribute", "value", "slug", "display_order")
    list_select_related = ("attribute",)
    search_fields = ("value", "slug", "attribute__name")
    ordering = ("attribute__name", "display_order", "value")

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .filter(attribute__type=ProductAttribute.AttributeType.SELECT)
            .select_related("attribute")
        )


@admin.register(ProductImage)
class ProductImageAdmin(ModelAdmin):
    form = ProductImageAdminForm

    list_display = (
        "product",
        "variant",
        "asset",
        "is_main",
        "display_order",
        "cloudinary_public_id",
        "preview",
    )
    list_select_related = ("product", "variant", "asset")
    list_filter = ("is_main", "asset__source")
    autocomplete_fields = ("product", "variant", "asset")
    search_fields = (
        "product__name",
        "variant__sku",
        "asset__title",
        "alt_text",
        "image_url",
        "cloudinary_public_id",
    )
    readonly_fields = ("preview",)
    fields = (
        "product",
        "variant",
        "upload_file",
        "asset",
        "image_url",
        "alt_text",
        "is_main",
        "display_order",
        "cloudinary_public_id",
        "preview",
    )
    ordering = ("product", "variant", "display_order", "id")
    actions = ("link_selected_images_to_media_assets",)

    def preview(self, obj):
        return image_preview(obj.image_url, height=60)

    preview.short_description = "Preview"

    def save_model(self, request, obj, form, change):
        unset_other_main_images(obj)
        super().save_model(request, obj, form, change)

    @admin.action(description="Create/link Media assets for selected product images")
    def link_selected_images_to_media_assets(self, request, queryset):
        linked = 0
        skipped = 0

        for image in queryset:
            if not image.image_url:
                skipped += 1
                continue

            asset = get_or_create_media_asset_from_url(
                image_url=image.image_url,
                alt_text=image.alt_text,
                cloudinary_public_id=image.cloudinary_public_id,
            )

            if asset and image.asset_id != asset.id:
                image.asset = asset
                image.save(update_fields=["asset"])
                linked += 1
            else:
                skipped += 1

        self.message_user(
            request,
            f"Linked images: {linked}. Skipped: {skipped}.",
            level=messages.SUCCESS,
        )


@admin.register(ProductReview)
class ProductReviewAdmin(ModelAdmin):
    list_display = (
        "product",
        "user",
        "rating",
        "is_verified",
        "is_active",
        "created_at",
    )
    list_select_related = ("product", "user")
    list_filter = ("is_active", "is_verified", "rating", "created_at")
    search_fields = (
        "product__name",
        "user__email",
        "title",
        "comment",
        "positive_comment",
        "negative_comment",
    )
    autocomplete_fields = ("product", "user")
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    actions = ("activate_reviews", "deactivate_reviews")

    fieldsets = (
        (
            "Review",
            {
                "fields": (
                    "product",
                    "user",
                    "rating",
                    "is_verified",
                    "is_active",
                    "title",
                    "comment",
                    "positive_comment",
                    "negative_comment",
                )
            },
        ),
        (
            "Service info",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    @admin.action(description="Activate selected reviews")
    def activate_reviews(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(
            request,
            f"{updated} review(s) activated.",
            level=messages.SUCCESS,
        )

    @admin.action(description="Deactivate selected reviews")
    def deactivate_reviews(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(
            request,
            f"{updated} review(s) deactivated.",
            level=messages.WARNING,
        )


@admin.register(Cart)
class CartAdmin(ModelAdmin):
    list_display = ("user", "total_items", "total_price", "created_at")
    inlines = (CartItemsInline,)
    search_fields = ("user__email", "user__first_name", "user__last_name")
    autocomplete_fields = ("user",)
    ordering = ("-created_at",)

    def get_queryset(self, request):
        line_total = ExpressionWrapper(
            F("items__variant__price") * F("items__quantity"),
            output_field=DecimalField(max_digits=12, decimal_places=2),
        )

        return (
            super()
            .get_queryset(request)
            .select_related("user")
            .annotate(
                _items_sum=Sum("items__quantity"),
                _price_sum=Sum(line_total),
            )
        )

    def total_items(self, obj):
        return obj._items_sum or 0

    total_items.short_description = "Items"

    def total_price(self, obj):
        return obj._price_sum or 0

    total_price.short_description = "Total price"


@admin.register(CartItem)
class CartItemAdmin(ModelAdmin):
    list_display = ("cart", "variant", "quantity", "total_price", "added_at")
    autocomplete_fields = ("cart", "variant")
    search_fields = ("cart__user__email", "variant__sku", "variant__product__name")
    ordering = ("-added_at",)
