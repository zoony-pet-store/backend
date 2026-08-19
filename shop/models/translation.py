from django.conf import settings
from django.db import models
from django.utils.translation import get_language
from django.core.exceptions import ValidationError
from django_jsonform.models.fields import JSONField as JSONFormField

from .animal_type import AnimalType
from .badge import Badge
from .category import Category
from .product import (
    Product,
    validate_product_content_blocks,
    PRODUCT_CONTENT_BLOCKS_SCHEMA,
)
from .product_attribute import ProductAttribute
from .product_attribute_value import ProductAttributeValue
from .product_variant import ProductVariant


def normalize_language_code(language):
    if not language:
        return settings.LANGUAGE_CODE.split("-")[0]

    return language.split("-")[0]


def get_current_language():
    return normalize_language_code(get_language())


def get_object_translation(obj, language=None, fallback_language=None):
    translations_manager = getattr(obj, "translations", None)

    if translations_manager is None:
        return None

    current_language = normalize_language_code(language or get_current_language())
    default_language = normalize_language_code(settings.LANGUAGE_CODE)

    if current_language == default_language:
        return None

    translations = list(translations_manager.all())

    for translation in translations:
        if normalize_language_code(translation.language) == current_language:
            return translation

    if fallback_language:
        fallback_language = normalize_language_code(fallback_language)

        if fallback_language != default_language:
            for translation in translations:
                if normalize_language_code(translation.language) == fallback_language:
                    return translation

    return None


def translated_field(obj, field_name, language=None, fallback_language=None):
    translation = get_object_translation(
        obj,
        language,
        fallback_language,
    )

    if translation:
        value = getattr(translation, field_name, None)

        if value not in (None, "", [], {}):
            return value

    return getattr(obj, field_name)


class BaseTranslation(models.Model):
    language = models.CharField(
        max_length=10,
        choices=settings.LANGUAGES,
        db_index=True,
    )

    class Meta:
        abstract = True

    def clean(self):
        super().clean()

        if self.language:
            self.language = normalize_language_code(self.language)

        default_language = normalize_language_code(settings.LANGUAGE_CODE)

        if self.language == default_language:
            raise ValidationError(
                {
                    "language": (
                        "Default-language content must be stored "
                        "in the model's base fields."
                    )
                }
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class AnimalTypeTranslation(BaseTranslation):
    animal_type = models.ForeignKey(
        AnimalType,
        on_delete=models.CASCADE,
        related_name="translations",
    )
    name = models.CharField(max_length=50)

    class Meta:
        db_table = "animal_type_translations"
        constraints = [
            models.UniqueConstraint(
                fields=["animal_type", "language"],
                name="unique_animal_type_translation_language",
            )
        ]

    def __str__(self):
        return f"{self.animal_type} [{self.language}]"


class CategoryTranslation(BaseTranslation):
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="translations",
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    class Meta:
        db_table = "category_translations"
        constraints = [
            models.UniqueConstraint(
                fields=["category", "language"],
                name="unique_category_translation_language",
            )
        ]

    def __str__(self):
        return f"{self.category} [{self.language}]"


class BadgeTranslation(BaseTranslation):
    badge = models.ForeignKey(
        Badge,
        on_delete=models.CASCADE,
        related_name="translations",
    )
    label = models.CharField(max_length=50)

    class Meta:
        db_table = "badge_translations"
        constraints = [
            models.UniqueConstraint(
                fields=["badge", "language"],
                name="unique_badge_translation_language",
            )
        ]

    def __str__(self):
        return f"{self.badge} [{self.language}]"


class ProductTranslation(BaseTranslation):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="translations",
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    short_description = models.TextField(max_length=500, blank=True)
    meta_title = models.CharField(max_length=255, blank=True)
    meta_description = models.TextField(blank=True)

    content_blocks = JSONFormField(
        schema=PRODUCT_CONTENT_BLOCKS_SCHEMA,
        default=list,
        blank=True,
        verbose_name="Translated content blocks",
        help_text=(
            "Localized version of the product content blocks. "
            "The block keys and structure should match the base product."
        ),
    )

    class Meta:
        db_table = "product_translations"
        constraints = [
            models.UniqueConstraint(
                fields=["product", "language"],
                name="unique_product_translation_language",
            )
        ]

    def clean(self):
        super().clean()
        validate_product_content_blocks(self.content_blocks)

    def __str__(self):
        return f"{self.product} [{self.language}]"


class ProductVariantTranslation(BaseTranslation):
    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.CASCADE,
        related_name="translations",
    )
    description = models.TextField(blank=True)
    short_description = models.TextField(blank=True)

    class Meta:
        db_table = "product_variant_translations"
        constraints = [
            models.UniqueConstraint(
                fields=["variant", "language"],
                name="unique_product_variant_translation_language",
            )
        ]

    def __str__(self):
        return f"{self.variant} [{self.language}]"


class ProductAttributeTranslation(BaseTranslation):
    attribute = models.ForeignKey(
        ProductAttribute,
        on_delete=models.CASCADE,
        related_name="translations",
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    class Meta:
        db_table = "product_attribute_translations"
        constraints = [
            models.UniqueConstraint(
                fields=["attribute", "language"],
                name="unique_product_attribute_translation_language",
            )
        ]

    def __str__(self):
        return f"{self.attribute} [{self.language}]"


class ProductAttributeValueTranslation(BaseTranslation):
    attribute_value = models.ForeignKey(
        ProductAttributeValue,
        on_delete=models.CASCADE,
        related_name="translations",
    )
    value = models.CharField(max_length=255)

    class Meta:
        db_table = "product_attribute_value_translations"
        constraints = [
            models.UniqueConstraint(
                fields=["attribute_value", "language"],
                name="unique_product_attribute_value_translation_language",
            )
        ]

    def __str__(self):
        return f"{self.attribute_value} [{self.language}]"
