import uuid

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from phonenumber_field.modelfields import PhoneNumberField
from django.utils.text import slugify


class CustomerManager(BaseUserManager):
    """Custom manager for Customer model"""

    def create_user(self, email, password=None, **extra_fields):
        """Create and save a regular user"""
        if not email:
            raise ValueError("User must have an email address")

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """Create and save a superuser"""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True")

        return self.create_user(email, password, **extra_fields)


class Customer(AbstractUser):
    """Custom user model for customers"""

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
    """Animal type/category (e.g., dogs, cats)"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50)
    slug = models.SlugField(unique=True)
    icon = models.CharField(max_length=100, blank=True)
    image_url = models.URLField(max_length=500, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "animal_types"

    def __str__(self):
        return self.name


class Category(models.Model):
    """Product category with hierarchical structure"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField()
    description = models.TextField(blank=True)
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="children"
    )
    animal_type = models.ForeignKey(
        AnimalType, on_delete=models.CASCADE, related_name="categories"
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
        unique_together = ["slug", "animal_type", "parent"]

    def save(self, *args, **kwargs):
        if self.parent:
            self.level = self.parent.level + 1
        else:
            self.level = 0

        if not self.slug:
            self.slug = self.generate_slug()

        super().save(*args, **kwargs)

    def generate_slug(self):
        """Generate unique slug for category"""
        base_slug = slugify(self.name)
        slug = base_slug
        counter = 1

        while Category.objects.filter(
            slug=slug, animal_type=self.animal_type, parent=self.parent
        ).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1

        return slug

    def __str__(self):
        return f"{'--' * self.level} {self.name} ({self.animal_type})"


class Brand(models.Model):
    """Product brands"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    logo_url = models.URLField(max_length=500, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Badge(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True)
    label = models.CharField(max_length=50)
    color = models.CharField(max_length=7, default="#000000")  # HEX color
    background_color = models.CharField(max_length=7, default="#FFFFFF")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.label


class Product(models.Model):
    """Main product model"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField()
    description = models.TextField(blank=True)
    short_description = models.TextField(max_length=500, blank=True)
    brand = models.ForeignKey(
        Brand, on_delete=models.SET_NULL, null=True, blank=True, related_name="products"
    )
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name="products"
    )
    is_active = models.BooleanField(default=True)
    badges = models.ManyToManyField(Badge, blank=True, related_name="products")
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.0)
    review_count = models.IntegerField(default=0)
    meta_title = models.CharField(max_length=255, blank=True)
    meta_description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    composition = models.TextField(blank=True, verbose_name="Product composition")
    nutritional_analysis = models.TextField(blank=True, verbose_name="Typical analysis")
    feeding_guidelines = models.TextField(blank=True, verbose_name="Feeding guidelines")
    ingredients = models.TextField(blank=True, verbose_name="Ingredients")
    nutritional_value = models.JSONField(
        default=dict, blank=True, verbose_name="Nutritional value (JSON)"
    )
    feeding_table = models.JSONField(
        default=dict, blank=True, verbose_name="Feeding table (JSON)"
    )
    # Main image for backward compatibility
    main_image = models.URLField(max_length=500, blank=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ["slug", "category"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.generate_slug()
        super().save(*args, **kwargs)

    def generate_slug(self):
        """Generate unique slug for product"""
        base_slug = slugify(self.name)
        slug = base_slug
        counter = 1

        while Product.objects.filter(slug=slug, category=self.category).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1

        return slug

    @property
    def min_price(self):
        """Minimum price from active variants"""
        from django.db.models import Min

        variants = self.variants.filter(is_active=True)
        if variants.exists():
            return variants.aggregate(min_price=Min("price"))["min_price"]
        return None

    @property
    def max_price(self):
        """Maximum price from active variants"""
        from django.db.models import Max

        variants = self.variants.filter(is_active=True)
        if variants.exists():
            return variants.aggregate(max_price=Max("price"))["max_price"]
        return None

    @property
    def in_stock(self):
        """Check if at least one variant is in stock"""
        return self.variants.filter(is_active=True, stock__gt=0).exists()


class ProductAttribute(models.Model):
    """Product attributes (e.g., size, color, flavor)"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    filterable = models.BooleanField(default=True)
    display_order = models.IntegerField(default=0)

    def __str__(self):
        return self.name


class ProductAttributeValue(models.Model):
    """Values for product attributes"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    attribute = models.ForeignKey(
        ProductAttribute, on_delete=models.CASCADE, related_name="values"
    )
    value = models.CharField(max_length=255)
    slug = models.SlugField()
    display_order = models.IntegerField(default=0)

    class Meta:
        unique_together = ["attribute", "slug"]

    def __str__(self):
        return f"{self.attribute.name}: {self.value}"


class ProductVariant(models.Model):
    """Product variants (e.g., different sizes, colors)"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="variants"
    )
    sku = models.CharField(max_length=100, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    old_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    cost_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    stock = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    has_discount = models.BooleanField(default=False)
    weight = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True)
    attributes = models.ManyToManyField(ProductAttributeValue, related_name="variants")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["price"]

    def __str__(self):
        return f"{self.product.name} - {self.sku}"

    @property
    def discount_percentage(self):
        """Calculate discount percentage"""
        if self.has_discount:
            return round((self.old_price - self.price) / self.old_price * 100)
        return 0


class ProductImage(models.Model):
    """Product images"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="images"
    )
    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.CASCADE,
        related_name="images",
        null=True,
        blank=True,
    )
    image_url = models.URLField(max_length=500)
    alt_text = models.CharField(max_length=255, blank=True)
    is_main = models.BooleanField(default=False)
    display_order = models.IntegerField(default=0)
    cloudinary_public_id = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        ordering = ["display_order", "id"]

    def __str__(self):
        return f"Image for {self.product.name}"


class ProductReview(models.Model):
    """Product reviews"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="reviews"
    )
    user = models.ForeignKey(
        "Customer", on_delete=models.SET_NULL, null=True, blank=True
    )
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])  # 1-5 stars
    title = models.CharField(max_length=200)
    comment = models.TextField()
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Review for {self.product.name} by {self.user}"


class Cart(models.Model):
    """User shopping cart"""

    user = models.OneToOneField(Customer, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cart for {self.user.email}"

    @property
    def total_price(self):
        """Total cart price"""
        return sum(item.total_price for item in self.items.all())

    @property
    def total_items(self):
        """Total number of items in cart"""
        return sum(item.quantity for item in self.items.all())


class CartItem(models.Model):
    """Cart item (now references product variant)"""

    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey(
        ProductVariant, on_delete=models.CASCADE, related_name="cart_items"
    )
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["cart", "variant"]

    def __str__(self):
        return f"{self.variant.product.name} - {self.variant.sku} x {self.quantity}"

    @property
    def total_price(self):
        """Total price for this cart item"""
        return self.variant.price * self.quantity
