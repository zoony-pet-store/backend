import uuid

from django.db import models
from django.utils.text import slugify


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
        db_table = "brands"
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
