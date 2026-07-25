from django.contrib import admin
from django import forms
from django.conf import settings

from ..models import (
    AnimalTypeTranslation,
    BadgeTranslation,
    CategoryTranslation,
    ProductAttributeTranslation,
    ProductAttributeValueTranslation,
    ProductTranslation,
    ProductVariantTranslation,
)


class TranslationInlineForm(forms.ModelForm):
    language = forms.ChoiceField(choices=settings.LANGUAGES)


class AnimalTypeTranslationInline(admin.TabularInline):
    model = AnimalTypeTranslation
    form = TranslationInlineForm
    extra = 0


class CategoryTranslationInline(admin.TabularInline):
    model = CategoryTranslation
    form = TranslationInlineForm
    extra = 0


class BadgeTranslationInline(admin.TabularInline):
    model = BadgeTranslation
    form = TranslationInlineForm
    extra = 0


class ProductTranslationInline(admin.StackedInline):
    model = ProductTranslation
    form = TranslationInlineForm
    extra = 0


class ProductVariantTranslationInline(admin.StackedInline):
    model = ProductVariantTranslation
    form = TranslationInlineForm
    extra = 0


class ProductAttributeTranslationInline(admin.TabularInline):
    model = ProductAttributeTranslation
    form = TranslationInlineForm
    extra = 0


class ProductAttributeValueTranslationInline(admin.TabularInline):
    model = ProductAttributeValueTranslation
    form = TranslationInlineForm
    extra = 0
