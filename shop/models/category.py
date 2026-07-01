import uuid

from django.db import models
from django.utils.text import slugify

from .animal_type import AnimalType
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
