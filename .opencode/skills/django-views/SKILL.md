---
name: django-views
description: Use when implementing DRF views or endpoints.
---

# Django Views

## Guidelines

- Prefer DRF generic views or ViewSets.
- Keep business logic outside views.
- Return proper HTTP status codes.
- Use serializers for validation.

## Template

```python
from rest_framework.viewsets import ModelViewSet


class ExampleViewSet(ModelViewSet):
    queryset = ExampleModel.objects.all()
    serializer_class = ExampleSerializer
```

## Checklist

- permissions
- queryset optimization
- serializer
- pagination
- filtering