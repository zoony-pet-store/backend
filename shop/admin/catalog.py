from django.contrib import admin
from django.db import transaction
from django.db.models import Count, Q
from django.utils.html import format_html
from unfold.admin import ModelAdmin

from ..models import AnimalType, Badge, Brand, Category
from .forms import BadgeForm, BrandForm, CategoryForm
from .helpers import image_preview
from .translation_inlines import (
    AnimalTypeTranslationInline,
    BadgeTranslationInline,
    CategoryTranslationInline,
)
from .widgets import CategoryTreeSelectWidget


@admin.register(AnimalType)
class AnimalTypeAdmin(ModelAdmin):
    list_display = ("name", "is_active", "category_count", "product_count")
    search_fields = ("name", "slug")
    list_filter = ("is_active",)
    ordering = ("name",)
    inlines = (AnimalTypeTranslationInline,)

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
    readonly_fields = ("image_preview",)
    inlines = (CategoryTranslationInline,)

    fieldsets = (
        (
            "Basic info",
            {
                "fields": (
                    "name",
                    "slug",
                    "description",
                    "is_active",
                    "sort_order",
                    "level",
                )
            },
        ),
        (
            "Hierarchy",
            {
                "fields": (
                    "animal_type",
                    "parent",
                    "cascade_animal_type_to_subtree",
                )
            },
        ),
        (
            "Image",
            {
                "fields": (
                    "image_preview",
                    "image_asset",
                    "upload_file",
                    "image_url",
                ),
                "description": (
                    "Choose an image from media library, upload a new image, "
                    "or provide a direct image URL fallback."
                ),
            },
        ),
    )

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

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        formfield = super().formfield_for_foreignkey(db_field, request, **kwargs)

        if db_field.name == "parent":
            formfield.widget = CategoryTreeSelectWidget(
                select_leaf_only=False,
                select_groups=True,
                animal_type_input_id="id_animal_type",
                category_queryset=formfield.queryset,
            )

        return formfield

    def save_model(self, request, obj, form, change):
        with transaction.atomic():
            super().save_model(request, obj, form, change)
            form.sync_subtree_after_save(obj)

    def product_count(self, obj):
        return obj._product_count

    product_count.short_description = "Active products"

    def image_preview(self, obj):
        return image_preview(obj.image_url, height=80)

    image_preview.short_description = "Image preview"


@admin.register(Brand)
class BrandAdmin(ModelAdmin):
    form = BrandForm

    list_display = ("name", "is_active", "product_count", "logo")
    list_filter = ("is_active",)
    search_fields = ("name", "slug")
    ordering = ("name",)
    readonly_fields = ("logo_preview",)

    fieldsets = (
        (
            "Basic info",
            {
                "fields": (
                    "name",
                    "slug",
                    "description",
                    "is_active",
                )
            },
        ),
        (
            "Logo",
            {
                "fields": (
                    "logo_preview",
                    "logo_url",
                    "image_asset",
                    "upload_file",
                ),
                "description": (
                    "Use direct logo URL, choose an image from media library, "
                    "or upload a new image from your computer."
                ),
            },
        ),
    )

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

    def logo_preview(self, obj):
        return image_preview(obj.logo_url, height=80)

    logo_preview.short_description = "Logo preview"


@admin.register(Badge)
class BadgeAdmin(ModelAdmin):
    form = BadgeForm
    list_display = ("label", "slug", "is_active", "color_preview", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "label", "slug")
    ordering = ("label",)
    inlines = (BadgeTranslationInline,)

    def color_preview(self, obj):
        return format_html(
            '<span style="display:inline-block; width:24px; height:24px; '
            'border-radius:6px; background:{}; border:1px solid #ccc;"></span>',
            obj.background_color,
        )

    color_preview.short_description = "Color"
