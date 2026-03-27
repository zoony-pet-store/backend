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
    ProductImage,
    ProductVariant,
)


class Command(BaseCommand):
    help = "Import products from Mockaroo CSV"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            required=True,
            help="Path to CSV file exported from Mockaroo",
        )

    def handle(self, *args, **options):
        file_path = Path(options["file"])

        if not file_path.exists():
            raise CommandError(f"File not found: {file_path}")

        created_products = 0
        skipped_products = 0
        created_variants = 0
        created_images = 0

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
                "weight",
            }

            missing_fields = required_fields - set(reader.fieldnames or [])
            if missing_fields:
                raise CommandError(
                    f"CSV is missing required fields: {', '.join(sorted(missing_fields))}"
                )

            for row_number, row in enumerate(reader, start=2):
                try:
                    with transaction.atomic():
                        product, image_created, variant_created = self.import_row(row)

                        if product is None:
                            skipped_products += 1
                            self.stdout.write(
                                self.style.WARNING(
                                    f"Skipped row {row_number}: duplicate or invalid product"
                                )
                            )
                            continue

                        created_products += 1
                        if image_created:
                            created_images += 1
                        if variant_created:
                            created_variants += 1

                        self.stdout.write(
                            self.style.SUCCESS(
                                f"Imported row {row_number}: {product.name}"
                            )
                        )

                except Exception as exc:
                    self.stderr.write(
                        self.style.ERROR(f"Row {row_number} failed: {exc}")
                    )

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Import finished"))
        self.stdout.write(f"Created products: {created_products}")
        self.stdout.write(f"Created variants: {created_variants}")
        self.stdout.write(f"Created images: {created_images}")
        self.stdout.write(f"Skipped rows: {skipped_products}")

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

        slug = self.build_unique_product_slug(name, category)

        existing_product = Product.objects.filter(slug=slug, category=category).first()
        if existing_product:
            return None, False, False

        price = self.parse_decimal(row.get("price"), required=True)
        old_price = self.parse_decimal(row.get("old_price"), required=False)
        stock = self.parse_int(row.get("stock"), default=0)
        weight = self.parse_decimal(row.get("weight"), required=False)

        if old_price is not None and old_price <= price:
            old_price = None

        has_discount = old_price is not None and old_price > price

        product = Product.objects.create(
            name=name,
            slug=slug,
            description=description or "",
            short_description=short_description or "",
            brand=brand,
            category=category,
            is_active=True,
            rating=0,
            review_count=0,
            main_image=main_image or "",
        )

        image_created = False
        if main_image:
            ProductImage.objects.create(
                product=product,
                image_url=main_image,
                alt_text=name,
                is_main=True,
                display_order=0,
            )
            image_created = True

        sku = self.generate_sku(product)
        variant = ProductVariant.objects.create(
            product=product,
            sku=sku,
            price=price,
            old_price=old_price,
            stock=stock,
            is_active=True,
            has_discount=has_discount,
            weight=weight,
        )
        variant_created = True

        self.attach_attribute_if_present(variant, "Size", row.get("size"))
        self.attach_attribute_if_present(variant, "Color", row.get("color"))
        self.attach_attribute_if_present(variant, "Material", row.get("material"))
        self.attach_attribute_if_present(variant, "Flavor", row.get("flavor"))
        self.attach_attribute_if_present(variant, "Age", row.get("age"))

        return product, image_created, variant_created

    def get_category_by_path(self, category_path):
        parts = category_path.strip("/").split("/")
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

        attribute = ProductAttribute.objects.filter(name=attribute_name).first()
        if not attribute:
            return

        attr_value, _ = ProductAttributeValue.objects.get_or_create(
            attribute=attribute,
            slug=slugify(value),
            defaults={"value": value},
        )
        variant.attributes.add(attr_value)

    def build_unique_product_slug(self, name, category):
        base_slug = slugify(name)
        slug = base_slug
        counter = 1

        while Product.objects.filter(slug=slug, category=category).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1

        return slug

    def generate_sku(self, product):
        return (
            f"MOCK-{slugify(product.name)[:20].upper()}-{uuid.uuid4().hex[:6].upper()}"
        )

    def clean_value(self, value):
        if value is None:
            return None
        value = str(value).strip()
        return value or None

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
