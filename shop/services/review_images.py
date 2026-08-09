import logging
from typing import TypedDict
from uuid import UUID

import cloudinary.uploader
from django.core.files.uploadedfile import UploadedFile


logger = logging.getLogger(__name__)

SUCCESSFUL_DELETE_RESULTS = {"ok", "not found"}

REVIEW_IMAGES_FOLDER = "user-content/reviews"


class ReviewImageUploadResult(TypedDict):
    cloudinary_asset_id: str
    cloudinary_public_id: str
    secure_url: str
    file_size_bytes: int
    file_format: str
    width_px: int
    height_px: int


class ReviewImageUploadError(Exception):
    """Raised when uploading a review image fails."""


def upload_review_image_to_cloudinary(
    image: UploadedFile,
    *,
    review_id: UUID,
) -> ReviewImageUploadResult:
    """Upload a validated product review image to Cloudinary."""

    try:
        result = cloudinary.uploader.upload(
            image,
            resource_type="image",
            folder=f"{REVIEW_IMAGES_FOLDER}/{review_id}",
            use_filename=False,
            overwrite=False,
        )
    except Exception as exc:
        logger.exception(
            "Failed to upload review image to Cloudinary: %s",
            image.name,
        )

        raise ReviewImageUploadError(f'Failed to upload image "{image.name}".') from exc

    required_fields = {
        "asset_id",
        "public_id",
        "secure_url",
        "bytes",
        "format",
        "width",
        "height",
    }

    missing_fields = required_fields.difference(result)

    if missing_fields:
        public_id = result.get("public_id")

        if public_id:
            delete_review_image_from_cloudinary(public_id)

        logger.error(
            "Incomplete Cloudinary response. Missing fields: %s",
            sorted(missing_fields),
        )

        raise ReviewImageUploadError("Cloudinary returned incomplete image data.")

    return {
        "cloudinary_asset_id": str(result["asset_id"]),
        "cloudinary_public_id": str(result["public_id"]),
        "secure_url": str(result["secure_url"]),
        "file_size_bytes": int(result["bytes"]),
        "file_format": str(result["format"]).lower(),
        "width_px": int(result["width"]),
        "height_px": int(result["height"]),
    }


def delete_review_image_from_cloudinary(
    cloudinary_public_id: str,
) -> None:
    """Delete a product review image from Cloudinary."""

    try:
        result = cloudinary.uploader.destroy(
            cloudinary_public_id,
            resource_type="image",
            invalidate=True,
        )
    except Exception:
        logger.exception(
            "Failed to delete review image from Cloudinary: %s",
            cloudinary_public_id,
        )
        return

    deletion_result = result.get("result")

    if deletion_result not in SUCCESSFUL_DELETE_RESULTS:
        logger.error(
            "Unexpected Cloudinary deletion result for %s: %s",
            cloudinary_public_id,
            result,
        )
