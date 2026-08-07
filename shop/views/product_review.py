from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from rest_framework import permissions, status
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Product
from ..serializers import (
    ProductReviewCreateSerializer,
    ProductReviewCreateResponseSerializer,
)
from ..services.review_images import ReviewImageUploadError
from ..services.reviews import create_product_review_with_images


class ProductReviewCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    parser_classes = [
        JSONParser,
        MultiPartParser,
        FormParser,
    ]

    @swagger_auto_schema(
        operation_description="Create product review",
        request_body=ProductReviewCreateSerializer,
        responses={
            201: ProductReviewCreateResponseSerializer,
            400: "Bad Request",
            401: "Unauthorized",
            404: "Product not found",
            503: "Image upload failed",
        },
    )
    def post(self, request, product_id):
        product = get_object_or_404(
            Product,
            id=product_id,
            is_active=True,
        )

        serializer = ProductReviewCreateSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)

        images = request.FILES.getlist("images")

        try:
            review = create_product_review_with_images(
                user=request.user,
                product=product,
                review_data=serializer.validated_data,
                images=images,
            )
        except DjangoValidationError as exc:
            raise DRFValidationError(
                {
                    "images": exc.messages,
                }
            ) from exc
        except ReviewImageUploadError as exc:
            return Response(
                {
                    "detail": str(exc),
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(
            {
                "id": str(review.id),
                "moderation_status": review.moderation_status,
            },
            status=status.HTTP_201_CREATED,
        )
