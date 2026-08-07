---
name: django-models
description: Use when creating, modifying, or reviewing Django models.
---

# Django Models

## Project conventions

- Place models under `shop/models/`.
- Re-export models from `shop/models/__init__.py`.
- Always create Django migrations for schema changes.
- Prefer explicit `related_name` when reverse access is used.
- Add indexes only for frequently queried fields.
- Keep models focused on persistence and domain logic.

## Project Example

```python
class ProductReviewImage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    review = models.ForeignKey(ProductReview, on_delete=models.CASCADE, related_name="images")
    secure_url = models.URLField(max_length=1000)
    position = models.PositiveSmallIntegerField(default=0)
```

## Checklist

- Correct field types
- Proper `on_delete`
- `related_name` where reverse access is used
- `verbose_name` if needed
- indexes if justified
- migration required
