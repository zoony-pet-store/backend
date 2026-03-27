from django import forms
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.db import transaction
from django.db.models import (
    Count,
    Q,
    Sum,
    F,
    DecimalField,
    ExpressionWrapper,
)
from django.utils.html import format_html
import random
import string

from .models import (
    Customer,
    AnimalType,
    Category,
    Brand,
    Badge,
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


class ProductImagesInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    autocomplete_fields = ("variant",)
    fields = (
        "variant",
        "image_url",
        "alt_text",
        "is_main",
        "display_order",
        "cloudinary_public_id",
        "preview",
    )
    readonly_fields = ("cloudinary_public_id", "preview")
    ordering = ("display_order", "id")
    show_change_link = True

    def preview(self, obj):
        if obj.image_url:
            return format_html(
                '<img src="{}" style="max-height:80px; border-radius:6px;" />',
                obj.image_url,
            )
        return "-"

    preview.short_description = "Preview"


class ProductVariantsInline(admin.StackedInline):
    model = ProductVariant
    form = ProductVariantForm
    extra = 0
    show_change_link = True
    readonly_fields = ("discount_percentage_display",)

    fieldsets = (
        (
            "Variant",
            {
                "fields": (
                    ("sku", "is_active"),
                    ("price", "old_price", "cost_price"),
                    ("stock", "weight"),
                    ("has_discount", "discount_percentage_display"),
                    "attributes",
                )
            },
        ),
    )

    def discount_percentage_display(self, obj):
        if not obj.pk:
            return "-"
        return f"{obj.discount_percentage}%"

    discount_percentage_display.short_description = "Discount %"


class CartItemsInline(admin.TabularInline):
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

    fieldsets = UserAdmin.fieldsets + (
        ("Verification", {"fields": ("email_verified",)}),
    )


# ======================================================
# ANIMAL TYPE
# ======================================================


@admin.register(AnimalType)
class AnimalTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "category_count", "product_count")
    search_fields = ("name",)
    list_filter = ("is_active",)

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .annotate(
                _category_count=Count(
                    "categories", filter=Q(categories__is_active=True)
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


# ======================================================
# CATEGORY
# ======================================================


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
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

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .annotate(
                _product_count=Count("products", filter=Q(products__is_active=True))
            )
        )

    def product_count(self, obj):
        return obj._product_count

    product_count.short_description = "Active products"


# ======================================================
# BRAND
# ======================================================


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "product_count", "logo")
    list_filter = ("is_active",)
    search_fields = ("name", "slug")
    ordering = ("name",)

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .annotate(
                _product_count=Count("products", filter=Q(products__is_active=True))
            )
        )

    def product_count(self, obj):
        return obj._product_count

    product_count.short_description = "Active products"

    def logo(self, obj):
        if obj.logo_url:
            return format_html('<img src="{}" style="height:40px" />', obj.logo_url)
        return "-"

    logo.short_description = "Logo"


# ======================================================
# BADGE
# ======================================================


@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
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


# ======================================================
# PRODUCT
# ======================================================


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "brand",
        "category",
        "is_active",
        "rating",
        "review_count",
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
        "min_price_display",
        "max_price_display",
        "in_stock_display",
    )
    date_hierarchy = "created_at"
    save_on_top = True
    ordering = ("-created_at",)
    inlines = (ProductVariantsInline, ProductImagesInline)

    fieldsets = (
        (
            "Basic info",
            {
                "fields": (
                    ("name", "slug", "is_active"),
                    ("brand", "category"),
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
                    ("rating", "review_count"),
                    ("min_price_display", "max_price_display"),
                    ("in_stock_display",),
                    "main_image",
                )
            },
        ),
        (
            "Content",
            {
                "fields": (
                    "composition",
                    "ingredients",
                    "nutritional_analysis",
                    "feeding_guidelines",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Structured data",
            {
                "fields": ("nutritional_value", "feeding_table"),
                "classes": ("collapse",),
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
    )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("brand", "category", "category__animal_type")
            .prefetch_related("variants", "badges")
        )

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

    def save_model(self, request, obj, form, change):
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
    list_display = (
        "sku",
        "product",
        "price",
        "old_price",
        "cost_price",
        "stock",
        "has_discount",
        "discount_percentage_display",
        "is_active",
    )
    list_select_related = ("product", "product__brand")
    list_filter = ("is_active", "has_discount", "product__brand")
    autocomplete_fields = ("product",)
    search_fields = ("sku", "product__name", "product__brand__name")
    readonly_fields = ("discount_percentage_display", "created_at", "updated_at")
    ordering = ("product", "price")

    fieldsets = (
        (
            "Basic info",
            {
                "fields": (
                    "product",
                    ("sku", "is_active"),
                    ("price", "old_price", "cost_price"),
                    ("stock", "weight"),
                    ("has_discount", "discount_percentage_display"),
                    "attributes",
                )
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

    def discount_percentage_display(self, obj):
        if not obj.pk:
            return "-"
        return f"{obj.discount_percentage}%"

    discount_percentage_display.short_description = "Discount %"

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
    list_filter = ("filterable",)
    search_fields = ("name", "slug")
    ordering = ("display_order", "name")


@admin.register(ProductAttributeValue)
class ProductAttributeValueAdmin(admin.ModelAdmin):
    list_display = ("attribute", "value", "display_order")
    autocomplete_fields = ("attribute",)
    search_fields = ("value", "slug", "attribute__name")
    ordering = ("attribute__name", "display_order", "value")


# ======================================================
# IMAGES
# ======================================================


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = (
        "product",
        "variant",
        "is_main",
        "display_order",
        "cloudinary_public_id",
        "preview",
    )
    list_filter = ("is_main",)
    autocomplete_fields = ("product", "variant")
    search_fields = ("product__name", "variant__sku", "alt_text")
    readonly_fields = ("preview",)
    fields = (
        "product",
        "variant",
        "image_url",
        "alt_text",
        "is_main",
        "display_order",
        "cloudinary_public_id",
        "preview",
    )
    ordering = ("product", "display_order", "id")

    def preview(self, obj):
        if obj.image_url:
            return format_html(
                '<img src="{}" style="height:60px; border-radius:6px;" />',
                obj.image_url,
            )
        return "-"

    preview.short_description = "Preview"


# ======================================================
# REVIEWS
# ======================================================


@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display = (
        "product",
        "user",
        "rating",
        "is_verified",
        "is_active",
        "created_at",
    )
    list_select_related = ("product", "user")
    list_filter = ("is_active", "is_verified", "rating", "created_at")
    search_fields = (
        "product__name",
        "user__email",
        "title",
        "comment",
    )
    autocomplete_fields = ("product", "user")
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    actions = ("activate_reviews", "deactivate_reviews")

    fieldsets = (
        (
            "Review",
            {
                "fields": (
                    ("product", "user"),
                    ("rating", "is_verified", "is_active"),
                    "title",
                    "comment",
                )
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

    @admin.action(description="Activate selected reviews")
    def activate_reviews(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(
            request,
            f"{updated} review(s) activated.",
            level=messages.SUCCESS,
        )

    @admin.action(description="Deactivate selected reviews")
    def deactivate_reviews(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(
            request,
            f"{updated} review(s) deactivated.",
            level=messages.WARNING,
        )


# ======================================================
# CART
# ======================================================


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
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


# ======================================================
# CART ITEM
# ======================================================


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ("cart", "variant", "quantity", "total_price", "added_at")
    autocomplete_fields = ("cart", "variant")
    search_fields = ("cart__user__email", "variant__sku", "variant__product__name")
    ordering = ("-added_at",)
