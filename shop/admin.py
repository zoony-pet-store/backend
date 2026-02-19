from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.utils.html import format_html
from django import forms
import random
import string

from .models import (
    Customer,
    AnimalType,
    Category,
    Brand,
    Product,
    ProductAttribute,
    ProductAttributeValue,
    ProductVariant,
    ProductImage,
    ProductReview,
    Cart,
    CartItem,
)

# ======================================================
# UTILITIES
# ======================================================

def generate_random_sku():
    """Generate UNIQUE SKU (collision-safe)."""
    prefix = "PROD-"
    chars = string.ascii_uppercase + string.digits

    while True:
        suffix = "".join(random.choices(chars, k=8))
        sku = f"{prefix}{suffix}"
        if not ProductVariant.objects.filter(sku=sku).exists():
            return sku


# ======================================================
# FORMS
# ======================================================

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = "__all__"

    def clean(self):
        cleaned = super().clean()
        parent = cleaned.get("parent")

        # Prevent circular hierarchy
        node = parent
        while node:
            if node == self.instance:
                raise forms.ValidationError("Circular category hierarchy detected")
            node = node.parent

        return cleaned


class ProductVariantForm(forms.ModelForm):
    class Meta:
        model = ProductVariant
        fields = "__all__"
        widgets = {"attributes": forms.CheckboxSelectMultiple}


# ======================================================
# INLINES
# ======================================================

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    autocomplete_fields = ("variant",)
    fields = ("image_url", "alt_text", "is_main", "display_order", "preview")
    readonly_fields = ("preview",)

    def preview(self, obj):
        if obj.image_url:
            return format_html('<img src="{}" style="max-height:80px;"/>', obj.image_url)
        return "-"


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    form = ProductVariantForm
    extra = 0
    autocomplete_fields = ("product",)


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    autocomplete_fields = ("variant",)
    readonly_fields = ("total_price",)


# ======================================================
# CUSTOMER
# ======================================================

@admin.register(Customer)
class CustomerAdmin(UserAdmin):
    ordering = ("-date_joined",)
    list_display = ("email", "first_name", "last_name", "is_active", "is_staff")
    search_fields = ("email", "first_name", "last_name")


# ======================================================
# ANIMAL TYPE
# ======================================================

@admin.register(AnimalType)
class AnimalTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "category_count", "product_count")

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            _category_count=Count("categories", filter=Q(categories__is_active=True)),
            _product_count=Count("categories__products", filter=Q(categories__products__is_active=True)),
        )

    def category_count(self, obj):
        return obj._category_count

    def product_count(self, obj):
        return obj._product_count


# ======================================================
# CATEGORY
# ======================================================

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    form = CategoryForm
    list_display = ("name", "animal_type", "parent", "is_active", "product_count")
    list_select_related = ("animal_type", "parent")

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            _product_count=Count("products", filter=Q(products__is_active=True))
        )

    def product_count(self, obj):
        return obj._product_count


# ======================================================
# BRAND
# ======================================================

@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "product_count", "logo")

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            _product_count=Count("products", filter=Q(products__is_active=True))
        )

    def product_count(self, obj):
        return obj._product_count

    def logo(self, obj):
        if obj.logo_url:
            return format_html('<img src="{}" style="height:40px"/>', obj.logo_url)
        return "-"


# ======================================================
# PRODUCT
# ======================================================

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "brand", "category", "is_active", "created_at")
    list_select_related = ("brand", "category", "category__animal_type")

    inlines = (ProductVariantInline, ProductImageInline)

    def save_model(self, request, obj, form, change):
        """Atomic creation of base variant."""
        with transaction.atomic():
            super().save_model(request, obj, form, change)

            if not obj.variants.select_for_update().exists():
                ProductVariant.objects.create(
                    product=obj,
                    sku=generate_random_sku(),
                    price=0,
                    stock=0,
                )


# ======================================================
# PRODUCT VARIANT
# ======================================================

@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ("sku", "product", "price", "stock", "is_active")
    list_select_related = ("product", "product__brand")
    autocomplete_fields = ("product",)

    def save_model(self, request, obj, form, change):
        if not obj.sku:
            obj.sku = generate_random_sku()
        super().save_model(request, obj, form, change)


# ======================================================
# ATTRIBUTES
# ======================================================

@admin.register(ProductAttribute)
class ProductAttributeAdmin(admin.ModelAdmin):
    list_display = ("name", "filterable", "display_order")


@admin.register(ProductAttributeValue)
class ProductAttributeValueAdmin(admin.ModelAdmin):
    list_display = ("attribute", "value", "display_order")
    autocomplete_fields = ("attribute",)


# ======================================================
# IMAGES
# ======================================================

@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ("product", "is_main", "display_order", "preview")
    autocomplete_fields = ("product", "variant")

    def preview(self, obj):
        if obj.image_url:
            return format_html('<img src="{}" style="height:50px"/>', obj.image_url)
        return "-"


# ======================================================
# REVIEWS
# ======================================================

@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ("product", "user", "rating", "is_active", "created_at")
    autocomplete_fields = ("product", "user")


# ======================================================
# CART
# ======================================================

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("user", "total_items", "total_price", "created_at")
    inlines = (CartItemInline,)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user").annotate(
            _items_sum=Sum("items__quantity"),
            _price_sum=Sum("items__total_price"),
        )

    def total_items(self, obj):
        return obj._items_sum or 0

    def total_price(self, obj):
        return obj._price_sum or 0


# ======================================================
# CART ITEM
# ======================================================

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ("cart", "variant", "quantity", "added_at")
    autocomplete_fields = ("cart", "variant")
