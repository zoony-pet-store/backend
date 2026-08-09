---
name: django-style-policy
description: Use when reviewing Django style, ORM usage, API structure, or migration practices.
---

# Django Style Policy

## Models
- Prefer splitting models into `shop/models/`.
- Add indexes only when justified.
- Define `related_name` when reverse access is used, as in `Product.reviews` or `Category.children`.
- Avoid business logic in views when it belongs in models or services.

## ORM
- Prefer `select_related` and `prefetch_related`.
- Avoid N+1 queries.
- Use transactions when modifying multiple related objects.

## API
- Use DRF serializers for validation.
- Return appropriate HTTP status codes.
- Keep views thin.
- Keep route paths explicit in `shop/urls.py`; `APPEND_SLASH = False`.
- Put reusable behavior in `shop/services/` or `shop/validators/` when views would become heavy.

## Migrations
- Always generate migrations.
- Never edit applied migrations unless explicitly requested.
