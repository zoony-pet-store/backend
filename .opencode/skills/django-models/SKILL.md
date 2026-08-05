---
name: django-models
description: Use when creating, modifying, or reviewing Django models.
---

# Django Models

## Project conventions

- Place models under `shop/models/`.
- Re-export models from `shop/models/__init__.py`.
- Always create Django migrations for schema changes.
- Prefer explicit `related_name`.
- Add indexes only for frequently queried fields.
- Keep models focused on persistence and domain logic.

## Template

```python
from django.db import models


class ExampleModel(models.Model):
    name = models.CharField(max_length=255)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.name
```

## Checklist

- Correct field types
- Proper `on_delete`
- `related_name`
- `verbose_name` if needed
- indexes if justified
- migration required