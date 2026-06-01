from decimal import Decimal, ROUND_HALF_UP

from django import forms
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.db.models import Count, DecimalField, ExpressionWrapper, F, Q, Sum
from django.forms.models import BaseInlineFormSet
from django.utils.html import format_html
from django_jsonform.widgets import JSONFormWidget
from unfold.admin import ModelAdmin, StackedInline, TabularInline

from .models import (
    AnimalType,
    Badge,
    Brand,
    Cart,
    CartItem,
    Category,
    Customer,
    Product,
    PRODUCT_CONTENT_BLOCKS_SCHEMA,
    ProductAttribute,
    ProductAttributeValue,
    ProductImage,
    ProductReview,
    ProductVariant,
    ProductVariantAttribute,
)


def image_preview(image_url, height=60):
    if image_url:
        return format_html(
            '<img src="{}" style="height:{}px; border-radius:6px;" />',
            image_url,
            height,
        )
    return "-"


def unset_other_main_images(image):
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


def sync_product_variants_auto_badges(product):
    variants = product.variants.all().prefetch_related("badges")

    for variant in variants:
        variant.sync_auto_price_badges()


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


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = "__all__"
        widgets = {
            "content_blocks": JSONFormWidget(schema=PRODUCT_CONTENT_BLOCKS_SCHEMA),
        }


class ProductVariantForm(forms.ModelForm):
    discount_percent = forms.DecimalField(
        required=False,
        min_value=Decimal("0.01"),
        max_value=Decimal("99.99"),
        decimal_places=2,
        max_digits=5,
        label="Discount %",
        help_text=(
            "Optional. If filled, Price will be calculated from Old price. "
            "Example: old price 1000 and discount 20 means price 800."
        ),
    )

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
            "is_active": (
                "Inactive variants are hidden from API and cannot be selected "
                "by customers."
            ),
            "cost_price": (
                "Internal purchase/cost price. Customers do not see this value."
            ),
            "auto_badges_enabled": (
                "If enabled, Discount and Sale badges are managed automatically "
                "based on Old price and Price. Disable this if you want to manage "
                "variant badges fully manually."
            ),
            "badges": (
                "Manual badges for this variant. Discount/Sale can be auto-managed "
                "when Auto badges enabled is checked."
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["price"].required = False

        instance = self.instance
        if instance and instance.pk and instance.old_price and instance.price:
            if instance.old_price > instance.price:
                discount = (
                    (instance.old_price - instance.price)
                    / instance.old_price
                    * Decimal("100")
                )
                self.fields["discount_percent"].initial = discount.quantize(
                    Decimal("0.01")
                )

    def clean(self):
        cleaned_data = super().clean()

        price = cleaned_data.get("price")
        old_price = cleaned_data.get("old_price")
        discount_percent = cleaned_data.get("discount_percent")

        if discount_percent is not None:
            if not old_price:
                raise forms.ValidationError(
                    {
                        "discount_percent": (
                            "Old price is required to calculate discount."
                        )
                    }
                )

            multiplier = (Decimal("100") - discount_percent) / Decimal("100")
            cleaned_data["price"] = (old_price * multiplier).quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP,
            )
            return cleaned_data

        if price is None:
            raise forms.ValidationError(
                {"price": "Price is required if discount percent is not provided."}
            )

        return cleaned_data


class ProductVariantAttributeForm(forms.ModelForm):
    class Meta:
        model = ProductVariantAttribute
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        attribute_id = None

        if self.data:
            attribute_id = self.data.get(self.add_prefix("attribute"))

        if not attribute_id and self.instance and self.instance.pk:
            attribute_id = self.instance.attribute_id

        if attribute_id:
            self.fields["value"].queryset = ProductAttributeValue.objects.filter(
                attribute_id=attribute_id
            ).order_by("display_order", "value")
        else:
            self.fields["value"].queryset = (
                ProductAttributeValue.objects.select_related("attribute")
                .all()
                .order_by("attribute__display_order", "display_order", "value")
            )

    def clean(self):
        cleaned_data = super().clean()

        attribute = cleaned_data.get("attribute")
        value = cleaned_data.get("value")

        if attribute and value and value.attribute_id != attribute.id:
            raise forms.ValidationError(
                {"value": "Selected value does not belong to selected attribute."}
            )

        return cleaned_data


class ProductVariantAttributeInlineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()

        seen_attributes = {}

        for form in self.forms:
            if not hasattr(form, "cleaned_data"):
                continue

            cleaned_data = form.cleaned_data

            if cleaned_data.get("DELETE"):
                continue

            attribute = cleaned_data.get("attribute")

            if not attribute:
                continue

            if attribute.id in seen_attributes:
                raise forms.ValidationError(
                    (
                        f"Variant can have only one value for attribute "
                        f'"{attribute.name}". Create another variant if you need '
                        f"another {attribute.name}."
                    )
                )

            seen_attributes[attribute.id] = attribute


class ProductImageInlineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()

        main_count = 0

        for form in self.forms:
            if not hasattr(form, "cleaned_data"):
                continue

            cleaned_data = form.cleaned_data

            if cleaned_data.get("DELETE"):
                continue

            if cleaned_data.get("is_main"):
                main_count += 1

        if main_count > 1:
            raise forms.ValidationError(
                "Only one main product image is allowed for one product."
            )

    def save_new(self, form, commit=True):
        image = super().save_new(form, commit=False)
        image.variant = None
        unset_other_main_images(image)

        if commit:
            image.save()
            form.save_m2m()

        return image

    def save_existing(self, form, instance, commit=True):
        image = super().save_existing(form, instance, commit=False)
        image.variant = None
        unset_other_main_images(image)

        if commit:
            image.save()
            form.save_m2m()

        return image


class ProductVariantImageInlineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()

        main_count = 0

        for form in self.forms:
            if not hasattr(form, "cleaned_data"):
                continue

            cleaned_data = form.cleaned_data

            if cleaned_data.get("DELETE"):
                continue

            if cleaned_data.get("is_main"):
                main_count += 1

        if main_count > 1:
            raise forms.ValidationError(
                "Only one main image is allowed for one product variant."
            )

    def save_new(self, form, commit=True):
        image = super().save_new(form, commit=False)
        image.product = self.instance.product
        image.variant = self.instance
        unset_other_main_images(image)

        if commit:
            image.save()
            form.save_m2m()

        return image

    def save_existing(self, form, instance, commit=True):
        image = super().save_existing(form, instance, commit=False)
        image.product = self.instance.product
        image.variant = self.instance
        unset_other_main_images(image)

        if commit:
            image.save()
            form.save_m2m()

        return image


class ProductVariantAttributeInline(TabularInline):
    model = ProductVariantAttribute
    form = ProductVariantAttributeForm
    formset = ProductVariantAttributeInlineFormSet
    extra = 1
    autocomplete_fields = ("attribute",)
    fields = ("attribute", "value")
    ordering = ("attribute__display_order", "value__display_order")
    show_change_link = True
    verbose_name = "Variant attribute"
    verbose_name_plural = "Variant attributes"


class ProductVariantImagesInline(TabularInline):
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
    verbose_name = "Variant image"
    verbose_name_plural = "Variant images"

    def preview(self, obj):
        return image_preview(obj.image_url, height=80)

    preview.short_description = "Preview"


class ProductVariantsInline(StackedInline):
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
    ordering = ("-is_default", "price", "id")
    verbose_name = "Product variant"
    verbose_name_plural = "Product variants"

    fieldsets = (
        (
            "Variant",
            {
                "fields": (
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


class ProductImagesInline(TabularInline):
    model = ProductImage
    formset = ProductImageInlineFormSet
    fk_name = "product"
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
    verbose_name = "Base product image"
    verbose_name_plural = "Base product images"

    def get_queryset(self, request):
        return super().get_queryset(request).filter(variant__isnull=True)

    def preview(self, obj):
        return image_preview(obj.image_url, height=80)

    preview.short_description = "Preview"


class CartItemsInline(TabularInline):
    model = CartItem
    extra = 0
    autocomplete_fields = ("variant",)
    readonly_fields = ("total_price",)


@admin.register(Customer)
class CustomerAdmin(UserAdmin):
    ordering = ("-date_joined",)
    list_display = ("email", "first_name", "last_name", "is_active", "is_staff")
    search_fields = ("email", "first_name", "last_name")

    fieldsets = UserAdmin.fieldsets + (
        ("Verification", {"fields": ("email_verified",)}),
    )


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
    )
    date_hierarchy = "created_at"
    save_on_top = True
    ordering = ("-created_at",)
    inlines = (
        ProductVariantsInline,
        ProductImagesInline,
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
        sync_product_variants_auto_badges(form.instance)

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


@admin.register(ProductVariantAttribute)
class ProductVariantAttributeAdmin(ModelAdmin):
    form = ProductVariantAttributeForm

    list_display = ("variant", "attribute", "value")
    list_select_related = ("variant", "variant__product", "attribute", "value")
    autocomplete_fields = ("variant", "attribute")
    search_fields = (
        "variant__sku",
        "variant__product__name",
        "attribute__name",
        "value__value",
    )
    list_filter = ("attribute",)
    ordering = ("variant__product__name", "variant__sku", "attribute__display_order")


@admin.register(ProductAttribute)
class ProductAttributeAdmin(ModelAdmin):
    list_display = ("name", "slug", "filterable", "display_order")
    list_filter = ("filterable",)
    search_fields = ("name", "slug")
    ordering = ("display_order", "name")
    autocomplete_fields = ("categories",)
    filter_horizontal = ("categories",)


@admin.register(ProductAttributeValue)
class ProductAttributeValueAdmin(ModelAdmin):
    list_display = ("attribute", "value", "slug", "display_order")
    list_select_related = ("attribute",)
    autocomplete_fields = ("attribute",)
    search_fields = ("value", "slug", "attribute__name")
    ordering = ("attribute__name", "display_order", "value")


@admin.register(ProductImage)
class ProductImageAdmin(ModelAdmin):
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


@admin.register(ProductReview)
class ProductReviewAdmin(ModelAdmin):
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
    search_fields = ("product__name", "user__email", "title", "comment")
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
                    "product",
                    "user",
                    "rating",
                    "is_verified",
                    "is_active",
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
