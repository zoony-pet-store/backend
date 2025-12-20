from django.contrib import admin
from .models import (
    Product,
    Category,
    AnimalType,
    Brand,
    ProductVariant,
    ProductImage,
    ProductReview,
)


@admin.register(AnimalType)
class AnimalTypeAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "is_active"]
    prepopulated_fields = {"slug": ("name",)}
    list_filter = ["is_active"]


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "animal_type", "parent", "level", "is_active"]
    list_filter = ["animal_type", "is_active", "parent"]
    search_fields = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}
    list_select_related = ["animal_type", "parent"]


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "is_active", "product_count"]
    list_filter = ["is_active"]
    search_fields = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}

    def product_count(self, obj):
        return obj.products.count()

    product_count.short_description = "Products"


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "brand",
        "category",
        "price_range",
        "rating",
        "review_count",
        "is_featured",
        "is_active",
    ]
    list_filter = [
        "is_active",
        "is_featured",
        "brand",
        "category__animal_type",
        "category",
    ]
    search_fields = ["name", "description", "brand__name"]
    prepopulated_fields = {"slug": ("name",)}
    list_select_related = ["brand", "category"]
    readonly_fields = ["rating", "review_count", "created_at", "updated_at"]

    fieldsets = (
        (
            "Basic Info",
            {
                "fields": (
                    "name",
                    "slug",
                    "brand",
                    "category",
                    "description",
                    "short_description",
                )
            },
        ),
        (
            "Pricing & Status",
            {"fields": ("is_featured", "is_active", "rating", "review_count")},
        ),
        (
            "SEO",
            {"fields": ("meta_title", "meta_description"), "classes": ("collapse",)},
        ),
        (
            "Additional Info",
            {
                "fields": (
                    "composition",
                    "nutritional_analysis",
                    "feeding_guidelines",
                    "ingredients",
                    "nutritional_value",
                    "feeding_table",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def price_range(self, obj):
        variants = obj.variants.filter(is_active=True)
        if variants.exists():
            prices = [v.price for v in variants]
            return f"${min(prices)} - ${max(prices)}"
        return "No variants"

    price_range.short_description = "Price Range"

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("variants")
