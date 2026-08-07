---
name: django-views
description: Use when implementing DRF APIView/generic views or endpoint routes under `shop/views/` and `shop/urls.py`.
---

# Django Views

## Guidelines

- Prefer existing DRF `APIView` and generic-view patterns.
- Keep business logic outside views.
- Return proper HTTP status codes.
- Use serializers for validation.
- This project mostly uses `APIView`, `ListAPIView`, and `RetrieveAPIView` with explicit `path(...)` routes.
- Do not assume router/ViewSet wiring unless adding it intentionally.

## Project Example

```python
class ProductListView(generics.ListAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = ProductCardSerializer
    pagination_class = ProductPagination

    def get_queryset(self):
        return get_product_base_queryset().distinct()
```

## Checklist

- permissions
- queryset optimization
- serializer
- pagination
- filtering
- explicit URL path without trailing slash
