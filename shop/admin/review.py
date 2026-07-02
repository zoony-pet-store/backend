from django.contrib import admin, messages
from unfold.admin import ModelAdmin

from ..models import ProductReview


@admin.register(ProductReview)
class ProductReviewAdmin(ModelAdmin):
    list_display = (
        "product",
        "user",
        "rating",
        "is_verified",
        "is_active",
        "created_at",
    )
    list_select_related = ("product", "user")
    list_filter = ("is_active", "is_verified", "rating", "created_at")
    search_fields = (
        "product__name",
        "user__email",
        "title",
        "comment",
        "positive_comment",
        "negative_comment",
    )
    autocomplete_fields = ("product", "user")
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    actions = ("activate_reviews", "deactivate_reviews")

    fieldsets = (
        (
            "Review",
            {
                "fields": (
                    "product",
                    "user",
                    "rating",
                    "is_verified",
                    "is_active",
                    "title",
                    "comment",
                    "positive_comment",
                    "negative_comment",
                )
            },
        ),
        (
            "Service info",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    @admin.action(description="Activate selected reviews")
    def activate_reviews(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(
            request,
            f"{updated} review(s) activated.",
            level=messages.SUCCESS,
        )

    @admin.action(description="Deactivate selected reviews")
    def deactivate_reviews(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(
            request,
            f"{updated} review(s) deactivated.",
            level=messages.WARNING,
        )
