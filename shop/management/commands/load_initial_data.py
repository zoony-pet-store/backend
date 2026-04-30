from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db.models import Avg
from django.utils.text import slugify

from shop.models import (
    AnimalType,
    Brand,
    Category,
    Customer,
    Product,
    ProductAttribute,
    ProductAttributeValue,
    ProductImage,
    ProductReview,
    ProductVariant,
    ProductVariantAttribute,
)


class Command(BaseCommand):
    help = "Load initial data including categories, brands, products, variants, and reviews"

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

        # 1. Create animal types
        dog_type, dog_created = AnimalType.objects.get_or_create(
            name="Dogs",
            slug="dogs",
            defaults={"icon": "🐕", "is_active": True},
        )
        cat_type, cat_created = AnimalType.objects.get_or_create(
            name="Cats",
            slug="cats",
            defaults={"icon": "🐈", "is_active": True},
        )

        if dog_created or cat_created:
            self.stdout.write("✅ Animal types created")
        else:
            self.stdout.write("✅ Animal types already exist")

        # 2. Create categories
        dog_categories = [
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

        cat_categories = [
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

        dog_count = self.create_categories(dog_type, dog_categories, "dogs")
        cat_count = self.create_categories(cat_type, cat_categories, "cats")

        self.stdout.write(f"✅ Created {dog_count} dog categories")
        self.stdout.write(f"✅ Created {cat_count} cat categories")

        # 3. Create brands
        brands = [
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

        brand_objects = {}
        for brand_data in brands:
            brand, created = Brand.objects.get_or_create(
                slug=brand_data["slug"],
                defaults={
                    "name": brand_data["name"],
                    "logo_url": brand_data.get("logo_url", ""),
                    "is_active": True,
                },
            )
            brand_objects[brand.slug] = brand

            if created:
                self.stdout.write(f"✅ Created brand: {brand.name}")

        # 4. Create product attributes
        attributes = [
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
                "values": ["Puppy/Kitten", "Adult", "Senior", "All Life Stages"],
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

        attribute_objects = {}
        for attr_data in attributes:
            attribute, created = ProductAttribute.objects.get_or_create(
                slug=attr_data["slug"],
                defaults={
                    "name": attr_data["name"],
                    "filterable": True,
                },
            )
            attribute_objects[attribute.slug] = attribute

            for index, value in enumerate(attr_data["values"]):
                ProductAttributeValue.objects.get_or_create(
                    attribute=attribute,
                    slug=slugify(value),
                    defaults={
                        "value": value,
                        "display_order": index,
                    },
                )

            if created:
                self.stdout.write(f"✅ Created attribute: {attribute.name}")

        # 5. Create products and variants
        self.create_sample_products(
            dog_type,
            cat_type,
            brand_objects,
            attribute_objects,
        )

        # 6. Create test users for reviews
        review_users = self.create_test_users()

        # 7. Create sample reviews and sync product stats
        self.create_sample_reviews(review_users)

        # 8. Print summaries for verification
        self.print_review_summary()
        self.print_testing_info()

    def create_categories(self, animal_type, categories_data, animal_name):
        categories_created = 0

        for cat_data in categories_data:
            parent, created = Category.objects.get_or_create(
                slug=cat_data["slug"],
                animal_type=animal_type,
                parent=None,
                defaults={
                    "name": cat_data["name"],
                    "description": cat_data.get("description", ""),
                    "image_url": cat_data.get("image_url", ""),
                    "sort_order": cat_data["sort_order"],
                    "is_active": True,
                },
            )

            if created:
                categories_created += 1
                self.stdout.write(
                    f"   ✅ Created {animal_name} category: {cat_data['name']}"
                )

            for child_data in cat_data.get("children", []):
                child, created = Category.objects.get_or_create(
                    parent=parent,
                    slug=child_data["slug"],
                    animal_type=animal_type,
                    defaults={
                        "name": child_data["name"],
                        "sort_order": child_data["sort_order"],
                        "image_url": child_data.get("image_url", ""),
                        "is_active": True,
                    },
                )

                if created:
                    categories_created += 1
                    self.stdout.write(
                        f"     ✅ Created {animal_name} subcategory: {child_data['name']}"
                    )

        return categories_created

    def create_test_users(self):
        users_data = [
            {"email": "anna@example.com", "username": "anna"},
            {"email": "ivan@example.com", "username": "ivan"},
            {"email": "max@example.com", "username": "max"},
        ]

        users = []

        for data in users_data:
            user, created = Customer.objects.get_or_create(
                email=data["email"],
                defaults={
                    "username": data["username"],
                    "email_verified": True,
                    "is_active": True,
                },
            )

            if created:
                user.set_password("test12345")
                user.save()
                self.stdout.write(f"✅ Created test user: {user.email}")

            users.append(user)

        return users

    def sync_product_review_stats(self, product):
        active_reviews = ProductReview.objects.filter(product=product, is_active=True)
        review_count = active_reviews.count()
        avg_rating = active_reviews.aggregate(avg=Avg("rating"))["avg"] or 0

        product.review_count = review_count
        product.rating = round(avg_rating, 2)
        product.save(update_fields=["review_count", "rating"])

    def create_sample_products(self, dog_type, cat_type, brands, attributes):
        dog_dry_food = Category.objects.get(
            animal_type=dog_type,
            slug="dry-food",
            parent__slug="food",
        )
        dog_treats = Category.objects.get(
            animal_type=dog_type,
            slug="treats",
            parent__slug="food",
        )
        dog_toys = Category.objects.get(
            animal_type=dog_type,
            slug="toys",
            parent__slug="sets-gifts",
        )
        dog_beds = Category.objects.get(
            animal_type=dog_type,
            slug="beds",
            parent__slug="home-comfort",
        )

        cat_dry_food = Category.objects.get(
            animal_type=cat_type,
            slug="dry-food",
            parent__slug="food",
        )
        cat_wet_food = Category.objects.get(
            animal_type=cat_type,
            slug="wet-food",
            parent__slug="food",
        )
        cat_toys = Category.objects.get(
            animal_type=cat_type,
            slug="toys",
            parent__slug="sets-gifts",
        )
        cat_litter = Category.objects.get(
            animal_type=cat_type,
            slug="litter-trays",
            parent__slug="care-hygiene",
        )

        dog_products = [
            {
                "name": "Premium Adult Dog Food",
                "slug": "premium-adult-dog-food",
                "description": "Complete and balanced nutrition for adult dogs with high-quality protein. Contains essential vitamins and minerals for optimal health.",
                "short_description": "High-quality dog food for adult dogs",
                "category": dog_dry_food,
                "brand": brands["royal-canin"],
                "images": [
                    "https://images.unsplash.com/photo-1560806887-1e4cd0b6cbd6?w=600&h=600&fit=crop",
                    "https://images.unsplash.com/photo-1559056199-641a0ac8b55e?w=600&h=600&fit=crop",
                ],
                "variants": [
                    {
                        "sku": "DOG-FOOD-2KG",
                        "size": "2kg",
                        "weight": 2.0,
                        "price": 25.99,
                        "stock": 50,
                    },
                    {
                        "sku": "DOG-FOOD-5KG",
                        "size": "5kg",
                        "weight": 5.0,
                        "price": 45.99,
                        "stock": 30,
                    },
                    {
                        "sku": "DOG-FOOD-10KG",
                        "size": "10kg",
                        "weight": 10.0,
                        "price": 79.99,
                        "stock": 20,
                    },
                ],
                "attributes": {"Flavor": "Chicken", "Age": "Adult"},
                "nutritional_value": {
                    "protein": "25%",
                    "fat": "15%",
                    "fiber": "4%",
                    "moisture": "10%",
                },
            },
            {
                "name": "Dental Chew Treats",
                "slug": "dental-chew-treats",
                "description": "Helps clean teeth and freshen breath while providing a tasty treat. Made with natural ingredients.",
                "short_description": "Dental care treats for dogs",
                "category": dog_treats,
                "brand": brands["purina"],
                "images": [
                    "https://images.unsplash.com/photo-1541364983171-a8ba01e95cfc?w=600&h=600&fit=crop"
                ],
                "variants": [
                    {
                        "sku": "TREATS-SMALL",
                        "size": "Small",
                        "weight": 0.5,
                        "price": 8.99,
                        "stock": 100,
                    },
                    {
                        "sku": "TREATS-MEDIUM",
                        "size": "Medium",
                        "weight": 1.0,
                        "price": 12.99,
                        "stock": 80,
                    },
                    {
                        "sku": "TREATS-LARGE",
                        "size": "Large",
                        "weight": 2.0,
                        "price": 18.99,
                        "stock": 60,
                    },
                ],
                "attributes": {"Flavor": "Beef", "Age": "Adult"},
            },
            {
                "name": "Interactive Rubber Ball",
                "slug": "interactive-rubber-ball",
                "description": "Durable rubber ball for interactive play, bounces unpredictably",
                "short_description": "Durable rubber ball for dogs",
                "category": dog_toys,
                "brand": brands["kong"],
                "images": [
                    "https://images.unsplash.com/photo-1548192746-dd526f154ed9?w=600&h=600&fit=crop"
                ],
                "variants": [
                    {
                        "sku": "BALL-SMALL",
                        "size": "Small",
                        "price": 9.99,
                        "stock": 40,
                        "color": "Red",
                    },
                    {
                        "sku": "BALL-MEDIUM",
                        "size": "Medium",
                        "price": 15.99,
                        "stock": 60,
                        "color": "Blue",
                    },
                    {
                        "sku": "BALL-LARGE",
                        "size": "Large",
                        "price": 21.99,
                        "stock": 30,
                        "color": "Green",
                    },
                ],
                "attributes": {"Material": "Rubber"},
            },
            {
                "name": "Orthopedic Memory Foam Bed",
                "slug": "orthopedic-memory-foam-bed",
                "description": "Provides superior comfort and support for dogs with joint issues",
                "short_description": "Orthopedic bed for dogs",
                "category": dog_beds,
                "brand": brands["petlux"],
                "images": [
                    "https://images.unsplash.com/photo-1561037404-61cd46aa615b?w=600&h=600&fit=crop"
                ],
                "variants": [
                    {
                        "sku": "BED-SMALL",
                        "size": "Small",
                        "price": 59.99,
                        "stock": 15,
                        "color": "Brown",
                    },
                    {
                        "sku": "BED-MEDIUM",
                        "size": "Medium",
                        "price": 89.99,
                        "stock": 20,
                        "color": "Gray",
                    },
                    {
                        "sku": "BED-LARGE",
                        "size": "Large",
                        "price": 119.99,
                        "stock": 10,
                        "color": "Black",
                    },
                ],
                "attributes": {"Material": "Fabric"},
            },
        ]

        cat_products = [
            {
                "name": "Indoor Cat Formula",
                "slug": "indoor-cat-formula",
                "description": "Specially formulated for indoor cats to maintain healthy weight",
                "short_description": "Dry food for indoor cats",
                "category": cat_dry_food,
                "brand": brands["hills-science-diet"],
                "images": [
                    "https://images.unsplash.com/photo-1608848461950-0fe51dfc41cb?w=600&h=600&fit=crop"
                ],
                "variants": [
                    {
                        "sku": "CAT-FOOD-1.5KG",
                        "size": "1.5kg",
                        "weight": 1.5,
                        "price": 22.99,
                        "stock": 40,
                    },
                    {
                        "sku": "CAT-FOOD-3KG",
                        "size": "3kg",
                        "weight": 3.0,
                        "price": 38.99,
                        "stock": 25,
                    },
                    {
                        "sku": "CAT-FOOD-7KG",
                        "size": "7kg",
                        "weight": 7.0,
                        "price": 65.99,
                        "stock": 15,
                    },
                ],
                "attributes": {"Flavor": "Salmon", "Age": "Adult"},
            },
            {
                "name": "Gourmet Wet Food Variety Pack",
                "slug": "gourmet-wet-food-variety-pack",
                "description": "Assorted flavors in convenient single-serve pouches",
                "short_description": "Wet food variety pack for cats",
                "category": cat_wet_food,
                "brand": brands["acme-pet-supplies"],
                "images": [
                    "https://images.unsplash.com/photo-1576675466969-38eeae4b41f6?w=600&h=600&fit=crop"
                ],
                "variants": [
                    {
                        "sku": "WET-12PACK",
                        "size": "12-pack",
                        "price": 24.99,
                        "stock": 50,
                    },
                    {
                        "sku": "WET-24PACK",
                        "size": "24-pack",
                        "price": 42.99,
                        "stock": 30,
                    },
                    {
                        "sku": "WET-48PACK",
                        "size": "48-pack",
                        "price": 78.99,
                        "stock": 20,
                    },
                ],
                "attributes": {"Flavor": "Assorted", "Age": "All Life Stages"},
            },
            {
                "name": "Feather Teaser Wand",
                "slug": "feather-teaser-wand",
                "description": "Interactive wand toy with colorful feathers to stimulate natural hunting instincts",
                "short_description": "Interactive wand toy for cats",
                "category": cat_toys,
                "brand": brands["petsafe"],
                "images": [
                    "https://images.unsplash.com/photo-1548192746-dd526f154ed9?w=600&h=600&fit=crop"
                ],
                "variants": [
                    {
                        "sku": "WAND-FEATHER",
                        "color": "Multicolor",
                        "price": 11.99,
                        "stock": 70,
                    },
                    {
                        "sku": "WAND-MOUSE",
                        "color": "Gray",
                        "price": 12.99,
                        "stock": 50,
                    },
                    {
                        "sku": "WAND-BELL",
                        "color": "Red",
                        "price": 10.99,
                        "stock": 60,
                    },
                ],
                "attributes": {"Material": "Fabric"},
            },
            {
                "name": "Clumping Cat Litter",
                "slug": "clumping-cat-litter",
                "description": "Low-dust, fast-clumping litter with odor control",
                "short_description": "Clumping litter with odor control",
                "category": cat_litter,
                "brand": brands["vetcare"],
                "images": [
                    "https://images.unsplash.com/photo-1591946614720-90a587da4a36?w=600&h=600&fit=crop"
                ],
                "variants": [
                    {
                        "sku": "LITTER-4KG",
                        "size": "4kg",
                        "weight": 4.0,
                        "price": 12.99,
                        "stock": 80,
                    },
                    {
                        "sku": "LITTER-8KG",
                        "size": "8kg",
                        "weight": 8.0,
                        "price": 18.99,
                        "stock": 45,
                    },
                    {
                        "sku": "LITTER-16KG",
                        "size": "16kg",
                        "weight": 16.0,
                        "price": 32.99,
                        "stock": 25,
                    },
                ],
                "attributes": {"Material": "Clay", "Color": "White"},
            },
        ]

        for product_data in dog_products:
            self.create_product_with_variants(product_data, "dog")

        for product_data in cat_products:
            self.create_product_with_variants(product_data, "cat")

    def create_product_with_variants(self, product_data, animal_type):
        product, created = Product.objects.get_or_create(
            slug=product_data["slug"],
            category=product_data["category"],
            defaults={
                "name": product_data["name"],
                "description": product_data["description"],
                "short_description": product_data["short_description"],
                "brand": product_data["brand"],
                "rating": 0.0,
                "review_count": 0,
                "is_active": True,
                "composition": "High-quality ingredients for optimal nutrition",
                "feeding_guidelines": "Feed according to your pet's weight and activity level",
                "nutritional_value": product_data.get("nutritional_value", {}),
            },
        )

        if created:
            self.stdout.write(f"✅ Created {animal_type} product: {product.name}")

        product_images = product_data.get("images", [])

        for i, image_url in enumerate(product_images):
            is_main = i == 0

            image, image_created = ProductImage.objects.get_or_create(
                product=product,
                variant=None,
                image_url=image_url,
                defaults={
                    "alt_text": f"{product.name} - Image {i + 1}",
                    "is_main": is_main,
                    "display_order": i,
                },
            )

            if is_main:
                product.main_image = image_url
                product.save(update_fields=["main_image"])

        for index, variant_data in enumerate(product_data["variants"]):
            weight = variant_data.get("weight")
            old_price = variant_data.get("old_price")
            price = Decimal(str(variant_data["price"]))

            if old_price is not None:
                old_price = Decimal(str(old_price))
                if old_price <= price:
                    old_price = None

            variant, variant_created = ProductVariant.objects.get_or_create(
                sku=variant_data["sku"],
                defaults={
                    "product": product,
                    "price": price,
                    "old_price": old_price,
                    "stock": variant_data["stock"],
                    "is_active": True,
                    "is_default": index == 0,
                    "weight": Decimal(str(weight)) if weight is not None else None,
                },
            )

            if not variant_created and variant.product_id == product.id:
                variant.price = price
                variant.old_price = old_price
                variant.stock = variant_data["stock"]
                variant.is_active = True
                variant.is_default = index == 0
                variant.weight = Decimal(str(weight)) if weight is not None else None
                variant.save()

            if "size" in variant_data:
                self.attach_variant_attribute(variant, "Size", variant_data["size"])

            if "color" in variant_data:
                self.attach_variant_attribute(variant, "Color", variant_data["color"])

            for attr_name, attr_value in product_data.get("attributes", {}).items():
                self.attach_variant_attribute(variant, attr_name, attr_value)

            if product_images:
                variant_image_url = variant_data.get("image_url") or product_images[0]

                ProductImage.objects.get_or_create(
                    product=product,
                    variant=variant,
                    image_url=variant_image_url,
                    defaults={
                        "alt_text": f"{product.name} - {variant.sku}",
                        "is_main": True,
                        "display_order": 0,
                    },
                )

            if variant_created:
                self.stdout.write(f"   ✅ Created variant: {variant.sku}")
            else:
                self.stdout.write(f"   ✅ Updated variant: {variant.sku}")

    def attach_variant_attribute(self, variant, attribute_name, raw_value):
        if raw_value is None:
            return

        value = str(raw_value).strip()

        if not value:
            return

        attribute, _ = ProductAttribute.objects.get_or_create(
            slug=slugify(attribute_name),
            defaults={
                "name": attribute_name,
                "filterable": True,
            },
        )

        attribute_value, _ = ProductAttributeValue.objects.get_or_create(
            attribute=attribute,
            slug=slugify(value),
            defaults={"value": value},
        )

        ProductVariantAttribute.objects.update_or_create(
            variant=variant,
            attribute=attribute,
            defaults={"value": attribute_value},
        )

    def create_sample_reviews(self, users=None):
        ProductReview.objects.all().delete()

        sample_reviews = [
            {
                "rating": 5,
                "title": "Excellent product!",
                "comment": "Very good quality, my pet really likes it.",
                "is_verified": True,
            },
            {
                "rating": 4,
                "title": "Good quality",
                "comment": "Overall I'm satisfied, would buy again.",
                "is_verified": True,
            },
            {
                "rating": 3,
                "title": "Average",
                "comment": "It's okay, but I expected a bit more.",
                "is_verified": False,
            },
        ]

        products = Product.objects.filter(is_active=True)
        users = users or []
        total_reviews_created = 0

        for product in products:
            for i, review_data in enumerate(sample_reviews):
                ProductReview.objects.create(
                    product=product,
                    user=users[i % len(users)] if users else None,
                    rating=review_data["rating"],
                    title=review_data["title"],
                    comment=review_data["comment"],
                    is_verified=review_data["is_verified"],
                    is_active=True,
                )
                total_reviews_created += 1

            self.sync_product_review_stats(product)

        self.stdout.write(f"✅ Created {total_reviews_created} sample reviews")

    def print_review_summary(self):
        self.stdout.write("\n📝 Review summary:")
        products = Product.objects.filter(is_active=True)[:5]

        for product in products:
            active_reviews = ProductReview.objects.filter(
                product=product,
                is_active=True,
            ).count()

            self.stdout.write(
                f"   {product.name} | rating={product.rating} | "
                f"review_count={product.review_count} | actual_reviews={active_reviews}"
            )

    def print_testing_info(self):
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("🎯 API TESTING INFORMATION FOR FRONTEND DEVELOPERS")
        self.stdout.write("=" * 60)

        sample_product = Product.objects.filter(is_active=True).first()
        product_id = sample_product.id if sample_product else "product-uuid-here"

        test_urls = [
            "GET /api/dashboard",
            "GET /api/dogs/",
            "GET /api/cats/",
            "GET /api/dogs/food/",
            "GET /api/dogs/food/dry-food/",
            "GET /api/cats/food/wet-food/",
            "GET /api/dogs/food/products/",
            "GET /api/cats/home-comfort/products/",
            "GET /api/products",
            f"GET /api/products/{product_id}",
            f"GET /api/products/{product_id}/related",
            "GET /api/products/search/?q=dog",
            "GET /api/brands",
            "GET /api/brands/royal-canin",
        ]

        self.stdout.write("\n📋 API endpoints for testing:")
        for url in test_urls:
            self.stdout.write(f"   {url}")

        self.stdout.write("\n📊 Statistics:")
        total_categories = Category.objects.count()
        total_animal_types = AnimalType.objects.count()
        total_brands = Brand.objects.count()
        total_products = Product.objects.count()
        total_variants = ProductVariant.objects.count()
        total_reviews = ProductReview.objects.count()
        total_users = Customer.objects.count()

        self.stdout.write(f"   Total animal types: {total_animal_types}")
        self.stdout.write(f"   Total categories: {total_categories}")
        self.stdout.write(f"   Total brands: {total_brands}")
        self.stdout.write(f"   Total products: {total_products}")
        self.stdout.write(f"   Total variants: {total_variants}")
        self.stdout.write(f"   Total reviews: {total_reviews}")
        self.stdout.write(f"   Total users: {total_users}")

        self.stdout.write("\n🔗 Sample product for testing:")
        if sample_product:
            self.stdout.write(f"   Product ID: {sample_product.id}")
            self.stdout.write(f"   Name: {sample_product.name}")
            self.stdout.write(f"   URL: /api/products/{sample_product.id}")

        self.stdout.write("\n💡 Product detail review structure now looks like:")
        self.stdout.write('   "reviews": {')
        self.stdout.write('       "rating": 4.0,')
        self.stdout.write('       "review_count": 3,')
        self.stdout.write('       "reviews": [')
        self.stdout.write("           {")
        self.stdout.write('               "id": "...",')
        self.stdout.write('               "username": "anna",')
        self.stdout.write('               "created_at": "...",')
        self.stdout.write('               "rating": 5,')
        self.stdout.write('               "image_urls": [],')
        self.stdout.write('               "updated_at": "...",')
        self.stdout.write('               "comment": "...",')
        self.stdout.write('               "positive_comment": null,')
        self.stdout.write('               "negative_comment": null')
        self.stdout.write("           }")
        self.stdout.write("       ]")
        self.stdout.write("   }")

        self.stdout.write("\n💡 Variant structure now looks like:")
        self.stdout.write('   "variants": [')
        self.stdout.write("       {")
        self.stdout.write('           "id": "...",')
        self.stdout.write('           "sku": "DOG-FOOD-2KG",')
        self.stdout.write('           "attributes": {')
        self.stdout.write(
            '               "Size": {"id": "...", "value": "2kg", "slug": "2kg"},'
        )
        self.stdout.write(
            '               "Flavor": {"id": "...", "value": "Chicken", "slug": "chicken"}'
        )
        self.stdout.write("           },")
        self.stdout.write('           "price": "25.99",')
        self.stdout.write('           "stock": 50')
        self.stdout.write("       }")
        self.stdout.write("   ]")

        self.stdout.write("\n💡 Quick test examples:")
        self.stdout.write("   curl http://localhost:8000/api/dashboard")
        self.stdout.write("   curl http://localhost:8000/api/products")
        self.stdout.write(f"   curl http://localhost:8000/api/products/{product_id}")

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(
            self.style.SUCCESS("🎉 All initial data loaded successfully!")
        )
        self.stdout.write("=" * 60)
