from django import forms
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.db.models import (
    Count,
    DecimalField,
    ExpressionWrapper,
    F,
    Q,
    Sum,
)
from django.forms.models import BaseInlineFormSet
from django.utils.html import format_html

from .models import (
    AnimalType,
    Badge,
    Brand,
    Cart,
    CartItem,
    Category,
    Customer,
    Product,
    ProductAttribute,
    ProductAttributeValue,
    ProductImage,
    ProductReview,
    ProductVariant,
    ProductVariantAttribute,
)


# ======================================================
# UTILITIES
# ======================================================


def image_preview(image_url, height=60):
    if image_url:
        return format_html(
            '<img src="{}" style="height:{}px; border-radius:6px;" />',
            image_url,
            height,
        )

    return "-"


def unset_other_main_images(image):
    """
    Keep only one main product image and one main image per variant.

    Product-level main image:
    product=X, variant=None, is_main=True

    Variant-level main image:
    product=X, variant=Y, is_main=True
    """
    if not image.is_main or not image.product_id:
        return

    if image.variant_id:
        ProductImage.objects.filter(
            product=image.product,
            variant=image.variant,
            is_main=True,
        ).exclude(pk=image.pk).update(is_main=False)
    else:
        ProductImage.objects.filter(
            product=image.product,
            variant__isnull=True,
            is_main=True,
        ).exclude(pk=image.pk).update(is_main=False)


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
                raise forms.ValidationError("Circular category hierarchy detected.")
            node = node.parent

        return cleaned


class ProductVariantForm(forms.ModelForm):
    class Meta:
        model = ProductVariant
        fields = "__all__"
        help_texts = {
            "sku": (
                "Optional. Leave empty to auto-generate SKU. "
                "Fill manually if you have supplier/internal SKU."
            ),
            "is_default": (
                "Default variant is used for product card price/image "
                "before customer selects another option."
            ),
        }


# ======================================================
# INLINE FORMSETS
# ======================================================


class ProductImageInlineFormSet(BaseInlineFormSet):
    """
    Inline for images inside Product admin.

    Product is set automatically by Django inline.
    """

    def save_new(self, form, commit=True):
        image = super().save_new(form, commit=False)
        unset_other_main_images(image)

        if commit:
            image.save()
            form.save_m2m()

        return image

    def save_existing(self, form, instance, commit=True):
        image = super().save_existing(form, instance, commit=False)
        unset_other_main_images(image)

        if commit:
            image.save()
            form.save_m2m()

        return image


class ProductVariantImageInlineFormSet(BaseInlineFormSet):
    """
    Inline for images inside ProductVariant admin.

    ProductImage has both product and variant.
    When editing image from variant page, product must be copied
    from current variant automatically.
    """

    def save_new(self, form, commit=True):
        image = super().save_new(form, commit=False)
        image.product = self.instance.product
        unset_other_main_images(image)

        if commit:
            image.save()
            form.save_m2m()

        return image

    def save_existing(self, form, instance, commit=True):
        image = super().save_existing(form, instance, commit=False)
        image.product = self.instance.product
        unset_other_main_images(image)

        if commit:
            image.save()
            form.save_m2m()

        return image


# ======================================================
# INLINES
# ======================================================


class ProductVariantAttributeInline(admin.TabularInline):
    """
    Attribute rows for concrete variant.

    Example:
    Attribute: Size  -> Value: M
    Attribute: Color -> Value: Pink

    This replaces the old checkbox-based attributes field.
    """

    model = ProductVariantAttribute
    extra = 1
    autocomplete_fields = ("attribute", "value")
    fields = ("attribute", "value")
    ordering = ("attribute__display_order", "value__display_order")
    show_change_link = True


class ProductImagesInline(admin.TabularInline):
    """
    Product-level images.

    You may optionally select variant here too.
    If variant is empty, image is common product image.
    If variant is selected, image belongs to that variant.
    """

    model = ProductImage
    formset = ProductImageInlineFormSet
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
        return image_preview(obj.image_url, height=80)

    preview.short_description = "Preview"


class ProductVariantImagesInline(admin.TabularInline):
    """
    Variant-specific images.

    Used on ProductVariant page.
    Product is set automatically from current variant.
    """

    model = ProductImage
    formset = ProductVariantImageInlineFormSet
    fk_name = "variant"
    extra = 1
    fields = (
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
        return image_preview(obj.image_url, height=80)

    preview.short_description = "Preview"


class ProductVariantsInline(admin.StackedInline):
    """
    Product variants shown inside Product admin.

    Django admin does not support nested inlines by default,
    so attributes are edited by opening the variant change page.
    """

    model = ProductVariant
    form = ProductVariantForm
    extra = 0
    show_change_link = True
    autocomplete_fields = ("badges",)
    readonly_fields = (
        "has_discount_display",
        "discount_percentage_display",
        "created_at",
        "updated_at",
    )

    fieldsets = (
        (
            "Variant",
            {
                "fields": (
                    ("sku", "is_active", "is_default"),
                    ("display_order", "stock", "weight"),
                    ("price", "old_price", "cost_price"),
                    ("has_discount_display", "discount_percentage_display"),
                    "badges",
                    "short_description",
                    "description",
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
                    (
                        "display_price_display",
                        "min_price_display",
                        "max_price_display",
                    ),
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
        "is_default",
        "has_discount_display",
        "discount_percentage_display",
        "is_active",
        "display_order",
    )
    list_select_related = ("product", "product__brand", "product__category")
    list_filter = ("is_active", "is_default", "product__brand", "product__category")
    autocomplete_fields = ("product", "badges")
    search_fields = ("sku", "product__name", "product__brand__name")
    readonly_fields = (
        "has_discount_display",
        "discount_percentage_display",
        "created_at",
        "updated_at",
    )
    ordering = ("product", "display_order", "price")
    inlines = (ProductVariantAttributeInline, ProductVariantImagesInline)

    fieldsets = (
        (
            "Basic info",
            {
                "fields": (
                    "product",
                    ("sku", "is_active", "is_default"),
                    ("display_order", "stock", "weight"),
                    ("price", "old_price", "cost_price"),
                    ("has_discount_display", "discount_percentage_display"),
                    "badges",
                )
            },
        ),
        (
            "Variant content overrides",
            {
                "fields": (
                    "short_description",
                    "description",
                ),
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


# ======================================================
# VARIANT ATTRIBUTES
# ======================================================


@admin.register(ProductVariantAttribute)
class ProductVariantAttributeAdmin(admin.ModelAdmin):
    list_display = ("variant", "attribute", "value")
    list_select_related = (
        "variant",
        "variant__product",
        "attribute",
        "value",
    )
    autocomplete_fields = ("variant", "attribute", "value")
    search_fields = (
        "variant__sku",
        "variant__product__name",
        "attribute__name",
        "value__value",
    )
    ordering = ("variant__product__name", "variant__sku", "attribute__display_order")


# ======================================================
# ATTRIBUTES
# ======================================================


@admin.register(ProductAttribute)
class ProductAttributeAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "filterable", "display_order")
    list_filter = ("filterable",)
    search_fields = ("name", "slug")
    ordering = ("display_order", "name")
    autocomplete_fields = ("categories",)
    filter_horizontal = ("categories",)


@admin.register(ProductAttributeValue)
class ProductAttributeValueAdmin(admin.ModelAdmin):
    list_display = ("attribute", "value", "slug", "display_order")
    list_select_related = ("attribute",)
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
    list_select_related = ("product", "variant")
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
        return image_preview(obj.image_url, height=60)

    preview.short_description = "Preview"

    def save_model(self, request, obj, form, change):
        unset_other_main_images(obj)
        super().save_model(request, obj, form, change)


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
