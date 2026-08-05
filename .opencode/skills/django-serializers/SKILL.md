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

## Template

```python
from rest_framework import serializers


class ExampleSerializer(serializers.ModelSerializer):

    class Meta:
        model = ExampleModel
        fields = "__all__"

    def validate(self, attrs):
        return attrs
```

## Checklist

- validation
- read_only_fields
- write_only_fields
- nested serializers only when necessary