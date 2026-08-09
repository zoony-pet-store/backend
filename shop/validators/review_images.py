from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from PIL import Image, UnidentifiedImageError


MAX_REVIEW_IMAGE_COUNT = 5
MAX_REVIEW_IMAGE_SIZE_BYTES = 5 * 1024 * 1024

ALLOWED_REVIEW_IMAGE_EXTENSIONS = {
    "jpg",
    "jpeg",
    "png",
    "webp",
}

ALLOWED_REVIEW_IMAGE_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
}

ALLOWED_REVIEW_IMAGE_FORMATS = {
    "JPEG",
    "PNG",
    "WEBP",
}


def validate_review_images(
    images: list[UploadedFile],
) -> list[UploadedFile]:
    images = list(images)

    if len(images) > MAX_REVIEW_IMAGE_COUNT:
        raise ValidationError(
            f"A review can contain no more than " f"{MAX_REVIEW_IMAGE_COUNT} images."
        )

    for image in images:
        validate_review_image(image)

    return images


def validate_review_image(image: UploadedFile) -> None:
    if image.size == 0:
        raise ValidationError(f'Image "{image.name}" is empty.')

    if image.size > MAX_REVIEW_IMAGE_SIZE_BYTES:
        raise ValidationError(f'Image "{image.name}" exceeds the maximum size of 5 MB.')

    extension = Path(image.name).suffix.lower().lstrip(".")

    if extension not in ALLOWED_REVIEW_IMAGE_EXTENSIONS:
        raise ValidationError(
            f'Image "{image.name}" has an unsupported file extension.'
        )

    if image.content_type not in ALLOWED_REVIEW_IMAGE_CONTENT_TYPES:
        raise ValidationError(f'Image "{image.name}" has an unsupported content type.')

    try:
        image.seek(0)

        with Image.open(image) as opened_image:
            actual_format = opened_image.format
            opened_image.verify()

    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ValidationError(f'File "{image.name}" is not a valid image.') from exc
    finally:
        image.seek(0)

    if actual_format not in ALLOWED_REVIEW_IMAGE_FORMATS:
        raise ValidationError(f'Image "{image.name}" has an unsupported file format.')
