---
name: django-admin
description: Use when modifying Django Admin or Unfold admin classes under `shop/admin/`.
---

# Django Admin

## Project Conventions

- Admin classes live under `shop/admin/` and use `unfold.admin.ModelAdmin`.
- Prefer `list_display`, `list_filter`, `search_fields`, `autocomplete_fields`, and `readonly_fields` where useful.
- Use `list_select_related` or queryset annotations for admin list performance.
- Keep shared admin form/widget logic in `shop/admin/forms.py`, `shop/admin/widgets.py`, or `shop/admin/helpers.py`.

## Project Example

```python
@admin.register(Product)
class ProductAdmin(ModelAdmin):
    list_display = ("name", "brand", "category_display", "is_active")
    list_select_related = ("brand", "category", "category__animal_type")
    search_fields = ("name", "slug", "brand__name", "category__name")
    autocomplete_fields = ("brand", "badges")
```
