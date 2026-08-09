from django.contrib import admin
from django.db.models import DecimalField, ExpressionWrapper, F, Sum
from unfold.admin import ModelAdmin

from ..models import Cart, CartItem
from .inlines import CartItemsInline


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
