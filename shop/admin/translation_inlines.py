from django.conf import settings
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


def get_default_language_code():
    return settings.LANGUAGE_CODE.split("-")[0]


class TranslationLanguageInlineMixin:
    def get_translation_language_choices(self):
        default_language = get_default_language_code()

        return [
            (code, label)
            for code, label in settings.LANGUAGES
            if code.split("-")[0] != default_language
        ]

    def formfield_for_choice_field(self, db_field, request, **kwargs):
        if db_field.name == "language":
            kwargs["choices"] = self.get_translation_language_choices()

        return super().formfield_for_choice_field(db_field, request, **kwargs)

    def get_queryset(self, request):
        return (
            super().get_queryset(request).exclude(language=get_default_language_code())
        )


class AnimalTypeTranslationInline(TranslationLanguageInlineMixin, TabularInline):
    model = AnimalTypeTranslation
    extra = 0


class CategoryTranslationInline(TranslationLanguageInlineMixin, TabularInline):
    model = CategoryTranslation
    extra = 0


class BadgeTranslationInline(TranslationLanguageInlineMixin, TabularInline):
    model = BadgeTranslation
    extra = 0


class ProductTranslationInline(TranslationLanguageInlineMixin, StackedInline):
    model = ProductTranslation
    extra = 0


class ProductVariantTranslationInline(TranslationLanguageInlineMixin, StackedInline):
    model = ProductVariantTranslation
    extra = 0


class ProductAttributeTranslationInline(TranslationLanguageInlineMixin, TabularInline):
    model = ProductAttributeTranslation
    extra = 0


class ProductAttributeValueTranslationInline(
    TranslationLanguageInlineMixin, TabularInline
):
    model = ProductAttributeValueTranslation
    extra = 0
