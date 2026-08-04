from urllib.parse import urlencode

from django.urls import reverse
from django.utils.html import format_html
from unfold.admin import StackedInline, TabularInline

from ..models import CartItem, ProductImage, ProductVariant, ProductVariantAttribute
from .forms import ProductImageInlineAdminForm, ProductVariantAttributeForm
from .formsets import (
    ProductImageInlineFormSet,
    ProductVariantAttributeInlineFormSet,
    ProductVariantImageInlineFormSet,
    ProductVariantImagesOnProductInlineFormSet,
    ProductVariantSummaryInlineFormSet,
)
from .helpers import image_preview


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

    def get_initial_attribute_data(self, request, obj=None):
        product_id = self.get_product_id_for_initial_structure(request, obj)

        if not product_id:
            return []

        from shop.services.variant_attribute_sync import (
            get_template_attribute_items_for_product,
        )

        template_items = get_template_attribute_items_for_product(
            product_id=product_id,
            exclude_variant_id=obj.id if obj and obj.pk else None,
        )

        return [
            {
                "attribute": item.attribute_id,
                "value": item.value_id,
                "value_numeric": item.value_numeric,
                "unit": item.unit,
            }
            for item in template_items
        ]

    def get_extra(self, request, obj=None, **kwargs):
        if obj and obj.pk:
            return 1

        initial_attribute_data = self.get_initial_attribute_data(request, obj)

        return len(initial_attribute_data) or 1

    def get_formset(self, request, obj=None, **kwargs):
        formset_class = super().get_formset(request, obj, **kwargs)
        initial_attribute_data = self.get_initial_attribute_data(request, obj)

        if obj and obj.pk:
            return formset_class

        class ProductVariantAttributeInitialFormSet(formset_class):
            def __init__(self, *args, **formset_kwargs):
                if initial_attribute_data:
                    formset_kwargs.setdefault("initial", initial_attribute_data)

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
    show_change_link = False

    fields = (
        "variant_preview",
        "sku",
        "attributes_summary",
        "price",
        "old_price",
        "stock",
        "is_active_display",
        "is_default",
        "edit_variant_modal",
    )

    readonly_fields = (
        "variant_preview",
        "sku",
        "attributes_summary",
        "price",
        "old_price",
        "stock",
        "is_active_display",
        "edit_variant_modal",
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

    def edit_variant_modal(self, obj):
        if not obj or not obj.pk:
            return "—"

        base_url = reverse(
            "admin:shop_productvariant_change",
            args=[obj.pk],
        )
        regular_url = base_url
        modal_url = f"{base_url}?{urlencode({'_modal': '1'})}"

        return format_html(
            '<a href="{}" '
            'class="button js-related-object-modal" '
            'data-modal-url="{}" '
            'data-modal-title="Edit variant {}" '
            'aria-haspopup="dialog">'
            "Edit"
            "</a>",
            regular_url,
            modal_url,
            obj.sku or obj.pk,
        )

    edit_variant_modal.short_description = "Actions"


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
    autocomplete_fields = ("variant",)
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
