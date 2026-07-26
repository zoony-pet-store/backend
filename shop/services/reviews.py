from collections.abc import Sequence

from django.core.files.uploadedfile import UploadedFile
from django.db import transaction

from shop.models import Customer, Product
from shop.models.product_review import (
    ProductReview,
    ProductReviewImage,
)
from shop.services.review_images import (
    delete_review_image_from_cloudinary,
    upload_review_image_to_cloudinary,
)
from shop.validators.review_images import validate_review_images


def create_product_review_with_images(
    *,
    user: Customer,
    product: Product,
    review_data: dict,
    images: Sequence[UploadedFile],
) -> ProductReview:
    images = validate_review_images(list(images))

    uploaded_public_ids: list[str] = []

    try:
        with transaction.atomic():
            review = ProductReview.objects.create(
                user=user,
                product=product,
                **review_data,
            )

            for position, image in enumerate(images):
                upload_data = upload_review_image_to_cloudinary(
                    image,
                    review_id=review.id,
                )

                uploaded_public_ids.append(upload_data["cloudinary_public_id"])

                ProductReviewImage.objects.create(
                    review=review,
                    position=position,
                    **upload_data,
                )

            return review

    except Exception:
        for public_id in uploaded_public_ids:
            delete_review_image_from_cloudinary(public_id)

        raise
