import csv
import re
import uuid
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

from shop.models import (
    AnimalType,
    Brand,
    Category,
    Product,
    ProductAttribute,
    ProductAttributeValue,
    ProductImage,
    ProductTranslation,
    ProductVariant,
    ProductVariantAttribute,
)


ENGLISH_LANGUAGE = "en"


# CSV column -> stable ProductAttribute slug.
SELECT_ATTRIBUTE_COLUMNS = {
    "size": "size",
    "color": "color",
    "material": "material",
    "flavor": "flavor",
    "age": "age",
}


NUMERIC_ATTRIBUTE_COLUMNS = {
    "weight": {
        "attribute_slug": "weight",
        "value_column": "weight_value",
        "unit_column": "weight_unit",
        "available_units": ["g", "kg"],
        "default_unit": "kg",
    },
    "volume": {
        "attribute_slug": "volume",
        "value_column": "volume_value",
        "unit_column": "volume_unit",
        "available_units": ["ml", "l"],
        "default_unit": "ml",
    },
    "pack_count": {
        "attribute_slug": "pack-count",
        "value_column": "pack_count_value",
        "unit_column": "pack_count_unit",
        "available_units": ["pcs", "pack"],
        "default_unit": "pack",
    },
}


NUMERIC_VALUE_WITH_UNIT_PATTERN = re.compile(
    r"^\s*(?P<value>\d+(?:[.,]\d+)?)\s*-?\s*" r"(?P<unit>kg|g|ml|l|pcs|pack|packs)\s*$",
    re.IGNORECASE,
)


class Command(BaseCommand):
    help = (
        "Import Mockaroo products with Ukrainian base content "
        "and English translations"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            required=True,
            help="Path to CSV file exported from Mockaroo",
        )
        parser.add_argument(
            "--replace",
            action="store_true",
            help="Delete previously imported MOCK products before import",
        )

    def handle(self, *args, **options):
        file_path = Path(options["file"])

        if not file_path.exists():
            raise CommandError(f"File not found: {file_path}")

        created_products = 0
        reused_products = 0
        created_variants = 0
        created_product_images = 0
        created_variant_images = 0
        skipped_rows = 0

        with file_path.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as csv_file:
            reader = csv.DictReader(csv_file)

            required_fields = {
                "name",
                "name_uk",
                "short_description",
                "short_description_uk",
                "description",
                "description_uk",
                "brand_slug",
                "category_path",
                "main_image",
                "price",
                "old_price",
                "stock",
                "size",
                "color",
                "material",
                "flavor",
                "age",
            }

            missing_fields = required_fields - set(reader.fieldnames or [])

            if missing_fields:
                raise CommandError(
                    "CSV is missing required fields: "
                    f"{', '.join(sorted(missing_fields))}"
                )

            rows = list(reader)
            self.validate_rows(rows)

            # Delete old mock products only after the CSV structure
            # and required row values have been validated.
            if options["replace"]:
                deleted_count = self.delete_existing_mock_products()
                self.stdout.write(
                    self.style.WARNING(
                        f"Deleted existing mock products: {deleted_count}"
                    )
                )

            for row_number, row in enumerate(rows, start=2):
                try:
                    with transaction.atomic():
                        result = self.import_row(row)

                    if result["product_created"]:
                        created_products += 1
                    else:
                        reused_products += 1

                    if result["variant_created"]:
                        created_variants += 1

                    if result["product_image_created"]:
                        created_product_images += 1

                    if result["variant_image_created"]:
                        created_variant_images += 1

                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Imported row {row_number}: "
                            f"{result['product'].name} / "
                            f"{result['variant'].sku}"
                        )
                    )

                except Exception as exc:
                    skipped_rows += 1
                    self.stderr.write(
                        self.style.ERROR(f"Row {row_number} failed: {exc}")
                    )

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Import finished"))
        self.stdout.write(f"Created products: {created_products}")
        self.stdout.write(f"Reused products: {reused_products}")
        self.stdout.write(f"Created variants: {created_variants}")
        self.stdout.write(f"Created product images: {created_product_images}")
        self.stdout.write(f"Created variant images: {created_variant_images}")
        self.stdout.write(f"Skipped rows: {skipped_rows}")

    def validate_rows(self, rows):
        errors = []

        for row_number, row in enumerate(rows, start=2):
            missing_values = []

            for field_name in (
                "name",
                "name_uk",
                "brand_slug",
                "category_path",
                "price",
            ):
                if not self.clean_value(row.get(field_name)):
                    missing_values.append(field_name)

            if missing_values:
                errors.append(f"row {row_number}: {', '.join(missing_values)}")

        if errors:
            preview = "; ".join(errors[:10])

            if len(errors) > 10:
                preview += f"; ... and {len(errors) - 10} more"

            raise CommandError(
                "CSV contains rows with missing required values: " f"{preview}"
            )

    def delete_existing_mock_products(self):
        product_ids = (
            Product.objects.filter(variants__sku__startswith="MOCK-")
            .values_list(
                "id",
                flat=True,
            )
            .distinct()
        )

        queryset = Product.objects.filter(id__in=product_ids)
        count = queryset.count()
        queryset.delete()

        return count

    def import_row(self, row):
        name_en = self.clean_value(row.get("name"))
        name_uk = self.clean_value(row.get("name_uk"))

        short_description_en = self.clean_value(row.get("short_description"))
        short_description_uk = self.clean_value(row.get("short_description_uk"))

        description_en = self.clean_value(row.get("description"))
        description_uk = self.clean_value(row.get("description_uk"))

        brand_slug = self.clean_value(row.get("brand_slug"))
        category_path = self.clean_value(row.get("category_path"))
        main_image = self.clean_value(row.get("main_image"))

        if (
            not name_en
            or not name_uk
            or not brand_slug
            or not category_path
            or not row.get("price")
        ):
            raise CommandError(
                "name, name_uk, brand_slug, " "category_path, and price are required"
            )

        brand = Brand.objects.filter(
            slug=brand_slug,
            is_active=True,
        ).first()

        if not brand:
            raise CommandError(f"Brand not found: {brand_slug}")

        category = self.get_category_by_path(category_path)

        if not category:
            raise CommandError(f"Category not found for path: " f"{category_path}")

        product, product_created = self.get_or_create_product(
            name_uk=name_uk,
            name_en=name_en,
            brand=brand,
            category=category,
            short_description_uk=(short_description_uk),
            short_description_en=(short_description_en),
            description_uk=description_uk,
            description_en=description_en,
            main_image=main_image,
        )

        self.sync_product_content_blocks(
            product=product,
            row=row,
            brand=brand,
            category=category,
        )

        price = self.parse_decimal(
            row.get("price"),
            required=True,
        )
        old_price = self.parse_decimal(
            row.get("old_price"),
            required=False,
        )
        stock = self.parse_int(
            row.get("stock"),
            default=0,
        )

        if old_price is not None and old_price <= price:
            old_price = None

        is_default = not product.variants.exists()

        variant = ProductVariant.objects.create(
            product=product,
            sku=self.generate_sku(product),
            price=price,
            old_price=old_price,
            stock=stock,
            is_active=True,
            is_default=is_default,
        )

        for (
            column_name,
            attribute_slug,
        ) in SELECT_ATTRIBUTE_COLUMNS.items():
            raw_value = row.get(column_name)

            if self.is_numeric_size_value(
                column_name=column_name,
                raw_value=raw_value,
            ):
                continue

            self.attach_select_attribute_if_present(
                variant=variant,
                attribute_slug=attribute_slug,
                raw_value=raw_value,
            )

        for numeric_attribute in self.get_numeric_attributes_from_row(row):
            self.attach_numeric_attribute_if_present(
                variant=variant,
                attribute_slug=numeric_attribute["attribute_slug"],
                raw_value=numeric_attribute["value"],
                raw_unit=numeric_attribute["unit"],
                available_units=numeric_attribute["available_units"],
                default_unit=numeric_attribute["default_unit"],
            )

        product_image_created = False
        variant_image_created = False

        if main_image:
            product_image_created = self.ensure_product_image(
                product=product,
                image_url=main_image,
                alt_text=name_uk,
                is_main=is_default,
            )

            variant_image_created = self.create_variant_image(
                product=product,
                variant=variant,
                image_url=main_image,
                alt_text=name_uk,
                is_main=True,
            )

        return {
            "product": product,
            "variant": variant,
            "product_created": product_created,
            "variant_created": True,
            "product_image_created": (product_image_created),
            "variant_image_created": (variant_image_created),
        }

    def get_or_create_product(
        self,
        name_uk,
        name_en,
        brand,
        category,
        short_description_uk,
        short_description_en,
        description_uk,
        description_en,
        main_image,
    ):
        english_translation = (
            ProductTranslation.objects.filter(
                product__brand=brand,
                product__category=category,
                language=ENGLISH_LANGUAGE,
                name=name_en,
            )
            .select_related("product")
            .first()
        )

        product = english_translation.product if english_translation else None

        # Current localized representation.
        if product is None:
            product = Product.objects.filter(
                name=name_uk,
                brand=brand,
                category=category,
            ).first()

        # Legacy fallback: old mock products stored
        # English directly in base fields.
        if product is None:
            product = Product.objects.filter(
                name=name_en,
                brand=brand,
                category=category,
            ).first()

        product_created = product is None

        if product_created:
            product = Product.objects.create(
                name=name_uk,
                slug=self.build_unique_product_slug(
                    name_en,
                    category,
                ),
                description=description_uk or "",
                short_description=(short_description_uk or ""),
                brand=brand,
                category=category,
                is_active=True,
                rating=0,
                review_count=0,
                main_image=main_image or "",
            )

        else:
            product.name = name_uk
            product.description = description_uk or ""
            product.short_description = short_description_uk or ""
            product.main_image = main_image or product.main_image
            product.is_active = True

            product.save(
                update_fields=[
                    "name",
                    "description",
                    "short_description",
                    "main_image",
                    "is_active",
                    "updated_at",
                ]
            )

        ProductTranslation.objects.update_or_create(
            product=product,
            language=ENGLISH_LANGUAGE,
            defaults={
                "name": name_en,
                "description": description_en or "",
                "short_description": (short_description_en or ""),
            },
        )

        return product, product_created

    def sync_product_content_blocks(
        self,
        product,
        row,
        brand,
        category,
    ):
        items_uk = [
            {
                "key": "Тварина",
                "value": category.animal_type.name,
            },
            {
                "key": "Бренд",
                "value": brand.name,
            },
            {
                "key": "Група товару",
                "value": category.name,
            },
        ]

        items_en = [
            {
                "key": "Animal",
                "value": (
                    self.get_required_translation_value(
                        category.animal_type,
                        "name",
                    )
                ),
            },
            {
                "key": "Brand",
                "value": brand.name,
            },
            {
                "key": "Product group",
                "value": (
                    self.get_required_translation_value(
                        category,
                        "name",
                    )
                ),
            },
        ]

        for (
            column_name,
            attribute_slug,
        ) in SELECT_ATTRIBUTE_COLUMNS.items():
            raw_value_en = self.clean_value(row.get(column_name))

            if not raw_value_en:
                continue

            if self.is_numeric_size_value(
                column_name=column_name,
                raw_value=raw_value_en,
            ):
                continue

            attribute = self.get_required_attribute(
                attribute_slug=attribute_slug,
                expected_type=(ProductAttribute.AttributeType.SELECT),
            )

            attribute_value = self.get_required_attribute_value(
                attribute=attribute,
                raw_value_en=raw_value_en,
            )

            self.append_content_item_once(
                items=items_uk,
                key=attribute.name,
                value=attribute_value.value,
            )

            self.append_content_item_once(
                items=items_en,
                key=self.get_required_translation_value(
                    attribute,
                    "name",
                ),
                value=self.get_required_translation_value(
                    attribute_value,
                    "value",
                ),
            )

        for numeric_attribute in self.get_numeric_attributes_from_row(row):
            value = self.parse_decimal(
                numeric_attribute["value"],
                required=False,
            )

            if value is None:
                continue

            unit = (
                self.normalize_unit(numeric_attribute["unit"])
                or numeric_attribute["default_unit"]
            )

            attribute = self.get_required_attribute(
                attribute_slug=numeric_attribute["attribute_slug"],
                expected_type=(ProductAttribute.AttributeType.NUMERIC),
            )

            display_value_uk = self.format_numeric_display(
                value=value,
                unit=unit,
                language="uk",
            )
            display_value_en = self.format_numeric_display(
                value=value,
                unit=unit,
                language=ENGLISH_LANGUAGE,
            )

            self.append_content_item_once(
                items=items_uk,
                key=attribute.name,
                value=display_value_uk,
            )

            self.append_content_item_once(
                items=items_en,
                key=self.get_required_translation_value(
                    attribute,
                    "name",
                ),
                value=display_value_en,
            )

        content_blocks_uk = [
            {
                # Stable frontend identifier.
                # Do not translate this key.
                "key": "characteristics",
                "type": "key_value",
                "title": "Характеристики",
                "content": {
                    "items": items_uk,
                },
            }
        ]

        content_blocks_en = [
            {
                "key": "characteristics",
                "type": "key_value",
                "title": "Characteristics",
                "content": {
                    "items": items_en,
                },
            }
        ]

        product.content_blocks = content_blocks_uk
        product.save(
            update_fields=[
                "content_blocks",
                "updated_at",
            ]
        )

        english_translation = ProductTranslation.objects.get(
            product=product,
            language=ENGLISH_LANGUAGE,
        )

        english_translation.content_blocks = content_blocks_en
        english_translation.save(update_fields=["content_blocks"])

    def append_content_item_once(
        self,
        items,
        key,
        value,
    ):
        existing_keys = {item["key"] for item in items}

        if key in existing_keys:
            return

        items.append(
            {
                "key": key,
                "value": value,
            }
        )

    def ensure_product_image(
        self,
        product,
        image_url,
        alt_text,
        is_main=False,
    ):
        exists = ProductImage.objects.filter(
            product=product,
            variant__isnull=True,
            image_url=image_url,
        ).exists()

        if exists:
            return False

        if is_main:
            ProductImage.objects.filter(
                product=product,
                variant__isnull=True,
                is_main=True,
            ).update(is_main=False)

        ProductImage.objects.create(
            product=product,
            variant=None,
            image_url=image_url,
            alt_text=alt_text,
            is_main=is_main,
            display_order=0,
        )

        return True

    def create_variant_image(
        self,
        product,
        variant,
        image_url,
        alt_text,
        is_main=True,
    ):
        if is_main:
            ProductImage.objects.filter(
                product=product,
                variant=variant,
                is_main=True,
            ).update(is_main=False)

        ProductImage.objects.create(
            product=product,
            variant=variant,
            image_url=image_url,
            alt_text=alt_text,
            is_main=is_main,
            display_order=0,
        )

        return True

    def get_category_by_path(
        self,
        category_path,
    ):
        parts = [part for part in category_path.strip("/").split("/") if part]

        if len(parts) < 2:
            return None

        animal_type_slug = parts[0]
        category_slugs = parts[1:]

        animal_type = AnimalType.objects.filter(
            slug=animal_type_slug,
            is_active=True,
        ).first()

        if not animal_type:
            return None

        current = Category.objects.filter(
            animal_type=animal_type,
            slug=category_slugs[0],
            parent__isnull=True,
            is_active=True,
        ).first()

        if not current:
            return None

        for slug in category_slugs[1:]:
            current = Category.objects.filter(
                animal_type=animal_type,
                slug=slug,
                parent=current,
                is_active=True,
            ).first()

            if not current:
                return None

        return current

    def attach_select_attribute_if_present(
        self,
        variant,
        attribute_slug,
        raw_value,
    ):
        value_en = self.clean_value(raw_value)

        if not value_en:
            return

        attribute = self.get_required_attribute(
            attribute_slug=attribute_slug,
            expected_type=(ProductAttribute.AttributeType.SELECT),
        )

        attribute_value = self.get_required_attribute_value(
            attribute=attribute,
            raw_value_en=value_en,
        )

        ProductVariantAttribute.objects.update_or_create(
            variant=variant,
            attribute=attribute,
            defaults={
                "value": attribute_value,
                "value_numeric": None,
                "unit": "",
            },
        )

    def attach_numeric_attribute_if_present(
        self,
        variant,
        attribute_slug,
        raw_value,
        raw_unit,
        available_units,
        default_unit,
    ):
        value = self.parse_decimal(
            raw_value,
            required=False,
        )

        if value is None:
            return

        unit = self.normalize_unit(raw_unit) or default_unit

        if unit not in available_units:
            raise CommandError(
                f'Unit "{unit}" is not allowed '
                f'for numeric attribute "{attribute_slug}".'
            )

        attribute = self.get_required_attribute(
            attribute_slug=attribute_slug,
            expected_type=(ProductAttribute.AttributeType.NUMERIC),
        )

        if attribute.available_units != available_units:
            raise CommandError(
                f'Attribute "{attribute.slug}" has '
                f"unexpected available units: "
                f"{attribute.available_units}. "
                f"Expected: {available_units}. "
                f"Run load_initial_data first."
            )

        ProductVariantAttribute.objects.update_or_create(
            variant=variant,
            attribute=attribute,
            defaults={
                "value": None,
                "value_numeric": value,
                "unit": unit,
            },
        )

    def is_numeric_size_value(
        self,
        column_name,
        raw_value,
    ):
        if column_name != "size":
            return False

        return self.infer_numeric_attribute_from_text(raw_value) is not None

    def get_numeric_attributes_from_row(
        self,
        row,
    ):
        numeric_attributes_by_slug = {}

        inferred_attribute = self.infer_numeric_attribute_from_text(row.get("size"))

        if inferred_attribute:
            numeric_attributes_by_slug[inferred_attribute["attribute_slug"]] = (
                inferred_attribute
            )

        for config in NUMERIC_ATTRIBUTE_COLUMNS.values():
            value = self.parse_decimal(
                row.get(config["value_column"]),
                required=False,
            )

            if value is None:
                continue

            unit = self.normalize_unit(row.get(config["unit_column"]))

            numeric_attributes_by_slug[config["attribute_slug"]] = {
                "attribute_slug": (config["attribute_slug"]),
                "value": value,
                "unit": (unit or config["default_unit"]),
                "available_units": (config["available_units"]),
                "default_unit": (config["default_unit"]),
            }

        return list(numeric_attributes_by_slug.values())

    def infer_numeric_attribute_from_text(
        self,
        raw_value,
    ):
        value = self.clean_value(raw_value)

        if not value:
            return None

        match = NUMERIC_VALUE_WITH_UNIT_PATTERN.match(value)

        if not match:
            return None

        number = match.group("value").replace(",", ".")
        unit = self.normalize_unit(match.group("unit"))

        if unit in ["g", "kg"]:
            config = NUMERIC_ATTRIBUTE_COLUMNS["weight"]
        elif unit in ["ml", "l"]:
            config = NUMERIC_ATTRIBUTE_COLUMNS["volume"]
        elif unit in ["pcs", "pack"]:
            config = NUMERIC_ATTRIBUTE_COLUMNS["pack_count"]
        else:
            return None

        return {
            "attribute_slug": (config["attribute_slug"]),
            "value": number,
            "unit": unit,
            "available_units": (config["available_units"]),
            "default_unit": (config["default_unit"]),
        }

    def get_required_attribute(
        self,
        attribute_slug,
        expected_type=None,
    ):
        attribute = ProductAttribute.objects.filter(
            slug=attribute_slug,
        ).first()

        if not attribute:
            raise CommandError(
                f'Attribute "{attribute_slug}" '
                f"not found. "
                f"Run load_initial_data first."
            )

        if expected_type is not None and attribute.type != expected_type:
            raise CommandError(
                f'Attribute "{attribute.name}" '
                f'has type "{attribute.type}", '
                f'expected "{expected_type}".'
            )

        return attribute

    def get_required_attribute_value(
        self,
        attribute,
        raw_value_en,
    ):
        attribute_value = (
            ProductAttributeValue.objects.filter(
                attribute=attribute,
                translations__language=ENGLISH_LANGUAGE,
                translations__value=raw_value_en,
            )
            .distinct()
            .first()
        )

        if not attribute_value:
            raise CommandError(
                f'Attribute value "{raw_value_en}" '
                f'not found for "{attribute.name}". '
                f"Run load_initial_data first."
            )

        return attribute_value

    def get_required_translation_value(
        self,
        obj,
        field_name,
    ):
        translations_manager = getattr(
            obj,
            "translations",
            None,
        )

        if translations_manager is None:
            raise CommandError(f"{obj._meta.label} does not " f"support translations.")

        translation = translations_manager.filter(
            language=ENGLISH_LANGUAGE,
        ).first()

        if translation is None:
            raise CommandError(
                f"English translation missing for "
                f"{obj._meta.label} "
                f"id={obj.pk}. "
                f"Run load_initial_data first."
            )

        value = getattr(
            translation,
            field_name,
            None,
        )

        if value in (
            None,
            "",
            [],
            {},
        ):
            raise CommandError(
                f"English translation field "
                f'"{field_name}" is empty for '
                f"{obj._meta.label} "
                f"id={obj.pk}."
            )

        return value

    def normalize_unit(
        self,
        raw_unit,
    ):
        unit = self.clean_value(raw_unit)

        if not unit:
            return None

        unit = unit.lower()

        if unit == "packs":
            return "pack"

        return unit

    def build_unique_product_slug(
        self,
        name_en,
        category,
    ):
        base_slug = slugify(name_en)

        if not base_slug:
            raise CommandError(
                f"Could not generate slug from " f'English product name "{name_en}".'
            )

        slug = base_slug
        counter = 1

        while Product.objects.filter(
            slug=slug,
            category=category,
        ).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1

        return slug

    def generate_sku(
        self,
        product,
    ):
        product_slug_part = product.slug.replace("-", "").upper()[:20]

        suffix = uuid.uuid4().hex[:6].upper()

        return f"MOCK-" f"{product_slug_part}-" f"{suffix}"

    def clean_value(
        self,
        value,
    ):
        if value is None:
            return None

        value = str(value).strip()

        if not value:
            return None

        if value.lower() in [
            "nan",
            "none",
            "null",
        ]:
            return None

        return value

    def parse_decimal(
        self,
        value,
        required=False,
    ):
        value = self.clean_value(value)

        if value is None:
            if required:
                raise CommandError("Missing required decimal value")

            return None

        try:
            return Decimal(value)

        except (
            InvalidOperation,
            TypeError,
        ):
            if required:
                raise CommandError(f"Invalid decimal value: {value}")

            return None

    def parse_int(
        self,
        value,
        default=0,
    ):
        value = self.clean_value(value)

        if value is None:
            return default

        try:
            return int(Decimal(value))

        except (
            InvalidOperation,
            TypeError,
            ValueError,
        ):
            return default

    def format_numeric_display(
        self,
        value,
        unit,
        language,
    ):
        number = self.format_decimal(value)

        if language == "uk":
            number = number.replace(".", ",")
            unit_labels = {
                "g": "г",
                "kg": "кг",
                "ml": "мл",
                "l": "л",
                "pcs": "шт.",
                "pack": "уп.",
            }
        else:
            unit_labels = {
                "g": "g",
                "kg": "kg",
                "ml": "ml",
                "l": "l",
                "pcs": "pcs",
                "pack": "pack",
            }

        return f"{number} {unit_labels.get(unit, unit)}"

    def format_decimal(
        self,
        value,
    ):
        normalized_value = value.normalize()
        display_value = format(
            normalized_value,
            "f",
        )

        if "." in display_value:
            display_value = display_value.rstrip("0").rstrip(".")

        return display_value
