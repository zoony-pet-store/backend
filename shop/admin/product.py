from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from unfold.admin import ModelAdmin

from .modal import RelatedObjectModalAdminMixin
from ..models import Product, ProductVariant
from .forms import ProductForm, ProductVariantForm
from .helpers import sync_product_variants_auto_badges
from .inlines import (
    ProductImagesInline,
    ProductVariantAttributeInline,
    ProductVariantImagesInline,
    ProductVariantImagesOnProductInline,
    ProductVariantsInline,
)
from .translation_inlines import (
    ProductTranslationInline,
    ProductVariantTranslationInline,
)
from .widgets import CategoryTreeSelectWidget


@admin.register(Product)
class ProductAdmin(ModelAdmin):
    form = ProductForm

    change_form_outer_after_template = "admin/shop/product/related_object_modal.html"
    warn_unsaved_form = True

    class Media:
        css = {
            "all": (
                "shop/admin/css/related_object_modal.css",
                "shop/admin/css/content_blocks_editor.css",
            ),
        }
        js = (
            "shop/admin/js/related_object_modal.js",
            "shop/admin/js/content_blocks_editor.js",
        )

    list_display = (
        "name",
        "brand",
        "category_display",
        "is_active",
        "rating",
        "review_count",
        "display_price_display",
        "min_price_display",
        "max_price_display",
        "in_stock_display",
        "created_at",
    )
    list_select_related = (
        "brand",
        "category",
        "category__animal_type",
        "category__parent",
        "category__parent__parent",
        "category__parent__parent__parent",
    )
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
    autocomplete_fields = ("brand", "badges")
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
        ProductTranslationInline,
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
            .select_related(
                "brand",
                "category",
                "category__animal_type",
                "category__parent",
                "category__parent__parent",
                "category__parent__parent__parent",
            )
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

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        formfield = super().formfield_for_foreignkey(db_field, request, **kwargs)

        if db_field.name == "category":
            formfield.widget = CategoryTreeSelectWidget(
                select_leaf_only=True,
                category_queryset=formfield.queryset,
            )

        return formfield

    @admin.display(description="Category", ordering="category__name")
    def category_display(self, obj):
        return f"{obj.category.name} ({obj.category.animal_type.name})"

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

    @admin.display(description="Add variant")
    def add_variant_link(self, obj):
        if not obj or not obj.pk:
            return "Save product before adding variants."

        base_url = reverse("admin:shop_productvariant_add")

        regular_url = f"{base_url}?" f"{urlencode({'product': str(obj.pk)})}"
        modal_url = (
            f"{base_url}?"
            f"{urlencode({
                'product': str(obj.pk),
                '_modal': '1',
            })}"
        )

        return format_html(
            '<a href="{}" '
            'class="button js-related-object-modal" '
            'data-modal-url="{}" '
            'data-modal-title="Add product variant" '
            'aria-haspopup="dialog">'
            "+ Add variant for this product"
            "</a>",
            regular_url,
            modal_url,
        )

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
class ProductVariantAdmin(
    RelatedObjectModalAdminMixin,
    ModelAdmin,
):
    form = ProductVariantForm

    warn_unsaved_form = True

    class Media:
        js = ("shop/admin/js/related_object_modal_child.js",)

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
        ProductVariantTranslationInline,
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

    def get_form(self, request, obj=None, change=False, **kwargs):
        form_class = super().get_form(
            request,
            obj=obj,
            change=change,
            **kwargs,
        )

        if not self.is_related_modal_request(request):
            return form_class

        product_id = (
            getattr(obj, "product_id", None)
            or request.GET.get("product")
            or request.POST.get("product")
        )

        if not product_id:
            return form_class

        class ModalProductVariantForm(form_class):
            def __init__(self, *args, **form_kwargs):
                initial = dict(form_kwargs.get("initial") or {})
                initial.setdefault("product", product_id)
                form_kwargs["initial"] = initial

                super().__init__(*args, **form_kwargs)

                product_field = self.fields.get("product")

                if product_field is not None:
                    product_field.queryset = product_field.queryset.filter(
                        pk=product_id
                    )
                    product_field.disabled = True
                    product_field.help_text = (
                        "The product is fixed because this variant "
                        "was opened from its product page."
                    )

        return ModalProductVariantForm

    def get_related_modal_payload(self, obj, *, action):
        payload = super().get_related_modal_payload(
            obj,
            action=action,
        )
        payload.update(
            {
                "productId": str(obj.product_id),
                "sku": obj.sku or "",
                "message": (f"Variant {obj.sku or obj.pk} saved successfully."),
            }
        )
        return payload

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

    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        product_id = request.GET.get("product")

        if product_id:
            initial["product"] = product_id

        return initial

    def response_add(self, request, obj, post_url_continue=None):
        response = super().response_add(request, obj, post_url_continue)
        return self._preserve_product_for_add_another(request, response, obj)

    def response_change(self, request, obj):
        response = super().response_change(request, obj)
        return self._preserve_product_for_add_another(request, response, obj)

    def _preserve_product_for_add_another(self, request, response, obj):
        if "_addanother" not in request.POST:
            return response

        if not getattr(obj, "product_id", None):
            return response

        if not response.has_header("Location"):
            return response

        response["Location"] = self._add_query_param(
            response["Location"],
            "product",
            str(obj.product_id),
        )
        return response

    @staticmethod
    def _add_query_param(url, key, value):
        parts = urlsplit(url)
        query_params = parse_qsl(parts.query, keep_blank_values=True)

        query_params = [
            (param_key, param_value)
            for param_key, param_value in query_params
            if param_key != key
        ]

        query_params.append((key, value))

        return urlunsplit(
            (
                parts.scheme,
                parts.netloc,
                parts.path,
                urlencode(query_params),
                parts.fragment,
            )
        )
