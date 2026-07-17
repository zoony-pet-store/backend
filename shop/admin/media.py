from django.contrib import admin, messages
from unfold.admin import ModelAdmin

from ..models import MediaAsset, ProductImage
from .forms import MediaAssetAdminForm, ProductImageAdminForm
from .helpers import (
    get_or_create_media_asset_from_url,
    image_preview,
    unset_other_main_images,
)


@admin.register(MediaAsset)
class MediaAssetAdmin(ModelAdmin):
    form = MediaAssetAdminForm

    list_display = (
        "preview",
        "title",
        "source",
        "is_active",
        "cloudinary_public_id",
        "created_at",
    )
    list_filter = ("source", "is_active", "created_at")
    search_fields = ("title", "alt_text", "image_url", "cloudinary_public_id")
    readonly_fields = ("preview", "created_at", "updated_at")
    ordering = ("-created_at", "title")

    fields = (
        "upload_file",
        "title",
        "image_url",
        "alt_text",
        "cloudinary_public_id",
        "source",
        "is_active",
        "preview",
        "created_at",
        "updated_at",
    )

    def preview(self, obj):
        return image_preview(obj.image_url, height=80)

    preview.short_description = "Preview"


@admin.register(ProductImage)
class ProductImageAdmin(ModelAdmin):
    form = ProductImageAdminForm

    list_display = (
        "product",
        "variant",
        "asset",
        "is_main",
        "display_order",
        "cloudinary_public_id",
        "preview",
    )
    list_select_related = ("product", "variant", "asset")
    list_filter = ("is_main", "asset__source")
    autocomplete_fields = (
        "product",
        "variant",
    )
    search_fields = (
        "product__name",
        "variant__sku",
        "asset__title",
        "alt_text",
        "image_url",
        "cloudinary_public_id",
    )
    readonly_fields = ("preview",)
    fields = (
        "product",
        "variant",
        "upload_file",
        "asset",
        "image_url",
        "alt_text",
        "is_main",
        "display_order",
        "cloudinary_public_id",
        "preview",
    )
    ordering = ("product", "variant", "display_order", "id")
    actions = ("link_selected_images_to_media_assets",)

    def preview(self, obj):
        return image_preview(obj.image_url, height=60)

    preview.short_description = "Preview"

    def save_model(self, request, obj, form, change):
        unset_other_main_images(obj)
        super().save_model(request, obj, form, change)

    @admin.action(description="Create/link Media assets for selected product images")
    def link_selected_images_to_media_assets(self, request, queryset):
        linked = 0
        skipped = 0

        for image in queryset:
            if not image.image_url:
                skipped += 1
                continue

            asset = get_or_create_media_asset_from_url(
                image_url=image.image_url,
                alt_text=image.alt_text,
                cloudinary_public_id=image.cloudinary_public_id,
            )

            if asset and image.asset_id != asset.id:
                image.asset = asset
                image.save(update_fields=["asset"])
                linked += 1
            else:
                skipped += 1

        self.message_user(
            request,
            f"Linked images: {linked}. Skipped: {skipped}.",
            level=messages.SUCCESS,
        )
