from unfold.admin import StackedInline, TabularInline

from ..models import (
    AnimalTypeTranslation,
    BadgeTranslation,
    CategoryTranslation,
    ProductAttributeTranslation,
    ProductAttributeValueTranslation,
    ProductTranslation,
    ProductVariantTranslation,
)


class AnimalTypeTranslationInline(TabularInline):
    model = AnimalTypeTranslation
    extra = 0


class CategoryTranslationInline(TabularInline):
    model = CategoryTranslation
    extra = 0


class BadgeTranslationInline(TabularInline):
    model = BadgeTranslation
    extra = 0


class ProductTranslationInline(StackedInline):
    model = ProductTranslation
    extra = 0


class ProductVariantTranslationInline(StackedInline):
    model = ProductVariantTranslation
    extra = 0


class ProductAttributeTranslationInline(TabularInline):
    model = ProductAttributeTranslation
    extra = 0


class ProductAttributeValueTranslationInline(TabularInline):
    model = ProductAttributeValueTranslation
    extra = 0
