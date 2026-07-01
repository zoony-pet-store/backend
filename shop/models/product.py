import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Max, Min
from django.utils.text import slugify
from django_jsonform.models.fields import JSONField as JSONFormField

from .badge import Badge
from .brand import Brand
from .category import Category
PRODUCT_CONTENT_BLOCK_TYPES = {"text", "key_value", "table"}


PRODUCT_CONTENT_BLOCKS_SCHEMA = {
    "type": "array",
    "title": "Advanced custom content blocks",
    "items": {
        "type": "dict",
        "keys": {
            "key": {
                "type": "string",
                "title": "Key",
                "helpText": (
                    "Stable unique block key for frontend. "
                    "Example: description, characteristics, feeding_guidelines."
                ),
            },
            "type": {
                "type": "string",
                "title": "Block type",
                "choices": [
                    {"title": "Text", "value": "text"},
                    {"title": "Key / Value", "value": "key_value"},
                    {"title": "Table", "value": "table"},
                ],
            },
            "title": {
                "type": "string",
                "title": "Title",
            },
            "content": {
                "type": "dict",
                "title": "Content",
                "keys": {
                    "text": {
                        "type": "string",
                        "title": "Text",
                        "widget": "textarea",
                    },
                    "items": {
                        "type": "array",
                        "title": "Key / Value items",
                        "items": {
                            "type": "dict",
                            "keys": {
                                "key": {
                                    "type": "string",
                                    "title": "Key",
                                },
                                "value": {
                                    "type": "string",
                                    "title": "Value",
                                },
                            },
                        },
                    },
                    "columns": {
                        "type": "array",
                        "title": "Table columns",
                        "items": {
                            "type": "dict",
                            "keys": {
                                "id": {
                                    "type": "string",
                                    "title": "Column ID",
                                },
                                "title": {
                                    "type": "string",
                                    "title": "Column title",
                                },
                            },
                        },
                    },
                    "rows": {
                        "type": "array",
                        "title": "Table rows",
                        "items": {
                            "type": "dict",
                            "additionalProperties": True,
                            "keys": {},
                        },
                    },
                },
            },
        },
    },
}


def validate_product_content_blocks(value):
    if value in (None, ""):
        return

    if not isinstance(value, list):
        raise ValidationError({"content_blocks": "Content blocks must be a list."})

    seen_keys = set()

    for index, block in enumerate(value, start=1):
        if not isinstance(block, dict):
            raise ValidationError(
                {"content_blocks": f"Block #{index} must be an object."}
            )

        block_key = block.get("key")
        block_type = block.get("type")
        title = block.get("title")
        content = block.get("content")

        if not isinstance(block_key, str) or not block_key.strip():
            raise ValidationError(
                {"content_blocks": f"Block #{index} must have a non-empty key."}
            )

        normalized_key = block_key.strip()

        if normalized_key in seen_keys:
            raise ValidationError(
                {
                    "content_blocks": (
                        f'Content block key "{normalized_key}" is duplicated. '
                        "Keys must be unique within one product."
                    )
                }
            )

        seen_keys.add(normalized_key)

        if block_type not in PRODUCT_CONTENT_BLOCK_TYPES:
            raise ValidationError(
                {
                    "content_blocks": (
                        f"Block #{index} has invalid type: {block_type}. "
                        f"Allowed types: {', '.join(sorted(PRODUCT_CONTENT_BLOCK_TYPES))}."
                    )
                }
            )

        if not title:
            raise ValidationError(
                {"content_blocks": f"Block #{index} must have a title."}
            )

        if not isinstance(content, dict):
            raise ValidationError(
                {"content_blocks": f"Block #{index} content must be an object."}
            )

        if block_type == "text":
            text = content.get("text")

            if not isinstance(text, str) or not text.strip():
                raise ValidationError(
                    {
                        "content_blocks": (
                            f"Text block #{index} must have non-empty content.text."
                        )
                    }
                )

        elif block_type == "key_value":
            items = content.get("items")

            if not isinstance(items, list) or not items:
                raise ValidationError(
                    {
                        "content_blocks": (
                            f"Key/value block #{index} must have non-empty content.items."
                        )
                    }
                )

            for item_position, item in enumerate(items, start=1):
                if not isinstance(item, dict):
                    raise ValidationError(
                        {
                            "content_blocks": (
                                f"Item #{item_position} in block #{index} "
                                f"must be an object."
                            )
                        }
                    )

                if not item.get("key") or not item.get("value"):
                    raise ValidationError(
                        {
                            "content_blocks": (
                                f"Item #{item_position} in block #{index} "
                                f"must have key and value."
                            )
                        }
                    )

        elif block_type == "table":
            columns = content.get("columns")
            rows = content.get("rows")

            if not isinstance(columns, list) or not columns:
                raise ValidationError(
                    {
                        "content_blocks": (
                            f"Table block #{index} must have non-empty content.columns."
                        )
                    }
                )

            if not isinstance(rows, list):
                raise ValidationError(
                    {
                        "content_blocks": (
                            f"Table block #{index} must have content.rows list."
                        )
                    }
                )

            column_ids = []

            for column_position, column in enumerate(columns, start=1):
                if not isinstance(column, dict):
                    raise ValidationError(
                        {
                            "content_blocks": (
                                f"Column #{column_position} in block #{index} "
                                f"must be an object."
                            )
                        }
                    )

                column_id = column.get("id")
                column_title = column.get("title")

                if not column_id or not column_title:
                    raise ValidationError(
                        {
                            "content_blocks": (
                                f"Column #{column_position} in block #{index} "
                                f"must have id and title."
                            )
                        }
                    )

                column_ids.append(column_id)

            duplicated_column_ids = {
                column_id for column_id in column_ids if column_ids.count(column_id) > 1
            }

            if duplicated_column_ids:
                raise ValidationError(
                    {
                        "content_blocks": (
                            f"Table block #{index} has duplicated column ids: "
                            f"{', '.join(sorted(duplicated_column_ids))}."
                        )
                    }
                )

            allowed_column_ids = set(column_ids)

            for row_position, row in enumerate(rows, start=1):
                if not isinstance(row, dict):
                    raise ValidationError(
                        {
                            "content_blocks": (
                                f"Row #{row_position} in block #{index} "
                                f"must be an object."
                            )
                        }
                    )

                unknown_keys = set(row.keys()) - allowed_column_ids

                if unknown_keys:
                    raise ValidationError(
                        {
                            "content_blocks": (
                                f"Row #{row_position} in block #{index} "
                                f"has unknown keys: {', '.join(sorted(unknown_keys))}."
                            )
                        }
                    )


class Product(models.Model):
    """
    Base product.

    Product does not store stock.
    Real stock and real price live on ProductVariant.
    Dynamic product-page data is exposed through content_blocks in API.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(blank=True)

    description = models.TextField(blank=True)
    short_description = models.TextField(max_length=500, blank=True)

    brand = models.ForeignKey(
        Brand,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="products",
    )

    is_active = models.BooleanField(default=True)
    badges = models.ManyToManyField(Badge, blank=True, related_name="products")

    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.0)
    review_count = models.IntegerField(default=0)

    meta_title = models.CharField(max_length=255, blank=True)
    meta_description = models.TextField(blank=True)

    content_blocks = JSONFormField(
        schema=PRODUCT_CONTENT_BLOCKS_SCHEMA,
        default=list,
        blank=True,
        verbose_name="Advanced custom content blocks",
        help_text=(
            "Main way to manage custom product page content. "
            "Each block must have a unique key within this product. "
            "Supported block types: text, key_value, table."
        ),
    )

    # Keep for backward compatibility / fallback image.
    main_image = models.URLField(max_length=500, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["slug", "category"],
                name="unique_product_slug_per_category",
            )
        ]

    def clean(self):
        validate_product_content_blocks(self.content_blocks)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.generate_slug()

        self.full_clean()
        super().save(*args, **kwargs)

    def generate_slug(self):
        base_slug = slugify(self.name)
        slug = base_slug
        counter = 1

        queryset = Product.objects.filter(slug=slug, category=self.category)

        if self.pk:
            queryset = queryset.exclude(pk=self.pk)

        while queryset.exists():
            slug = f"{base_slug}-{counter}"
            counter += 1

            queryset = Product.objects.filter(slug=slug, category=self.category)

            if self.pk:
                queryset = queryset.exclude(pk=self.pk)

        return slug

    @property
    def default_variant(self):
        """
        Variant that should be used as base display variant on catalog/product page.

        Priority:
        1. active variant with is_default=True
        2. first active variant by price/id
        """
        return (
            self.variants.filter(is_active=True)
            .order_by("-is_default", "price", "id")
            .first()
        )

    @property
    def display_price(self):
        variant = self.default_variant
        return variant.price if variant else None

    @property
    def display_old_price(self):
        variant = self.default_variant

        if variant and variant.has_discount:
            return variant.old_price

        return None

    @property
    def min_price(self):
        return self.variants.filter(is_active=True).aggregate(min_price=Min("price"))[
            "min_price"
        ]

    @property
    def max_price(self):
        return self.variants.filter(is_active=True).aggregate(max_price=Max("price"))[
            "max_price"
        ]

    @property
    def in_stock(self):
        return self.variants.filter(is_active=True, stock__gt=0).exists()

    def __str__(self):
        return self.name


class ProductCharacteristic(models.Model):
    """
    Product characteristics section.

    Rendered in API as:
    type=key_value
    title=Characteristics
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="characteristics",
    )
    label = models.CharField(max_length=255)
    value = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = "Product characteristic"
        verbose_name_plural = "Product characteristics"

    def __str__(self):
        return f"{self.label}: {self.value}"


class ProductTypicalAnalysisItem(models.Model):
    """
    Typical analysis section.

    Rendered in API as:
    type=key_value
    title=Typical Analysis
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="typical_analysis_items",
    )
    label = models.CharField(max_length=255)
    value = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = "Typical analysis item"
        verbose_name_plural = "Typical analysis items"

    def __str__(self):
        return f"{self.label}: {self.value}"


class ProductFeedingGuidelineRow(models.Model):
    """
    Feeding guidelines section.

    Rendered in API as table:
    Pet weight | Active lifestyle | Sedentary lifestyle | Overweight
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="feeding_guideline_rows",
    )
    pet_weight = models.CharField(max_length=100)
    active_lifestyle = models.CharField(max_length=100, blank=True)
    sedentary_lifestyle = models.CharField(max_length=100, blank=True)
    overweight = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = "Feeding guideline row"
        verbose_name_plural = "Feeding guideline rows"

    def __str__(self):
        return self.pet_weight
