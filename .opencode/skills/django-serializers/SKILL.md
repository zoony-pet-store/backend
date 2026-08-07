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
class ProductReviewCreateSerializer(serializers.ModelSerializer):
    rating = serializers.IntegerField(min_value=1, max_value=5)
    comment = serializers.CharField(required=True, allow_blank=False, min_length=1)

    class Meta:
        model = ProductReview
        fields = ["rating", "title", "comment", "positive_comment", "negative_comment"]

    def validate_comment(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError(_("Comment is required."))
        return value
```

## Checklist

- validation
- read_only_fields
- write_only_fields
- nested serializers only when necessary
