from django.contrib import admin, messages
from django.db.models import Count
from django.utils.html import format_html
from unfold.admin import ModelAdmin, TabularInline

from ..models.product_review import (
    ProductReview,
    ProductReviewImage,
    ReviewImageModerationStatus,
)


class ProductReviewImageInline(TabularInline):
    """Review images displayed inside ProductReview admin."""

    model = ProductReviewImage

    extra = 0
    max_num = 5
    can_delete = True
    show_change_link = True

    fields = (
        "preview",
        "moderation_status",
        "position",
        "file_format",
        "file_size_display",
        "dimensions",
        "created_at",
    )

    readonly_fields = (
        "preview",
        "file_format",
        "file_size_display",
        "dimensions",
        "created_at",
    )

    ordering = (
        "position",
        "created_at",
    )

    def has_add_permission(self, request, obj=None):
        """
        Review images must be uploaded through the API.

        Admin users can moderate, reorder and delete existing images,
        but cannot manually create them without a Cloudinary upload.
        """
        return False

    @admin.display(description="Preview")
    def preview(self, obj):
        if not obj or not obj.secure_url:
            return "—"

        return format_html(
            (
                '<a href="{}" target="_blank" rel="noopener noreferrer">'
                '<img src="{}" '
                'style="width: 90px; height: 90px; '
                'object-fit: cover; border-radius: 8px;" />'
                "</a>"
            ),
            obj.secure_url,
            obj.secure_url,
        )

    @admin.display(description="File size")
    def file_size_display(self, obj):
        if not obj or obj.file_size_bytes is None:
            return "—"

        size_mb = obj.file_size_bytes / (1024 * 1024)

        return f"{size_mb:.2f} MB"

    @admin.display(description="Dimensions")
    def dimensions(self, obj):
        if not obj:
            return "—"

        return f"{obj.width_px} × {obj.height_px} px"


@admin.register(ProductReview)
class ProductReviewAdmin(ModelAdmin):
    list_display = (
        "product",
        "user",
        "rating",
        "is_verified",
        "is_active",
        "image_count",
        "created_at",
    )

    list_select_related = (
        "product",
        "user",
    )

    list_filter = (
        "is_active",
        "is_verified",
        "rating",
        "created_at",
    )

    search_fields = (
        "product__name",
        "user__email",
        "title",
        "comment",
        "positive_comment",
        "negative_comment",
    )

    autocomplete_fields = (
        "product",
        "user",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    date_hierarchy = "created_at"
    ordering = ("-created_at",)

    actions = (
        "activate_reviews",
        "deactivate_reviews",
    )

    inlines = (ProductReviewImageInline,)

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
                "fields": (
                    "created_at",
                    "updated_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .annotate(
                admin_image_count=Count("images"),
            )
        )

    @admin.display(
        description="Images",
        ordering="admin_image_count",
    )
    def image_count(self, obj):
        return obj.admin_image_count

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


@admin.register(ProductReviewImage)
class ProductReviewImageAdmin(ModelAdmin):
    """Separate moderation page for all review images."""

    list_display = (
        "preview",
        "review",
        "product_name",
        "moderation_status",
        "position",
        "file_format",
        "file_size_display",
        "created_at",
    )

    list_display_links = ("review",)

    list_editable = (
        "moderation_status",
        "position",
    )

    list_filter = (
        "moderation_status",
        "file_format",
        "created_at",
    )

    search_fields = (
        "review__product__name",
        "review__user__email",
        "review__title",
        "cloudinary_public_id",
    )

    readonly_fields = (
        "id",
        "review",
        "preview",
        "cloudinary_asset_id",
        "cloudinary_public_id",
        "secure_url",
        "file_size_bytes",
        "file_format",
        "width_px",
        "height_px",
        "created_at",
        "updated_at",
    )

    fieldsets = (
        (
            "Moderation",
            {
                "fields": (
                    "review",
                    "preview",
                    "moderation_status",
                    "position",
                ),
            },
        ),
        (
            "Image information",
            {
                "fields": (
                    "id",
                    "secure_url",
                    "file_size_bytes",
                    "file_format",
                    "width_px",
                    "height_px",
                    "created_at",
                    "updated_at",
                ),
            },
        ),
        (
            "Cloudinary information",
            {
                "fields": (
                    "cloudinary_asset_id",
                    "cloudinary_public_id",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    ordering = ("-created_at",)

    date_hierarchy = "created_at"

    actions = (
        "approve_selected_images",
        "reject_selected_images",
        "mark_selected_images_as_pending",
    )

    def has_add_permission(self, request):
        """
        Images must be uploaded through the product review API.
        """
        return False

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related(
                "review",
                "review__product",
                "review__user",
            )
        )

    @admin.display(description="Preview")
    def preview(self, obj):
        if not obj or not obj.secure_url:
            return "—"

        return format_html(
            (
                '<a href="{}" target="_blank" rel="noopener noreferrer">'
                '<img src="{}" '
                'style="width: 70px; height: 70px; '
                'object-fit: cover; border-radius: 8px;" />'
                "</a>"
            ),
            obj.secure_url,
            obj.secure_url,
        )

    @admin.display(
        description="Product",
        ordering="review__product__name",
    )
    def product_name(self, obj):
        return obj.review.product.name

    @admin.display(description="File size")
    def file_size_display(self, obj):
        if obj.file_size_bytes is None:
            return "—"

        size_mb = obj.file_size_bytes / (1024 * 1024)

        return f"{size_mb:.2f} MB"

    @admin.action(description="Approve selected images")
    def approve_selected_images(self, request, queryset):
        updated = queryset.update(
            moderation_status=ReviewImageModerationStatus.APPROVED,
        )

        self.message_user(
            request,
            f"{updated} image(s) approved.",
            level=messages.SUCCESS,
        )

    @admin.action(description="Reject selected images")
    def reject_selected_images(self, request, queryset):
        updated = queryset.update(
            moderation_status=ReviewImageModerationStatus.REJECTED,
        )

        self.message_user(
            request,
            f"{updated} image(s) rejected.",
            level=messages.WARNING,
        )

    @admin.action(description="Mark selected images as pending")
    def mark_selected_images_as_pending(self, request, queryset):
        updated = queryset.update(
            moderation_status=ReviewImageModerationStatus.PENDING,
        )

        self.message_user(
            request,
            f"{updated} image(s) marked as pending.",
            level=messages.INFO,
        )
