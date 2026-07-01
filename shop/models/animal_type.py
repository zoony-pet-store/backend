import uuid

from django.db import models
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
