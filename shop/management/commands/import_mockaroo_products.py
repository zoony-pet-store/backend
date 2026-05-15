import csv
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
    ProductCharacteristic,
    ProductImage,
    ProductVariant,
    ProductVariantAttribute,
)


ATTRIBUTE_COLUMNS = {
    "size": "Size",
    "color": "Color",
    "material": "Material",
    "flavor": "Flavor",
    "age": "Age",
}


class Command(BaseCommand):
    help = "Import products from Mockaroo CSV"

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

        if options["replace"]:
            deleted_count = self.delete_existing_mock_products()
            self.stdout.write(
                self.style.WARNING(f"Deleted existing mock products: {deleted_count}")
            )

        created_products = 0
        reused_products = 0
        created_variants = 0
        created_product_images = 0
        created_variant_images = 0
        skipped_rows = 0

        with file_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
            reader = csv.DictReader(csv_file)

            required_fields = {
                "name",
                "short_description",
                "description",
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
                    f"CSV is missing required fields: "
                    f"{', '.join(sorted(missing_fields))}"
                )

            for row_number, row in enumerate(reader, start=2):
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
                            f"{result['product'].name} / {result['variant'].sku}"
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

    def delete_existing_mock_products(self):
        """
        Deletes products that were imported as mock data.

        We identify them by variants with SKU starting with MOCK-.
        Since ProductImage, ProductVariant, ProductVariantAttribute and structured
        content section rows are linked by CASCADE, deleting Product will clean
        related mock data too.
        """
        product_ids = (
            Product.objects.filter(variants__sku__startswith="MOCK-")
            .values_list("id", flat=True)
            .distinct()
        )

        queryset = Product.objects.filter(id__in=product_ids)
        count = queryset.count()
        queryset.delete()

        return count

    def import_row(self, row):
        name = self.clean_value(row.get("name"))
        short_description = self.clean_value(row.get("short_description"))
        description = self.clean_value(row.get("description"))
        brand_slug = self.clean_value(row.get("brand_slug"))
        category_path = self.clean_value(row.get("category_path"))
        main_image = self.clean_value(row.get("main_image"))

        if not name or not brand_slug or not category_path or not row.get("price"):
            raise CommandError(
                "name, brand_slug, category_path, and price are required"
            )

        brand = Brand.objects.filter(slug=brand_slug, is_active=True).first()
        if not brand:
            raise CommandError(f"Brand not found: {brand_slug}")

        category = self.get_category_by_path(category_path)
        if not category:
            raise CommandError(f"Category not found for path: {category_path}")

        product, product_created = self.get_or_create_product(
            name=name,
            brand=brand,
            category=category,
            short_description=short_description,
            description=description,
            main_image=main_image,
        )

        self.sync_product_characteristics(
            product=product,
            row=row,
            brand=brand,
            category=category,
        )

        price = self.parse_decimal(row.get("price"), required=True)
        old_price = self.parse_decimal(row.get("old_price"), required=False)
        stock = self.parse_int(row.get("stock"), default=0)

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

        for column_name, attribute_name in ATTRIBUTE_COLUMNS.items():
            self.attach_attribute_if_present(
                variant=variant,
                attribute_name=attribute_name,
                raw_value=row.get(column_name),
            )

        product_image_created = False
        variant_image_created = False

        if main_image:
            product_image_created = self.ensure_product_image(
                product=product,
                image_url=main_image,
                alt_text=name,
                is_main=is_default,
            )

            variant_image_created = self.create_variant_image(
                product=product,
                variant=variant,
                image_url=main_image,
                alt_text=name,
                is_main=True,
            )

        return {
            "product": product,
            "variant": variant,
            "product_created": product_created,
            "variant_created": True,
            "product_image_created": product_image_created,
            "variant_image_created": variant_image_created,
        }

    def get_or_create_product(
        self,
        name,
        brand,
        category,
        short_description,
        description,
        main_image,
    ):
        """
        Reuse product if same name + brand + category already exists.

        This allows CSV to contain several rows for the same product,
        where each row represents a separate variant.
        """
        product = Product.objects.filter(
            name=name,
            brand=brand,
            category=category,
        ).first()

        if product:
            product.description = description or product.description
            product.short_description = short_description or product.short_description
            product.main_image = main_image or product.main_image
            product.is_active = True
            product.save(
                update_fields=[
                    "description",
                    "short_description",
                    "main_image",
                    "is_active",
                    "updated_at",
                ]
            )
            return product, False

        product = Product.objects.create(
            name=name,
            slug=self.build_unique_product_slug(name, category),
            description=description or "",
            short_description=short_description or "",
            brand=brand,
            category=category,
            is_active=True,
            rating=0,
            review_count=0,
            main_image=main_image or "",
        )

        return product, True

    def sync_product_characteristics(self, product, row, brand, category):
        """
        Populate the admin-friendly Characteristics section from CSV data.

        We intentionally do not create Typical Analysis or Feeding Guidelines here,
        because the current Mockaroo CSV does not contain reliable columns for them.
        """
        values = {
            "Animal": category.animal_type.name,
            "Brand": brand.name,
            "Product group": category.name,
        }

        for column_name, attribute_name in ATTRIBUTE_COLUMNS.items():
            value = self.clean_value(row.get(column_name))
            if value:
                values[attribute_name] = value

        for label, value in values.items():
            characteristic = (
                ProductCharacteristic.objects.filter(
                    product=product,
                    label=label,
                )
                .order_by("created_at")
                .first()
            )

            if characteristic:
                if characteristic.value != value:
                    characteristic.value = value
                    characteristic.save(update_fields=["value"])
            else:
                ProductCharacteristic.objects.create(
                    product=product,
                    label=label,
                    value=value,
                )

    def ensure_product_image(self, product, image_url, alt_text, is_main=False):
        """
        Create product-level image only if the same image does not already exist.

        Product-level image has variant=None.
        """
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

    def create_variant_image(self, product, variant, image_url, alt_text, is_main=True):
        """
        Create variant-specific image.

        This lets frontend switch image when user selects another variant.
        """
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

    def get_category_by_path(self, category_path):
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

    def attach_attribute_if_present(self, variant, attribute_name, raw_value):
        value = self.clean_value(raw_value)

        if not value:
            return

        attribute_slug = slugify(attribute_name)
        value_slug = slugify(value)

        attribute, _ = ProductAttribute.objects.get_or_create(
            slug=attribute_slug,
            defaults={
                "name": attribute_name,
                "filterable": True,
            },
        )

        attr_value, _ = ProductAttributeValue.objects.get_or_create(
            attribute=attribute,
            slug=value_slug,
            defaults={
                "value": value,
            },
        )

        ProductVariantAttribute.objects.update_or_create(
            variant=variant,
            attribute=attribute,
            defaults={
                "value": attr_value,
            },
        )

    def build_unique_product_slug(self, name, category):
        base_slug = slugify(name)
        slug = base_slug
        counter = 1

        while Product.objects.filter(slug=slug, category=category).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1

        return slug

    def generate_sku(self, product):
        product_slug_part = slugify(product.name).replace("-", "").upper()[:20]
        suffix = uuid.uuid4().hex[:6].upper()

        return f"MOCK-{product_slug_part}-{suffix}"

    def clean_value(self, value):
        if value is None:
            return None

        value = str(value).strip()

        if not value:
            return None

        if value.lower() in ["nan", "none", "null"]:
            return None

        return value

    def parse_decimal(self, value, required=False):
        value = self.clean_value(value)

        if value is None:
            if required:
                raise CommandError("Missing required decimal value")
            return None

        try:
            return Decimal(value)
        except (InvalidOperation, TypeError):
            if required:
                raise CommandError(f"Invalid decimal value: {value}")
            return None

    def parse_int(self, value, default=0):
        value = self.clean_value(value)

        if value is None:
            return default

        try:
            return int(Decimal(value))
        except (InvalidOperation, TypeError, ValueError):
            return default
