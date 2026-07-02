from urllib.parse import urlencode

from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from unfold.admin import ModelAdmin

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
