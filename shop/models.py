import uuid

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Max, Min, Q
from django.utils.text import slugify
from django_jsonform.models.fields import JSONField as JSONFormField
from phonenumber_field.modelfields import PhoneNumberField


class CustomerManager(BaseUserManager):
    """Custom manager for Customer model."""

    def create_user(self, email, password=None, **extra_fields):
        """Create and save a regular user."""
        if not email:
            raise ValueError("User must have an email address.")

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """Create and save a superuser."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")

        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


class Customer(AbstractUser):
    """Custom user model for customers."""

    username = models.CharField(max_length=150, blank=True, null=True)
    email = models.EmailField(unique=True)
    phone_number = PhoneNumberField(region="UA", blank=True, null=True)
    address = models.TextField(blank=True)
    email_verified = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = CustomerManager()

    def save(self, *args, **kwargs):
        if not self.username:
            self.username = self.email

        super().save(*args, **kwargs)

    def __str__(self):
        return self.email


class AnimalType(models.Model):
    """Animal type/category, e.g. dogs, cats."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50)
    slug = models.SlugField(unique=True)
    icon = models.CharField(max_length=100, blank=True)
    image_url = models.URLField(max_length=500, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "animal_types"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Category(models.Model):
    """Product category with hierarchical structure."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(blank=True)
    description = models.TextField(blank=True)
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
    )
    animal_type = models.ForeignKey(
        AnimalType,
        on_delete=models.CASCADE,
        related_name="categories",
    )
    image_url = models.URLField(max_length=500, blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    level = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "categories"
        ordering = ["sort_order", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["slug", "animal_type", "parent"],
                name="unique_category_slug_per_parent_and_animal_type",
            )
        ]

    def save(self, *args, **kwargs):
        self.level = self.parent.level + 1 if self.parent else 0

        if not self.slug:
            self.slug = self.generate_slug()

        super().save(*args, **kwargs)

    def generate_slug(self):
        base_slug = slugify(self.name)
        slug = base_slug
        counter = 1

        queryset = Category.objects.filter(
            slug=slug,
            animal_type=self.animal_type,
            parent=self.parent,
        )

        if self.pk:
            queryset = queryset.exclude(pk=self.pk)

        while queryset.exists():
            slug = f"{base_slug}-{counter}"
            counter += 1

            queryset = Category.objects.filter(
                slug=slug,
                animal_type=self.animal_type,
                parent=self.parent,
            )

            if self.pk:
                queryset = queryset.exclude(pk=self.pk)

        return slug

    def __str__(self):
        return f"{'--' * self.level} {self.name} ({self.animal_type})"


class Brand(models.Model):
    """Product brand."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True)
    logo_url = models.URLField(max_length=500, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.generate_slug()

        super().save(*args, **kwargs)

    def generate_slug(self):
        base_slug = slugify(self.name)
        slug = base_slug
        counter = 1

        queryset = Brand.objects.filter(slug=slug)

        if self.pk:
            queryset = queryset.exclude(pk=self.pk)

        while queryset.exists():
            slug = f"{base_slug}-{counter}"
            counter += 1

            queryset = Brand.objects.filter(slug=slug)

            if self.pk:
                queryset = queryset.exclude(pk=self.pk)

        return slug

    def __str__(self):
        return self.name


class Badge(models.Model):
    """Product or variant badge, e.g. New, Sale, Bestseller."""

    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True, blank=True)
    label = models.CharField(max_length=50)
    color = models.CharField(max_length=7, default="#000000")
    background_color = models.CharField(max_length=7, default="#FFFFFF")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["label"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)

        super().save(*args, **kwargs)

    def __str__(self):
        return self.label


PRODUCT_CONTENT_BLOCK_TYPES = {"text", "key_value", "table"}


AUTO_DISCOUNT_BADGE_SLUG = "discount"
AUTO_SALE_BADGE_SLUG = "sale"
AUTO_SALE_MIN_PERCENTAGE = 20


AUTO_PRICE_BADGE_DEFINITIONS = {
    AUTO_DISCOUNT_BADGE_SLUG: {
        "name": "discount",
        "slug": "discount",
        "label": "Discount",
        "color": "#FFFFFF",
        "background_color": "#DC3545",
    },
    AUTO_SALE_BADGE_SLUG: {
        "name": "sale",
        "slug": "sale",
        "label": "Sale",
        "color": "#FFFFFF",
        "background_color": "#FF6B6B",
    },
}


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


class ProductAttribute(models.Model):
    """
    Attribute type, e.g. Size, Color, Weight, Flavor.

    type:
    - SELECT: value is selected from ProductAttributeValue
    - NUMERIC: value is entered as number + unit on ProductVariantAttribute

    categories is optional:
    - empty means global attribute
    - filled means this attribute is relevant only for selected categories
    """

    class AttributeType(models.TextChoices):
        SELECT = "select", "Select"
        NUMERIC = "numeric", "Numeric"

    UNIT_CHOICES = [
        ("g", "g"),
        ("kg", "kg"),
        ("ml", "ml"),
        ("l", "l"),
        ("mm", "mm"),
        ("cm", "cm"),
        ("m", "m"),
        ("pcs", "pcs"),
        ("pack", "pack"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True)

    type = models.CharField(
        max_length=20,
        choices=AttributeType.choices,
        default=AttributeType.SELECT,
        db_index=True,
        help_text=(
            "Select = predefined text values. " "Numeric = number + unit, e.g. 10 kg."
        ),
    )

    available_units = models.JSONField(
        default=list,
        blank=True,
        help_text=(
            "Only for numeric attributes. Example: ['kg', 'g']. "
            "Leave empty to allow all supported units."
        ),
    )

    filterable = models.BooleanField(default=True)
    display_order = models.IntegerField(default=0)

    categories = models.ManyToManyField(
        Category,
        blank=True,
        related_name="attributes",
    )

    class Meta:
        ordering = ["display_order", "name"]

    @property
    def is_select(self):
        return self.type == self.AttributeType.SELECT

    @property
    def is_numeric(self):
        return self.type == self.AttributeType.NUMERIC

    @property
    def allowed_units(self):
        if self.available_units:
            return self.available_units

        return [unit for unit, _label in self.UNIT_CHOICES]

    def clean(self):
        errors = {}

        supported_units = {unit for unit, _label in self.UNIT_CHOICES}
        invalid_units = [
            unit for unit in self.available_units if unit not in supported_units
        ]

        if invalid_units:
            errors["available_units"] = "Unsupported units: " + ", ".join(
                sorted(invalid_units)
            )

        if self.type == self.AttributeType.SELECT and self.available_units:
            errors["available_units"] = (
                "Available units should be empty for select attributes."
            )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)

        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class ProductAttributeValue(models.Model):
    """
    Possible predefined value for SELECT attributes, e.g. Size: S, Color: Pink.

    Numeric attributes should not use this model. Their values are stored in
    ProductVariantAttribute.value_numeric + ProductVariantAttribute.unit.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    attribute = models.ForeignKey(
        ProductAttribute,
        on_delete=models.CASCADE,
        related_name="values",
    )
    value = models.CharField(max_length=255)
    slug = models.SlugField(blank=True)
    display_order = models.IntegerField(default=0)

    class Meta:
        ordering = ["attribute__display_order", "display_order", "value"]
        constraints = [
            models.UniqueConstraint(
                fields=["attribute", "slug"],
                name="unique_attribute_value_slug_per_attribute",
            )
        ]

    def clean(self):
        if (
            self.attribute_id
            and self.attribute.type == ProductAttribute.AttributeType.NUMERIC
        ):
            raise ValidationError(
                {
                    "attribute": (
                        "ProductAttributeValue can be used only for select "
                        "attributes. Numeric attributes store values directly "
                        "on ProductVariantAttribute."
                    )
                }
            )

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.generate_slug()

        self.full_clean()
        super().save(*args, **kwargs)

    def generate_slug(self):
        base_slug = slugify(self.value)
        slug = base_slug
        counter = 1

        queryset = ProductAttributeValue.objects.filter(
            attribute=self.attribute,
            slug=slug,
        )

        if self.pk:
            queryset = queryset.exclude(pk=self.pk)

        while queryset.exists():
            slug = f"{base_slug}-{counter}"
            counter += 1

            queryset = ProductAttributeValue.objects.filter(
                attribute=self.attribute,
                slug=slug,
            )

            if self.pk:
                queryset = queryset.exclude(pk=self.pk)

        return slug

    def __str__(self):
        return f"{self.attribute.name}: {self.value}"


def format_numeric_attribute_value(value):
    if value is None:
        return ""

    normalized_value = value.normalize()
    display_value = format(normalized_value, "f")

    if "." in display_value:
        display_value = display_value.rstrip("0").rstrip(".")

    return display_value


def get_or_create_auto_price_badge(slug):
    badge_data = AUTO_PRICE_BADGE_DEFINITIONS[slug]

    badge, _ = Badge.objects.get_or_create(
        slug=badge_data["slug"],
        defaults={
            "name": badge_data["name"],
            "label": badge_data["label"],
            "color": badge_data["color"],
            "background_color": badge_data["background_color"],
            "is_active": True,
        },
    )

    updated_fields = []

    if badge.name != badge_data["name"]:
        badge.name = badge_data["name"]
        updated_fields.append("name")

    if badge.label != badge_data["label"]:
        badge.label = badge_data["label"]
        updated_fields.append("label")

    if badge.color != badge_data["color"]:
        badge.color = badge_data["color"]
        updated_fields.append("color")

    if badge.background_color != badge_data["background_color"]:
        badge.background_color = badge_data["background_color"]
        updated_fields.append("background_color")

    if not badge.is_active:
        badge.is_active = True
        updated_fields.append("is_active")

    if updated_fields:
        badge.save(update_fields=updated_fields)

    return badge


class ProductVariant(models.Model):
    """
    Concrete SKU / physical item.

    This is what user adds to cart.
    Price, old_price and stock belong here, not on Product.

    Variant options such as weight, size, color or package size
    should be stored through ProductVariantAttribute, not hardcoded fields.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="variants",
    )

    sku = models.CharField(max_length=100, unique=True, blank=True)

    price = models.DecimalField(max_digits=10, decimal_places=2)
    old_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    cost_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )

    stock = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    # Optional overrides for selected variant.
    description = models.TextField(blank=True)
    short_description = models.TextField(blank=True)
    badges = models.ManyToManyField(Badge, blank=True, related_name="variants")

    auto_badges_enabled = models.BooleanField(
        default=True,
        help_text=(
            "If enabled, Discount and Sale badges are managed automatically "
            "based on old_price and price."
        ),
    )

    is_default = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_default", "price", "id"]
        indexes = [
            models.Index(fields=["product", "is_active"]),
            models.Index(fields=["product", "is_default"]),
            models.Index(fields=["sku"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["product"],
                condition=Q(is_default=True),
                name="unique_default_variant_per_product",
            )
        ]

    def clean(self):
        if self.old_price is not None and self.price is not None:
            if self.old_price <= self.price:
                raise ValidationError(
                    {"old_price": "Old price must be greater than current price."}
                )

    def save(self, *args, **kwargs):
        if not self.sku:
            self.sku = self.generate_sku()
        else:
            self.sku = self.sku.strip().upper()

        if self.product_id and not self.is_default:
            has_default_variant = (
                ProductVariant.objects.filter(
                    product_id=self.product_id,
                    is_default=True,
                )
                .exclude(pk=self.pk)
                .exists()
            )

            if not has_default_variant:
                self.is_default = True

        if self.product_id and self.is_default:
            ProductVariant.objects.filter(
                product_id=self.product_id,
                is_default=True,
            ).exclude(pk=self.pk).update(is_default=False)

        self.full_clean()
        super().save(*args, **kwargs)

        self.sync_auto_price_badges()

    def generate_sku(self):
        """
        Hybrid SKU approach:
        - if admin provides SKU manually, we keep it;
        - if SKU is empty, backend generates stable SKU.
        """
        if not self.id:
            self.id = uuid.uuid4()

        product_part = slugify(self.product.slug or self.product.name or "product")
        product_part = product_part.replace("-", "").upper()[:24]

        return f"{product_part}-{self.id.hex[:8].upper()}"

    def sync_auto_price_badges(self):
        """
        Synchronize DB-backed automatic price badges.

        Only Discount and Sale are managed automatically.
        New, Bestseller and Trending should be managed manually in admin.
        """
        if not self.auto_badges_enabled:
            return

        discount_badge = get_or_create_auto_price_badge(AUTO_DISCOUNT_BADGE_SLUG)
        sale_badge = get_or_create_auto_price_badge(AUTO_SALE_BADGE_SLUG)

        if self.has_discount:
            self.badges.add(discount_badge)
        else:
            self.badges.remove(discount_badge)

        if self.has_discount and self.discount_percentage >= AUTO_SALE_MIN_PERCENTAGE:
            self.badges.add(sale_badge)
        else:
            self.badges.remove(sale_badge)

    @property
    def has_discount(self):
        return bool(self.old_price and self.old_price > self.price)

    @property
    def discount_percentage(self):
        if self.has_discount:
            return round((self.old_price - self.price) / self.old_price * 100)

        return 0

    @property
    def in_stock(self):
        return self.is_active and self.stock > 0

    def __str__(self):
        return f"{self.product.name} - {self.sku}"


class ProductVariantAttribute(models.Model):
    """
    Attribute selected for concrete variant.

    SELECT attribute example:
    Variant: BED-S-PINK
    Attribute: Color
    Value: Pink

    NUMERIC attribute example:
    Variant: FOOD-10KG
    Attribute: Weight
    value_numeric: 10
    unit: kg

    Constraint:
    One variant can have only one value for the same attribute.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.CASCADE,
        related_name="variant_attributes",
    )
    attribute = models.ForeignKey(
        ProductAttribute,
        on_delete=models.CASCADE,
        related_name="variant_attributes",
    )

    # Used only when attribute.type == SELECT.
    value = models.ForeignKey(
        ProductAttributeValue,
        on_delete=models.CASCADE,
        related_name="variant_attributes",
        null=True,
        blank=True,
    )

    # Used only when attribute.type == NUMERIC.
    value_numeric = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        null=True,
        blank=True,
        help_text="Numeric value for numeric attributes, e.g. 10.",
    )
    unit = models.CharField(
        max_length=20,
        blank=True,
        default="",
        help_text="Unit for numeric attributes, e.g. kg, g, ml, l.",
    )

    class Meta:
        ordering = [
            "attribute__display_order",
            "value__display_order",
            "value_numeric",
            "unit",
        ]
        indexes = [
            models.Index(fields=["attribute", "value"]),
            models.Index(fields=["attribute", "value_numeric", "unit"]),
            models.Index(fields=["variant", "attribute"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["variant", "attribute"],
                name="unique_attribute_per_variant",
            )
        ]

    @property
    def display_value(self):
        if self.attribute.type == ProductAttribute.AttributeType.NUMERIC:
            if self.value_numeric is None:
                return ""

            return (
                f"{format_numeric_attribute_value(self.value_numeric)} {self.unit}"
            ).strip()

        if self.value_id:
            return self.value.value

        return ""

    @property
    def raw_value(self):
        if self.attribute.type == ProductAttribute.AttributeType.NUMERIC:
            return {
                "type": ProductAttribute.AttributeType.NUMERIC,
                "display_value": self.display_value,
                "value": (
                    float(self.value_numeric)
                    if self.value_numeric is not None
                    else None
                ),
                "value_decimal": (
                    str(self.value_numeric) if self.value_numeric is not None else None
                ),
                "unit": self.unit or None,
            }

        return {
            "type": ProductAttribute.AttributeType.SELECT,
            "display_value": self.display_value,
            "value_id": str(self.value_id) if self.value_id else None,
            "value": self.value.value if self.value_id else None,
            "slug": self.value.slug if self.value_id else None,
        }

    def clean(self):
        errors = {}

        if self.variant_id and self.attribute_id:
            allowed_categories = self.attribute.categories.all()

            if allowed_categories.exists():
                is_allowed_for_category = allowed_categories.filter(
                    id=self.variant.product.category_id
                ).exists()

                if not is_allowed_for_category:
                    errors["attribute"] = (
                        "This attribute is not allowed for product category."
                    )

        if self.attribute_id:
            if self.attribute.type == ProductAttribute.AttributeType.SELECT:
                if self.value_numeric is not None:
                    errors["value_numeric"] = (
                        "Numeric value must be empty for select attribute."
                    )

                if self.unit:
                    errors["unit"] = "Unit must be empty for select attribute."

            elif self.attribute.type == ProductAttribute.AttributeType.NUMERIC:
                if self.value_id:
                    errors["value"] = "Text value must be empty for numeric attribute."

                has_numeric_value = self.value_numeric is not None
                has_unit = bool(self.unit)

                if has_numeric_value and not has_unit:
                    errors["unit"] = "Unit is required when numeric value is filled."

                if has_unit and not has_numeric_value:
                    errors["value_numeric"] = (
                        "Numeric value is required when unit is filled."
                    )

                if self.unit:
                    supported_units = {
                        unit for unit, _label in ProductAttribute.UNIT_CHOICES
                    }

                    if self.unit not in supported_units:
                        errors["unit"] = f'Unsupported unit "{self.unit}".'

                    available_units = self.attribute.available_units or []

                    if available_units and self.unit not in available_units:
                        errors["unit"] = (
                            f'Unit "{self.unit}" is not allowed for this attribute.'
                        )

        if self.value_id and self.attribute_id:
            if self.value.attribute_id != self.attribute_id:
                errors["value"] = (
                    "Selected value does not belong to selected attribute."
                )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.variant} | {self.attribute.name}: {self.display_value}"


class MediaAsset(models.Model):
    """
    Reusable image from media library.

    Admin can upload/select image once and reuse it for:
    - base product images;
    - variant images;
    - future brand/category images if needed.
    """

    SOURCE_MANUAL = "manual"
    SOURCE_CLOUDINARY = "cloudinary"
    SOURCE_EXTERNAL = "external"

    SOURCE_CHOICES = [
        (SOURCE_MANUAL, "Manual"),
        (SOURCE_CLOUDINARY, "Cloudinary"),
        (SOURCE_EXTERNAL, "External URL"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    title = models.CharField(
        max_length=255,
        blank=True,
        help_text="Human-readable name for admin media library.",
    )
    image_url = models.URLField(max_length=1000)
    alt_text = models.CharField(max_length=255, blank=True)

    cloudinary_public_id = models.CharField(
        max_length=255,
        blank=True,
        default="",
        db_index=True,
    )

    source = models.CharField(
        max_length=20,
        choices=SOURCE_CHOICES,
        default=SOURCE_MANUAL,
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "title"]
        indexes = [
            models.Index(fields=["source"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["cloudinary_public_id"]),
        ]
        verbose_name = "Media asset"
        verbose_name_plural = "Media assets"

    def clean(self):
        if not self.image_url:
            raise ValidationError({"image_url": "Image URL is required."})

    def save(self, *args, **kwargs):
        if not self.title:
            self.title = self.generate_title()

        self.full_clean()
        super().save(*args, **kwargs)

    def generate_title(self):
        if self.cloudinary_public_id:
            return self.cloudinary_public_id.split("/")[-1]

        if self.image_url:
            return self.image_url.rstrip("/").split("/")[-1][:255]

        return "Untitled image"

    def __str__(self):
        return self.title or self.image_url


class ProductImage(models.Model):
    """
    Product image.

    If variant is empty: common product image.
    If variant is filled: image belongs to specific variant.

    Image can be selected from MediaAsset library or provided as direct URL.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="images",
    )
    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.CASCADE,
        related_name="images",
        null=True,
        blank=True,
    )

    asset = models.ForeignKey(
        MediaAsset,
        on_delete=models.SET_NULL,
        related_name="product_images",
        null=True,
        blank=True,
        help_text=(
            "Select an existing image from media library. "
            "If selected, image_url and cloudinary_public_id can be filled automatically."
        ),
    )

    image_url = models.URLField(
        max_length=1000,
        blank=True,
        help_text=(
            "Direct image URL fallback. "
            "Can be auto-filled from selected media asset."
        ),
    )
    alt_text = models.CharField(max_length=255, blank=True)
    is_main = models.BooleanField(default=False)
    display_order = models.IntegerField(default=0)
    cloudinary_public_id = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        ordering = ["display_order", "id"]
        indexes = [
            models.Index(fields=["product", "variant"]),
            models.Index(fields=["product", "is_main"]),
            models.Index(fields=["variant", "is_main"]),
            models.Index(fields=["asset"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["product"],
                condition=Q(is_main=True, variant__isnull=True),
                name="unique_main_product_image",
            ),
            models.UniqueConstraint(
                fields=["variant"],
                condition=Q(is_main=True, variant__isnull=False),
                name="unique_main_variant_image",
            ),
        ]

    def clean(self):
        errors = {}

        if self.variant_id and self.product_id:
            if self.variant.product_id != self.product_id:
                errors["variant"] = "Variant must belong to the selected product."

        if not self.asset_id and not self.image_url:
            errors["image_url"] = (
                "Select image from media library or provide direct image URL."
            )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self.asset_id:
            if not self.image_url:
                self.image_url = self.asset.image_url

            if not self.cloudinary_public_id:
                self.cloudinary_public_id = self.asset.cloudinary_public_id

            if not self.alt_text:
                self.alt_text = self.asset.alt_text

        if not self.alt_text and self.product_id:
            self.alt_text = self.product.name

        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        if self.variant_id:
            return f"Image for {self.variant}"

        return f"Image for {self.product.name}"


class ProductReview(models.Model):
    """Product review."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    user = models.ForeignKey(
        Customer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    title = models.CharField(max_length=200)
    comment = models.TextField()

    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["product", "is_active"]),
            models.Index(fields=["user"]),
        ]

    def __str__(self):
        return f"Review for {self.product.name} by {self.user}"


class Cart(models.Model):
    """User shopping cart."""

    user = models.OneToOneField(Customer, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def total_price(self):
        return sum(item.total_price for item in self.items.select_related("variant"))

    @property
    def total_items(self):
        return sum(item.quantity for item in self.items.all())

    def __str__(self):
        return f"Cart for {self.user.email}"


class CartItem(models.Model):
    """
    Cart item.

    Important:
    CartItem references ProductVariant, not Product.
    User adds exact selected variant to cart.
    """

    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name="items",
    )
    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.CASCADE,
        related_name="cart_items",
    )
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["cart", "variant"],
                name="unique_variant_per_cart",
            )
        ]

    def clean(self):
        if self.variant_id:
            if not self.variant.is_active or not self.variant.product.is_active:
                raise ValidationError({"variant": "Selected variant is not available."})

            if self.quantity > self.variant.stock:
                raise ValidationError(
                    {"quantity": "Requested quantity is greater than available stock."}
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def total_price(self):
        return self.variant.price * self.quantity

    def __str__(self):
        return f"{self.variant.product.name} - {self.variant.sku} x {self.quantity}"
