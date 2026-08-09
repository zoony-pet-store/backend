import cloudinary.uploader
from django import forms
from django.utils.html import format_html

from ..models import MediaAsset, ProductAttribute, ProductImage


CLOUDINARY_PRODUCT_IMAGES_FOLDER = "zoony/product-images"


def image_preview(image_url, height=60):
    if image_url:
        return format_html(
            '<img src="{}" style="height:{}px; border-radius:8px; object-fit:cover;" />',
            image_url,
            height,
        )
    return "-"


def upload_image_to_cloudinary(uploaded_file):
    try:
        return cloudinary.uploader.upload(
            uploaded_file,
            folder=CLOUDINARY_PRODUCT_IMAGES_FOLDER,
            resource_type="image",
        )
    except Exception as error:
        raise forms.ValidationError(
            {"upload_file": f"Image upload failed: {error}"}
        ) from error


def create_media_asset_from_upload(uploaded_file, alt_text=""):
    upload_result = upload_image_to_cloudinary(uploaded_file)

    image_url = upload_result.get("secure_url") or upload_result.get("url")
    public_id = upload_result.get("public_id", "")

    if not image_url:
        raise forms.ValidationError(
            {"upload_file": "Cloudinary did not return image URL."}
        )

    return MediaAsset.objects.create(
        title=uploaded_file.name,
        image_url=image_url,
        alt_text=alt_text,
        cloudinary_public_id=public_id,
        source=MediaAsset.SOURCE_CLOUDINARY,
        is_active=True,
    )


def get_or_create_media_asset_from_url(
    image_url,
    alt_text="",
    cloudinary_public_id="",
):
    if not image_url:
        return None

    source = (
        MediaAsset.SOURCE_CLOUDINARY
        if cloudinary_public_id
        else MediaAsset.SOURCE_EXTERNAL
    )

    asset, created = MediaAsset.objects.get_or_create(
        image_url=image_url,
        defaults={
            "title": alt_text or image_url.rstrip("/").split("/")[-1][:255],
            "alt_text": alt_text,
            "cloudinary_public_id": cloudinary_public_id or "",
            "source": source,
            "is_active": True,
        },
    )

    update_fields = []

    if alt_text and not asset.alt_text:
        asset.alt_text = alt_text
        update_fields.append("alt_text")

    if cloudinary_public_id and not asset.cloudinary_public_id:
        asset.cloudinary_public_id = cloudinary_public_id
        asset.source = MediaAsset.SOURCE_CLOUDINARY
        update_fields.extend(["cloudinary_public_id", "source"])

    if not asset.is_active:
        asset.is_active = True
        update_fields.append("is_active")

    if update_fields:
        asset.save(update_fields=update_fields)

    return asset


def unset_other_main_images(image):
    if not image.is_main or not image.product_id:
        return

    if image.variant_id:
        ProductImage.objects.filter(
            product=image.product,
            variant=image.variant,
            is_main=True,
        ).exclude(pk=image.pk).update(is_main=False)
    else:
        ProductImage.objects.filter(
            product=image.product,
            variant__isnull=True,
            is_main=True,
        ).exclude(pk=image.pk).update(is_main=False)


def sync_product_variants_auto_badges(product):
    variants = product.variants.all().prefetch_related("badges")

    for variant in variants:
        variant.sync_auto_price_badges()


def get_unit_choices_for_attribute(attribute=None):
    unit_choices = list(ProductAttribute.UNIT_CHOICES)

    if (
        attribute
        and attribute.type == ProductAttribute.AttributeType.NUMERIC
        and attribute.available_units
    ):
        allowed_units = set(attribute.available_units)
        unit_choices = [
            (unit, label) for unit, label in unit_choices if unit in allowed_units
        ]

    return [("", "---------")] + unit_choices
