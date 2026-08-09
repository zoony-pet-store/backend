from django.core.management.base import BaseCommand
from django.utils.text import slugify

from shop.models import (
    AnimalType,
    Badge,
    Brand,
    Category,
    ProductAttribute,
    ProductAttributeValue,
)


SELECT_ATTRIBUTES = [
    {
        "name": "Size",
        "slug": "size",
        "values": [
            "Small",
            "Medium",
            "Large",
            "X-Large",
            "1.5kg",
            "2kg",
            "3kg",
            "4kg",
            "5kg",
            "7kg",
            "8kg",
            "10kg",
            "15kg",
            "16kg",
            "12-pack",
            "24-pack",
            "48-pack",
        ],
    },
    {
        "name": "Flavor",
        "slug": "flavor",
        "values": [
            "Chicken",
            "Beef",
            "Fish",
            "Lamb",
            "Turkey",
            "Salmon",
            "Duck",
            "Assorted",
        ],
    },
    {
        "name": "Age",
        "slug": "age",
        "values": [
            "Puppy/Kitten",
            "Adult",
            "Senior",
            "All Life Stages",
        ],
    },
    {
        "name": "Color",
        "slug": "color",
        "values": [
            "Red",
            "Blue",
            "Green",
            "Black",
            "Brown",
            "Gray",
            "Multicolor",
            "White",
        ],
    },
    {
        "name": "Material",
        "slug": "material",
        "values": [
            "Plastic",
            "Rubber",
            "Fabric",
            "Metal",
            "Wood",
            "Silicone",
            "Clay",
        ],
    },
]


NUMERIC_ATTRIBUTES = [
    {
        "name": "Weight",
        "slug": "weight",
        "available_units": ["g", "kg"],
    },
    {
        "name": "Volume",
        "slug": "volume",
        "available_units": ["ml", "l"],
    },
    {
        "name": "Pack count",
        "slug": "pack-count",
        "available_units": ["pcs", "pack"],
    },
]


BADGES = [
    {
        "name": "new",
        "slug": "new",
        "label": "New",
        "color": "#FFFFFF",
        "background_color": "#198754",
    },
    {
        "name": "bestseller",
        "slug": "bestseller",
        "label": "Bestseller",
        "color": "#FFFFFF",
        "background_color": "#FFC107",
    },
    {
        "name": "trending",
        "slug": "trending",
        "label": "Trending",
        "color": "#FFFFFF",
        "background_color": "#0D6EFD",
    },
    {
        "name": "recommended",
        "slug": "recommended",
        "label": "Recommended",
        "color": "#FFFFFF",
        "background_color": "#6F42C1",
    },
]


BRANDS = [
    {
        "name": "Acme Pet Supplies",
        "slug": "acme-pet-supplies",
        "logo_url": "https://via.placeholder.com/150x80/4A90E2/FFFFFF?text=Acme",
    },
    {
        "name": "Royal Canin",
        "slug": "royal-canin",
        "logo_url": "https://via.placeholder.com/150x80/7B68EE/FFFFFF?text=Royal+Canin",
    },
    {
        "name": "Purina",
        "slug": "purina",
        "logo_url": "https://via.placeholder.com/150x80/32CD32/FFFFFF?text=Purina",
    },
    {
        "name": "Hill's Science Diet",
        "slug": "hills-science-diet",
        "logo_url": "https://via.placeholder.com/150x80/FF4500/FFFFFF?text=Hill's",
    },
    {
        "name": "PetLux",
        "slug": "petlux",
        "logo_url": "https://via.placeholder.com/150x80/FFD700/000000?text=PetLux",
    },
    {
        "name": "VetCare",
        "slug": "vetcare",
        "logo_url": "https://via.placeholder.com/150x80/20B2AA/FFFFFF?text=VetCare",
    },
    {
        "name": "PetSafe",
        "slug": "petsafe",
        "logo_url": "https://via.placeholder.com/150x80/9370DB/FFFFFF?text=PetSafe",
    },
    {
        "name": "Kong",
        "slug": "kong",
        "logo_url": "https://via.placeholder.com/150x80/FF6347/FFFFFF?text=KONG",
    },
]


DOG_CATEGORIES = [
    {
        "name": "Food",
        "slug": "food",
        "description": "Dog food and treats",
        "image_url": "https://images.unsplash.com/photo-1565708097881-bbf4ecf47cc1?w=600&h=400&fit=crop",
        "sort_order": 1,
        "children": [
            {
                "name": "Dry Food",
                "slug": "dry-food",
                "sort_order": 1,
                "image_url": "https://images.unsplash.com/photo-1560806887-1e4cd0b6cbd6?w=400&h=300&fit=crop",
            },
            {
                "name": "Wet Food",
                "slug": "wet-food",
                "sort_order": 2,
                "image_url": "https://images.unsplash.com/photo-1623387641168-d9803ddd3f35?w=400&h=300&fit=crop",
            },
            {
                "name": "Medical Food",
                "slug": "medical-food",
                "sort_order": 3,
                "image_url": "https://images.unsplash.com/photo-1576201836106-db1758fd1c97?w=400&h=300&fit=crop",
            },
            {
                "name": "Treats",
                "slug": "treats",
                "sort_order": 4,
                "image_url": "https://images.unsplash.com/photo-1541364983171-a8ba01e95cfc?w=400&h=300&fit=crop",
            },
        ],
    },
    {
        "name": "Care & Hygiene",
        "slug": "care-hygiene",
        "description": "Dog care products",
        "image_url": "https://images.unsplash.com/photo-1509205477838-a534e43a849f?w=600&h=400&fit=crop",
        "sort_order": 2,
        "children": [
            {
                "name": "Care Products",
                "slug": "care-products",
                "sort_order": 1,
                "image_url": "https://images.unsplash.com/photo-1591946614720-90a587da4a36?w=400&h=300&fit=crop",
            },
            {
                "name": "Shampoos",
                "slug": "shampoos",
                "sort_order": 2,
                "image_url": "https://images.unsplash.com/photo-1548192746-dd526f154ed9?w=400&h=300&fit=crop",
            },
            {
                "name": "Brushes & Combs",
                "slug": "brushes-combs",
                "sort_order": 3,
                "image_url": "https://images.unsplash.com/photo-1564561998327-db0cce0c4c5f?w=400&h=300&fit=crop",
            },
        ],
    },
    {
        "name": "Veterinary Pharmacy",
        "slug": "veterinary-pharmacy",
        "description": "Medicines and vitamins for dogs",
        "image_url": "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?w=600&h=400&fit=crop",
        "sort_order": 3,
        "children": [
            {
                "name": "Vitamins",
                "slug": "vitamins",
                "sort_order": 1,
                "image_url": "https://images.unsplash.com/photo-1559757148-5c350d0d3c56?w=400&h=300&fit=crop",
            },
            {
                "name": "Medicines",
                "slug": "medicines",
                "sort_order": 2,
                "image_url": "https://images.unsplash.com/photo-1559757175-0eb30cd8c063?w=400&h=300&fit=crop",
            },
            {
                "name": "Prevention",
                "slug": "prevention",
                "sort_order": 3,
                "image_url": "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=400&h=300&fit=crop",
            },
        ],
    },
    {
        "name": "Walks & Travel",
        "slug": "walks-travel",
        "image_url": "https://images.unsplash.com/photo-1535930749574-1399327ce78f?w=600&h=400&fit=crop",
        "sort_order": 4,
        "children": [
            {
                "name": "Leashes",
                "slug": "leashes",
                "sort_order": 1,
                "image_url": "https://images.unsplash.com/photo-1551326844-4df70f78d0e9?w=400&h=300&fit=crop",
            },
            {
                "name": "Collars",
                "slug": "collars",
                "sort_order": 2,
                "image_url": "https://images.unsplash.com/photo-1598134700628-d2de1b9d0b4a?w=400&h=300&fit=crop",
            },
            {
                "name": "Carriers",
                "slug": "carriers",
                "sort_order": 3,
                "image_url": "https://images.unsplash.com/photo-1596273315327-5f059a2e52c9?w=400&h=300&fit=crop",
            },
        ],
    },
    {
        "name": "Sets & Gifts",
        "slug": "sets-gifts",
        "image_url": "https://images.unsplash.com/photo-1591946653358-5a2e7156cde3?w=600&h=400&fit=crop",
        "sort_order": 5,
        "children": [
            {
                "name": "Gift Sets",
                "slug": "gift-sets",
                "sort_order": 1,
                "image_url": "https://images.unsplash.com/photo-1559056199-5c0a5b5c5c5a?w=400&h=300&fit=crop",
            },
            {
                "name": "Toys",
                "slug": "toys",
                "sort_order": 2,
                "image_url": "https://images.unsplash.com/photo-1548192746-dd526f154ed9?w=400&h=300&fit=crop",
            },
        ],
    },
    {
        "name": "Home Comfort",
        "slug": "home-comfort",
        "image_url": "https://images.unsplash.com/photo-1559715541-5d0a4e8c7c6e?w=600&h=400&fit=crop",
        "sort_order": 6,
        "children": [
            {
                "name": "Beds",
                "slug": "beds",
                "sort_order": 1,
                "image_url": "https://images.unsplash.com/photo-1561037404-61cd46aa615b?w=400&h=300&fit=crop",
            },
            {
                "name": "Bowls",
                "slug": "bowls",
                "sort_order": 2,
                "image_url": "https://images.unsplash.com/photo-1560806887-1e4cd0b6cbd6?w=400&h=300&fit=crop",
            },
            {
                "name": "Houses",
                "slug": "houses",
                "sort_order": 3,
                "image_url": "https://images.unsplash.com/photo-1561037404-61cd46aa615b?w=400&h=300&fit=crop",
            },
        ],
    },
]


CAT_CATEGORIES = [
    {
        "name": "Food",
        "slug": "food",
        "description": "Cat food and treats",
        "image_url": "https://images.unsplash.com/photo-1574231164645-d6f0e8553590?w=600&h=400&fit=crop",
        "sort_order": 1,
        "children": [
            {
                "name": "Dry Food",
                "slug": "dry-food",
                "sort_order": 1,
                "image_url": "https://images.unsplash.com/photo-1608848461950-0fe51dfc41cb?w=400&h=300&fit=crop",
            },
            {
                "name": "Wet Food",
                "slug": "wet-food",
                "sort_order": 2,
                "image_url": "https://images.unsplash.com/photo-1576675466969-38eeae4b41f6?w=400&h=300&fit=crop",
            },
            {
                "name": "Treats",
                "slug": "treats",
                "sort_order": 3,
                "image_url": "https://images.unsplash.com/photo-1591946653358-5a2e7156cde3?w=400&h=300&fit=crop",
            },
        ],
    },
    {
        "name": "Care & Hygiene",
        "slug": "care-hygiene",
        "description": "Cat care products",
        "image_url": "https://images.unsplash.com/photo-1591946625865-df6dbb0e2db0?w=600&h=400&fit=crop",
        "sort_order": 2,
        "children": [
            {
                "name": "Care Products",
                "slug": "care-products",
                "sort_order": 1,
                "image_url": "https://images.unsplash.com/photo-1591946614720-90a587da4a36?w=400&h=300&fit=crop",
            },
            {
                "name": "Shampoos",
                "slug": "shampoos",
                "sort_order": 2,
                "image_url": "https://images.unsplash.com/photo-1548192746-dd526f154ed9?w=400&h=300&fit=crop",
            },
            {
                "name": "Litter & Trays",
                "slug": "litter-trays",
                "sort_order": 3,
                "image_url": "https://images.unsplash.com/photo-1591946614720-90a587da4a36?w=400&h=300&fit=crop",
            },
        ],
    },
    {
        "name": "Veterinary Pharmacy",
        "slug": "veterinary-pharmacy",
        "description": "Medicines and vitamins for cats",
        "image_url": "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?w=600&h=400&fit=crop",
        "sort_order": 3,
        "children": [
            {
                "name": "Vitamins",
                "slug": "vitamins",
                "sort_order": 1,
                "image_url": "https://images.unsplash.com/photo-1559757148-5c350d0d3c56?w=400&h=300&fit=crop",
            },
            {
                "name": "Medicines",
                "slug": "medicines",
                "sort_order": 2,
                "image_url": "https://images.unsplash.com/photo-1559757175-0eb30cd8c063?w=400&h=300&fit=crop",
            },
            {
                "name": "Prevention",
                "slug": "prevention",
                "sort_order": 3,
                "image_url": "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=400&h=300&fit=crop",
            },
        ],
    },
    {
        "name": "Walks & Travel",
        "slug": "walks-travel",
        "image_url": "https://images.unsplash.com/photo-1535930749574-1399327ce78f?w=600&h=400&fit=crop",
        "sort_order": 4,
        "children": [
            {
                "name": "Carriers",
                "slug": "carriers",
                "sort_order": 1,
                "image_url": "https://images.unsplash.com/photo-1596273315327-5f059a2e52c9?w=400&h=300&fit=crop",
            },
            {
                "name": "Travel Accessories",
                "slug": "travel-accessories",
                "sort_order": 2,
                "image_url": "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=400&h=300&fit=crop",
            },
        ],
    },
    {
        "name": "Sets & Gifts",
        "slug": "sets-gifts",
        "image_url": "https://images.unsplash.com/photo-1591946653358-5a2e7156cde3?w=600&h=400&fit=crop",
        "sort_order": 5,
        "children": [
            {
                "name": "Gift Sets",
                "slug": "gift-sets",
                "sort_order": 1,
                "image_url": "https://images.unsplash.com/photo-1559056199-5c0a5b5c5c5a?w=400&h=300&fit=crop",
            },
            {
                "name": "Toys",
                "slug": "toys",
                "sort_order": 2,
                "image_url": "https://images.unsplash.com/photo-1548192746-dd526f154ed9?w=400&h=300&fit=crop",
            },
        ],
    },
    {
        "name": "Home Comfort",
        "slug": "home-comfort",
        "image_url": "https://images.unsplash.com/photo-1559715541-5d0a4e8c7c6e?w=600&h=400&fit=crop",
        "sort_order": 6,
        "children": [
            {
                "name": "Beds",
                "slug": "beds",
                "sort_order": 1,
                "image_url": "https://images.unsplash.com/photo-1561037404-61cd46aa615b?w=400&h=300&fit=crop",
            },
            {
                "name": "Bowls",
                "slug": "bowls",
                "sort_order": 2,
                "image_url": "https://images.unsplash.com/photo-1560806887-1e4cd0b6cbd6?w=400&h=300&fit=crop",
            },
            {
                "name": "Houses",
                "slug": "houses",
                "sort_order": 3,
                "image_url": "https://images.unsplash.com/photo-1561037404-61cd46aa615b?w=400&h=300&fit=crop",
            },
            {
                "name": "Scratching Posts",
                "slug": "scratching-posts",
                "sort_order": 4,
                "image_url": "https://images.unsplash.com/photo-1561037404-61cd46aa615b?w=400&h=300&fit=crop",
            },
        ],
    },
]


class Command(BaseCommand):
    help = "Load base catalog data: animal types, categories, brands, badges, and attributes"

    def add_arguments(self, parser):
        parser.add_argument(
            "--skip-if-exists",
            action="store_true",
            help="Skip if base catalog data already exists",
        )

    def handle(self, *args, **options):
        if options["skip_if_exists"] and self.base_data_exists():
            self.stdout.write("✅ Base catalog data already exists, skipping...")
            return

        self.stdout.write("🚀 Starting to load base catalog data...")

        dog_type, _ = self.create_or_update_animal_type(
            name="Dogs",
            slug="dogs",
            icon="🐕",
        )
        cat_type, _ = self.create_or_update_animal_type(
            name="Cats",
            slug="cats",
            icon="🐈",
        )

        dog_count = self.create_categories(dog_type, DOG_CATEGORIES, "dogs")
        cat_count = self.create_categories(cat_type, CAT_CATEGORIES, "cats")
        brand_count = self.create_brands()
        badge_count = self.create_badges()
        select_attribute_count = self.create_select_attributes()
        numeric_attribute_count = self.create_numeric_attributes()

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS("🎉 Base catalog data loaded successfully")
        )
        self.stdout.write(f"Animal types: {AnimalType.objects.count()}")
        self.stdout.write(f"Dog categories touched: {dog_count}")
        self.stdout.write(f"Cat categories touched: {cat_count}")
        self.stdout.write(f"Brands touched: {brand_count}")
        self.stdout.write(f"Badges touched: {badge_count}")
        self.stdout.write(f"Select attributes touched: {select_attribute_count}")
        self.stdout.write(f"Numeric attributes touched: {numeric_attribute_count}")

        self.stdout.write("")
        self.stdout.write("Next step:")
        self.stdout.write(
            "python manage.py import_mockaroo_products --file MOCK_DATA.csv --replace"
        )

    def base_data_exists(self):
        return (
            AnimalType.objects.filter(slug__in=["dogs", "cats"]).count() == 2
            and Brand.objects.exists()
            and Category.objects.exists()
            and ProductAttribute.objects.exists()
        )

    def create_or_update_animal_type(self, name, slug, icon):
        animal_type, created = AnimalType.objects.get_or_create(
            slug=slug,
            defaults={
                "name": name,
                "icon": icon,
                "is_active": True,
            },
        )

        update_fields = []

        if animal_type.name != name:
            animal_type.name = name
            update_fields.append("name")

        if animal_type.icon != icon:
            animal_type.icon = icon
            update_fields.append("icon")

        if not animal_type.is_active:
            animal_type.is_active = True
            update_fields.append("is_active")

        if update_fields:
            animal_type.save(update_fields=update_fields)

        action = "Created" if created else "Updated"
        self.stdout.write(f"✅ {action} animal type: {animal_type.name}")

        return animal_type, created

    def create_categories(self, animal_type, categories_data, animal_name):
        touched_count = 0

        for category_data in categories_data:
            parent, parent_created = Category.objects.get_or_create(
                slug=category_data["slug"],
                animal_type=animal_type,
                parent=None,
                defaults={
                    "name": category_data["name"],
                    "description": category_data.get("description", ""),
                    "image_url": category_data.get("image_url", ""),
                    "sort_order": category_data["sort_order"],
                    "is_active": True,
                },
            )

            self.update_category(parent, category_data)
            touched_count += 1

            if parent_created:
                self.stdout.write(
                    f"   ✅ Created {animal_name} category: {parent.name}"
                )

            for child_data in category_data.get("children", []):
                child, child_created = Category.objects.get_or_create(
                    parent=parent,
                    slug=child_data["slug"],
                    animal_type=animal_type,
                    defaults={
                        "name": child_data["name"],
                        "description": child_data.get("description", ""),
                        "image_url": child_data.get("image_url", ""),
                        "sort_order": child_data["sort_order"],
                        "is_active": True,
                    },
                )

                self.update_category(child, child_data)
                touched_count += 1

                if child_created:
                    self.stdout.write(
                        f"      ✅ Created {animal_name} subcategory: {child.name}"
                    )

        return touched_count

    def update_category(self, category, category_data):
        update_fields = []

        for field_name in [
            "name",
            "description",
            "image_url",
            "sort_order",
        ]:
            new_value = category_data.get(field_name)

            if new_value is not None and getattr(category, field_name) != new_value:
                setattr(category, field_name, new_value)
                update_fields.append(field_name)

        if not category.is_active:
            category.is_active = True
            update_fields.append("is_active")

        if update_fields:
            category.save(update_fields=update_fields)

    def create_brands(self):
        touched_count = 0

        for brand_data in BRANDS:
            brand, created = Brand.objects.get_or_create(
                slug=brand_data["slug"],
                defaults={
                    "name": brand_data["name"],
                    "logo_url": brand_data.get("logo_url", ""),
                    "is_active": True,
                },
            )

            update_fields = []

            if brand.name != brand_data["name"]:
                brand.name = brand_data["name"]
                update_fields.append("name")

            if brand.logo_url != brand_data.get("logo_url", ""):
                brand.logo_url = brand_data.get("logo_url", "")
                update_fields.append("logo_url")

            if not brand.is_active:
                brand.is_active = True
                update_fields.append("is_active")

            if update_fields:
                brand.save(update_fields=update_fields)

            touched_count += 1

            if created:
                self.stdout.write(f"✅ Created brand: {brand.name}")

        return touched_count

    def create_badges(self):
        touched_count = 0

        for badge_data in BADGES:
            badge, created = Badge.objects.get_or_create(
                slug=badge_data["slug"],
                defaults={
                    "name": badge_data["name"],
                    "label": badge_data["label"],
                    "color": badge_data["color"],
                    "background_color": badge_data["background_color"],
                    "is_active": True,
                },
            )

            update_fields = []

            for field_name in [
                "name",
                "label",
                "color",
                "background_color",
            ]:
                if getattr(badge, field_name) != badge_data[field_name]:
                    setattr(badge, field_name, badge_data[field_name])
                    update_fields.append(field_name)

            if not badge.is_active:
                badge.is_active = True
                update_fields.append("is_active")

            if update_fields:
                badge.save(update_fields=update_fields)

            touched_count += 1

            if created:
                self.stdout.write(f"✅ Created badge: {badge.label}")

        return touched_count

    def create_select_attributes(self):
        touched_count = 0

        for attribute_data in SELECT_ATTRIBUTES:
            attribute, created = ProductAttribute.objects.get_or_create(
                slug=attribute_data["slug"],
                defaults={
                    "name": attribute_data["name"],
                    "type": ProductAttribute.AttributeType.SELECT,
                    "available_units": [],
                    "filterable": True,
                },
            )

            update_fields = []

            if attribute.name != attribute_data["name"]:
                attribute.name = attribute_data["name"]
                update_fields.append("name")

            if attribute.type != ProductAttribute.AttributeType.SELECT:
                attribute.type = ProductAttribute.AttributeType.SELECT
                update_fields.append("type")

            if attribute.available_units:
                attribute.available_units = []
                update_fields.append("available_units")

            if not attribute.filterable:
                attribute.filterable = True
                update_fields.append("filterable")

            if update_fields:
                attribute.save(update_fields=update_fields)

            for index, value in enumerate(attribute_data["values"]):
                value_slug = slugify(value)

                attribute_value, value_created = (
                    ProductAttributeValue.objects.get_or_create(
                        attribute=attribute,
                        slug=value_slug,
                        defaults={
                            "value": value,
                            "display_order": index,
                        },
                    )
                )

                value_update_fields = []

                if attribute_value.value != value:
                    attribute_value.value = value
                    value_update_fields.append("value")

                if attribute_value.display_order != index:
                    attribute_value.display_order = index
                    value_update_fields.append("display_order")

                if value_update_fields:
                    attribute_value.save(update_fields=value_update_fields)

                if value_created:
                    self.stdout.write(
                        f"   ✅ Created value: {attribute.name} / {attribute_value.value}"
                    )

            touched_count += 1

            if created:
                self.stdout.write(f"✅ Created select attribute: {attribute.name}")

        return touched_count

    def create_numeric_attributes(self):
        touched_count = 0

        for attribute_data in NUMERIC_ATTRIBUTES:
            attribute, created = ProductAttribute.objects.get_or_create(
                slug=attribute_data["slug"],
                defaults={
                    "name": attribute_data["name"],
                    "type": ProductAttribute.AttributeType.NUMERIC,
                    "available_units": attribute_data["available_units"],
                    "filterable": True,
                },
            )

            update_fields = []

            if attribute.name != attribute_data["name"]:
                attribute.name = attribute_data["name"]
                update_fields.append("name")

            if attribute.type != ProductAttribute.AttributeType.NUMERIC:
                attribute.type = ProductAttribute.AttributeType.NUMERIC
                update_fields.append("type")

            if attribute.available_units != attribute_data["available_units"]:
                attribute.available_units = attribute_data["available_units"]
                update_fields.append("available_units")

            if not attribute.filterable:
                attribute.filterable = True
                update_fields.append("filterable")

            if update_fields:
                attribute.save(update_fields=update_fields)

            touched_count += 1

            if created:
                self.stdout.write(f"✅ Created numeric attribute: {attribute.name}")

        return touched_count
