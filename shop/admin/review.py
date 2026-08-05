from django import forms
from django.contrib import admin, messages
from django.db.models import Count
from django.utils.html import format_html
from unfold.admin import ModelAdmin, TabularInline

from ..models.product_review import (
    ProductReview,
    ProductReviewImage,
    ReviewModerationStatus,
    ReviewImageModerationStatus,
)
from ..services.reviews import update_product_review_stats


class ProductReviewImageInline(TabularInline):
    """Review images displayed inside ProductReview admin."""

    model = ProductReviewImage
    verbose_name = "Review image"
    verbose_name_plural = "Review images"

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


class ProductReviewAdminForm(forms.ModelForm):
    class Meta:
        model = ProductReview
        fields = "__all__"
        widgets = {
            "rejection_reason": forms.Textarea(
                attrs={
                    "class": "review-rejection-reason-autogrow",
                    "data-max-rows": "7",
                    "rows": 2,
                }
            ),
        }


@admin.register(ProductReview)
class ProductReviewAdmin(ModelAdmin):
    form = ProductReviewAdminForm

    class Media:
        css = {
            "all": (
                "shop/admin/css/review_admin.css",
            ),
        }
        js = (
            "shop/admin/js/review_rejection_reason.js",
        )

    list_display = (
        "reviewer_name",
        "product",
        "rating_display",
        "moderation_status",
        "image_count",
        "created_at",
    )

    list_select_related = (
        "product",
        "user",
    )

    list_filter = (
        "moderation_status",
        "created_at",
    )

    search_fields = (
        "product__name",
        "user__email",
        "reviewer_name",
        "reviewer_email",
        "title",
        "comment",
        "positive_comment",
        "negative_comment",
    )

    list_editable = (
        "moderation_status",
    )

    autocomplete_fields = (
        "product",
        "user",
    )

    readonly_fields = (
        "product",
        "user",
        "reviewer_name",
        "reviewer_email",
        "rating_display",
        "rating_score",
        "is_verified",
        "is_active",
        "title",
        "comment",
        "positive_comment",
        "negative_comment",
        "created_at",
        "updated_at",
    )

    date_hierarchy = "created_at"
    ordering = ("-created_at",)

    actions = (
        "approve_selected_reviews",
        "reject_selected_reviews",
    )

    inlines = (ProductReviewImageInline,)

    fieldsets = (
        (
            "Moderation",
            {
                "fields": (
                    "moderation_status",
                    "rejection_reason",
                )
            },
        ),
        (
            "Review content",
            {
                "fields": (
                    "product",
                    "user",
                    "reviewer_name",
                    "reviewer_email",
                    "rating_display",
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
                    "is_verified",
                    "is_active",
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

    @admin.display(description="Rating", ordering="rating_score")
    def rating_display(self, obj):
        rating = obj.rating_score / 2

        if rating.is_integer():
            rating = int(rating)

        return f"{rating} / 5"

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def _update_related_product_stats(self, queryset):
        product_ids = list(queryset.values_list("product_id", flat=True).distinct())
        self._update_product_stats_by_ids(product_ids)

    def _update_product_stats_by_ids(self, product_ids):
        product_model = ProductReview._meta.get_field("product").related_model

        for product in product_model.objects.filter(id__in=product_ids):
            update_product_review_stats(product)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        update_product_review_stats(obj.product)

    def delete_model(self, request, obj):
        product_id = obj.product_id
        super().delete_model(request, obj)
        self._update_product_stats_by_ids([product_id])

    def delete_queryset(self, request, queryset):
        product_ids = list(queryset.values_list("product_id", flat=True).distinct())
        super().delete_queryset(request, queryset)
        self._update_product_stats_by_ids(product_ids)

    @admin.action(description="Approve selected reviews")
    def approve_selected_reviews(self, request, queryset):
        updated = queryset.update(
            moderation_status=ReviewModerationStatus.APPROVED,
            rejection_reason=None,
        )
        self._update_related_product_stats(queryset)

        self.message_user(
            request,
            f"{updated} review(s) approved.",
            level=messages.SUCCESS,
        )

    @admin.action(description="Reject selected reviews")
    def reject_selected_reviews(self, request, queryset):
        updated = queryset.update(
            moderation_status=ReviewModerationStatus.REJECTED,
        )
        self._update_related_product_stats(queryset)

        self.message_user(
            request,
            f"{updated} review(s) rejected.",
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
