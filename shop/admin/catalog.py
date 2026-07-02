from django.contrib import admin
from django.db.models import Count, Q
from django.utils.html import format_html
from unfold.admin import ModelAdmin

from ..models import AnimalType, Badge, Brand, Category
from .forms import CategoryForm
from .helpers import image_preview


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
