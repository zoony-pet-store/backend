---
name: django-admin
description: Use when modifying Django admin.
---

# Django Admin

## Prefer

- list_display
- list_filter
- search_fields
- autocomplete_fields
- readonly_fields where appropriate

## Template

```python
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (...)
    search_fields = (...)
```