from collections.abc import Sequence
from decimal import Decimal

from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django.db.models import Avg, Count

from shop.models import Customer, Product
from shop.models.product_review import (
    ProductReview,
    ProductReviewImage,
    ReviewModerationStatus,
)
from shop.services.review_images import (
    delete_review_image_from_cloudinary,
    upload_review_image_to_cloudinary,
)
from shop.validators.review_images import validate_review_images


def update_product_review_stats(product: Product) -> None:
    stats = product.reviews.filter(
        is_active=True,
        moderation_status=ReviewModerationStatus.APPROVED,
    ).aggregate(
        avg_rating_score=Avg("rating_score"),
        review_count=Count("id"),
    )

    avg_rating_score = stats["avg_rating_score"]
    product.rating = Decimal(str(avg_rating_score or 0)) / Decimal("2")
    product.review_count = stats["review_count"] or 0
    product.save(update_fields=["rating", "review_count"])


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
