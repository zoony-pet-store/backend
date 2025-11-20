from django.core.management.base import BaseCommand
from shop.models import Category, AnimalType


class Command(BaseCommand):
    help = "Load initial categories data for dogs and cats"

    def add_arguments(self, parser):
        parser.add_argument(
            "--skip-if-exists",
            action="store_true",
            help="Skip if data already exists",
        )

    def handle(self, *args, **options):
        if options["skip_if_exists"] and AnimalType.objects.exists():
            self.stdout.write("✅ Data already exists, skipping...")
            return

        self.stdout.write("🚀 Starting to load initial data...")

        # Створення типів тварин з більш простими slug
        dog_type, created = AnimalType.objects.get_or_create(
            name="Dogs", slug="dogs", icon="🐕", defaults={"is_active": True}
        )
        cat_type, created = AnimalType.objects.get_or_create(
            name="Cats", slug="cats", icon="🐈", defaults={"is_active": True}
        )

        if created:
            self.stdout.write("✅ Animal types created")
        else:
            self.stdout.write("✅ Animal types already exist")

        # Повний набір категорій для собак
        dog_categories = [
            {
                "name": "Food",
                "slug": "food",
                "description": "Dog food and treats",
                "sort_order": 1,
                "children": [
                    {"name": "Dry Food", "slug": "dry-food", "sort_order": 1},
                    {"name": "Wet Food", "slug": "wet-food", "sort_order": 2},
                    {"name": "Medical Food", "slug": "medical-food", "sort_order": 3},
                    {"name": "Treats", "slug": "treats", "sort_order": 4},
                ],
            },
            {
                "name": "Care & Hygiene",
                "slug": "care-hygiene",
                "description": "Dog care products",
                "sort_order": 2,
                "children": [
                    {"name": "Care Products", "slug": "care-products", "sort_order": 1},
                    {"name": "Shampoos", "slug": "shampoos", "sort_order": 2},
                    {
                        "name": "Brushes & Combs",
                        "slug": "brushes-combs",
                        "sort_order": 3,
                    },
                ],
            },
            {
                "name": "Veterinary Pharmacy",
                "slug": "veterinary-pharmacy",
                "description": "Medicines and vitamins for dogs",
                "sort_order": 3,
                "children": [
                    {"name": "Vitamins", "slug": "vitamins", "sort_order": 1},
                    {"name": "Medicines", "slug": "medicines", "sort_order": 2},
                    {"name": "Prevention", "slug": "prevention", "sort_order": 3},
                ],
            },
            {
                "name": "Walks & Travel",
                "slug": "walks-travel",
                "sort_order": 4,
                "children": [
                    {"name": "Leashes", "slug": "leashes", "sort_order": 1},
                    {"name": "Collars", "slug": "collars", "sort_order": 2},
                    {"name": "Carriers", "slug": "carriers", "sort_order": 3},
                ],
            },
            {
                "name": "Sets & Gifts",
                "slug": "sets-gifts",
                "sort_order": 5,
                "children": [
                    {"name": "Gift Sets", "slug": "gift-sets", "sort_order": 1},
                    {"name": "Toys", "slug": "toys", "sort_order": 2},
                ],
            },
            {
                "name": "Home Comfort",
                "slug": "home-comfort",
                "sort_order": 6,
                "children": [
                    {"name": "Beds", "slug": "beds", "sort_order": 1},
                    {"name": "Bowls", "slug": "bowls", "sort_order": 2},
                    {"name": "Houses", "slug": "houses", "sort_order": 3},
                ],
            },
        ]

        # Повний набір категорій для котів (без постфіксів для consistency)
        cat_categories = [
            {
                "name": "Food",
                "slug": "food",
                "description": "Cat food and treats",
                "sort_order": 1,
                "children": [
                    {"name": "Dry Food", "slug": "dry-food", "sort_order": 1},
                    {"name": "Wet Food", "slug": "wet-food", "sort_order": 2},
                    {"name": "Treats", "slug": "treats", "sort_order": 3},
                ],
            },
            {
                "name": "Care & Hygiene",
                "slug": "care-hygiene",
                "description": "Cat care products",
                "sort_order": 2,
                "children": [
                    {"name": "Care Products", "slug": "care-products", "sort_order": 1},
                    {"name": "Shampoos", "slug": "shampoos", "sort_order": 2},
                    {"name": "Litter & Trays", "slug": "litter-trays", "sort_order": 3},
                ],
            },
            {
                "name": "Veterinary Pharmacy",
                "slug": "veterinary-pharmacy",
                "description": "Medicines and vitamins for cats",
                "sort_order": 3,
                "children": [
                    {"name": "Vitamins", "slug": "vitamins", "sort_order": 1},
                    {"name": "Medicines", "slug": "medicines", "sort_order": 2},
                    {"name": "Prevention", "slug": "prevention", "sort_order": 3},
                ],
            },
            {
                "name": "Walks & Travel",
                "slug": "walks-travel",
                "sort_order": 4,
                "children": [
                    {"name": "Carriers", "slug": "carriers", "sort_order": 1},
                    {
                        "name": "Travel Accessories",
                        "slug": "travel-accessories",
                        "sort_order": 2,
                    },
                ],
            },
            {
                "name": "Sets & Gifts",
                "slug": "sets-gifts",
                "sort_order": 5,
                "children": [
                    {"name": "Gift Sets", "slug": "gift-sets", "sort_order": 1},
                    {"name": "Toys", "slug": "toys", "sort_order": 2},
                ],
            },
            {
                "name": "Home Comfort",
                "slug": "home-comfort",
                "sort_order": 6,
                "children": [
                    {"name": "Beds", "slug": "beds", "sort_order": 1},
                    {"name": "Bowls", "slug": "bowls", "sort_order": 2},
                    {"name": "Houses", "slug": "houses", "sort_order": 3},
                    {
                        "name": "Scratching Posts",
                        "slug": "scratching-posts",
                        "sort_order": 4,
                    },
                ],
            },
        ]

        # Створення категорій з використанням покращеного методу
        dog_count = self.create_categories(dog_type, dog_categories, "dogs")
        cat_count = self.create_categories(cat_type, cat_categories, "cats")

        self.stdout.write(f"✅ Created {dog_count} dog categories")
        self.stdout.write(f"✅ Created {cat_count} cat categories")

        # Вивід інформації для фронтендерів
        self.print_testing_info()

    def create_categories(self, animal_type, categories_data, animal_name):
        """Універсальний метод для створення категорій"""
        categories_created = 0

        for cat_data in categories_data:
            parent, created = Category.objects.get_or_create(
                name=cat_data["name"],
                slug=cat_data["slug"],
                animal_type=animal_type,
                defaults={
                    "description": cat_data.get("description", ""),
                    "sort_order": cat_data["sort_order"],
                },
            )
            if created:
                categories_created += 1
                self.stdout.write(
                    f"   ✅ Created {animal_name} category: {cat_data['name']}"
                )

            # Створення підкатегорій
            for child_data in cat_data.get("children", []):
                child, created = Category.objects.get_or_create(
                    parent=parent,
                    name=child_data["name"],
                    slug=child_data["slug"],
                    animal_type=animal_type,
                    defaults={"sort_order": child_data["sort_order"]},
                )
                if created:
                    categories_created += 1
                    self.stdout.write(
                        f"     ✅ Created {animal_name} subcategory: {child_data['name']}"
                    )

        return categories_created

    def print_testing_info(self):
        """Виводить інформацію для тестування API"""
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("🎯 API TESTING INFORMATION FOR FRONTEND DEVELOPERS")
        self.stdout.write("=" * 60)

        # Приклади URL для тестування
        test_urls = [
            "GET /api/categories/dogs/food/subcategories/",
            "GET /api/categories/dogs/care-hygiene/subcategories/",
            "GET /api/categories/cats/food/subcategories/",
            "GET /api/categories/cats/care-hygiene/subcategories/",
            "GET /api/animal-types/",
            "GET /api/categories/dogs/tree/",
            "GET /api/categories/cats/tree/",
            "GET /api/categories/dogs/food/leaves/",
            "GET /api/categories/cats/food/leaves/",
        ]

        self.stdout.write("\n📋 Available endpoints for testing:")
        for url in test_urls:
            self.stdout.write(f"   {url}")

        # Список доступних slug
        self.stdout.write("\n🔗 Available animal_type_slug values:")
        for animal in AnimalType.objects.all():
            categories_count = Category.objects.filter(animal_type=animal).count()
            self.stdout.write(
                f"   - {animal.slug} ({animal.name}) - {categories_count} categories"
            )

        self.stdout.write("\n🔗 Available category_slug values for dogs:")
        dog_categories = Category.objects.filter(
            animal_type__slug="dogs", parent__isnull=True
        )
        for cat in dog_categories:
            subcats_count = Category.objects.filter(parent=cat).count()
            self.stdout.write(
                f"   - {cat.slug} ({cat.name}) - {subcats_count} subcategories"
            )
            # Підкатегорії
            subcats = Category.objects.filter(parent=cat)
            for subcat in subcats:
                self.stdout.write(f"     └── {subcat.slug} ({subcat.name})")

        self.stdout.write("\n🔗 Available category_slug values for cats:")
        cat_categories = Category.objects.filter(
            animal_type__slug="cats", parent__isnull=True
        )
        for cat in cat_categories:
            subcats_count = Category.objects.filter(parent=cat).count()
            self.stdout.write(
                f"   - {cat.slug} ({cat.name}) - {subcats_count} subcategories"
            )
            # Підкатегорії
            subcats = Category.objects.filter(parent=cat)
            for subcat in subcats:
                self.stdout.write(f"     └── {subcat.slug} ({subcat.name})")

        self.stdout.write("\n💡 Quick test examples:")
        self.stdout.write(
            "   curl http://localhost:8000/api/categories/dogs/food/subcategories/"
        )
        self.stdout.write(
            "   curl http://localhost:8000/api/categories/cats/care-hygiene/subcategories/"
        )

        self.stdout.write("\n📊 Statistics:")
        total_categories = Category.objects.count()
        total_animal_types = AnimalType.objects.count()
        self.stdout.write(f"   Total animal types: {total_animal_types}")
        self.stdout.write(f"   Total categories: {total_categories}")

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(
            self.style.SUCCESS("🎉 All initial data loaded successfully!")
        )
