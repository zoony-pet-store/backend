---
name: django-style-policy
description: Use when reviewing Django style, ORM usage, API structure, or migration practices.
---

# Django Style Policy

## Models
- Prefer splitting models into `shop/models/`.
- Add indexes only when justified.
- Always define `related_name` for relations.
- Avoid business logic in views when it belongs in models or services.

## ORM
- Prefer `select_related` and `prefetch_related`.
- Avoid N+1 queries.
- Use transactions when modifying multiple related objects.

## API
- Use DRF serializers for validation.
- Return appropriate HTTP status codes.
- Keep views thin.

## Migrations
- Always generate migrations.
- Never edit applied migrations unless explicitly requested.
