---
name: django-serializers
description: Use when creating or modifying DRF serializers.
---

# Django REST Framework Serializers

## Guidelines

- Prefer `ModelSerializer`.
- Validate inside serializers.
- Keep views thin.
- Use `validate_<field>()` or `validate()`.
- Prefer explicit `fields = [...]` over `fields = "__all__"`.
- Use `SerializerMethodField` for translated/read-only computed fields when needed.

## Project Example

```python
def validate_name(self, value):
    value = value.strip()

    if not value:
        raise serializers.ValidationError(_("Name is required."))

    return value
```

## Checklist

- validation
- read_only_fields
- write_only_fields
- nested serializers only when necessary
