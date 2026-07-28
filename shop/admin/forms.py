from decimal import Decimal, ROUND_HALF_UP

from django import forms
from django_jsonform.widgets import JSONFormWidget

from ..models import (
    Brand,
    Category,
    MediaAsset,
    Product,
    PRODUCT_CONTENT_BLOCKS_SCHEMA,
    ProductAttribute,
    ProductAttributeValue,
    ProductImage,
    ProductVariant,
    ProductVariantAttribute,
)
from .helpers import (
    create_media_asset_from_upload,
    get_or_create_media_asset_from_url,
    get_unit_choices_for_attribute,
    upload_image_to_cloudinary,
)
from .widgets import (
    AttributeSelectWidget,
    AttributeValueSelectWidget,
    CategoryTreeSelectWidget,
    MediaAssetSelectWidget,
)


class MediaAssetChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj: MediaAsset) -> str:
        return obj.title or "Untitled image"


class ImageUrlAdminFormMixin(forms.ModelForm):
    image_url_field_name = ""
    image_alt_text_source_field = "name"

    image_asset = MediaAssetChoiceField(
        queryset=MediaAsset.objects.none(),
        required=False,
        label="Choose from media library",
        help_text="Choose an existing image from media library.",
        widget=MediaAssetSelectWidget(),
    )
    upload_file = forms.ImageField(
        required=False,
        label="Upload new image",
        help_text=(
            "Upload a new image from your computer/device. "
            "It will be uploaded to Cloudinary and saved to Media assets automatically."
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        image_asset_field = self.fields.get("image_asset")

        if isinstance(image_asset_field, forms.ModelChoiceField):
            image_asset_field.queryset = MediaAsset.objects.filter(
                is_active=True
            ).order_by("-created_at", "title")

        if self.image_url_field_name in self.fields:
            self.fields[self.image_url_field_name].required = False
            self.fields[self.image_url_field_name].help_text = (
                "Direct image URL fallback. "
                "Usually filled automatically from uploaded/selected image."
            )

        if self.instance and self.instance.pk and self.image_url_field_name:
            image_url = getattr(self.instance, self.image_url_field_name, "")

            if image_url and not self.initial.get("image_asset"):
                matching_asset = MediaAsset.objects.filter(
                    image_url=image_url,
                    is_active=True,
                ).first()

                if matching_asset:
                    self.initial["image_asset"] = matching_asset.pk

    def clean(self):
        cleaned_data = super().clean()

        image_asset = cleaned_data.get("image_asset")
        upload_file = cleaned_data.get("upload_file")

        if image_asset and upload_file:
            raise forms.ValidationError(
                "Choose either an image from media library or upload a new image, not both."
            )

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)

        image_asset = self.cleaned_data.get("image_asset")
        upload_file = self.cleaned_data.get("upload_file")
        alt_text = self._get_image_alt_text(instance)

        if upload_file:
            uploaded_asset = create_media_asset_from_upload(
                uploaded_file=upload_file,
                alt_text=alt_text,
            )
            setattr(instance, self.image_url_field_name, uploaded_asset.image_url)

        elif image_asset:
            setattr(instance, self.image_url_field_name, image_asset.image_url)

        elif getattr(instance, self.image_url_field_name, ""):
            get_or_create_media_asset_from_url(
                image_url=getattr(instance, self.image_url_field_name),
                alt_text=alt_text,
            )

        if commit:
            instance.save()
            self.save_m2m()

        return instance

    def _get_image_alt_text(self, instance):
        return getattr(instance, self.image_alt_text_source_field, "") or ""


class BrandForm(ImageUrlAdminFormMixin):
    image_url_field_name = "logo_url"
    image_alt_text_source_field = "name"

    class Meta:
        model = Brand
        fields = "__all__"


class CategoryForm(forms.ModelForm):
    cascade_animal_type_to_subtree = forms.BooleanField(
        required=False,
        label="Move whole subtree to this animal type",
        help_text=(
            "Use this when moving a parent category to another animal type. "
            "All child categories will get the same animal type and their levels "
            "will be recalculated."
        ),
    )

    class Meta:
        model = Category
        fields = "__all__"
        widgets = {
            "animal_type": forms.HiddenInput,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._original_animal_type_id = getattr(self.instance, "animal_type_id", None)
        self._original_parent_id = getattr(self.instance, "parent_id", None)

        if not self.instance.pk or not self.instance.children.exists():
            self.fields.pop("cascade_animal_type_to_subtree", None)

        parent_field = self.fields.get("parent")

        if not parent_field or not isinstance(
            parent_field.widget, CategoryTreeSelectWidget
        ):
            return

        animal_type_id = (
            self.data.get(self.add_prefix("animal_type"))
            or self.initial.get("animal_type")
            or getattr(self.instance, "animal_type_id", "")
        )

        animal_type_id = getattr(animal_type_id, "pk", animal_type_id)

        parent_field.widget.selected_animal_type = str(animal_type_id or "")

    def clean(self):
        cleaned = super().clean()
        parent = cleaned.get("parent")
        animal_type = cleaned.get("animal_type")

        if parent:
            animal_type = parent.animal_type
            cleaned["animal_type"] = parent.animal_type

        if (
            self.instance.pk
            and animal_type
            and animal_type.pk != self._original_animal_type_id
            and self.instance.children.exists()
            and not cleaned.get("cascade_animal_type_to_subtree")
        ):
            raise forms.ValidationError(
                "Enable subtree move to change animal type for a category with children."
            )

        node = parent
        while node:
            if node == self.instance:
                raise forms.ValidationError("Circular category hierarchy detected.")
            node = node.parent

        return cleaned

    def sync_subtree_after_save(self, category):
        if not category.pk:
            return

        cascade_animal_type = bool(
            self.cleaned_data.get("cascade_animal_type_to_subtree")
        )
        animal_type_changed = (
            self._original_animal_type_id
            and category.animal_type_id != self._original_animal_type_id
        )
        parent_changed = category.parent_id != self._original_parent_id

        if not parent_changed and not (cascade_animal_type and animal_type_changed):
            return

        descendants_to_update = []
        pending = list(
            category.children.only("id", "parent_id", "animal_type_id", "level")
        )
        levels_by_parent = {category.pk: category.level}

        while pending:
            descendant = pending.pop(0)
            expected_level = levels_by_parent[descendant.parent_id] + 1
            should_update = False

            if descendant.level != expected_level:
                descendant.level = expected_level
                should_update = True

            if (
                cascade_animal_type
                and descendant.animal_type_id != category.animal_type_id
            ):
                descendant.animal_type_id = category.animal_type_id
                should_update = True

            levels_by_parent[descendant.pk] = descendant.level

            if should_update:
                descendants_to_update.append(descendant)

            pending.extend(
                Category.objects.filter(parent=descendant).only(
                    "id",
                    "parent_id",
                    "animal_type_id",
                    "level",
                )
            )

        if descendants_to_update:
            Category.objects.bulk_update(
                descendants_to_update,
                ["animal_type", "level"],
            )


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = "__all__"
        widgets = {
            "content_blocks": JSONFormWidget(schema=PRODUCT_CONTENT_BLOCKS_SCHEMA),
        }

    def clean_category(self):
        category = self.cleaned_data.get("category")

        if not category:
            return category

        if not category.is_active:
            raise forms.ValidationError("Choose an active category.")

        if category.children.filter(is_active=True).exists():
            raise forms.ValidationError(
                "Choose a final subcategory, not a parent category."
            )

        return category


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

        if upload_file:
            upload_result = upload_image_to_cloudinary(upload_file)
            image_url = upload_result.get("secure_url") or upload_result.get("url")
            public_id = upload_result.get("public_id", "")

            if not image_url:
                raise forms.ValidationError(
                    {"upload_file": "Cloudinary did not return image URL."}
                )

            cleaned_data["image_url"] = image_url
            cleaned_data["cloudinary_public_id"] = public_id
            cleaned_data["source"] = MediaAsset.SOURCE_CLOUDINARY

            if not cleaned_data.get("title"):
                cleaned_data["title"] = upload_file.name

            return cleaned_data

        if not upload_file and not image_url:
            raise forms.ValidationError(
                "Upload image file or provide direct image URL."
            )

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)

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

    asset = MediaAssetChoiceField(
        queryset=MediaAsset.objects.none(),
        required=False,
        label="Select existing image",
        help_text="Search and choose an existing image from media library.",
        widget=MediaAssetSelectWidget(),
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

        asset_field = self.fields.get("asset")

        if isinstance(asset_field, forms.ModelChoiceField):
            asset_field.queryset = MediaAsset.objects.filter(is_active=True).order_by(
                "-created_at", "title"
            )

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
