from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
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


# ========== CUSTOM ADMIN FORMS ==========
class CategoryForm(forms.ModelForm):
    """Form for Category model with custom validation"""

    class Meta:
        model = Category
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        parent = cleaned_data.get('parent')

        if parent and parent.pk == self.instance.pk:
            raise ValidationError('Category cannot be its own parent')

        return cleaned_data


class ProductVariantForm(forms.ModelForm):
    """Form for ProductVariant model"""

    class Meta:
        model = ProductVariant
        fields = '__all__'
        widgets = {
            'attributes': forms.CheckboxSelectMultiple,
        }


class ProductForm(forms.ModelForm):
    """Form for Product model"""

    class Meta:
        model = Product
        fields = '__all__'
        widgets = {
            'short_description': forms.Textarea(attrs={'rows': 3}),
            'description': forms.Textarea(attrs={'rows': 5}),
            'nutritional_value': forms.Textarea(attrs={'rows': 3}),
            'feeding_table': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Hide deprecated main_image field
        if 'main_image' in self.fields:
            self.fields['main_image'].help_text = _('Deprecated. Use Product Images below.')
            self.fields['main_image'].required = False


# ========== INLINE ADMIN CLASSES ==========
class ProductImageInline(admin.TabularInline):
    """Inline for ProductImage model"""

    model = ProductImage
    extra = 1
    fields = ('image_url', 'alt_text', 'is_main', 'display_order', 'image_preview')
    readonly_fields = ('image_preview',)

    def image_preview(self, obj):
        """Return HTML for image preview"""
        if obj.image_url:
            return format_html('<img src="{}" style="max-height: 100px; max-width: 100px;" />', obj.image_url)
        return "-"

    image_preview.short_description = 'Preview'


class ProductVariantInline(admin.TabularInline):
    """Inline for ProductVariant model"""

    model = ProductVariant
    form = ProductVariantForm
    extra = 0
    fields = ('sku', 'price', 'old_price', 'stock', 'is_active', 'attributes_display', 'has_discount',
              'discount_percentage')
    readonly_fields = ('attributes_display', 'discount_percentage')

    def attributes_display(self, obj):
        """Return comma-separated list of attribute values"""
        return ", ".join([str(attr) for attr in obj.attributes.all()[:3]])

    attributes_display.short_description = 'Attributes'


class ProductReviewInline(admin.TabularInline):
    """Inline for ProductReview model"""

    model = ProductReview
    extra = 0
    fields = ('user', 'rating', 'title', 'is_verified', 'is_active', 'created_at')
    readonly_fields = ('created_at',)
    can_delete = True


class CartItemInline(admin.TabularInline):
    """Inline for CartItem model"""

    model = CartItem
    extra = 0
    fields = ('variant', 'quantity', 'total_price')
    readonly_fields = ('total_price',)


# ========== CUSTOM FILTERS ==========
class InStockFilter(admin.SimpleListFilter):
    """Filter for product stock status"""

    title = _('Stock status')
    parameter_name = 'stock_status'

    def lookups(self, request, model_admin):
        return (
            ('in_stock', _('In stock')),
            ('out_of_stock', _('Out of stock')),
            ('low_stock', _('Low stock (< 10)')),
        )

    def queryset(self, request, queryset):
        if self.value() == 'in_stock':
            return queryset.filter(variants__stock__gt=0).distinct()
        elif self.value() == 'out_of_stock':
            return queryset.filter(variants__stock=0).distinct()
        elif self.value() == 'low_stock':
            return queryset.filter(variants__stock__lt=10, variants__stock__gt=0).distinct()
        return queryset


class HasDiscountFilter(admin.SimpleListFilter):
    """Filter for product discount status"""

    title = _('Discount status')
    parameter_name = 'discount_status'

    def lookups(self, request, model_admin):
        return (
            ('has_discount', _('Has discount')),
            ('no_discount', _('No discount')),
        )

    def queryset(self, request, queryset):
        if self.value() == 'has_discount':
            return queryset.filter(variants__has_discount=True).distinct()
        elif self.value() == 'no_discount':
            return queryset.filter(variants__has_discount=False).distinct()
        return queryset


# ========== CUSTOM ACTIONS ==========
def generate_random_sku():
    """Generate a random SKU for products"""
    prefix = 'PROD-'
    chars = string.ascii_uppercase + string.digits
    suffix = ''.join(random.choices(chars, k=8))
    return f"{prefix}{suffix}"


# ========== MAIN ADMIN CLASSES ==========
@admin.register(Customer)
class CustomerAdmin(UserAdmin):
    """Admin interface for Customer model"""

    list_display = ('email', 'first_name', 'last_name', 'phone_number', 'email_verified', 'is_active', 'is_staff',
                    'date_joined')
    list_filter = ('email_verified', 'is_active', 'is_staff', 'is_superuser', 'date_joined')
    search_fields = ('email', 'first_name', 'last_name', 'phone_number')
    ordering = ('-date_joined',)
    readonly_fields = ('last_login', 'date_joined')

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'phone_number', 'address')}),
        (_('Permissions'), {
            'fields': ('email_verified', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2'),
        }),
    )


@admin.register(AnimalType)
class AnimalTypeAdmin(admin.ModelAdmin):
    """Admin interface for AnimalType model"""

    list_display = ('name', 'slug', 'icon', 'is_active', 'category_count', 'product_count')
    list_filter = ('is_active',)
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    actions = ['activate_types', 'deactivate_types']

    def category_count(self, obj):
        """Return count of active categories for this animal type"""
        return obj.categories.filter(is_active=True).count()

    category_count.short_description = 'Categories'

    def product_count(self, obj):
        """Return count of active products for this animal type"""
        return Product.objects.filter(category__animal_type=obj, is_active=True).count()

    product_count.short_description = 'Products'

    def activate_types(self, request, queryset):
        """Activate selected animal types"""
        queryset.update(is_active=True)

    activate_types.short_description = "Activate selected animal types"

    def deactivate_types(self, request, queryset):
        """Deactivate selected animal types"""
        queryset.update(is_active=False)

    deactivate_types.short_description = "Deactivate selected animal types"


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Admin interface for Category model"""

    form = CategoryForm
    list_display = ('name', 'animal_type', 'parent', 'level', 'is_active', 'product_count', 'sort_order')
    list_filter = ('animal_type', 'is_active', 'level')
    search_fields = ('name', 'slug', 'description')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('level', 'created_at', 'updated_at')
    actions = ['activate_categories', 'deactivate_categories']

    fieldsets = (
        (_('Basic Information'), {
            'fields': ('name', 'slug', 'animal_type', 'parent', 'description')
        }),
        (_('Display'), {
            'fields': ('image_url', 'sort_order', 'is_active')
        }),
        (_('System Information'), {
            'fields': ('level', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def product_count(self, obj):
        """Return count of active products in this category"""
        return obj.products.filter(is_active=True).count()

    product_count.short_description = 'Products'

    def activate_categories(self, request, queryset):
        """Activate selected categories"""
        queryset.update(is_active=True)

    activate_categories.short_description = "Activate selected categories"

    def deactivate_categories(self, request, queryset):
        """Deactivate selected categories"""
        queryset.update(is_active=False)

    deactivate_categories.short_description = "Deactivate selected categories"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('animal_type', 'parent')


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    """Admin interface for Brand model"""

    list_display = ('name', 'slug', 'is_active', 'product_count', 'logo_preview', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'slug', 'description')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created_at', 'updated_at', 'logo_preview')

    fieldsets = (
        (_('Basic Information'), {
            'fields': ('name', 'slug', 'description')
        }),
        (_('Logo'), {
            'fields': ('logo_url', 'logo_preview')
        }),
        (_('Status'), {
            'fields': ('is_active',)
        }),
        (_('Dates'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def product_count(self, obj):
        """Return count of active products for this brand"""
        return obj.products.filter(is_active=True).count()

    product_count.short_description = 'Products'

    def logo_preview(self, obj):
        """Return HTML for logo preview"""
        if obj.logo_url:
            return format_html('<img src="{}" style="max-height: 50px;" />', obj.logo_url)
        return "-"

    logo_preview.short_description = 'Logo Preview'


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """Admin interface for Product model"""

    form = ProductForm
    list_display = ('name', 'brand', 'category', 'price_range', 'stock_status', 'rating', 'is_active', 'is_featured',
                    'created_at')
    list_filter = (InStockFilter, HasDiscountFilter, 'is_active', 'is_featured', 'category__animal_type', 'category',
                   'brand', 'created_at')
    search_fields = ('name', 'slug', 'description', 'brand__name', 'category__name')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('rating', 'review_count', 'created_at', 'updated_at', 'main_image_preview')
    actions = ['activate_products', 'deactivate_products', 'feature_products', 'unfeature_products']

    fieldsets = (
        (_('Basic Information'), {
            'fields': ('name', 'slug', 'brand', 'category', 'short_description', 'description')
        }),
        (_('Pricing & Status'), {
            'fields': ('is_active', 'is_featured')
        }),
        (_('Product Details'), {
            'fields': ('composition', 'nutritional_analysis', 'feeding_guidelines', 'ingredients')
        }),
        (_('Nutritional Information'), {
            'fields': ('nutritional_value', 'feeding_table'),
            'classes': ('collapse',)
        }),
        (_('SEO'), {
            'fields': ('meta_title', 'meta_description'),
            'classes': ('collapse',)
        }),
        (_('Statistics'), {
            'fields': ('rating', 'review_count'),
            'classes': ('collapse',)
        }),
        (_('Dates'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    inlines = [ProductVariantInline, ProductImageInline, ProductReviewInline]

    def price_range(self, obj):
        """Return formatted price range for the product"""
        min_price = obj.min_price
        max_price = obj.max_price

        if min_price and max_price:
            if min_price == max_price:
                return f"${min_price}"
            return f"${min_price} - ${max_price}"
        return "-"

    price_range.short_description = 'Price Range'

    def stock_status(self, obj):
        """Return HTML for stock status with color coding"""
        if obj.in_stock:
            total_stock = sum(variant.stock for variant in obj.variants.filter(is_active=True))
            if total_stock < 10:
                return format_html('<span style="color: orange;">Low ({})</span>', total_stock)
            return format_html('<span style="color: green;">In Stock ({})</span>', total_stock)
        return format_html('<span style="color: red;">Out of Stock</span>')

    stock_status.short_description = 'Stock'

    def main_image_preview(self, obj):
        """Show main image from ProductImage"""
        main_image = obj.images.filter(is_main=True).first()
        if main_image:
            return format_html('<img src="{}" style="max-height: 100px; max-width: 100px;" />', main_image.image_url)

        first_image = obj.images.first()
        if first_image:
            return format_html('<img src="{}" style="max-height: 100px; max-width: 100px;" />', first_image.image_url)

        return "-"

    main_image_preview.short_description = 'Main Image Preview'

    def save_model(self, request, obj, form, change):
        """Automatically create variant if none exists"""
        super().save_model(request, obj, form, change)

        # Create base variant if none exists
        if not obj.variants.exists():
            ProductVariant.objects.create(
                product=obj,
                sku=generate_random_sku(),
                price=0,
                stock=0,
                is_active=True
            )

    def save_formset(self, request, form, formset, change):
        """Handle inline forms saving"""
        instances = formset.save(commit=False)

        # For ProductImage: make first image main if no main exists
        if formset.model == ProductImage:
            product = form.instance
            if not product.images.filter(is_main=True).exists() and instances:
                instances[0].is_main = True

        # For ProductVariant: generate SKU if empty
        elif formset.model == ProductVariant:
            for instance in instances:
                if not instance.sku:
                    instance.sku = generate_random_sku()

        # Save all changes
        for instance in instances:
            instance.save()

        for obj in formset.deleted_objects:
            obj.delete()

        formset.save_m2m()

    def activate_products(self, request, queryset):
        """Activate selected products"""
        queryset.update(is_active=True)

    activate_products.short_description = "Activate selected products"

    def deactivate_products(self, request, queryset):
        """Deactivate selected products"""
        queryset.update(is_active=False)

    deactivate_products.short_description = "Deactivate selected products"

    def feature_products(self, request, queryset):
        """Mark selected products as featured"""
        queryset.update(is_featured=True)

    feature_products.short_description = "Mark as featured"

    def unfeature_products(self, request, queryset):
        """Remove selected products from featured"""
        queryset.update(is_featured=False)

    unfeature_products.short_description = "Remove from featured"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('brand', 'category', 'category__animal_type')


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    """Admin interface for ProductVariant model"""

    form = ProductVariantForm
    list_display = ('sku', 'product', 'price', 'old_price', 'discount_percentage', 'stock', 'is_active', 'created_at')
    list_filter = ('is_active', 'has_discount', 'created_at', 'product__category__animal_type')
    search_fields = ('sku', 'product__name', 'product__brand__name')
    readonly_fields = ('discount_percentage', 'created_at', 'updated_at')
    list_editable = ('price', 'old_price', 'stock', 'is_active')
    actions = ['activate_variants', 'deactivate_variants', 'apply_discount', 'remove_discount']

    fieldsets = (
        (_('Basic Information'), {
            'fields': ('product', 'sku')
        }),
        (_('Pricing'), {
            'fields': ('price', 'old_price', 'has_discount', 'discount_percentage', 'cost_price')
        }),
        (_('Inventory'), {
            'fields': ('stock', 'is_active')
        }),
        (_('Attributes'), {
            'fields': ('attributes',)
        }),
        (_('Physical Properties'), {
            'fields': ('weight', 'dimensions'),
            'classes': ('collapse',)
        }),
        (_('Dates'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def save_model(self, request, obj, form, change):
        """Automatically generate SKU if empty"""
        if not obj.sku:
            obj.sku = generate_random_sku()
        super().save_model(request, obj, form, change)

    def activate_variants(self, request, queryset):
        """Activate selected variants"""
        queryset.update(is_active=True)

    activate_variants.short_description = "Activate selected variants"

    def deactivate_variants(self, request, queryset):
        """Deactivate selected variants"""
        queryset.update(is_active=False)

    deactivate_variants.short_description = "Deactivate selected variants"

    def apply_discount(self, request, queryset):
        """Apply discount to selected variants"""
        for variant in queryset:
            if variant.old_price and variant.old_price > variant.price:
                variant.has_discount = True
                variant.save()

    apply_discount.short_description = "Apply discount to selected variants"

    def remove_discount(self, request, queryset):
        """Remove discount from selected variants"""
        queryset.update(has_discount=False)

    remove_discount.short_description = "Remove discount from selected variants"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('product', 'product__brand').prefetch_related('attributes')


@admin.register(ProductAttribute)
class ProductAttributeAdmin(admin.ModelAdmin):
    """Admin interface for ProductAttribute model"""

    list_display = ('name', 'slug', 'filterable', 'display_order', 'values_count')
    list_filter = ('filterable',)
    search_fields = ('name', 'slug', 'description')
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ('filterable', 'display_order')

    def values_count(self, obj):
        """Return count of values for this attribute"""
        return obj.values.count()

    values_count.short_description = 'Values'


@admin.register(ProductAttributeValue)
class ProductAttributeValueAdmin(admin.ModelAdmin):
    """Admin interface for ProductAttributeValue model"""

    list_display = ('attribute', 'value', 'slug', 'display_order', 'variants_count')
    list_filter = ('attribute',)
    search_fields = ('value', 'slug', 'attribute__name')
    list_editable = ('display_order',)

    def variants_count(self, obj):
        """Return count of variants using this attribute value"""
        return obj.variants.count()

    variants_count.short_description = 'Used in Variants'


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    """Admin interface for ProductImage model"""

    list_display = ('product', 'image_preview', 'alt_text', 'is_main', 'display_order', 'variant')
    list_filter = ('is_main', 'product__category__animal_type')
    search_fields = ('product__name', 'alt_text')
    list_editable = ('display_order', 'is_main')
    readonly_fields = ('image_preview',)

    def image_preview(self, obj):
        """Return HTML for image preview"""
        if obj.image_url:
            return format_html('<img src="{}" style="max-height: 50px; max-width: 50px;" />', obj.image_url)
        return "-"

    image_preview.short_description = 'Preview'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('product', 'variant')


@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    """Admin interface for ProductReview model"""

    list_display = ('product', 'user', 'rating_stars', 'title', 'is_verified', 'is_active', 'created_at')
    list_filter = ('rating', 'is_verified', 'is_active', 'created_at', 'product__category__animal_type')
    search_fields = ('product__name', 'user__email', 'title', 'comment')
    list_editable = ('is_verified', 'is_active')
    readonly_fields = ('created_at', 'updated_at')
    actions = ['verify_reviews', 'unverify_reviews', 'activate_reviews', 'deactivate_reviews']

    def rating_stars(self, obj):
        """Return star rating as HTML"""
        stars = '★' * obj.rating + '☆' * (5 - obj.rating)
        return format_html('<span style="color: gold; font-size: 14px;">{}</span>', stars)

    rating_stars.short_description = 'Rating'

    def verify_reviews(self, request, queryset):
        """Verify selected reviews"""
        queryset.update(is_verified=True)

    verify_reviews.short_description = "Verify selected reviews"

    def unverify_reviews(self, request, queryset):
        """Unverify selected reviews"""
        queryset.update(is_verified=False)

    unverify_reviews.short_description = "Unverify selected reviews"

    def activate_reviews(self, request, queryset):
        """Activate selected reviews"""
        queryset.update(is_active=True)

    activate_reviews.short_description = "Activate selected reviews"

    def deactivate_reviews(self, request, queryset):
        """Deactivate selected reviews"""
        queryset.update(is_active=False)

    deactivate_reviews.short_description = "Deactivate selected reviews"


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    """Admin interface for Cart model"""

    list_display = ('user', 'total_items', 'total_price_display', 'created_at', 'updated_at')
    search_fields = ('user__email', 'user__first_name', 'user__last_name')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [CartItemInline]

    def total_price_display(self, obj):
        """Return formatted total price of cart"""
        total = sum(item.total_price for item in obj.items.all())
        return f"${total:.2f}"

    total_price_display.short_description = 'Total Price'

    def total_items(self, obj):
        """Return total number of items in cart"""
        return sum(item.quantity for item in obj.items.all())

    total_items.short_description = 'Items'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    """Admin interface for CartItem model"""

    list_display = ('cart', 'variant', 'quantity', 'unit_price', 'total_price', 'added_at')
    list_filter = ('added_at', 'variant__product__category__animal_type')
    search_fields = ('cart__user__email', 'variant__sku', 'variant__product__name')
    readonly_fields = ('added_at',)

    def unit_price(self, obj):
        """Return formatted unit price"""
        return f"${obj.variant.price:.2f}"

    unit_price.short_description = 'Unit Price'

    def total_price(self, obj):
        """Return formatted total price"""
        return f"${obj.total_price:.2f}"

    total_price.short_description = 'Total Price'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('cart__user', 'variant__product')


# ========== ADMIN SITE CONFIGURATION ==========
class EcommerceAdminSite(admin.AdminSite):
    """Custom admin site configuration"""

    site_header = "Pet Shop Administration"
    site_title = "Pet Shop Admin"
    index_title = "Welcome to Pet Shop Admin Panel"


# Create custom admin site
admin_site = EcommerceAdminSite(name='admin')

# Register all models with custom admin site
admin_site.register(Customer, CustomerAdmin)
admin_site.register(AnimalType, AnimalTypeAdmin)
admin_site.register(Category, CategoryAdmin)
admin_site.register(Brand, BrandAdmin)
admin_site.register(Product, ProductAdmin)
admin_site.register(ProductVariant, ProductVariantAdmin)
admin_site.register(ProductAttribute, ProductAttributeAdmin)
admin_site.register(ProductAttributeValue, ProductAttributeValueAdmin)
admin_site.register(ProductImage, ProductImageAdmin)
admin_site.register(ProductReview, ProductReviewAdmin)
admin_site.register(Cart, CartAdmin)
admin_site.register(CartItem, CartItemAdmin)
