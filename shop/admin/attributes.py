from django.contrib import admin
from unfold.admin import ModelAdmin

from ..models import ProductAttribute, ProductAttributeValue, ProductVariantAttribute
from .forms import (
    ProductAttributeAdminForm,
    ProductAttributeValueAdminForm,
    ProductVariantAttributeForm,
)


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
